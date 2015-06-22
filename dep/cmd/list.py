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
parser_list.add_argument("--no-root", dest="list_root", action="store_false",
                         help="Do not include the root project in list of dependencies")
parser_list.add_argument("--root", dest="list_root", action="store_true",
                         help="Include the root project in list of dependencies")
parser_list.add_argument("--children", dest="list_children", action="store_true",
                         help="List only explicit child dependencies of the local working directory")
parser_list.add_argument("--implicit-children", dest="list_implicit_children", action="store_true",
                         help="List all explicit and implicit child dependencies of the local working directory")
parser_list.set_defaults(func=command_list)
