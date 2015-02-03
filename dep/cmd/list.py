#
# List Command
# ============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_list(args):
    root = comp.RootComponent()
    root.list_dependencies()

parser_list = opts.subparsers.add_parser("list",
                                         help="List dependencies",
                                         description="List dependencies.")
parser_list.set_defaults(func=command_list)
