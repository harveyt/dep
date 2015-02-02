# --------------------------------------------------------------------------------
# Command: pull
#
def command_pull(args):
    args.cmd = ["git", "pull"]
    command_foreach(args)

parser_pull = subparsers.add_parser("pull",
                                     help="Pull changes for each dependency",
                                     description="Pull changes for each dependency")
parser_pull.set_defaults(func=command_pull)
