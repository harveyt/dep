# --------------------------------------------------------------------------------
# Command: record
#
def command_record(args):
    root = RootComponent()
    root.read_dep_tree()
    root.debug_dump("record pre: ")
    root.record_dep_tree()
    root.write_dep_tree_config()
    root.debug_dump("record post: ")

parser_record = subparsers.add_parser("record",
                                   help="Record dependencies from current source repository state",
                                   description="Record dependencies from current source repository state.")
parser_record.set_defaults(func=command_record)
