# --------------------------------------------------------------------------------
# Command: help
#
from dep import opts

def command_help(args):
      if args.command:
          opts.parser.parse_args([args.command, "--help"])
      else:
          opts.parser.print_help()

parser_help = opts.subparsers.add_parser("help",
                                    help="Show general or specific command help",
                                    description="Without any arguments display short help for all commands. With a specified 'command' argument show more specific help for the given command.")
parser_help.add_argument("command", nargs="?")
parser_help.set_defaults(func=command_help)
