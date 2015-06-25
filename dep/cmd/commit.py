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
    flags = vars(args)
    root.foreach_dependency(["git", "add", "--all", "."], flags)
    flags.update(foreach_record=True, foreach_only_modified=True)
    root.foreach_dependency(["git", "commit"] + opts.rest_args, flags)

parser_commit = opts.subparsers.add_parser("commit",
                                      help="Commit changes for each dependency",
                                      description="Commit changes for each dependency")
add_list_arguments(parser_commit)
parser_commit.set_defaults(func=command_commit)
opts.allow_rest.append("commit")
