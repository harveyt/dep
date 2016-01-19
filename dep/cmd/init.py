#
# Init Command
# ============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_init(args):
    root_path = os.getcwd()
    tree = dependency.Tree(root_path)
    tree.init_dependency()

parser_init = opts.subparsers.add_parser("init",
                                         help="Initialise dependency system for this component",
                                         description="Initialise dependency system for this component.")
parser_init.set_defaults(func=command_init)
