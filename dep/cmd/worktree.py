#
# Worktree Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_worktree(args):
    tree = dependency.Tree()
    tree.worktree_dependency_tree(args.branch)
    
parser_worktree = opts.subparsers.add_parser("worktree",
                                      help="Create a worktree for all dependencies",
                                      description="Create a worktree for all dependencies. Creates the worktree under branch/BRANCH.")
add_list_arguments(parser_worktree)
parser_worktree.add_argument("branch",
                             help="Name of branch of worktree to create, must exist")
parser_worktree.set_defaults(func=command_worktree)
