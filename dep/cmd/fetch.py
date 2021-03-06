#
# Fetch Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_fetch(args):
    tree = dependency.Tree()
    tree.foreach_dependency(["git", "fetch"] + opts.rest_args, vars(args))

parser_fetch = opts.subparsers.add_parser("fetch",
                                      help="Fetch changes for each dependency",
                                      description="Fetch changes for each dependency")
add_list_arguments(parser_fetch)
parser_fetch.set_defaults(func=command_fetch)
opts.allow_rest.append("fetch")
