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
import re
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

def status(fmt, *a):
    if args.quiet:
        return
    sys.stderr.write(fmt.format(*a))
    sys.stderr.write("\n")

def verbose(fmt, *a):
    if not args.verbose or args.quiet:
        return
    sys.stderr.write(fmt.format(*a))
    sys.stderr.write("\n")

def validate_file_exists(file):
    if not os.path.isfile(file):
        error("File '{}' does not exist", file)

def validate_file_notexists(file):
    if os.path.exists(file):
        error("File '{}' already exists", file)

def validate_dir_exists(dir):
    if not os.path.isdir(dir):
        error("Directory '{}' does not exist", dir)

def validate_dir_notexists(dir):
    if os.path.exists(dir):
        error("Directory '{}' already exists", dir)
    
# --------------------------------------------------------------------------------
# Configuration
#
class Config:
    def __init__(self, path):
        self.path = path
        self.sections = []

    def __str__(self):
        return "config file '{}'".format(self.path)

    def read(self):
        status("Reading {}", self)
        try:
            section = None
            with open(self.path, 'r') as handle:
                for lineno, line in enumerate(handle, start=1):
                    line = line.rstrip('\r\n')
                    # TODO: Handle comments
                    # TODO: Handle escapes here? Would make parsing "\"" harder.
                    # TODO: Handle line continuation
                    if re.match(r"^\s*$", line):
                        continue
                    s = ConfigSection.parse(self, line)
                    if s:
                        section = s
                        continue
                    v = ConfigVar.parse(section, line)
                    if v:
                        continue
                    error("{}, line {} cannot be parsed:\n>>> {}", self, lineno, line)
        except IOError, e:
            error("Cannot open {} for reading: {}'", self, e)

    def write(self):
        status("Writing {}", self)
        if args.dry_run:
            return
        try:
            with open(self.path, 'w') as handle:
                for b in self.sections:
                    b.write(handle)
        except IOError, e:
            error("Cannot open {} for writing: {}'", self, e)

    def __getitem__(self, key):
        for s in self.sections:
            if s.fullname == key:
                return s
        raise KeyError("Unknown section '{}' in {}".format(key, self))

class ConfigSection:
    def __init__(self, config, name, subname=None):
        self.config = config
        self.name = name
        self.subname = subname
        if subname:
            self.fullname = "{}.{}".format(section.name, subname)
        else:
            self.fullname = name
        self.vars = []
        config.sections.append(self)

    def __str__(self):
        return self.fullname
        
    @staticmethod
    def parse(config, line):
        if not config:
            return None
        m = re.match(r'^\s*\[\s*([-a-zA-Z0-9]*)\s*("([^"]*)")?\s*\]\s*$', line)
        if not m:
            return None
        section = ConfigSection(config, m.group(1), m.group(3))
        return section

    def write(self, handle):
        if handle.tell() != 0:
            handle.write('\n')
        if self.subname:
            handle.write('[{} "{}"]\n'.format(self.name, self.subname))
        else:
            handle.write('[{}]\n'.format(self.name))
        for v in self.vars:
            v.write(handle)

    def __getitem__(self, key):
        for s in self.vars:
            if s.name == key:
                return s
        raise KeyError("Unknown variable '{}.{}' in {}".format(self.fullname, key, self.config))
            
class ConfigVar:
    def __init__(self, section, name, value):
        self.section = section
        self.fullname = "{}.{}".format(section.fullname, name)
        self.name = name
        self.value = value
        section.vars.append(self)

    def __str__(self):
        return self.value
        
    @staticmethod
    def parse(section, line):
        if not section:
            return None
        m = re.match(r'^\s*([-a-zA-Z0-9]*)\s*=\s*(.*?)\s*$', line)
        if not m:
            return None
        var = ConfigVar(section, m.group(1), m.group(2))
        return var

    def write(self, handle):
        # TODO: Handle escapes, quoting, whitespacing
        handle.write('\t{} = {}\n'.format(self.name, self.value))

# --------------------------------------------------------------------------------
# Component
#
class Component:
    def __init__(self, name):
        self.name = name
        # TODO: Root directory determined how?
        self.root_dir = os.getcwd()
        self.config = Config(os.path.join(self.root_dir, ".depconfig"))

    def __str__(self):
        return "component '{}'".format(self.name)
    
    def init(self):
        verbose("Initializing {}", self)
        validate_file_notexists(self.config.path)
        core = ConfigSection(self.config, "core")
        ConfigVar(core, "default-dep-dir", "dep")
        self.config.write()

# --------------------------------------------------------------------------------
# Command: help
#
def command_help(args):
    if args.command:
        parser.parse_args([args.command, "--help"])
    else:
        parser.print_help()

# --------------------------------------------------------------------------------
# Command: init
#
def command_init(args):
    component = Component("test")
    component.init()
    
# --------------------------------------------------------------------------------
# Main
#
parser = argparse.ArgumentParser(description="Manages component based dependencies using version control systems (VCS).")

subparsers = parser.add_subparsers(title="command arguments")

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

parser_help = subparsers.add_parser("help",
                                    help="Show general or specific command help",
                                    description="Without any arguments display short help for all commands. With a specified 'command' argument show more specific help for the given command.")
parser_help.add_argument("command", nargs="?")
parser_help.set_defaults(func=command_help)

parser_init = subparsers.add_parser("init",
                                    help="Initialise dependency system for this component",
                                    description="Initialise dependency system for this component.")
parser_init.set_defaults(func=command_init)

if len(sys.argv) == 1:
    parser.print_help()
    exit(0)

args = parser.parse_args()
if args.version:
    show_version()
    exit(0)

args.func(args)
exit(0)
