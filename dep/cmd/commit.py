#
# Commit Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_commit(args):
    tree = dependency.Tree()
    tree.commit_dependency_tree(opts.rest_args, vars(args))

parser_commit = opts.subparsers.add_parser("commit",
                                      help="Commit changes for each dependency",
                                      description="Commit changes for each dependency")
add_list_arguments(parser_commit)
parser_commit.set_defaults(func=command_commit)
opts.allow_rest.append("commit")
