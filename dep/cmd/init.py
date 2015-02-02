# --------------------------------------------------------------------------------
# Command: init
#
def command_init(args):
    root = RootComponent()
    verbose("Initializing {}", root)
    validate_file_notexists(root.config.path)    
    root.init_config()
    root.debug_dump("init post: ")

parser_init = subparsers.add_parser("init",
                                    help="Initialise dependency system for this component",
                                    description="Initialise dependency system for this component.")
parser_init.set_defaults(func=command_init)

