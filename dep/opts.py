#
# Options
# =======
#
# %%LICENSE%%
#
import argparse

global parser
global subparsers
global args
global allow_rest

parser = argparse.ArgumentParser(description="Manages component based dependencies using version control systems (VCS).")

subparsers = parser.add_subparsers(title="command arguments", dest="subparser_name")

args = []
allow_rest = []

parser.add_argument("--version", action="version", version="dep %%VERSION%%",
                    help="Show version and exit")
parser.add_argument("-D", "--debug", action="store_true",
                    help="Show debugging information on stderr")
parser.add_argument("-q", "--quiet", action="store_true",
                    help="Only print error messages")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Show more verbose information, including commands executed")
parser.add_argument("--dry-run", action="store_true",
                    help="Only show what actions and commands would be executed, make no changes")
