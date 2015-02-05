#
# Pull Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_pull(args):
    root = comp.RootComponent()
    root.foreach_dependency(["git", "pull"] + opts.rest_args)

parser_pull = opts.subparsers.add_parser("pull",
                                      help="Pull changes for each dependency",
                                      description="Pull changes for each dependency")
parser_pull.set_defaults(func=command_pull)
opts.allow_rest.append("pull")
