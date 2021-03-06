#
# Checkout Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_checkout(args):
    tree = dependency.Tree()
    tree.checkout_dependency_tree(args.name, args.startpoint, vars(args))

parser_checkout = opts.subparsers.add_parser("checkout",
                                             help="Checkout current dependency, refresh children",
                                             description="Checkout current dependency, refresh children. Shortcut for \"git checkout\" followed by \"dep refresh\".")
add_local_arguments(parser_checkout)
parser_checkout.add_argument("name",
                             help="Name of branch to checkout, must exist")
parser_checkout.add_argument("startpoint", nargs="?",
                             help="Optional start point to checkout, either tag or commit")
parser_checkout.set_defaults(func=command_checkout)
