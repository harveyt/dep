# --------------------------------------------------------------------------------
# Command: status
#
def command_status(args):
    root = RootComponent()
    show_files=(args.show_files or args.show_long)
    show_branch=(args.show_branch or args.show_short or args.show_long)
    root.read_dep_tree()
    root.debug_dump("status pre: ")        
    root.status_header()
    root.status(show_files, show_branch)

parser_status = subparsers.add_parser("status",
                                      help="Show dependency status for all source repositories",
                                      description="Show dependency status for all source repositories.")

parser_status.add_argument("-s", "--short", dest="show_short", action="store_true",
                           help="Short version of status; equivalent to just --branch.")
parser_status.add_argument("-l", "--long", dest="show_long", action="store_true",
                           help="Long version of each dependency; equivalent to --files and --branch")
parser_status.add_argument("-f", "--files", dest="show_files", action="store_true",
                           help="Show the files which have changes for each dependency.")
parser_status.add_argument("-b", "--branch", dest="show_branch", action="store_true",
                           help="Show the branch information for each dependency.")
parser_status.set_defaults(func=command_status)
