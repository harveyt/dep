#
# Foreach Command
# ===============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_foreach(args):
    root = comp.RootComponent()
    root.foreach_dependency(args.cmd)

parser_foreach = opts.subparsers.add_parser("foreach",
                                            help="Run a shell command for each dependency",
                                            description="Run a shell command for each dependency.")
parser_foreach.add_argument("cmd", action="append",
                            help="The command to run for each dependency")
parser_foreach.set_defaults(func=command_foreach)
