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

def find_root_work_dir(path=None):
    last_work_dir = None
    while True:
        work_dir = find_local_work_dir(path)
        if work_dir is None:
            return last_work_dir
        last_work_dir = work_dir
        path = os.path.dirname(work_dir)
        if path == os.path.sep:
            return None
            
# --------------------------------------------------------------------------------
# Configuration
#
class Config:
    def __init__(self, path):
        self.path = path
        self.sections = []
        self.need_read = True
        self.need_write = False

    def __str__(self):
        return "Config '{}'".format(self.path)

    def exists(self):
        return os.path.exists(self.path)
    
    def read(self):
        if not self.need_read:
            return
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
            self.need_read = False            
        except IOError, e:
            error("Cannot open {} for reading: {}'", self, e)

    def write(self):
        if not self.need_write:
            return
        status("Writing {}", self)
        if args.dry_run:
            self.need_write = False
            return
        try:
            with open(self.path, 'w') as handle:
                for b in self.sections:
                    b.write(handle)
            self.need_write = False
        except IOError, e:
            error("Cannot open {} for writing: {}'", self, e)

    def __getitem__(self, key):
        for s in self.sections:
            if s.fullname == key:
                return s
        raise KeyError("Unknown section '{}' in {}".format(key, self))

    def has_section(self, name, subname=None):
        for s in self.sections:
            if s.name == name and s.subname == subname:
                return True
        return False
        
    def add_section(self, name, subname=None):
        self.need_write = True        
        return ConfigSection(self, name, subname)

    def sections_named(self, name):
        for b in self.sections:
            if b.name == name:
                yield b
    
    def debug_dump(self, prefix=""):
        if not args.debug or args.quiet:
            return
        debug("{}--- {} ---", prefix, self)
        debug("{}need_read = {}", prefix, self.need_read)
        debug("{}need_write = {}", prefix, self.need_write)
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
        self.config.need_write = True
        for v in self.vars:
            if v.name == key:
                v.value = value
                return
        ConfigVar(self, key, value)

    def has_key(self, key):
        for v in self.vars:
            if v.name == key:
                return True
        return False
    
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

    def write_state_to_config_section(self, section):
        section["url"] = self.url
        section["vcs"] = self.vcs
        if self.branch:
            section["branch"] = self.branch
        if self.commit:
            section["commit"] = self.commit

    def read_state_from_config_section(self, section):
        self.branch = section["branch"] if section.has_key("branch") else None
        self.commit = section["commit"] if section.has_key("commit") else None
        
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
# DAGComponent
# Models the directed acyclic graph (DAG) of a component heirachy.
#
class DAGComponent:
    def __init__(self, name, path, parent):
        self.name = name
        self.rel_path = path
        self.abs_path = os.path.join(parent.abs_path, path) if parent else path
        self.parent = parent
        self.root = parent.root if parent else self
        self.children = []
        if parent:
            parent.children.append(self)

    def __str__(self):
        return "{} '{}'".format(self.__class__.__name__, self.name)

    def _debug_dump_content(self, prefix):
        pass

    def debug_dump(self, prefix=""):
        if not args.debug or args.quiet:
            return
        debug("{}--- {} ---", prefix, self)
        debug("{}name = {}", prefix, self.name)
        debug("{}rel_path = {}", prefix, self.rel_path)
        debug("{}abs_path = {}", prefix, self.abs_path)
        debug("{}parent = {}", prefix, str(self.parent))
        debug("{}root = {}", prefix, str(self.root))
        debug("{}children[] = {}", prefix, self.children)        
        self._debug_dump_content(prefix)
    
# --------------------------------------------------------------------------------
# FlatDAGComponent
# Models the flat view of each component's direct and indirect child dependencies.
#
class FlatDAGComponent(DAGComponent):
    def __init__(self, name, path, parent):
        DAGComponent.__init__(name, path, parent)
        self._flat_children = None

    @property
    def flat_children(self):
        if self._flat_children is None:
            self._rebuild_flat_children()
        return self._flat_children

    def _find_unique_child(self, name):
        return next((c for c in self._flat_children if c.name == name), None)

    def _add_unique_child(self, child):
        if self._find_unique_child(child):
            return
        self._flat_children.append(self._create_flat_child(child))

    def _create_flat_child(self, child):
        return child

    def _add_unique_children(self, children):
        for child in children:
            self._add_unique_child(child)

    def _rebuild_flat_children(self):
        self._flat_children = []
        for child in self.children:
            self._add_unique_children(child.flat_children)
        self._add_unique_children(self.children)

    def _debug_dump_content(self, prefix):
        debug("{}flat_children = {{", prefix, self.name)
        for i, c in enumerate(self.children):
            if i > 0:
                debug("{},".format(prefix))
            c.debug_dump("{}[{}] ".format(prefix, i))
        debug("{}}}", prefix)

# --------------------------------------------------------------------------------
# Component
# Models any component that appears in the dependency tree:
#
# * RealComponent - real physical components
#   * RootComponent - the root component
#   * TopComponent - top-level components under the root component
# * LinkComponent - all other level components which are links to a RealComponent
#
class Component(FlatDAGComponent):
    def __init__(self, name, path, parent):
        FlatDAGComponent.__init__(name, path, parent)

    def read_dep_tree(self):
        self.debug_dump("read_dep_tree pre: ")
        self._read_dep_tree_recurse()
        self.debug_dump("read_dep_tree post: ")        

    def _read_dep_tree_create_children():
        pass
    
    def _read_dep_tree_recurse(self):
        self._read_dep_tree_create_children()
        for child in self.children:
            child._read_dep_tree_recurse()

    def refresh_dep_tree(self):
        self.debug_dump("refresh_dep_tree pre: ")
        self._refresh_dep_tree_recurse()
        self.debug_dump("refresh_dep_tree post: ")

    def _refresh_dep_tree_create_children():
        pass

    def _refresh_dep_tree_recurse(self):
        self._refresh_dep_tree_create_children()
        for child in self.children:
            child._refresh_dep_tree_recurse()

    def record_dep_tree(self):
        for child in self.children:
            child._record_dep_tree_recurse()
        self._record_dep_tree_to_config()

    def record_dep_tree(self):
        self.debug_dump("record_dep_tree pre: ")
        self._record_dep_tree_recurse()
        self.debug_dump("record_dep_tree post: ")

    def _record_dep_tree_to_config():
        pass
        
    def _record_dep_tree_recurse(self):
        for child in self.children:
            child._record_dep_tree_recurse()
        self._record_dep_tree_to_config()
        
    def write_dep_tree(self):
        self.debug_dump("write_dep_tree pre: ")
        self._write_dep_tree_recurse()
        self.debug_dump("write_dep_tree post: ")

    def _write_dep_tree_config():
        pass
        
    def _write_dep_tree_recurse(self):
        for child in self.children:
            child._write_dep_tree_recurse()
        self._write_dep_tree_config()
        
    def _debug_dump_content(self, prefix):
        FlatDAGComponent._debug_dump_content(prefix)
        
# --------------------------------------------------------------------------------
# RealComponent
# Models a "real" component with a physical location, config and repository.
#
class RealComponent(Component):
    def __init__(self, name, path, parent, url=None):
        Component.__init__(name, path, parent)
        self._parent_section = None
        self.config = Config(os.path.join(self.abs_path, ".depconfig"))
        self.repository = Repository.create(self.abs_path, url)

    @property
    def parent_section(self):
        if self._parent_section is None:
            self._rebuild_parent_section()
        return self._parent_section

    def _rebuild_parent_section(self):
        if self.parent is None:
            return
        if not self.parent.config.has_section("dep", self.name):
            return
        self.parent_section = self.parent.config["dep.{}".format(self.name)]
        
    def _read_repository_state_from_config(self):
        if self.parent_section is None:
            return
        self.repository.read_state_from_config_section(self.parent_section)

    def _has_config(self):
        return self.config.exists()
        
    def _read_config(self):
        if self.config.need_read:
            self.config.read()
            self._read_repository_state_from_config()

    def _write_config(self):
        if self.config.need_write:
            self.repository.pre_edit(self.config.path)
            self.config.write()
            self.repository.post_edit(self.config.path)

    def _add_to_parent_config(self):
        self._parent_section = self.parent.config.add_section("dep", self.name)
        self.parent_section["relpath"] = self.rel_path
        self.repository.write_state_to_config_section(self.parent_section)

    def _record_to_parent_config(self):
        if self.parent_section:
            self.repository.record()            
            self.repository.write_state_to_config_section(self.parent_section)
            
    def _debug_dump_content(self, prefix):
        debug("{}parent_section = {}", prefix, self.parent_section)
        self.config.debug_dump(prefix)
        self.repository.debug_dump(prefix)        
        Component._debug_dump_content(prefix)
            
# --------------------------------------------------------------------------------
# Component
#
class Component:
    def __init__(self, name, relpath, parent, url=None, parent_section=None):
        self.name = name
        self.relpath = relpath
        self.work_dir = os.path.join(parent.work_dir, relpath) if parent else relpath
        self.parent = parent
        self.root = parent.root if parent else self
        self.parent_section = parent_section
        self.config = Config(os.path.join(self.work_dir, ".depconfig"))
        # TODO: Pass down name?            
        self.repository = Repository.create(self.work_dir, url)
        if self.parent_section:
            self.repository.read_state_from_config_section(self.parent_section)        
        self.children = []
        if parent:
            parent.children.append(self)

    def __str__(self):
        return "{} '{}'".format(self.__class__.__name__, self.name)

    def _has_config(self):
        return self.config.exists()
        
    def _read_config(self):
        self.config.read()

    def _write_config(self):
        if self.config.need_write:
            self.repository.pre_edit(self.config.path)
            self.config.write()
            self.repository.post_edit(self.config.path)

    def _add_to_parent_config(self):
        self.parent_section = self.parent.config.add_section("dep", self.name)
        self.parent_section["relpath"] = self.relpath
        self.repository.write_state_to_config_section(self.parent_section)

    def _record_to_parent_config(self):
        if self.parent_section:
            self.repository.record()            
            self.repository.write_state_to_config_section(self.parent_section)

    def _create_children(self):
        self.children = []
        for section in self.config.sections_named("dep"):
            Component._create_from_config_section(self, section)
        
    @staticmethod
    def _create_from_config_section(parent, section):
        return TopComponent(parent, section=section)

    @staticmethod
    def _create_from_url(parent, url):
        return TopComponent(parent, url=url)

    def _build_dep_tree(self, refresh=False):
        if not self._has_config():
            return
#        if refresh:
#            self.config.need_read = True
        self.debug_dump("_build_dep_tree pre: ")
        self._read_config()
        self._create_children()
        self.debug_dump("_build_dep_tree read: ")
        for child in self.children:
            if refresh:
                child.repository.refresh()
            child._build_dep_tree(refresh=refresh)

    def init_config(self):
        core = self.config.add_section("core")
        core["default-dep-dir"] = "dep"
        self.config.need_read = False
        self._write_config()
        
    def read_dep_tree(self):
        self._build_dep_tree(refresh=False)
            
    def refresh_dep_tree(self):
        self._build_dep_tree(refresh=True)
        
    def record_dep_tree(self):
        for child in self.children:
            child.record_dep_tree()
        self._record_to_parent_config()

    def write_dep_tree_config(self):
        for child in self.children:
            child.write_dep_tree_config()
        self._write_config()

    def add_child(self, url):
        child = Component._create_from_url(self, url)
        child._add_to_parent_config()
        self.repository.add_ignore(child.relpath)
        self.refresh_dep_tree()
        self.record_dep_tree()
        self.write_dep_tree_config()

    def status_header(self):
        status("M  Branch           Commit                                    Ahead Behind Path")
        status("-- ---------------  ---------------------------------------- ------ ------ -----------------------")
        
    def status(self, show_files, show_branch):
        self.repository.status_brief(self.relpath if self.parent else ".")
        for c in self.children:
            c.status(show_files, show_branch)
        
    def run_command(self, cmd):
        status("##===================================================================================================")
        status("## {}:", self)
        old_quiet = args.quiet
        args.quiet = False
        run(*cmd, shell=True, cwd=self.work_dir)
        args.quiet = old_quiet
        
    def foreach(self, cmd):
        for child in self.children:
            child.foreach(cmd)
        self.run_command(cmd)

    def debug_dump(self, prefix=""):
        if not args.debug or args.quiet:
            return
        debug("{}--- {} ---", prefix, self)
        debug("{}name = {}", prefix, self.name)
        debug("{}relpath = {}", prefix, self.relpath)
        debug("{}work_dir = {}", prefix, self.work_dir)
        debug("{}parent = {}", prefix, str(self.parent))
        debug("{}root = {}", prefix, str(self.root))
        debug("{}parent_section = {}", prefix, str(self.parent_section))        
        self.config.debug_dump(prefix)
        self.repository.debug_dump(prefix)        
        debug("{}children[] = {{", prefix)        
        for i, c in enumerate(self.children):
            if i > 0:
                debug("{},".format(prefix))
            c.debug_dump("{}[{}] ".format(prefix, i))
        debug("{}}}", prefix)

# --------------------------------------------------------------------------------
# RootComponent
#
class RootComponent(Component):
    def __init__(self):
        if args.root or not args.local:
            cwd = find_root_work_dir()
        else:
            cwd = find_local_work_dir()
        if cwd is None:
            cwd = os.getcwd()
        name = Repository.determine_name_from_url(cwd)
        Component.__init__(self, name, cwd, None, None, None)

# --------------------------------------------------------------------------------
# TopComponent
#
class TopComponent(Component):
    def __init__(self, parent, url=None, section=None):
        if url:
            name = Repository.determine_name_from_url(url)
        elif section:
            name = section.subname
            url = section["url"]
        else:
            error("TopComponent needs either a url or section")
        dep_dir = parent.config["core"]["default-dep-dir"]
        relpath = os.path.join(dep_dir, name)
        Component.__init__(self, name, relpath, parent, url, section)

# --------------------------------------------------------------------------------
# Main Arguments
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

# --------------------------------------------------------------------------------
# Command: help
#
def command_help(args):
    if args.command:
        parser.parse_args([args.command, "--help"])
    else:
        parser.print_help()

parser_help = subparsers.add_parser("help",
                                    help="Show general or specific command help",
                                    description="Without any arguments display short help for all commands. With a specified 'command' argument show more specific help for the given command.")
parser_help.add_argument("command", nargs="?")
parser_help.set_defaults(func=command_help)

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

# --------------------------------------------------------------------------------
# Command: add
#   
def command_add(args):
    root = RootComponent()
    root.read_dep_tree()
    root.debug_dump("add read: ")
    root.add_child(args.url)
    root.debug_dump("add post: ")

parser_add = subparsers.add_parser("add",
                                   help="Add a new dependency to this component",
                                   description="Add a new dependency to this component.")
parser_add.add_argument("url",
                        help="The URL of the dependant component's VCS repository")
parser_add.set_defaults(func=command_add)

# --------------------------------------------------------------------------------
# Command: config
#
def command_config(args):
    if args.work_dir:
        path = find_local_work_dir()
        if path is None:
            error("Cannot determine local working directory")
        print path
    if args.root_work_dir:
        path = find_root_work_dir()
        if path is None:
            error("Cannot determine root working directory")
        print path

parser_config = subparsers.add_parser("config",
                                      help="Dependency configuration",
                                      description="Dependency configuration.")
parser_config.add_argument("--work-dir", action="store_true",
                           help="Show the working directory of this dependency and exit")
parser_config.add_argument("--root-work-dir", action="store_true",
                           help="Show the working directory of the root dependency and exit")
parser_config.set_defaults(func=command_config)

# --------------------------------------------------------------------------------
# Command: refresh
#
def command_refresh(args):
    root = RootComponent()
    root.refresh_dep_tree()
    root.debug_dump("refresh post: ")

parser_refresh = subparsers.add_parser("refresh",
                                   help="Refresh dependencies from their source repositories",
                                   description="Refresh dependencies from their source repositories.")
parser_refresh.set_defaults(func=command_refresh)

# --------------------------------------------------------------------------------
# Command: record
#
def command_record(args):
    root = RootComponent()
    root.read_dep_tree()
    root.debug_dump("record pre: ")
    root.record_dep_tree()
    root.write_dep_tree_config()
    root.debug_dump("record post: ")

parser_record = subparsers.add_parser("record",
                                   help="Record dependencies from current source repository state",
                                   description="Record dependencies from current source repository state.")
parser_record.set_defaults(func=command_record)

# --------------------------------------------------------------------------------
# Command: list
#
def command_list(args):
    root = RootComponent()
    root.read_dep_tree()
    root.debug_dump("list pre: ")
    for c in root.children:
        print c.name
    print root.name

parser_list = subparsers.add_parser("list",
                                   help="List dependencies",
                                   description="List dependencies.")
parser_list.set_defaults(func=command_list)

# --------------------------------------------------------------------------------
# Command: status
#
def command_status(args):
    root = RootComponent()
    show_files=(args.show_files or args.show_long)
    show_branch=(args.show_branch or args.show_short or args.show_long)
    root.read_dep_tree()
    root.debug_dump("status pre: ")        
    root.status_header()
    root.status(show_files, show_branch)

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

# --------------------------------------------------------------------------------
# Command: foreach
#
def command_foreach(args):
    root = RootComponent()
    root.read_dep_tree()
    root.debug_dump("foreach pre: ")
    root.foreach(args.cmd)

parser_foreach = subparsers.add_parser("foreach",
                                       help="Run a shell command for each dependency",
                                       description="Run a shell command for each dependency.")
parser_foreach.add_argument("cmd", action="append",
                            help="The command to run for each dependency")
parser_foreach.set_defaults(func=command_foreach)

# --------------------------------------------------------------------------------
# Command: pull
#
def command_pull(args):
    args.cmd = ["git", "pull"]
    command_foreach(args)

parser_pull = subparsers.add_parser("pull",
                                     help="Pull changes for each dependency",
                                     description="Pull changes for each dependency")
parser_pull.set_defaults(func=command_pull)

# --------------------------------------------------------------------------------
# Command: push
#
def command_push(args):
    args.cmd = ["git", "push"]
    command_foreach(args)

parser_push = subparsers.add_parser("push",
                                     help="Push changes for each dependency",
                                     description="Push changes for each dependency")
parser_push.set_defaults(func=command_push)

# --------------------------------------------------------------------------------
# Command: fetch
#
def command_fetch(args):
    args.cmd = ["git", "fetch"]
    command_foreach(args)

parser_fetch = subparsers.add_parser("fetch",
                                     help="Fetch changes for each dependency",
                                     description="Fetch changes for each dependency")
parser_fetch.set_defaults(func=command_fetch)

# --------------------------------------------------------------------------------
# Command: commit
#
def command_commit(args):
    args.cmd = ["git", "commit"]
    command_foreach(args)

parser_commit = subparsers.add_parser("commit",
                                      help="Commit changes for each dependency",
                                      description="Commit changes for each dependency")
parser_commit.set_defaults(func=command_commit)

# --------------------------------------------------------------------------------
# Main
#
if len(sys.argv) == 1:
    parser.print_help()
    exit(0)

args = parser.parse_args()
if args.version:
    show_version()
    exit(0)

args.func(args)
exit(0)
