#
# Tag Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_tag(args):
    tree = dependency.Tree()
    tree.foreach_dependency(["git", "tag"] + opts.rest_args, vars(args))

parser_tag = opts.subparsers.add_parser("tag",
                                      help="Tag each dependency",
                                      description="Tag each dependency.")
add_list_arguments(parser_tag)
parser_tag.set_defaults(func=command_tag)
opts.allow_rest.append("tag")
