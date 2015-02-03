#
# Commit Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_commit(args):
    root = comp.RootComponent()
    root.foreach_dependency(["git", "commit"])

parser_commit = opts.subparsers.add_parser("commit",
                                      help="Commit changes for each dependency",
                                      description="Commit changes for each dependency")
parser_commit.set_defaults(func=command_commit)
