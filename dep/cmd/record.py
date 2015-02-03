#
# Record Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_record(args):
    root = comp.RootComponent()
    root.record_dependencies()

parser_record = opts.subparsers.add_parser("record",
                                           help="Record dependencies from current source repository state",
                                           description="Record dependencies from current source repository state.")
parser_record.set_defaults(func=command_record)
