#
# Status Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_status(args):
    tree = dependency.Tree()
    tree.status_dependency_tree(vars(args))
    
parser_status = opts.subparsers.add_parser("status",
                                           help="Show dependency status for all source repositories",
                                           description="Show dependency status for all source repositories.")
parser_status.add_argument("-s", "--short", dest="status_short", action="store_true",
                           help="Show short status only (default)")
parser_status.add_argument("--long", dest="status_long", action="store_true",
                           help="Show long status")
parser_status.add_argument("-d", "--describe", dest="status_describe", action="store_true",
                           help="Status output describes commits using tags (default on master)")
parser_status.add_argument("--commit", dest="status_commit", action="store_true",
                           help="Status shows full and unique commit (default on non-master)")
parser_status.add_argument("--exit", dest="status_exit", action="store_true",
                           help="Exit 0 if no changes under M, Branch or Commit. Exit 1 otherwise.")
parser_status.add_argument("--exit-only", dest="status_exit_only", action="store_true",
                           help="Only set exit status, no other output.")
add_list_arguments(parser_status)
parser_status.set_defaults(func=command_status)
