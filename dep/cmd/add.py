#
# Add Command
# ============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_add(args):
    tree = dependency.Tree()
    tree.add_dependency(args.url)

parser_add = opts.subparsers.add_parser("add",
                                        help="Add a new dependency to root dependency",
                                        description="Add a new dependency to root dependency.")
add_local_arguments(parser_add)
parser_add.add_argument("url",
                        help="The URL of the dependency's VCS repository")
parser_add.set_defaults(func=command_add)
