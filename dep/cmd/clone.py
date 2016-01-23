#
# Clone Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_clone(args):
    dependency.Tree.clone_dependency_tree(args.url, args.directory, vars(args))

parser_clone = opts.subparsers.add_parser("clone",
                                          help="Clone given URL then refresh children",
                                          description="Clone given URL then refresh children. Shortcut form for \"git clone\" followed by \"dep checkout\".")
add_local_arguments(parser_clone)
parser_clone.add_argument("-b", "--branch", dest="clone_branch",
                          help="Branch to checkout after clone, default is master.")
parser_clone.add_argument("-c", "--commit", dest="clone_commit",
                          help="Commit or tag to checkout after clone, default is head of branch.")
parser_clone.add_argument("url",
                          help="URL of repository to clone")
parser_clone.add_argument("directory", nargs="?",
                          help="Directory to clone into. Default derived from basename of URL.")
parser_clone.set_defaults(func=command_clone)
