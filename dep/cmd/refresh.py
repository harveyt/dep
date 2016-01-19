#
# Refresh Command
# ===============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_refresh(args):
    tree = dependency.Tree()
    tree.refresh_dependency_tree()

parser_refresh = opts.subparsers.add_parser("refresh",
                                            help="Refresh dependencies from their source repositories",
                                            description="Refresh dependencies from their source repositories.")
parser_refresh.set_defaults(func=command_refresh)
