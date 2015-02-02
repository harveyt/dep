# --------------------------------------------------------------------------------
# Command: fetch
#
def command_fetch(args):
    args.cmd = ["git", "fetch"]
    command_foreach(args)

parser_fetch = subparsers.add_parser("fetch",
                                     help="Fetch changes for each dependency",
                                     description="Fetch changes for each dependency")
parser_fetch.set_defaults(func=command_fetch)
