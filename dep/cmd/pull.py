#
# Pull Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_fetch(args):
    root = comp.RootComponent()
    root.foreach_dependency(["git", "fetch"])

parser_fetch = opts.subparsers.add_parser("fetch",
                                      help="Pull changes for each dependency",
                                      description="Pull changes for each dependency")
parser_fetch.set_defaults(func=command_fetch)
