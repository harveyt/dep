#!/usr/bin/env python
#
# %%README%%
# %%LICENSE%%
# --------------------------------------------------------------------------------
# Globals
#
version = "%%VERSION%%"

# --------------------------------------------------------------------------------
# Imports
#
import sys
import os
import argparse

# --------------------------------------------------------------------------------
# Helper Functions
#
def get_program_path():
    return os.path.realpath(__file__)

def show_version():
    if args.quiet:
        return
    print """dep version {}
Copyright (c) 2015 Harvey John Thompson
See {} for LICENSE.""".format(version, get_program_path())

def error(fmt, *a):
    sys.stderr.write("dep: ")
    sys.stderr.write(fmt.format(*a))
    sys.stderr.write("\n")
    exit(1)

def debug(fmt, *a):
    if not args.debug or args.quiet:
        return
    sys.stderr.write(fmt.format(*a))
    sys.stderr.write("\n")

def verbose(fmt, *a):
    if not args.verbose or args.quiet:
        return
    sys.stderr.write(fmt.format(*a))
    sys.stderr.write("\n")
    
# --------------------------------------------------------------------------------
# Main
#
parser = argparse.ArgumentParser(description="Manages component based dependencies using version control systems (VCS).")

parser.add_argument("--version", action="store_true",
                    help="Show version and exit")
parser.add_argument("-D", "--debug", action="store_true",
                    help="Show debugging information on stderr")
parser.add_argument("-q", "--quiet", action="store_true",
                    help="Only print error messages")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Show more verbose information, including commands executed")
parser.add_argument("--dry-run", action="store_true",
                    help="Only show what actions and commands would be executed, make no changes")

args = parser.parse_args()
if args.version:
    show_version()
    exit(0)

exit(0)
