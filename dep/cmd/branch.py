#
# Branch Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_branch(args):
    root = comp.RootComponent()
    root.branch_dependencies(args.name, args.startpoint, vars(args))
    
parser_branch = opts.subparsers.add_parser("branch",
                                      help="Branch all dependencies to new branch",
                                      description="Branch all dependencies to new branch. Each dependency gets a new commit.")
add_list_arguments(parser_branch)
parser_branch.add_argument("name",
                           help="Name of branch to create, must not exist")
parser_branch.add_argument("startpoint", nargs="?",
                           help="Optional start point for each branch, should be a common tag")
parser_branch.set_defaults(func=command_branch)

