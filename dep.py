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
import os

# --------------------------------------------------------------------------------
# Functions
#
def get_program_path():
    return os.path.realpath(__file__)

def show_version():
    print "dep version", version
    print "Copyright (c) 2015 Harvey John Thompson"
    print "See", get_program_path(), "for LICENSE."
    exit(0)
    
# --------------------------------------------------------------------------------
# Main
#
show_version()
