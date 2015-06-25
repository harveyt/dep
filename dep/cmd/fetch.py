#
# Fetch Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_fetch(args):
    root = comp.RootComponent()
    root.foreach_dependency(["git", "fetch"] + opts.rest_args, dict())

parser_fetch = opts.subparsers.add_parser("fetch",
                                      help="Fetch changes for each dependency",
                                      description="Fetch changes for each dependency")
parser_fetch.set_defaults(func=command_fetch)
opts.allow_rest.append("fetch")
