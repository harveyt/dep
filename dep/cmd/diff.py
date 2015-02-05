#
# Diff Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_diff(args):
    root = comp.RootComponent()
    root.foreach_dependency(["git", "diff"] + opts.rest_args)

parser_diff = opts.subparsers.add_parser("diff",
                                      help="Diff changes for each dependency",
                                      description="Diff changes for each dependency")
parser_diff.set_defaults(func=command_diff)
opts.allow_rest.append("diff")