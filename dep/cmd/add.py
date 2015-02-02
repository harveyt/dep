#
# Add Command
# ============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_add(args):
    root = comp.RootComponent()
    root.add_new_dependency(args.url)

parser_add = opts.subparsers.add_parser("add",
                                        help="Add a new dependency to this component",
                                        description="Add a new dependency to this component.")
parser_add.add_argument("url",
                        help="The URL of the dependant component's VCS repository")
parser_add.set_defaults(func=command_add)
