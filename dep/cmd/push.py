#
# Push Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_push(args):
    root = comp.RootComponent()
    flags = vars(args)
    flags.update(foreach_only_ahead=True)
    root.foreach_dependency(["git", "push"] + opts.rest_args, flags)

parser_push = opts.subparsers.add_parser("push",
                                      help="Push changes for each dependency",
                                      description="Push changes for each dependency")
add_list_arguments(parser_push)
parser_push.set_defaults(func=command_push)
opts.allow_rest.append("push")
