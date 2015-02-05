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
    root.foreach_dependency(opts.rest_args)

parser_foreach = opts.subparsers.add_parser("foreach",
                                            help="Run a shell command for each dependency",
                                            description="Run a shell command for each dependency.")
parser_foreach.set_defaults(func=command_foreach)
opts.allow_rest.append("foreach")
