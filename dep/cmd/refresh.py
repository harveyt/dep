#
# Refresh Command
# ===============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_refresh(args):
    root = comp.RootComponent()
    root.refresh_dependencies()

parser_refresh = opts.subparsers.add_parser("refresh",
                                            help="Refresh dependencies from their source repositories",
                                            description="Refresh dependencies from their source repositories.")
parser_refresh.set_defaults(func=command_refresh)
