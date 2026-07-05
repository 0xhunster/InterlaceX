#!/usr/bin/python3
import sys
from sys import argv

from Interlace.lib.core.input import InputParser, InputHelper
from Interlace.lib.core.output import OutputHelper
from Interlace.lib.threader import Pool

def task_queue_generator_func(arguments, repeat):
    tasks_data = InputHelper.process_data_for_tasks_iterator(arguments)
    tasks_count = tasks_data["tasks_count"]
    yield tasks_count
    for i in range(repeat):
        # Each round gets its own copy of the template tasks so its
        # CloneGroup dependency graph is independent of every other round's
        # (see InputHelper.clone_template_tasks).
        round_tasks_data = {**tasks_data, "tasks": InputHelper.clone_template_tasks(tasks_data["tasks"])}
        tasks_generator_func = InputHelper.make_tasks_generator_func(round_tasks_data)
        for task in tasks_generator_func():
            yield task

def main():
    """Main entry point for InterlaceX."""
    from Interlace.lib.core.__version__ import __version__

    # Handle version check early, before full arg parsing
    if '-V' in argv or '--version' in argv:
        print(f'InterlaceX v{__version__}')
        return

    parser = InputParser()
    arguments = parser.parse(argv[1:])
    output = OutputHelper(arguments)

    # Hide banner in silent mode or when --no-bar is used
    if not arguments.sober:
        output.print_banner()

    repeat = arguments.repeat

    try:
        pool = Pool(
            arguments.threads,
            task_queue_generator_func(arguments, repeat),
            arguments.timeout,
            output,
            arguments.sober,
            quiet=getattr(arguments, 'quiet', False)
        )
        pool.run()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
