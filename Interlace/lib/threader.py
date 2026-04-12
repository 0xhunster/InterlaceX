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

class Task:
    """Represents a single command task to be executed."""
    def __init__(self, command, suppress_output=False):
        self.task = command
        self.self_lock = None
        self.sibling_locks = []
        self.suppress_output = suppress_output

    def __cmp__(self, other):
        return self.name() == other.name()

    def __hash__(self):
        return self.task.__hash__()

    def clone(self):
        """Create a copy of this task with same configuration."""
        new_task = Task(self.task, self.suppress_output)
        new_task.self_lock = self.self_lock
        new_task.sibling_locks = self.sibling_locks
        return new_task

    def replace(self, old, new):
        """Replace a substring in the command."""
        self.task = self.task.replace(old, new)

    def run(self, t=False, timeout=None):
        for lock in self.sibling_locks:
            lock.wait()
        self._run_task(t, timeout)
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
        """Get or create this task's lock for synchronization."""
        if not self.self_lock:
            self.self_lock = Event()
            self.self_lock.clear()
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
