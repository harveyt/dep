# --------------------------------------------------------------------------------
# Command: list
#
def command_list(args):
    root = RootComponent()
    root.read_dep_tree()
    root.debug_dump("list pre: ")
    for c in root.children:
        print c.name
    print root.name

parser_list = subparsers.add_parser("list",
                                   help="List dependencies",
                                   description="List dependencies.")
parser_list.set_defaults(func=command_list)
