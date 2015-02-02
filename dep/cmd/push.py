# --------------------------------------------------------------------------------
# Command: push
#
def command_push(args):
    args.cmd = ["git", "push"]
    command_foreach(args)

parser_push = subparsers.add_parser("push",
                                     help="Push changes for each dependency",
                                     description="Push changes for each dependency")
parser_push.set_defaults(func=command_push)
