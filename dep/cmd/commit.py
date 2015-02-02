# --------------------------------------------------------------------------------
# Command: commit
#
def command_commit(args):
    args.cmd = ["git", "commit"]
    command_foreach(args)

parser_commit = subparsers.add_parser("commit",
                                      help="Commit changes for each dependency",
                                      description="Commit changes for each dependency")
parser_commit.set_defaults(func=command_commit)
