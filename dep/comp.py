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
        self.real_path = os.path.realpath(self.abs_path)
        self.parent = parent
        self.root = parent.root if parent else self
        self.top_component = self
        self.children = []
        self.implicit_children = []

    def __str__(self):
        return "{} '{}' at {}".format(self.__class__.__name__, self.name, self.abs_path)

    def _get_url(self):
        return None

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

    def _add_child(self, child):
        self.children.append(child)

    def _create_children_from_config(self, refresh=False):
        self.children = []
        for section in self._get_child_config_sections():
            new_dep = self.root._find_or_create_component(section=section, parent=self, refresh=refresh)
            self._add_child(new_dep)
        
    def _build_dep_tree_recurse(self, refresh=False):
        self._read_config()
        self._create_children_from_config(refresh)
        for child in self.children:
            child._build_dep_tree_recurse(refresh)

    def _find_implicit_child(self, name):
        return next((c for c in self.implicit_children if c.name == name), None)

    def _find_implicit_child_for_top(self, top):
        return next((c for c in self.implicit_children if c.top_component == top), None)
            
    def _add_implicit_child(self, child):
        self.implicit_children.append(child)
            
    def _build_dep_tree_implicit_recurse(self, refresh=False):
        self.implicit_children = self.children[:]
        for child in self.children:
            child._build_dep_tree_implicit_recurse(refresh)
            for implicit_child in child.implicit_children:
                comp = self._find_implicit_child(implicit_child.name)
                if comp is not None:
                    continue
                url = implicit_child._get_url()
                new_dep = self.root._find_or_create_component(url=url, parent=self, refresh=refresh)
                self._add_implicit_child(new_dep)

    def _build_dep_tree_top_order(self):
        self.top_component._move_top_component_to_front()        
        for child in self.children:
            child._build_dep_tree_top_order()

    def read_dep_tree(self):
        self._build_dep_tree_recurse()
        self._build_dep_tree_implicit_recurse()
        self._build_dep_tree_top_order()
        self.debug_dump("read: ")

    def refresh_dep_tree(self):
        self._build_dep_tree_recurse(True)
        self._build_dep_tree_implicit_recurse(True)
        self._build_dep_tree_top_order()        
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

    def run_command(self, cmd):
        status("##===================================================================================================")
        status("## {}:", self)
        old_quiet = opts.args.quiet
        opts.args.quiet = False
        run(*cmd, shell=True, cwd=self.abs_path)
        opts.args.quiet = old_quiet

    def find_local_component(self):
        real_path = find_local_work_dir()
        return self.find_component_by_real_path(real_path)
        
    def find_component_by_real_path(self, real_path):
        comp = self._find_component_by_real_path(real_path)
        if comp is None:
            error("Cannot find component with path '{}'", real_path)
        return comp

    def _find_component_by_real_path(self, real_path):
        if self.real_path == real_path:
            return self
        for c in self.children:
            comp = c._find_component_by_real_path(real_path)
            if comp is not None:
                return comp
        return None
        
    def _debug_dump_content(self, prefix):
        pass

    def debug_dump(self, prefix=""):
        if not opts.args.debug or opts.args.quiet:
            return
        debug("{}--- {} ---", prefix, repr(self))
        debug("{}name = {}", prefix, self.name)
        debug("{}rel_path = {}", prefix, self.rel_path)
        debug("{}abs_path = {}", prefix, self.abs_path)
        debug("{}real_path = {}", prefix, self.real_path)
        debug("{}parent = {}", prefix, repr(self.parent))
        debug("{}root = {}", prefix, repr(self.root))
        debug("{}top_component = {}", prefix, repr(self.top_component))
        self._debug_dump_content(prefix)
        debug("{}children[] = {{", prefix)
        for i, c in enumerate(self.children):
            if i > 0:
                debug("{},".format(prefix))
            c.debug_dump("{}[{}] ".format(prefix, i))
        debug("{}}}", prefix)
        debug("{}implicit_children[] = {{", prefix)
        for i, c in enumerate(self.implicit_children):
            if i > 0:
                debug("{},".format(prefix))
            c.debug_dump("{}[{}] ".format(prefix, i))
        debug("{}}}", prefix)

class ComponentList:
    def __init__(self, comp, **kw):
        self.comp = comp
        self.list_children = kw.get('list_children')
        self.list_implicit_children = kw.get('list_implicit_children')
        self.list_top = kw.get('list_top') or (self.list_children is False and
                                               self.list_implicit_children is False)
        self.list_root = kw.get('list_root') 

    def build(self):
        items = []
        if self.list_top:
            items.extend(self.comp.root.top_components)
            if self.list_root:
                items.append(self.comp.root)
        elif self.list_children:
            items.extend(self.comp.children)
        elif self.list_implicit_children:
            for top in self.comp.root.top_components:
                child = self.comp._find_implicit_child_for_top(top)
                if child:
                    items.append(child)
        return items
        
class RealComponent(BasicComponent):
    def __init__(self, name, path, parent, url=None):
        BasicComponent.__init__(self, name, path, parent)
        self.config = config.Config(os.path.join(self.abs_path, ".depconfig"))
        self.repository = scm.Repository.create(self.abs_path, url)

    def _get_url(self):
        return self.repository.url
    
    def _read_config(self):
        if self.config.need_read:
            if self.config.exists():
                self.config.read()
            self._read_repository_state_from_parent_config()

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

    def _find_child_config_section(self, child_name):
        if not self.config.has_section("dep", child_name):
            return None
        return self.config["dep.{}".format(child_name)]
        
    def _add_to_parent_config(self):
        if self.parent._find_child_config_section(self.name):
            error("Cannot add {} to {}, already exists", self, self.parent)
            return
        parent_section = self.parent.config.add_section("dep", self.name)
        parent_section["relpath"] = self.rel_path
        
    def _read_repository_state_from_parent_config(self):
        if self.parent:
            parent_section = self.parent._find_child_config_section(self.name)
            if parent_section:
                self.repository.read_state_from_config_section(parent_section)
        
    def _refresh_work_dir(self):
        self.repository.refresh()
        
    def _record_to_parent_config(self):
        if self.parent:        
            parent_section = self.parent._find_child_config_section(self.name)
            if parent_section:
                self.repository.record()
                self.repository.write_state_to_config_section(parent_section)

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
        self._add_child(new_dep)        
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

    def list_dependencies(self):
        self._validate_has_repo()
        self.read_dep_tree()
        local = self.find_local_component()
        items = ComponentList(local,
                              list_children=opts.args.list_children,
                              list_implicit_children=opts.args.list_implicit_children,
                              list_root=opts.args.list_root).build()
        for comp in items:
            print comp.name

    def _foreach_pre(self, comp, kw):
        if kw.get('foreach_only_modified') and not comp.repository.has_local_modifications():
            return False
        if kw.get('foreach_only_ahead') and not comp.repository.is_ahead():
            return False
        return True
    
    def _foreach_post(self, comp, kw):
        if kw.get('foreach_record'):
            self.record_dependencies()
        if kw.get('foreach_refresh'):
            self.refresh_dependencies()
        
    def foreach_dependency(self, cmd, **kw):
        self._validate_has_repo()
        self.read_dep_tree()
        for top in self.root.top_components:
            if self._foreach_pre(top, kw):
                top.run_command(cmd)
                self._foreach_post(top, kw)
        if self._foreach_pre(self.root, kw):
            self.root.run_command(cmd)
            self._foreach_post(self.root, kw)

    def status_dependencies(self):
        self._validate_has_repo()
        self.read_dep_tree()
        status("M  Branch           Commit                                    Ahead Behind Path")
        status("-- ---------------  ---------------------------------------- ------ ------ -----------------------")
        for top in self.root.top_components:
            top.repository.status_brief(top.rel_path)
        self.root.repository.status_brief(".")
        
    def _debug_dump_content(self, prefix=""):
        self.config.debug_dump(prefix)
        self.repository.debug_dump(prefix)        

class RootComponent(RealComponent):
    def __init__(self):
        if opts.args.local:
            error("--local flag not yet supported")
        path = find_root_work_dir()
        if path is None:
            path = os.getcwd()
        name = scm.Repository.determine_name_from_url(path)
        RealComponent.__init__(self, name, path, None)
        self.top_components = []

    def _move_top_component_to_front(self):
        pass
    
    def _build_dep_tree_implicit_recurse(self, refresh=False):
        RealComponent._build_dep_tree_implicit_recurse(self, refresh)        
        for child in self.top_components:
            child._build_dep_tree_implicit_recurse(refresh)

    def _find_top_component(self, name):
        return next((c for c in self.top_components if c.name == name), None)

    def _create_top_component(self, name, section, url):
        parent = self
        if section:
            path = section["relpath"]
            url = section["url"]
        else:
            dep_dir = parent.config["core"]["default-dep-dir"]
            path = os.path.join(dep_dir, name)
        return TopComponent(name, path, parent, url)

    def _create_link_component(self, name, section, parent, top_component):
        if section:
            path = section["relpath"]
        else:
            dep_dir = parent.top_component.config["core"]["default-dep-dir"]
            path = os.path.join(dep_dir, name)
        return LinkComponent(name, path, parent, top_component)

    def _find_or_create_component(self, section=None, url=None, parent=None, refresh=False):
        if parent is None:
            error("Must pass parent to _find_or_create_component")
        if (not section and not url) or (section and url):
            error("Must pass section or url to _find_or_create_component")
        if section:
            name = section.subname
        else:
            name = scm.Repository.determine_name_from_url(url)
        top = self._find_top_component(name)
        new_top = False
        if top is None:
            top = self._create_top_component(name, section, url)
            new_top = True
        if parent is self:
            comp = top
            if new_top and refresh:
                top._refresh_work_dir()
        else:
            if new_top:
                top._build_dep_tree_recurse(refresh)
            comp = self._create_link_component(name, section, parent, top)
            if refresh:
                comp._refresh_work_dir()
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
        parent.root.top_components.insert(0, self)

    def _move_top_component_to_front(self):
        self.root.top_components.remove(self)
        self.root.top_components.insert(0, self)
        
class LinkComponent(BasicComponent):
    def __init__(self, name, path, parent, top_component):
        BasicComponent.__init__(self, name, path, parent)
        self.top_component = top_component

    def _get_url(self):
        return self.top_component._get_url()

    def _read_config(self):
        self.top_component._read_config()

    def _write_config(self):
        self.top_component._write_config()

    def _refresh_work_dir(self):
        self.top_component._refresh_work_dir()
        if not os.path.isdir(self.abs_path):
            status("Linking {} to {}", self.top_component, self)
            source_abs_path = self.top_component.real_path
            dest_abs_path = self.real_path
            debug("source_abs_path={}", source_abs_path)
            debug("dest_abs_path={}", dest_abs_path)
            make_relative_symlink(source_abs_path, dest_abs_path)

    def _record_to_parent_config(self):
        if self.parent:
            top_parent = self.parent.top_component
            top_parent_section = top_parent._find_child_config_section(self.name)
            if top_parent_section:
                self.top_component.repository.record()
                self.top_component.repository.write_state_to_config_section(top_parent_section)

    def _find_child_config_section(self, child_name):
        return self.top_component._find_child_config_section(child_name)

    def _get_child_config_sections(self):
        return self.top_component._get_child_config_sections()
        
    def _debug_dump_content(self, prefix=""):
        BasicComponent._debug_dump_content(self, prefix)        
