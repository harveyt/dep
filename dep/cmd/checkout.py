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
    tree.checkout_dependency_tree(opts.rest_args, vars(args))

parser_checkout = opts.subparsers.add_parser("checkout",
                                             help="Checkout current dependency, refresh children",
                                             description="Checkout current dependency, refresh children. Synonym for \"git checkout [args]\" followed by \"dep refresh\".")
add_local_arguments(parser_checkout)
parser_checkout.set_defaults(func=command_checkout)
opts.allow_rest.append("checkout")
