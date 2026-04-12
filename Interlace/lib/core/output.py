from enum import IntEnum
from time import localtime, strftime

from Interlace.lib.core.__version__ import __version__

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class OutputHelper:
    def __init__(self, arguments=None):
        if arguments is not None:
            self._no_color = arguments.nocolor
            self.verbose = arguments.verbose
            self.silent = arguments.silent
            self.quiet = getattr(arguments, 'quiet', False)
        else:
            self._no_color = False
            self.verbose = False
            self.silent = False
            self.quiet = False
        self.separator = "====================================================="
        self._tqdm = None
    
    def set_tqdm(self, tqdm_instance):
        self._tqdm = tqdm_instance

    def print_banner(self):
        if self.silent or self.quiet:
            return

        print(self.separator)
        print("InterlaceX v%s" % __version__)
        print("  Original: Michael Skelton (@codingo_) & Sajeeb Lohani (@sml555_)")
        print("  Fork: Akash Sarkar (@0xhunster)")
        print(self.separator)

    def terminal(self, level, task_command, status, message=""):  # FIX BUG 7: renamed 'target' → 'task_command', 'command' → 'status' to match actual usage
        if level == 0 and not self.verbose:
            return

        if not self._no_color:
            formatting = {
                0: f'{bcolors.OKBLUE}[VERBOSE]{bcolors.ENDC}',
                1: f'{bcolors.OKGREEN}[THREAD]{bcolors.ENDC}',
                3: f'{bcolors.FAIL}[ERROR]{bcolors.ENDC}'
            }
        else:
            formatting = {
                0: '[VERBOSE]',
                1: '[THREAD]',
                3: '[ERROR]'
            }

        leader = formatting.get(level, '[#]')

        format_args = {
            'time': strftime("%H:%M:%S", localtime()),
            'task_command': task_command,  # FIX BUG 7: renamed from 'target'
            'status': status,  # FIX BUG 7: renamed from 'command'
            'message': message,
            'leader': leader
        }

        # Quiet mode suppresses all output
        # Silent mode suppresses thread info but allows error messages
        if self.quiet:
            return
        if self.silent and level != Level.ERROR:
            return
            
        template = '[{time}] {leader} [{task_command}] {status} {message}'  # FIX BUG 7: updated template keys
        output_line = template.format(**format_args)
        
        # Use tqdm.write() if tqdm is active to prevent progress bar conflicts
        if self._tqdm is not None:
            self._tqdm.write(output_line)
        else:
            print(output_line)

class Level(IntEnum):
    """Enumeration for output verbosity levels."""
    VERBOSE = 0
    THREAD = 1
    ERROR = 3
