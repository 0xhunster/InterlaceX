import subprocess
import os
import queue
import platform
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from tqdm import tqdm
from Interlace.lib.core.output import OutputHelper, Level

# Global shutdown flag for graceful termination
_shutdown_event = threading.Event()

def _signal_handler(signum, frame):
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    _shutdown_event.set()
    os._exit(1)

# Register signal handler
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# Determine shell based on platform
if platform.system().lower() == 'linux':
    shell = os.getenv("SHELL") if os.getenv("SHELL") else "/bin/sh"
else:
    shell = None

class CloneGroup:
    """
    Synchronization primitive shared by a template task and every clone
    produced from it via Task.clone() (once per target/port/proto/etc).

    Clones are tracked in a trie keyed by the actual (variable, value)
    substitution applied at each fan-out stage -- e.g. ("target", "a.com"),
    then ("_port_", "8080") for cascading fan-out -- so a dependent task can
    resolve the *specific* clone of its prerequisite that matches its own
    fan-out key (see Task.clone()/Task.run() for how keys are tracked, and
    find_deepest() below for how a dependent resolves them), giving
    independent per-target/per-port barriers instead of one global one.

    Each node's `pending` count reflects how many leaf completions are
    still outstanding *underneath it*, aggregated recursively through
    children via set()'s upward propagation -- not just its own direct
    completion. A node with no children behaves exactly like a flat
    counter: pending starts at 1 (for the un-cloned task) and set() fires
    its event once that single completion happens.
    """
    def __init__(self, parent=None):
        self._struct_lock = threading.Lock()
        self._pending = 1
        self._event = Event()
        self._children = {}
        self._parent = parent

    def add_clone(self, key_component, is_first_clone_of_self):
        """Register a newly created clone under a specific fan-out key.

        Returns the child CloneGroup the new clone should use as its own
        self_lock. `is_first_clone_of_self` retires this node's own
        reserved slot the first time it is cloned (superseded by its
        children); a new, never-seen key_component adds one outstanding
        slot to `self`. Reusing an existing key_component (e.g. a
        duplicate value in a replacements list) instead adds the extra
        slot directly to that child, so a stray double-registration can't
        leave an ancestor permanently short one decrement.
        """
        with self._struct_lock:
            if is_first_clone_of_self:
                self._pending -= 1
            child = self._children.get(key_component)
            is_new_child = child is None
            if is_new_child:
                child = CloneGroup(parent=self)
                self._children[key_component] = child
                self._pending += 1
        if not is_new_child:
            with child._struct_lock:
                child._pending += 1
        return child

    def find_deepest(self, key_path):
        """Walk this trie following key_path as far as matching children
        exist. Stops -- returning the deepest node reached -- as soon as
        the path runs out or the next component has no matching child,
        which is exactly right when the dependent's fan-out is narrower
        or wider than the prerequisite's: the coarsest common node is
        always the correct thing to wait on.
        """
        node = self
        for component in key_path:
            with node._struct_lock:
                child = node._children.get(component)
            if child is None:
                break
            node = child
        return node

    def set(self):
        """Called when one clone (or the un-cloned template) finishes
        running. Fires this node's event only once every clone
        registered under it has also finished, and propagates the
        completion up to the parent so ancestor nodes -- and anyone
        waiting on a coarser key -- resolve correctly too."""
        with self._struct_lock:
            self._pending -= 1
            just_finished = self._pending == 0
        if just_finished:
            self._event.set()
            if self._parent is not None:
                self._parent.set()

    def wait(self):
        self._event.wait()

class Task:
    """Represents a single command task to be executed."""
    def __init__(self, command, suppress_output=False):
        self.task = command
        self.self_lock = None
        self.sibling_locks = []
        self.suppress_output = suppress_output
        self._cloned = False
        # Ordered tuple of (variable, value) substitutions applied so far,
        # e.g. (("target", "a.com"), ("_port_", "8080")) -- used to resolve
        # which specific clone of a prerequisite this task depends on.
        self.fanout_key = ()

    def __cmp__(self, other):
        return self.name() == other.name()

    def __hash__(self):
        return self.task.__hash__()

    def clone(self, fanout_key_update=None):
        """Create a copy of this task with same configuration.

        `fanout_key_update` is the (variable, value) pair being applied by
        this clone (e.g. ("target", "a.com")), if any -- it extends the
        clone's fanout_key and, if something depends on this task, routes
        the clone into the matching child of this task's CloneGroup.
        """
        new_task = Task(self.task, self.suppress_output)
        new_task.sibling_locks = list(self.sibling_locks)
        if fanout_key_update is not None:
            new_task.fanout_key = self.fanout_key + (fanout_key_update,)
        else:
            new_task.fanout_key = self.fanout_key
        if self.self_lock is not None:
            new_task.self_lock = self.self_lock.add_clone(
                key_component=fanout_key_update,
                is_first_clone_of_self=not self._cloned,
            )
            self._cloned = True
        return new_task

    def replace(self, old, new):
        """Replace a substring in the command."""
        self.task = self.task.replace(old, new)

    def run(self, t=False, timeout=None):
        for root_lock in self.sibling_locks:
            root_lock.find_deepest(self.fanout_key).wait()
        try:
            self._run_task(t, timeout)
        finally:
            if self.self_lock:
                self.self_lock.set()

    def wait_for(self, siblings):
        """Add sibling tasks to wait for before execution."""
        for sibling in siblings:
            self.sibling_locks.append(sibling.get_lock())

    def name(self):
        """Return the command string."""
        return self.task

    def get_lock(self):
        """Get or create this task's root CloneGroup for synchronization."""
        if not self.self_lock:
            self.self_lock = CloneGroup()
        return self.self_lock

    def _run_task(self, t=False, timeout=None):
        """Internal method to execute the command."""
        if self.suppress_output:
            s = subprocess.Popen(
                self.task,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                executable=shell
            )
            try:
                s.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                s.kill()
                s.communicate()
            return
        else:
            s = subprocess.Popen(
                self.task,
                shell=True,
                stdout=subprocess.PIPE,
                executable=shell
            )
            try:
                out_bytes, _ = s.communicate(timeout=timeout)
                out = out_bytes.decode('utf-8', errors='replace') if out_bytes else ""
            except subprocess.TimeoutExpired:
                s.kill()
                s.communicate()
                return

        if out != "":
            if t:
                t.write(out)
            else:
                print(out, end='')

class Worker:
    """Worker that processes tasks from a queue."""
    def __init__(self, task_queue, timeout, tq, output_helper):
        self.queue = task_queue
        self.timeout = timeout
        self.tqdm = tq
        self.output_helper = output_helper

    def __call__(self):
        """Process tasks from queue until empty or shutdown requested."""
        while not _shutdown_event.is_set():
            try:
                task = self.queue.get(timeout=0.5)
            except queue.Empty:
                if self.queue.empty():
                    return
                continue

            self.output_helper.terminal(Level.THREAD, task.name(), "Added to Queue")

            try:
                if self.tqdm is not None:
                    task.run(self.tqdm, self.timeout)
                    self.tqdm.update(1)
                else:
                    task.run(timeout=self.timeout)
                self.output_helper.terminal(Level.VERBOSE, task.name(), "Completed")
            except Exception as e:
                if not _shutdown_event.is_set():
                    self.output_helper.terminal(Level.ERROR, task.name(), f"Task failed: {e}")

class Pool:
    """Thread pool for executing tasks concurrently."""

    def __init__(self, max_workers, task_queue, timeout, output_helper, hide_bar, quiet=False):
        max_workers = int(max_workers)
        tasks_count = next(task_queue)
        if not tasks_count:
            raise ValueError("The queue is empty")

        self.queue = queue.Queue()
        for task in task_queue:
            self.queue.put(task)

        self.timeout = timeout
        self.max_workers = min(tasks_count, max_workers)
        self.output_helper = output_helper if output_helper else OutputHelper()
        # Progress bar - hide in silent mode (clean output) or quiet mode (no output)
        silent = getattr(output_helper, 'silent', False) if output_helper else False
        if not hide_bar and not quiet and not silent:
            self.tqdm = tqdm(
                total=tasks_count,
                dynamic_ncols=True,
                leave=True,
                mininterval=0.1,
                file=sys.stderr,
                position=0
            )
            self.output_helper.set_tqdm(self.tqdm)
        else:
            self.tqdm = None

    def run(self):
        workers = [
            Worker(self.queue, self.timeout, self.tqdm, self.output_helper)
            for _ in range(self.max_workers)
        ]

        try:
            with ThreadPoolExecutor(self.max_workers) as executor:
                futures = [executor.submit(worker) for worker in workers]
                # Wait for completion or shutdown
                while not _shutdown_event.is_set():
                    if all(f.done() for f in futures):
                        break
                    _shutdown_event.wait(timeout=0.5)
        except KeyboardInterrupt:
            _shutdown_event.set()
        finally:
            if self.tqdm is not None:
                self.tqdm.close()
