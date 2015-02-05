# Main Program
# ============
#
# %%LICENSE%%
#
import sys
from dep import opts, helpers
from dep.cmd import *

def main():
    if len(sys.argv) == 1:
        opts.parser.print_help()
        sys.exit(0)

    (opts.args, opts.rest_args) = opts.parser.parse_known_args()
    if len(opts.rest_args) > 0:
        if opts.args.subparser_name not in opts.allow_rest:
            opts.parser.print_usage()
            helpers.error("unrecognized options: {}", *opts.rest_args)
    opts.args.func(opts.args)
    sys.exit(0)
