# --------------------------------------------------------------------------------
# Command: refresh
#
def command_refresh(args):
    root = RootComponent()
    root.refresh_dep_tree()
    root.debug_dump("refresh post: ")

parser_refresh = subparsers.add_parser("refresh",
                                   help="Refresh dependencies from their source repositories",
                                   description="Refresh dependencies from their source repositories.")
parser_refresh.set_defaults(func=command_refresh)
