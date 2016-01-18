#
# Test Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_test(args):
    dependency.test_dependency(args.root)

parser_test = opts.subparsers.add_parser("test",
                                      help="Test each dependency",
                                      description="Test each dependency.")
# add_list_arguments(parser_test)
parser_test.set_defaults(func=command_test)
parser_test.add_argument("root",
                         help="Root path of dependency tree.")
# opts.allow_rest.append("test")
