# --------------------------------------------------------------------------------
# Command: foreach
#
def command_foreach(args):
    root = RootComponent()
    root.read_dep_tree()
    root.debug_dump("foreach pre: ")
    root.foreach(args.cmd)

parser_foreach = subparsers.add_parser("foreach",
                                       help="Run a shell command for each dependency",
                                       description="Run a shell command for each dependency.")
parser_foreach.add_argument("cmd", action="append",
                            help="The command to run for each dependency")
parser_foreach.set_defaults(func=command_foreach)
