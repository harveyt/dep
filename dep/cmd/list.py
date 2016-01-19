#
# List Command
# ============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_list(args):
    tree = dependency.Tree()
    tree.list_dependency_tree(vars(args))

parser_list = opts.subparsers.add_parser("list",
                                         help="List dependencies",
                                         description="List dependencies.")
add_list_arguments(parser_list)
parser_list.set_defaults(func=command_list)
