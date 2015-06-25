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
    root.foreach_dependency(opts.rest_args, vars(args))

parser_foreach = opts.subparsers.add_parser("foreach",
                                            help="Run a shell command for each dependency",
                                            description="Run a shell command for each dependency.")
parser_foreach.add_argument("--record", dest="foreach_record", action="store_true",
                           help="Run record operation after each command run")
parser_foreach.add_argument("--refresh", dest="foreach_refresh", action="store_true",
                           help="Run refresh operation after each command run")
parser_foreach.add_argument("--only-modified", dest="foreach_only_modified", action="store_true",
                           help="Run command only on repositories with local modifications")
add_list_arguments(parser_foreach)
parser_foreach.set_defaults(func=command_foreach)
opts.allow_rest.append("foreach")
