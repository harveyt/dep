#
# Pull Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_pull(args):
    tree = dependency.Tree()
    tree.foreach_dependency(["git", "pull"] + opts.rest_args, vars(args))

parser_pull = opts.subparsers.add_parser("pull",
                                      help="Pull changes for each dependency",
                                      description="Pull changes for each dependency")
add_list_arguments(parser_pull)
parser_pull.set_defaults(func=command_pull)
opts.allow_rest.append("pull")
