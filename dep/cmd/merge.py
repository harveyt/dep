#
# Merge Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_merge(args):
    tree = dependency.Tree()
    tree.merge_dependency_tree(args.name, vars(args))
    
parser_merge = opts.subparsers.add_parser("merge",
                                          help="Merge all dependencies with given branch",
                                          description="Merge all dependencies with given branch.")
add_local_arguments(parser_merge)
parser_merge.add_argument("name",
                           help="Name of branch to merge, must exist")
parser_merge.set_defaults(func=command_merge)
