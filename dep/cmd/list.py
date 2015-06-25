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
                         help="Include the root project in list of dependencies (default)")
parser_list.add_argument("-t", "--top", dest="list_top", action="store_true",
                         help="Include all top explicit dependencies (default)")
parser_list.add_argument("-c", "--children", dest="list_children", action="store_true",
                         help="Include only explicit child dependencies of the local working directory")
parser_list.add_argument("-i", "--implicit-children", dest="list_implicit_children", action="store_true",
                         help="Include all explicit and implicit child dependencies of the local working directory")
parser_list.set_defaults(func=command_list)
