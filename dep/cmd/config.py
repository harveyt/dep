#
# Config Command
# ==============
#
# %%LICENSE%%
#
from dep import *
from dep.helpers import *

def command_config(args):
    if opts.args.work_dir:
        path = find_local_work_dir()
        if path is None:
            error("Cannot determine local working directory")
        print path
    if opts.args.root_work_dir:
        path = find_root_work_dir()
        if path is None:
            error("Cannot determine root working directory")
        print path

parser_config = opts.subparsers.add_parser("config",
                                           help="Dependency configuration",
                                           description="Dependency configuration.")
parser_config.add_argument("--work-dir", action="store_true",
                           help="Show the working directory of this dependency and exit")
parser_config.add_argument("--root-work-dir", action="store_true",
                           help="Show the working directory of the root dependency and exit")
parser_config.set_defaults(func=command_config)
