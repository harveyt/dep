# --------------------------------------------------------------------------------
# Command: add
#   
def command_add(args):
    root = RootComponent()
    root.read_dep_tree()
    root.debug_dump("add read: ")
    root.add_child(args.url)
    root.debug_dump("add post: ")

parser_add = subparsers.add_parser("add",
                                   help="Add a new dependency to this component",
                                   description="Add a new dependency to this component.")
parser_add.add_argument("url",
                        help="The URL of the dependant component's VCS repository")
parser_add.set_defaults(func=command_add)
