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

    def __str__(self):
        return "{} '{}'".format(self.__class__.__name__, self.name)

    def _has_config(self):
        return False
    
    def _read_config(self):
        pass

    def _write_config(self):
        pass

    def _refresh_work_dir(self):
        pass

    def _record_to_parent_config(self):
        pass

    def _get_child_config_sections(self):
        return None

    def add_child(self, child):
        self.children.append(child)

    def _create_children_from_config(self):
        self.children = []
        for section in self._get_child_config_sections():
            new_dep = self.root._find_or_create_component(section=section, parent=self)
        
    def _build_dep_tree_recurse(self, refresh=False):
        if not self._has_config():
            return
        self._read_config()
        self._create_children_from_config()
        for child in self.children:
            if refresh:
                child._refresh_work_dir()
            child._build_dep_tree_recurse(refresh)

    def read_dep_tree(self):
        self._build_dep_tree_recurse()
        self.debug_dump("read: ")

    def refresh_dep_tree(self):
        self._build_dep_tree_recurse(True)
        self.debug_dump("refresh: ")

    def _record_dep_tree_recurse(self):
        for child in self.children:
            child._record_dep_tree_recurse()
        self._record_to_parent_config()

    def record_dep_tree(self):
        self._record_dep_tree_recurse()
        self.debug_dump("record: ")

    def write_dep_tree_config(self):
        for child in self.children:
            child.write_dep_tree_config()
        self._write_config()
        
    def _debug_dump_content(self, prefix):
        pass

    def debug_dump(self, prefix=""):
        if not opts.args.debug or opts.args.quiet:
            return
        debug("{}--- {} ---", prefix, repr(self))
        debug("{}name = {}", prefix, self.name)
        debug("{}rel_path = {}", prefix, self.rel_path)
        debug("{}abs_path = {}", prefix, self.abs_path)
        debug("{}parent = {}", prefix, repr(self.parent))
        debug("{}root = {}", prefix, repr(self.root))
        self._debug_dump_content(prefix)
        debug("{}children[] = {{", prefix)
        for i, c in enumerate(self.children):
            if i > 0:
                debug("{},".format(prefix))
            c.debug_dump("{}[{}] ".format(prefix, i))
        debug("{}}}", prefix)

class RealComponent(BasicComponent):
    def __init__(self, name, path, parent, url=None):
        BasicComponent.__init__(self, name, path, parent)
        self._parent_section = None
        self.config = config.Config(os.path.join(self.abs_path, ".depconfig"))
        self.repository = scm.Repository.create(self.abs_path, url)

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

    def _write_config(self):
        if self.config.need_write:
            self.repository.pre_edit(self.config.path)
            self.config.write()
            self.repository.post_edit(self.config.path)
            self.debug_dump("write: ")

    def _has_repo(self):
        return self.repository is not None and self.repository.vcs != "file"

    def _validate_has_repo(self):
        if self._has_repo():
            return
        error("{} does not have a non-file based SCM repository", self)
        
    def _add_to_parent_config(self):
        if self.parent_section:
            error("Cannot add {} to {}, already exists", self, self.parent)
            return
        self._parent_section = self.parent.config.add_section("dep", self.name)
        self.parent_section["relpath"] = self.rel_path

    def _refresh_work_dir(self):
        self.repository.refresh()        
        
    def _record_to_parent_config(self):
        if not self.parent_section:
            return
        self.repository.record()
        self.repository.write_state_to_config_section(self.parent_section)

    def _get_child_config_sections(self):
        return self.config.sections_named("dep")
        
    def initialize_new_config(self):
        verbose("Initializing {}", self)
        validate_file_notexists(self.config.path)
        core = self.config.add_section("core")
        core["default-dep-dir"] = "dep"
        self.config.need_read = False
        self._write_config()
        self.debug_dump("init post: ")

    def add_new_dependency(self, url):
        self._validate_has_repo()
        self.read_dep_tree()
        new_dep = self.root._find_or_create_component(url=url, parent=self)
        verbose("Adding dependency {} to {}", new_dep, self)
        new_dep._add_to_parent_config()
        new_dep.repository.refresh()
        new_dep._record_to_parent_config()
        self.debug_dump("add post: ")
        self.repository.add_ignore(new_dep.rel_path)        
        self.refresh_dep_tree()
        self.record_dep_tree()
        self.write_dep_tree_config()

    def refresh_dependencies(self):
        self._validate_has_repo()
        verbose("Refreshing dependencies under {}", self)        
        self.refresh_dep_tree()

    def record_dependencies(self):
        self._validate_has_repo()
        verbose("Recording dependencies under {}", self)        
        self.read_dep_tree()
        self.record_dep_tree()
        self.write_dep_tree_config()
        
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
        self.top_components = []

    def _find_top_component(self, name):
        return next((c for c in self.top_components if c.name == name), None)

    def _find_or_create_component(self, section=None, url=None, parent=None):
        if parent is None:
            error("Must pass parent to _find_or_create_component")
        if (not section and not url) or (section and url):
            error("Must pass section or url to _find_or_create_component")
        if section:
            name = section.subname
            path = section["relpath"]
            url = section["url"]
        else:
            name = scm.Repository.determine_name_from_url(url)
            dep_dir = parent.config["core"]["default-dep-dir"]
            path = os.path.join(dep_dir, name)
        top = self._find_top_component(name)
        if top is None:
            top = TopComponent(name, path, parent, url)
        if parent is self:
            comp = top
        else:
            comp = LinkComponent(name, path, parent, top)
        parent.add_child(comp)
        return comp

    def _debug_dump_content(self, prefix=""):
        RealComponent._debug_dump_content(self, prefix)
        debug("{}top_components[] = {{", prefix)
        for i, c in enumerate(self.top_components):
            if i > 0:
                debug("{},".format(prefix))
            c.debug_dump("{}[{}] ".format(prefix, i))
        debug("{}}}", prefix)

class TopComponent(RealComponent):
    def __init__(self, name, path, parent, url):
        RealComponent.__init__(self, name, path, parent, url)
        parent.root.top_components.append(self)
        
class LinkComponent(BasicComponent):
    def __init__(self, name, path, parent, top_component):
        BasicComponent.__init__(self, name, path, parent)
        self.top_component = top_component

    def _has_config(self):
        return self.top_component._has_config()
        
    def _read_config(self):
        self.top_component._read_config()

    def _write_config(self):
        self.top_component._write_config()

    def _refresh_work_dir(self):
        self.top_component._refresh_work_dir()

    def _record_to_parent_config(self):
        self.top_component._record_to_parent_config()

    def _get_child_config_sections(self):
        return self.top_component._get_child_config_sections()
        
    def _debug_dump_content(self, prefix=""):
        BasicComponent._debug_dump_content(self, prefix)        
        debug("{}top_component = {}", prefix, repr(self.top_component))
