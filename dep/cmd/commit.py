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
    root.foreach_dependency(["git", "add", "--all", "."])
    root.foreach_dependency(["git", "commit"] + opts.rest_args,
                            record=True, only_modified=True)

parser_commit = opts.subparsers.add_parser("commit",
                                      help="Commit changes for each dependency",
                                      description="Commit changes for each dependency")
parser_commit.set_defaults(func=command_commit)
opts.allow_rest.append("commit")
