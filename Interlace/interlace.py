#!/usr/bin/python3
from sys import argv

from Interlace.lib.core.input import InputParser, InputHelper
from Interlace.lib.core.output import OutputHelper, Level
from Interlace.lib.threader import Pool


def task_queue_generator_func(arguments, output, repeat):
    tasks_data = InputHelper.process_data_for_tasks_iterator(arguments)
    tasks_count = tasks_data["tasks_count"]
    yield tasks_count
    tasks_generator_func = InputHelper.make_tasks_generator_func(tasks_data)
    for i in range(repeat):
        tasks_iterator = tasks_generator_func()
        for task in tasks_iterator:
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

    if arguments.repeat:
        repeat = int(arguments.repeat)
    else:
        repeat = 1

    pool = Pool(
        arguments.threads,
        task_queue_generator_func(arguments, output, repeat),
        arguments.timeout,
        output,
        arguments.sober,
        quiet=getattr(arguments, 'quiet', False)
    )
    pool.run()


if __name__ == "__main__":
    main()

