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
    root.foreach_dependency(["git", "push"] + opts.rest_args)

parser_push = opts.subparsers.add_parser("push",
                                      help="Push changes for each dependency",
                                      description="Push changes for each dependency")
parser_push.set_defaults(func=command_push)
opts.allow_rest.append("push")
