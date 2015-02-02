# Main Program
# ============
#
# %%LICENSE%%
#
import sys
from dep import opts
from dep.cmd import *

def main():
    if len(sys.argv) == 1:
        opts.parser.print_help()
        sys.exit(0)

    opts.args = opts.parser.parse_args()
    opts.args.func(opts.args)
    sys.exit(0)
