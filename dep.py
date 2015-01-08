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
import subprocess

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

def run(*cmd, **kw):
    status = 0
    cmd = filter(None, cmd)
    cmd_text = ' '.join(cmd)
    cwd = kw.get('cwd')
    query = kw.get('query')
    if not query:
        if cwd:
            verbose("-> pushd {}", cwd)
        verbose("-> {}", cmd_text)
        if cwd:
            verbose("-> popd")
    if args.dry_run and not query:
        return
    try:
        if query:
            return subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        elif args.quiet:
            with open(os.devnull, "wb") as dev_null:
                status = subprocess.call(cmd, stdout=dev_null)
        else:
            status = subprocess.call(cmd)
        if status != 0:
            error("Execution of '{}' returned exit status {}", cmd_text, status)
    except OSError, e:
        error("Cannot execute '{}': {}'", cmd_text, e)
    except Exception, e:
        error("{}", e)

def run_query(*cmd, **kw):
    return run(*cmd, query=True, **kw)

def make_dirs(dir):
    if os.path.isdir(dir):
        return
    verbose("-> mkdir -p {}", dir)
    if args.dry_run:
        return
    try:
        os.makedirs(dir)
    except OSError, e:
        error("Cannot make directory path '{}'", dir)

# --------------------------------------------------------------------------------
# Configuration
#
class Config:
    def __init__(self, path):
        self.path = path
        self.sections = []

    def __str__(self):
        return "Config '{}'".format(self.path)

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

    def debug_dump(self, prefix=""):
        if not args.debug or args.quiet:
            return
        debug("{}--- {} ---", prefix, self)
        for s in self.sections:
            s.debug_dump(prefix)
    
class ConfigSection:
    def __init__(self, config, name, subname=None):
        self.config = config
        self.name = name
        self.subname = subname
        if subname:
            self.fullname = "{}.{}".format(name, subname)
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
        for v in self.vars:
            if v.name == key:
                return v.value
        raise KeyError("Unknown variable '{}.{}' in {}".format(self.fullname, key, self.config))

    def debug_dump(self, prefix=""):
        prefix = "{}{}.".format(prefix, self.fullname)
        for v in self.vars:
            v.debug_dump(prefix)
    
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

    def debug_dump(self, prefix=""):
        debug("{}{} = {}", prefix, self.name, self.value)
        
# --------------------------------------------------------------------------------
# Repository
#
class Repository:
    def __init__(self, work_dir, url, vcs, name):
        self.work_dir = work_dir
        self.url = url
        self.vcs = vcs
        self.name = name

    def __str__(self):
        return "{} '{}'".format(self.__class__.__name__, self.work_dir)

    def add_to_config_section(self, section):
        ConfigVar(section, "url", self.url)
        ConfigVar(section, "vcs", self.vcs)
        
    @staticmethod
    def determine_vcs_from_url(url):
        # TODO: Hard coded for now
        return "git"

    @staticmethod
    def determine_name_from_url(url):
        # TODO: Hard coded for now        
        name = os.path.basename(url)
        name = re.sub(r"\.git$", "", name)        
        return name
    
    @staticmethod
    def create_from_url(work_dir, url):
        if not url:
            return FileRepository(work_dir)
        vcs = Repository.determine_vcs_from_url(url)
        # TODO: Support more VCS
        if vcs == "git":
            return GitRepository(work_dir, url)
        else:        
            error("Cannot determine VCS from repository URL '{}'", url)

    def debug_dump(self, prefix=""):
        if not args.debug or args.quiet:
            return
        debug("{}--- {} ---", prefix, self)
        debug("{}work_dir = {}", prefix, self.work_dir)
        debug("{}url = {}", prefix, self.url)
        debug("{}vcs = {}", prefix, self.vcs)
        debug("{}name = {}", prefix, self.name)        

class FileRepository(Repository):
    def __init__(self, work_dir):
        url = "file://{}".format(work_dir)
        name = Repository.determine_name_from_url(work_dir)
        Repository.__init__(self, work_dir, url, "file", name)

    def register(self, path):
        pass

    def unregister(self, path):
        pass

    def pre_edit(self, path):
        pass

    def post_edit(self, path):
        pass

    def download(self):
        pass

class GitRepository(Repository):
    def __init__(self, work_dir, url):
        name = Repository.determine_name_from_url(url)
        Repository.__init__(self, work_dir, url, "git", name)
        # TODO: Better way to find this?
        self.git_dir = os.path.join(work_dir, ".git")
        self.quiet_flag = "--quiet" if args.quiet else None

    def register(self, path):
        run("git", "add", path, cwd=self.work_dir)

    def unregister(self, path):
        run("git", "rm", "--cached", path, cwd=self.work_dir)

    def pre_edit(self, path):
        pass

    def post_edit(self, path):
        run("git", "add", path, cwd=self.work_dir)

    def download(self):
        validate_dir_notexists(self.work_dir)
        validate_dir_notexists(self.git_dir)
        status("Downloading {} from '{}'", self, self.url)
        run("git", "clone", self.quiet_flag, self.url, self.work_dir)
        
# --------------------------------------------------------------------------------
# Component
#
class Component:
    def __init__(self, parent=None, url=None):
        # TODO: Override by default
        if url:
            self.name = Repository.determine_name_from_url(url)
        else:
            self.name = Repository.determine_name_from_url(os.getcwd())
        # TODO: Override by default
        dep_dir = parent.config["core"]["default-dep-dir"] if parent else "dep"
        self.relpath = os.path.join(dep_dir, self.name)
        self.work_dir = os.path.join(parent.work_dir, self.relpath) if parent else os.getcwd()
        self.parent = parent
        self.children = []
        self.root = parent.root if parent else self
        if parent:
            parent.children.append(self)
        self.config = Config(os.path.join(self.work_dir, ".depconfig"))
        self.repository = Repository.create_from_url(self.work_dir, url)
        
    def __str__(self):
        return "Component '{}'".format(self.name)
    
    def init(self):
        verbose("Initializing {}", self)
        validate_file_notexists(self.config.path)
        core = ConfigSection(self.config, "core")
        ConfigVar(core, "default-dep-dir", "dep")
        self.config.write()
        self.repository.register(self.config.path)
        self.debug_dump("post: ")

    def add_to_config(self, config):
        section = ConfigSection(config, "dep", self.name)
        ConfigVar(section, "relpath", self.relpath)
        self.repository.add_to_config_section(section)

    def add_child(self, url):
        self.config.read()
        self.debug_dump("pre: ")
        child = Component(self, url)
        child.add_to_config(self.config)
        self.repository.pre_edit(self.config.path)
        self.config.write()
        self.repository.post_edit(self.config.path)
        child.repository.download()
        self.debug_dump("post: ")

    def debug_dump(self, prefix=""):
        if not args.debug or args.quiet:
            return
        debug("{}--- {} ---", prefix, self)
        debug("{}name = {}", prefix, self.name)
        debug("{}relpath = {}", prefix, self.relpath)
        debug("{}work_dir = {}", prefix, self.work_dir)        
        debug("{}parent = {}", prefix, str(self.parent))
        debug("{}root = {}", prefix, str(self.root))
        self.config.debug_dump(prefix)
        self.repository.debug_dump(prefix)
        debug("{}children[] = {{", prefix)
        for i, c in enumerate(self.children):
            if i > 0:
                debug("{},".format(prefix))
            c.debug_dump("{}[{}] ".format(prefix, i))
        debug("{}}}", prefix)            

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
    root = Component()
    root.init()

# --------------------------------------------------------------------------------
# Command: add
#
def command_add(args):
    root = Component()
    root.add_child(args.url)

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

parser_add = subparsers.add_parser("add",
                                   help="Add a new dependency to this component",
                                   description="Add a new dependency to this component.")
parser_add.add_argument("url",
                        help="The URL of the dependant component's VCS repository")
parser_add.set_defaults(func=command_add)

if len(sys.argv) == 1:
    parser.print_help()
    exit(0)

args = parser.parse_args()
if args.version:
    show_version()
    exit(0)

args.func(args)
exit(0)
