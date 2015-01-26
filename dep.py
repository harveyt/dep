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
    sys.exit(1)

def debug(fmt, *a):
    if not args.debug:
        return
    status(fmt, *a)

def verbose(fmt, *a):
    if not args.verbose:
        return
    status(fmt, *a)

def status(fmt, *a):
    if args.quiet:
        return
    sys.stdout.write(fmt.format(*a))
    sys.stdout.write("\n")

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
    if cwd == os.getcwd():
        cwd = None
    query = kw.get('query')
    pipe = kw.get('pipe')
    if not query and not pipe:
        if cwd:
            verbose("-> pushd {}", cwd)
        verbose("-> {}", cmd_text)
        if cwd:
            verbose("-> popd")
    if args.dry_run and not query and not pipe:
        return
    try:
        if query:
            return subprocess.check_output(cmd, stderr=subprocess.STDOUT, cwd=cwd)
        elif pipe:
            return subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=cwd)            
        elif args.quiet:
            with open(os.devnull, "wb") as dev_null:
                status = subprocess.call(cmd, stdout=dev_null, cwd=cwd)
        else:
            status = subprocess.call(cmd, cwd=cwd)
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

class Pipe:
    def __init__(self, *cmd, **kw):
        self.process = run(*cmd, pipe=True, **kw)
        self.cmd_text = ' '.join(filter(None, cmd))        

    def __enter__(self):
        return self.process.stdout

    def __exit__(self, type, value, traceback):
        exit_status = self.process.wait()
        if exit_status != 0:
            error("{} returned exit code {}", self.cmd_text, exit_status)
        
# --------------------------------------------------------------------------------
# Configuration
#
class Config:
    def __init__(self, path):
        self.path = path
        self.sections = []

    def __str__(self):
        return "Config '{}'".format(self.path)

    def exists(self):
        return os.path.exists(self.path)
    
    def read(self):
        verbose("Reading {}", self)
        self.sections = []
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

    def sections_named(self, name):
        for b in self.sections:
            if b.name == name:
                yield b
    
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

    def __setitem__(self, key, value):
        for v in self.vars:
            if v.name == key:
                v.value = value
                return
        ConfigVar(self, key, value)
    
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
        self.branch = None
        self.commit = None

    def update_config_section(self, section):
        section["url"] = self.url
        section["vcs"] = self.vcs
        if self.branch:
            section["branch"] = self.branch
        if self.commit:
            section["commit"] = self.commit
        
    @staticmethod
    def determine_vcs_from_url(url):
        # TODO: Hard coded for now
        return "git"

    @staticmethod
    def determine_vcs_from_work_dir(work_dir):
        # TODO: Hard coded for now                
        if GitRepository.is_present(work_dir):
            return "git"
        else:
            return "file"
        
    @staticmethod
    def determine_name_from_url(url):
        # TODO: Hard coded for now        
        name = os.path.basename(url)
        name = re.sub(r"\.git$", "", name)        
        return name
    
    @staticmethod
    def create(work_dir, url):
        if not url:
            url = "file://{}".format(work_dir)
            vcs = Repository.determine_vcs_from_work_dir(work_dir)
        else:
            vcs = Repository.determine_vcs_from_url(url)
        # TODO: Support more VCS
        if vcs == "git":
            return GitRepository(work_dir, url)
        elif vcs == "file":
            return FileRepository(work_dir, url)
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
        debug("{}branch = {}", prefix, self.branch)
        debug("{}commit = {}", prefix, self.commit)        

class FileRepository(Repository):
    def __init__(self, work_dir, url):
        name = Repository.determine_name_from_url(url)
        Repository.__init__(self, work_dir, url, "file", name)

    def __str__(self):
        return "{} '{}'".format(self.__class__.__name__, self.work_dir)

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

    def checkout(self, branch=None, commit=None):
        pass
    
    def has_ignore(self, path):
        return False

    def add_ignore(self, path):
        pass

    def remove_ignore(self, path):
        pass

    def has_local_modifications(self):
        return True
   
    def refresh(self):
        pass

    def record(self):
        pass

    def status_brief(self, path):
        pass

class GitRepository(Repository):
    def __init__(self, work_dir, url):
        name = Repository.determine_name_from_url(url)
        Repository.__init__(self, work_dir, url, "git", name)
        # TODO: Better way to find this?
        self.git_dir = os.path.join(work_dir, ".git")
        self.ignore_file = os.path.join(work_dir, ".gitignore")
        self.quiet_flag = "--quiet" if args.quiet else None

    def __str__(self):
        return "{} '{}'".format(self.__class__.__name__, self.git_dir)
        
    @staticmethod
    def is_present(work_dir):
        git_dir = os.path.join(work_dir, ".git")
        return os.path.exists(git_dir)
        
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
        status("Downloading {}\n    from '{}'", self, self.url)
        run("git", "clone", self.quiet_flag, "--no-checkout", self.url, self.work_dir)

    def checkout(self, branch=None, commit=None):
        branch_flag = None if branch is None else "-B"
        branch_name = None if branch is None else branch
        commit_flag = None if commit is None else commit
        branch_mesg = "" if branch is None else "\n    on branch '{}'".format(branch)        
        commit_mesg = "" if commit is None else "\n    at commit '{}'".format(commit)
        status("Checkout {}{}{}\n    in '{}'", self, branch_mesg, commit_mesg, self.work_dir)
        run("git", "checkout", self.quiet_flag, branch_flag, branch_name, commit_flag, cwd=self.work_dir)

    def _read_ignore(self):
        if not os.path.exists(self.ignore_file):
            return []
        try:
            ignores = []
            with open(self.ignore_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    ignores.append(line)
            return ignores
        except IOError, e:
            error("Cannot open '{}' for reading: {}'", self.ignore_file, e)

    def has_ignore(self, path):
        ignores = self._read_ignore()
        return path in ignores

    def add_ignore(self, path):
        verbose("Adding '{}' to ignore file '{}'", path, self.ignore_file)
        if args.dry_run:
            return
        # TODO: With git we know we can just post_edit the file to do the right thing.
        # TODO: With out vcs we might need register/pre_edit.
        try:
            with open(self.ignore_file, 'a') as f:
                f.write('/{}\n'.format(path))
        except IOError, e:
            error("Cannot open '{}' for writing: {}'", self.ignore_file, e)
        self.post_edit(self.ignore_file)            

    def remove_ignore(self, path):
        verbose("Removing '{}' from ignore file '{}'", path, self.ignore_file)
        if args.dry_run:
            return
        if not os.path.exists(self.ignore_file):
            # TODO: There is no ignore file, so cannot remove?
            return
        # TODO: With git we know we can just post_edit the file to do the right thing.        
        # TODO: With out vcs we might need pre_edit.
        ignores = self._read_ignore()
        try:
            with open(self.ignore_file, 'w') as f:
                for ignore in ignores:
                    if ignore != "/" + path:
                        f.write('{}\n'.format(ignore))
        except IOError, e:
            error("Cannot open '{}' for writing: {}'", self.ignore_file, e)
        self.post_edit(self.ignore_file)
        # TODO: Remove if ignore file is now empty?

    def _get_status(self):
        ahead = 0
        behind = 0
        changes = 0
        with Pipe("git", "status", "--porcelain", "--branch", cwd=self.work_dir) as p:
            for line in p:
                m = re.match(r"##\s+[^[]*(\[(\s*ahead\s+(\d+)\s*)?,?(\s*behind\s+(\d+)\s*)?\])?", line)
                if m:
                    ahead = m.group(3) if m.group(3) else 0
                    behind = m.group(5) if m.group(5) else 0
                else:
                    changes = changes + 1
        return (changes, ahead, behind)    

    def has_local_modifications(self):
        return self._get_status()[0] > 0
    
    def refresh(self):
        check_local = True
        if not os.path.exists(self.work_dir):
            check_local = False
        if not os.path.exists(self.git_dir):
            self.download()
        if check_local and self.has_local_modifications():
            error("{} has local modifications, not refreshed", self)
        self.checkout(self.branch, self.commit)

    def _get_branch(self):
        branch = run_query("git", "rev-parse", "--symbolic-full-name", "HEAD", cwd=self.work_dir).rstrip("\n")
        # TODO: Check it is valid!
        if branch == "HEAD":
            # Detached head is not supported (yet), need to checkout a branch.
            # TODO: Support checkout of tag and arbitary commit - pick the first sensible branch containing that commit.
            error("{} is checked out with a detached head, not yet supported; checkout a branch (not a tag)", self)
        return branch

    def _get_commit(self):
        commit = run_query("git", "rev-parse", "HEAD", cwd=self.work_dir).rstrip("\n")
        # TODO: Check it is valid!
        return commit

    def record(self):
        new_branch = self._get_branch()
        new_commit = self._get_commit()
        if new_branch != self.branch or new_commit != self.commit:
            self.branch = new_branch
            self.commit = new_commit
            status("""Recording {}
    at commit '{}'
    on branch '{}'""", self, self.commit, self.branch)

    def _branch_name_from_ref(self, ref):
        return re.sub(r"refs/heads/", "", ref)
            
    def status_brief(self, path):
        branch = self.branch
        commit = self.commit
        actual_branch = self._get_branch()
        actual_commit = self._get_commit()
        changes, ahead, behind = self._get_status()
        mod = "?" if changes is None else ("*" if changes else " ")
        if branch is None:
            branch = " " + actual_branch
        else:
            branch = (" " if branch == actual_branch else "*") + actual_branch
        if commit is None:
            commit = " " + actual_commit
        else:
            commit = (" " if commit == actual_commit else "*") + actual_commit
        ahead = "?" if ahead is None else ahead
        behind = "?" if behind is None else behind
        branch = self._branch_name_from_ref(branch)
        status("{:1} {:16} {:41} {:>6} {:>6} {}", mod, branch, commit, ahead, behind, path)
            
# --------------------------------------------------------------------------------
# Component
#
class Component:
    def __init__(self, parent=None, url=None, section=None):
        if (args.root or not args.local) and (parent is None and url is None and section is None):
            cwd = Component.find_root_work_dir()
        else:
            cwd = Component.find_local_work_dir()
        if cwd is None:
            cwd = os.getcwd()
        if url:
            self.name = Repository.determine_name_from_url(url)
        elif section:
            self.name = section.subname
            url = section["url"]
        else:
            self.name = Repository.determine_name_from_url(cwd)
            # TODO: This flags to use file style url, fix so this is done here?
            url = None
        dep_dir = parent.config["core"]["default-dep-dir"] if parent else "dep"
        self.relpath = os.path.join(dep_dir, self.name)
        self.work_dir = os.path.join(parent.work_dir, self.relpath) if parent else cwd
        self.parent = parent
        self.children = []
        self.root = parent.root if parent else self
        if parent:
            parent.children.append(self)
        self.config = Config(os.path.join(self.work_dir, ".depconfig"))
        # TODO: Pass down name?
        self.repository = Repository.create(self.work_dir, url)
        # TODO: Pass down section to do this?
        if section:
            self.repository.branch = section["branch"]
            self.repository.commit = section["commit"]
        
    def __str__(self):
        return "Component '{}'".format(self.name)

    @staticmethod
    def find_local_work_dir(path=None):
        if path is None:
            path = os.getcwd()
        path.rstrip(os.path.sep)
        while True:
            config_path = os.path.join(path, ".depconfig")
            if os.path.isfile(config_path):
                return path
            path = os.path.dirname(path)
            if path == os.path.sep:
                return None

    @staticmethod
    def find_root_work_dir(path=None):
        last_work_dir = None
        while True:
            work_dir = Component.find_local_work_dir(path)
            if work_dir is None:
                return last_work_dir
            last_work_dir = work_dir
            path = os.path.dirname(work_dir)
            if path == os.path.sep:
                return None
    
    def init(self):
        verbose("Initializing {}", self)
        validate_file_notexists(self.config.path)
        core = ConfigSection(self.config, "core")
        ConfigVar(core, "default-dep-dir", "dep")
        self.config.write()
        self.repository.register(self.config.path)
        self.debug_dump("post: ")

    def _add_to_config(self, config):
        section = ConfigSection(config, "dep", self.name)
        ConfigVar(section, "relpath", self.relpath)
        self.repository.update_config_section(section)

    def _check_has_vcs(self):
        if self.repository is None or self.repository.vcs == "file":
            error("{} must have been initialized with a VCS", self)

    def _read_state(self):
        self.config.read()
        for s in self.config.sections_named("dep"):
            child = Component(parent=self, section=s)

    def _refresh_state(self):
        self._check_has_vcs()
        for c in self.children:
            c.repository.refresh()

    def _record_state(self):
        self._check_has_vcs()
        self.repository.record()
        if self.parent:
            section = self.parent.config["dep." + self.name]
            self.repository.update_config_section(section)

    def _write_state(self):
        self.repository.pre_edit(self.config.path)
        self.config.write()
        self.repository.post_edit(self.config.path)

    def add_child(self, url):
        self._check_has_vcs()
        self._read_state()
        self.debug_dump("read: ")
        child = Component(parent=self, url=url)
        child.repository.refresh()
        child._add_to_config(self.config)
        child._record_state()
        child.refresh()
        self._write_state()
        self.repository.add_ignore(child.relpath)
        self.debug_dump("add_child: ")
        
    def refresh(self):
        if not self.config.exists():
            return
        self._check_has_vcs()
        self._read_state()
        self.debug_dump("read: ")
        self._refresh_state()
        self.debug_dump("refresh: ")
        for c in self.children:
            c.refresh()

    def record(self):
        self._check_has_vcs()
        self._read_state()
        self.debug_dump("read: ")
        for c in self.children:
            c._record_state()
        self._write_state()
        self.debug_dump("record: ")

    def list(self):
        if self.config.exists():
            self._read_state()
            for c in self.children:
                print c.name
        print self.name

    def status(self, show_files=False, show_branch=False):
        if not self.parent:
            status("M  Branch           Commit                                    Ahead Behind Path")
            status("-- ---------------  ---------------------------------------- ------ ------ -----------------------")
        self.repository.status_brief(self.relpath if self.parent else ".")
        if not self.config.exists():
            return
        self._read_state()
        for c in self.children:
            c.status(show_files, show_branch)

    def foreach(self, cmds):
        if self.config.exists():
            self._read_state()
            for c in self.children:
                c.foreach(cmds)
        status("##===================================================================================================")
        status("## {}:", self)
        old_quiet = args.quiet
        args.quiet = False
        run(*cmds, shell=True, cwd=self.work_dir)
        args.quiet = old_quiet


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
# Command: config
#
def command_config(args):
    if args.work_dir:
        path = Component.find_local_work_dir()
        if path is None:
            error("Cannot determine local working directory")
        print path
    if args.root_work_dir:
        path = Component.find_root_work_dir()
        if path is None:
            error("Cannot determine root working directory")
        print path

# --------------------------------------------------------------------------------
# Command: refresh
#
def command_refresh(args):
    root = Component()
    root.refresh()

# --------------------------------------------------------------------------------
# Command: record
#
def command_record(args):
    root = Component()
    root.record()

# --------------------------------------------------------------------------------
# Command: list
#
def command_list(args):
    root = Component()
    root.list()

# --------------------------------------------------------------------------------
# Command: status
#
def command_status(args):
    root = Component()
    root.status(show_files=(args.show_files or args.show_long),
                show_branch=(args.show_branch or args.show_short or args.show_long))

# --------------------------------------------------------------------------------
# Command: foreach
#
def command_foreach(args):
    root = Component()
    root.foreach(args.cmd)

def command_pull(args):
    root = Component()
    root.foreach(["git", "pull"])

def command_push(args):
    root = Component()
    root.foreach(["git", "push"])

def command_fetch(args):
    root = Component()
    root.foreach(["git", "fetch"])

def command_commit(args):
    root = Component()
    root.foreach(["git", "commit"])
    
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
parser.add_argument("-r", "--root", action="store_true",
                    help="Run from root dependency (default)")
parser.add_argument("-l", "--local", action="store_true",
                    help="Run as if local dependency is the root dependency")

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

parser_config = subparsers.add_parser("config",
                                      help="Dependency configuration",
                                      description="Dependency configuration.")
parser_config.add_argument("--work-dir", action="store_true",
                           help="Show the working directory of this dependency and exit")
parser_config.add_argument("--root-work-dir", action="store_true",
                           help="Show the working directory of the root dependency and exit")
parser_config.set_defaults(func=command_config)

parser_refresh = subparsers.add_parser("refresh",
                                   help="Refresh dependencies from their source repositories",
                                   description="Refresh dependencies from their source repositories.")
parser_refresh.set_defaults(func=command_refresh)

parser_record = subparsers.add_parser("record",
                                   help="Record dependencies from current source repository state",
                                   description="Record dependencies from current source repository state.")
parser_record.set_defaults(func=command_record)

parser_list = subparsers.add_parser("list",
                                   help="List dependencies",
                                   description="List dependencies.")
parser_list.set_defaults(func=command_list)

parser_status = subparsers.add_parser("status",
                                      help="Show dependency status for all source repositories",
                                      description="Show dependency status for all source repositories.")

parser_status.add_argument("-s", "--short", dest="show_short", action="store_true",
                           help="Short version of status; equivalent to just --branch.")
parser_status.add_argument("-l", "--long", dest="show_long", action="store_true",
                           help="Long version of each dependency; equivalent to --files and --branch")
parser_status.add_argument("-f", "--files", dest="show_files", action="store_true",
                           help="Show the files which have changes for each dependency.")
parser_status.add_argument("-b", "--branch", dest="show_branch", action="store_true",
                           help="Show the branch information for each dependency.")
parser_status.set_defaults(func=command_status)

parser_foreach = subparsers.add_parser("foreach",
                                       help="Run a shell command for each dependency",
                                       description="Run a shell command for each dependency.")
parser_foreach.add_argument("cmd", action="append",
                            help="The command to run for each dependency")
parser_foreach.set_defaults(func=command_foreach)

parser_pull = subparsers.add_parser("pull",
                                     help="Pull changes for each dependency",
                                     description="Pull changes for each dependency")
parser_pull.set_defaults(func=command_pull)

parser_push = subparsers.add_parser("push",
                                     help="Push changes for each dependency",
                                     description="Push changes for each dependency")
parser_push.set_defaults(func=command_push)

parser_fetch = subparsers.add_parser("fetch",
                                     help="Fetch changes for each dependency",
                                     description="Fetch changes for each dependency")
parser_fetch.set_defaults(func=command_fetch)

parser_commit = subparsers.add_parser("commit",
                                      help="Commit changes for each dependency",
                                      description="Commit changes for each dependency")
parser_commit.set_defaults(func=command_commit)

if len(sys.argv) == 1:
    parser.print_help()
    exit(0)

args = parser.parse_args()
if args.version:
    show_version()
    exit(0)

args.func(args)
exit(0)
