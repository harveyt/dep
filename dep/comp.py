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

    def _read_dep_tree_create_children(self):
        pass
    
    def _read_dep_tree_recurse(self):
        self._read_dep_tree_create_children()
        for child in self.children:
            child._read_dep_tree_recurse()

    def refresh_dep_tree(self):
        self.debug_dump("refresh_dep_tree pre: ")
        self._refresh_dep_tree_recurse()
        self.debug_dump("refresh_dep_tree post: ")

    def _refresh_dep_tree_create_children(self):
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

    def _read_dep_tree_create_children(self):
        self._read_config()
    
    def _refresh_dep_tree_create_children(self):
        self.repository.refresh()
        self.config.need_read = True
        self._read_config()

    def _record_dep_tree_to_config():
        pass
        
    def _write_dep_tree_config():
        pass
        
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
# LinkComponent
# Models a link component which points at a RealComponent.
#
class LinkComponent(Component):
    def __init__(self, name, path, parent, url=None):
        Component.__init__(name, path, parent)
    
    def _read_dep_tree_create_children(self):
        pass
    
    def _refresh_dep_tree_create_children(self):
        pass

    def _record_dep_tree_to_config():
        pass
        
    def _write_dep_tree_config():
        pass

    def _debug_dump_content(self, prefix):
        debug("{}linked_component = {}", prefix, self.linked_component)
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
