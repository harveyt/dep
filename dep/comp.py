#
# Components
# ==========
#
# %%LICENSE%%
#
import os;
from dep import config, opts, scm
from dep.helpers import *

class BasicComponent:
    def __init__(self, name, path, parent):
        self.name = name
        self.rel_path = path
        self.abs_path = os.path.join(parent.abs_path, path) if parent else path
        self.parent = parent
        self.root = parent.root if parent else self
        self.children = []
        if parent:
            parent._add_child(self)

    def __str__(self):
        return "{} '{}'".format(self.__class__.__name__, self.name)

    def _add_child(self, child):
        self.children.append(child)

    def _debug_dump_content(self, prefix):
        pass

    def debug_dump(self, prefix=""):
        if not opts.args.debug or opts.args.quiet:
            return
        debug("{}--- {} ---", prefix, self)
        debug("{}name = {}", prefix, self.name)
        debug("{}rel_path = {}", prefix, self.rel_path)
        debug("{}abs_path = {}", prefix, self.abs_path)
        debug("{}parent = {}", prefix, str(self.parent))
        debug("{}root = {}", prefix, str(self.root))
        debug("{}children[] = {}", prefix, self.children)        
        self._debug_dump_content(prefix)

class RealComponent(BasicComponent):
    def __init__(self, name, path, parent, url=None):
        BasicComponent.__init__(self, name, path, parent)
        self._parent_section = None
        self.config = config.Config(os.path.join(self.abs_path, ".depconfig"))
        self.repository = scm.Repository.create(self.abs_path, url)
        self.debug_dump("__init__: ")        

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
    
    def _has_config(self):
        return self.config.exists()
        
    def _read_config(self):
        if self.config.need_read:
            self.config.read()
            self.debug_dump("read: ")

    def _write_config(self):
        if self.config.need_write:
            self.debug_dump("write: ")            
            self.repository.pre_edit(self.config.path)
            self.config.write()
            self.repository.post_edit(self.config.path)

    def _add_to_parent_config(self):
        if self.parent_section:
            error("Cannot add {} to {}, already exists", self, self.parent)
            return
        self._parent_section = self.parent.config.add_section("dep", self.name)
        self.parent_section["relpath"] = self.rel_path
            
    def initialize_new_config(self):
        verbose("Initializing {}", self)
        validate_file_notexists(self.config.path)
        core = self.config.add_section("core")
        core["default-dep-dir"] = "dep"
        self.config.need_read = False
        self._write_config()
        self.debug_dump("init post: ")

    def add_new_dependency(self, url):
        self._read_config()
        new_dep = TopComponent(url, self)
        verbose("Adding dependency {} to {}", new_dep, self)
        new_dep._add_to_parent_config()
        new_dep.repository.refresh()        
        new_dep.repository.record()
        new_dep.repository.write_state_to_config_section(new_dep.parent_section)
        self.repository.add_ignore(new_dep.rel_path)
        self._write_config()
        
    def _debug_dump_content(self, prefix=""):
        debug("{}parent_section = {}", prefix, self.parent_section)
        self.config.debug_dump(prefix)
        self.repository.debug_dump(prefix)        
        
class RootComponent(RealComponent):
    def __init__(self):
        path = find_root_work_dir()
        if path is None:
            path = os.getcwd()
        name = scm.Repository.determine_name_from_url(path)
        RealComponent.__init__(self, name, path, None)

class TopComponent(RealComponent):
    def __init__(self, url, parent):
        name = scm.Repository.determine_name_from_url(url)
        dep_dir = parent.config["core"]["default-dep-dir"]
        path = os.path.join(dep_dir, name)
        RealComponent.__init__(self, name, path, parent, url)
