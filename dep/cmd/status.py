#
# Status Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_status(args):
    root = comp.RootComponent()
    root.status_dependencies()
    
parser_status = opts.subparsers.add_parser("status",
                                           help="Show dependency status for all source repositories",
                                           description="Show dependency status for all source repositories.")
parser_status.set_defaults(func=command_status)
