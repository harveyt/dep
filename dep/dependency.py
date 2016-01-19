#
# Dependency
# ==========
#
# %%LICENSE%%
#
import os;
from dep import config, opts, scm
from dep.helpers import *

# --------------------------------------------------------------------------------
class Dependency:
    def __init__(self, name):
        self.name = name
        self.rel_path = None
        self.url = None
        self.vcs = None
        self.branch = None
        self.commit = None

    @staticmethod
    def create_root(root_path):
        name = scm.Repository.determine_name_from_url(root_path)
        root_dep = Dependency(name)
        root_dep.rel_path = "."
        return root_dep

    def read_children_from_config(self, conf):
        children = []
        for section in conf.sections_named("dep"):
            child = Dependency(section.subname)
            child._populate_from_config_section(section)            
            children.append(child)
        return children

    def _resolve_with_field(self, dep, field, status, issues):
        self_value = eval("self.{}".format(field))
        dep_value = eval("dep.{}".format(field))
        if self_value != dep_value:
            status = False            
            issues += "\n\texisting {}:   '{}'\n\tdependency {}: '{}'".format(field, self_value, field, dep_value)
        return (status, issues)
                          
    def resolve_with(self, dep):
        status = True
        issues = ""
        (status, issues) = self._resolve_with_field(dep, "name", status, issues)
        # TODO: Allow rel_path to be different for links?        
        (status, issues) = self._resolve_with_field(dep, "rel_path", status, issues)
        (status, issues) = self._resolve_with_field(dep, "url", status, issues)
        (status, issues) = self._resolve_with_field(dep, "vcs", status, issues)
        (status, issues) = self._resolve_with_field(dep, "branch", status, issues)
        (status, issues) = self._resolve_with_field(dep, "commit", status, issues)
        return (status, issues)

    def _populate_from_config_section(self, section):
        self.rel_path = section["relpath"]
        self.url = section["url"]
        self.vcs = section["vcs"]
        self.branch = section["branch"]
        self.commit = section["commit"]

    def __str__(self):
        return "Dependency '{}' at {}".format(self.name, self.rel_path)

    def debug_dump(self, prefix=""):
        if not opts.args.debug or opts.args.quiet:
            return
        debug("{}--- {} ---", prefix, self)
        debug("{}name = {}", prefix, self.name)
        debug("{}rel_path = {}", prefix, self.rel_path)
        debug("{}url = {}", prefix, self.url)
        debug("{}vcs = {}", prefix, self.vcs)
        debug("{}branch = {}", prefix, self.branch)
        debug("{}commit = {}", prefix, self.commit)

# --------------------------------------------------------------------------------
class Node:
    def __init__(self, tree, abs_path, dep, config, parent=None):
        self.tree = tree
        self.abs_path = abs_path        
        self.dep = dep
        self.config = config
        self.explicit = False
        self.real_node = None
        self.parent = parent
        self.children = []
        if parent is not None:
            parent.children.insert(0, self)

    @property
    def name(self):
        return self.dep.name

    @property
    def rel_path(self):
        return self.dep.rel_path

    @property
    def url(self):
        return self.dep.url

    @property
    def vcs(self):
        return self.dep.vcs
    
    @property
    def branch(self):
        return self.dep.branch

    @property
    def commit(self):
        return self.dep.commit

    def read_config(self):
        if self.config.need_read:
            if self.config.exists():
                self.config.read()

    def write_config(self):
        if self.config.need_write:
            self.repository.pre_edit(self.config.path)
            self.config.write()
            self.repository.post_edit(self.config.path)

    def _validate_has_repository(self):
        if self.repository is None or self.repository.vcs == "file":
            error("{} does not have a non-file based SCM repository", self)
                
    def _build_dependency_tree(self):
        self.read_config()
        child_deps = self.dep.read_children_from_config(self.config)
        for child_dep in reversed(child_deps):
            child_node = self.resolve_child_by_dep(child_dep)
            child_node._build_dependency_tree()

    def _add_implicit_children(self):
        explicit_children = [c for c in self.children if c.explicit is True]
        for child_node in explicit_children:
            if child_node.explicit is False:
                continue
            child_node._add_implicit_children()
            for child_child_node in reversed(child_node.children):
                existing_child = self.find_child_node_by_name(child_child_node.name)
                if existing_child is not None:
                    continue
                implicit_real_child = child_child_node.real_node
                implicit_child = self.tree._create_link_node(implicit_real_child, self)
                self.move_child_to_front(implicit_child)

    def move_child_to_front(self, child):
        self.children.remove(child)
        self.children.insert(0, child)
        
    def find_child_node_by_name(self, name):
        return next((c for c in self.children if c.name == name), None)

    def _get_child_top_node_by_dep(self, dep):
        for top_node in self.tree.top_nodes:
            if top_node.name == dep.name:
                (status, issues) = top_node.dep.resolve_with(dep)
                if status:
                    return top_node
                else:
                    error("Cannot resolve dependency:\n\t{}\n\t{}\n{}", self.real_node, dep, issues)
        return self.tree._create_top_node_for_dep(dep)

    def _resolve_child_top_node_by_dep(self, dep):
        top_node = self._get_child_top_node_by_dep(dep)
        if isinstance(self, RootNode):
            top_node.explicit = True
        self.tree._move_top_node_to_front(top_node)
        return top_node

    def _resolve_child_link_node(self, top_node):
        for node in self.children:
            if isinstance(node, LinkNode) and node.real_node is top_node:
                return node
        link_node = self.tree._create_link_node(top_node, self)
        link_node.explicit = True
        return link_node

    def resolve_child_by_dep(self, dep):
        top_node = self._resolve_child_top_node_by_dep(dep)
        if isinstance(self, RootNode):
            return top_node
        link_node = self._resolve_child_link_node(top_node)
        return link_node

    def find_child_config_section(self, child_node):
        child_name = child_node.name
        if not self.config.has_section("dep", child_name):
            return None
        return self.config["dep.{}".format(child_name)]

    def add_child_config_section(self, child_name):
        if self.config.has_section("dep", child_name):
            error("Cannot add {} to {}, already exists", child_name, self)
        return self.config.add_section("dep", child_name)
            
    def _refresh_disk(self):
        pass

    def _record_disk(self, to_parent=None):
        pass

    def _status_disk(self, kw):
        pass

    def _init_disk(self):
        error("Cannot initialise '{}'", self)

    def _add_disk(self, url):
        pass

    def _run_command(self, cmd, kw=None):
        status_seperator()
        status("## {}:", self)
        status("##")
        allow_failure = (None if kw is None else kw.get('allow_failure'))
        old_quiet = opts.args.quiet
        opts.args.quiet = False
        run(*cmd, shell=True, cwd=self.abs_path, allow_failure=allow_failure)
        opts.args.quiet = old_quiet

    def _foreach_run(self, cmd, kw):
        if self._foreach_run_pre(kw):
            self._run_command(cmd, kw)
            self._foreach_run_post(kw)

    def _foreach_run_pre(self, kw):
        if kw.get('foreach_only_modified') and not self.repository.has_local_modifications():
            return False
        if kw.get('foreach_only_ahead') and not self.repository.is_ahead():
            return False
        return True

    def _foreach_run_post(self, kw):
        if kw.get('foreach_record') and not opts.args.dry_run:
            self.tree.record_dependency_tree()
        if kw.get('foreach_refresh') and not opts.args.dry_run:
            self.tree.refresh_dependency_tree()
            
    def __str__(self):
        return "Node '{}' at {}".format(self.name, self.abs_path)
                         
    def debug_dump(self, prefix="", recurse=False):
        debug("{}--- {} ---", prefix, self)
        debug("{}tree = {}", prefix, self.tree)
        debug("{}abs_path = {}", prefix, self.abs_path)
        if recurse:
            debug("{}dep =", prefix)
            self.dep.debug_dump(prefix + "    ")
            debug("{}config =", prefix)
            self.config.debug_dump(prefix + "    ")
        else:
            debug("{}dep = {}", prefix, self.dep)
            debug("{}config = {}", prefix, self.config)            
        debug("{}explicit = {}", prefix, self.explicit)
        debug("{}real_node = {}", prefix, self.real_node)
        self._debug_dump_content(prefix, recurse)
        if recurse:
            debug("{}parent = {}", prefix, self.parent)
            debug("{}children[] = {{", prefix)
            for i, c in enumerate(self.children):
                if i > 0:
                    debug("{},".format(prefix))
                c.debug_dump("{}[{}] ".format(prefix, i), recurse)
            debug("{}}}", prefix)

    def _debug_dump_content(self, prefix, recurse):
        pass

# --------------------------------------------------------------------------------
class RealNode(Node):
    def __init__(self, tree, abs_path, dep, parent=None, url=None):
        conf = config.Config(os.path.join(abs_path, ".depconfig"))
        Node.__init__(self, tree, abs_path, dep, conf, parent)
        self.real_node = self
        self.repository = scm.Repository.create(self.abs_path, url)

    def _status_disk(self, kw):
        self.repository.branch = self.branch
        self.repository.commit = self.commit
        self.repository.status(self.rel_path, kw)

    def _add_child_node(self, name, rel_path, url, vcs):
        new_dep = Dependency(name)
        new_dep.rel_path = rel_path
        new_dep.url = url
        new_dep.vcs = vcs                        
        # Resolve the dependency to what should be a new top node
        new_node = self.resolve_child_by_dep(new_dep)
        new_top_node = new_node.real_node
        new_config_section = self.add_child_config_section(name)
        new_config_section["relpath"] = rel_path
        verbose("Adding {}\n    as {}\n    to {}", new_dep, new_top_node, self)
        return new_node

    def _add_child_node_refresh_and_record(self, new_node):
        new_top_node = new_node.real_node
        new_parent_top_node = new_node.parent.real_node
        # Refresh both the real node and possibly the link node
        new_top_node._refresh_disk()
        if new_node is not new_top_node:
            new_node._refresh_disk()
        # Read the config (for any dependencies from new node)
        new_top_node.read_config()
        # Record new node state
        new_top_node._record_disk(new_parent_top_node)
        new_top_node.dep.branch = new_top_node.repository.branch
        new_top_node.dep.commit = new_top_node.repository.commit
        
    def _add_disk(self, url):
        # Determine default values from url
        self.tree._validate_url_notexists(url)
        name = scm.Repository.determine_name_from_url(url)
        self.tree._validate_name_notexists(name)
        dep_dir = self.config["core"]["default-dep-dir"]
        rel_path = os.path.join(dep_dir, name)
        vcs = scm.Repository.determine_vcs_from_url(url)
        # Create new child top node
        new_node = self._add_child_node(name, rel_path, url, vcs)
        new_top_node = new_node.real_node
        # Refresh the new child node and then record its state
        self._add_child_node_refresh_and_record(new_node)
        # Write our config (which now includes new node)
        self.write_config()
        # Ignore the new top node directory
        self.repository.add_ignore(new_top_node.rel_path)
        
    def __str__(self):
        return "RealNode '{}' at {}".format(self.name, self.abs_path)

    def _debug_dump_content(self, prefix, recurse):
        if recurse:
            debug("{}repository =", prefix)
            if self.repository is not None:
                self.repository.debug_dump(prefix + "    ")
        else:
            debug("{}repository = {}", prefix, self.repository)
    
# --------------------------------------------------------------------------------
class RootNode(RealNode):
    def __init__(self, tree, root_path):
        root_path = os.path.realpath(root_path)
        root_dep = Dependency.create_root(root_path)
        RealNode.__init__(self, tree, root_path, root_dep)
        self.explicit = True

    def _init_disk(self):
        verbose("Initializing {}", self)
        validate_file_notexists(self.config.path)
        core = self.config.add_section("core")
        core["default-dep-dir"] = "dep"
        self.config.need_read = False
        self.write_config()
        self.debug_dump("init post: ")
        
    def __str__(self):
        return "RootNode '{}' at {}".format(self.name, self.abs_path)

# --------------------------------------------------------------------------------
class TopNode(RealNode):
    def __init__(self, tree, dep, parent):
        abs_path = os.path.join(tree.root_node.abs_path, dep.rel_path)
        RealNode.__init__(self, tree, abs_path, dep, parent, dep.url)
        
    def _refresh_disk(self):
        verbose("Refresh {}", self)
        self.repository.branch = self.branch
        self.repository.commit = self.commit
        self.repository.refresh()

    def _record_disk(self, to_parent=None):
        verbose("Record {}", self)
        if to_parent is None:
            to_parent = self.parent
        self.repository.branch = self.branch
        self.repository.commit = self.commit
        self.repository.record()
        parent_section = to_parent.find_child_config_section(self)
        self.repository.write_state_to_config_section(parent_section)
        
    def __str__(self):
        return "TopNode '{}' at {}".format(self.name, self.abs_path)

# --------------------------------------------------------------------------------
class LinkNode(Node):
    def __init__(self, top_node, parent):
        abs_path = os.path.join(parent.real_node.abs_path, top_node.rel_path)
        Node.__init__(self, top_node.tree, abs_path, top_node.dep, top_node.config, parent)
        self.real_node = top_node

    def _refresh_disk(self):
        verbose("Refresh {}", self)
        if not os.path.isdir(self.abs_path):
            status("Linking {}\n     to {}", self.abs_path, self.real_node.abs_path)
            source_abs_path = self.real_node.abs_path
            dest_abs_path = self.abs_path
            debug("source_abs_path={}", source_abs_path)
            debug("dest_abs_path={}", dest_abs_path)
            make_relative_symlink(source_abs_path, dest_abs_path)
        
    def __str__(self):
        return "LinkNode '{}' at {}".format(self.name, self.abs_path)

# --------------------------------------------------------------------------------
class TreeList:
    def __init__(self, tree, kw):
        self.tree = tree
        self.list_children = kw.get('list_children')
        self.list_implicit_children = kw.get('list_implicit_children')
        self.list_local = kw.get('list_local')
        self.list_top = kw.get('list_top') or (not self.list_children and
                                               not self.list_implicit_children and
                                               not self.list_local)
        self.list_root = kw.get('list_root')

    def build(self):
        items = []
        if self.list_top:
            items.extend(self.tree.top_nodes)
            if self.list_root:
                items.append(self.tree.root_node)
        else:
            local_node = self.tree._find_local_real_node()
            if self.list_children:
                for child in local_node.children:
                    if child.explicit is True:
                        items.append(child.real_node)
            elif self.list_implicit_children:
                items.extend(local_node.children)
            elif self.list_local:
                items.extend(local_node.children)
                items.append(local_node)
        return items
        
# --------------------------------------------------------------------------------
class Tree:
    def __init__(self, root_path=None):
        if root_path is None:
            root_path = find_root_work_dir()
            if root_path is None:
                error("Cannot find root dependency working directory from '{}'", os.getcwd())
        root_path = os.path.realpath(root_path)
        self.root_node = self._create_root_node_for_path(root_path)
        self.top_nodes = []
        self.refresh_mode = False
        self.record_mode = False

    # --------------------------------------------------------------------------------
    # Begin General Tree API
    #
    def add_dependency(self, url):
        self._validate_has_repository()
        self.read_dependency_tree()
        parent_node = self.root_node
        if opts.args.local:
            parent_node = self._find_local_real_node()
        parent_node._add_disk(url)
        self.refresh_dependency_tree()
    
    def branch_dependency_tree(self, branch_name, branch_startpoint, kw):
        self._validate_has_repository()        
        self.read_dependency_tree()
        node_list = TreeList(self, kw).build()
        for node in node_list:
            node.repository.create_branch(branch_name, branch_startpoint)
        starting_msg = (" with start point '{}'".format(branch_startpoint) if branch_startpoint is not None else "")
        commit_msg = "Created branch '{}'{}".format(branch_name, starting_msg)
        kw.update(foreach_force_all=True)
        self.commit_dependency_tree(["--allow-empty", "-m", commit_msg], kw)
    
    def commit_dependency_tree(self, commit_args, kw):
        # TODO: Should call self.repository to do work!
        self.foreach_dependency(["git", "add", "--all", "."], kw)
        if kw.get('foreach_force_all'):
            kw.update(foreach_record=True, foreach_only_modified=False)
        else:
            kw.update(foreach_record=True, foreach_only_modified=True)
        self.foreach_dependency(["git", "commit"] + commit_args, kw)
        
    def foreach_dependency(self, cmd, kw):
        self._validate_has_repository()        
        self.read_dependency_tree()
        node_list = TreeList(self, kw).build()
        for node in node_list:
            node._foreach_run(cmd, kw)

    def init_dependency(self):
        self.root_node._init_disk()

    def list_dependency_tree(self, kw):
        self._validate_has_repository()        
        self.read_dependency_tree()
        node_list = TreeList(self, kw).build()
        for node in node_list:
            print node.name
    
    def read_dependency_tree(self):
        self.refresh_mode = False
        self.record_mode = False
        self._build_dependency_tree()

    def refresh_dependency_tree(self):
        self._validate_has_repository()
        self.refresh_mode = True
        self.record_mode = False
        self._build_dependency_tree()

    def record_dependency_tree(self):
        self._validate_has_repository()        
        self.refresh_mode = False
        self.record_mode = True        
        self._build_dependency_tree()

    def status_dependency_tree(self, kw):
        self._validate_has_repository()        
        self.read_dependency_tree()
        node_list = TreeList(self, kw).build()
        kw['status_first'] = True
        for node in node_list:
            node._status_disk(kw)
            kw['status_first'] = False
            
    #        
    # End General Tree API
    # --------------------------------------------------------------------------------
    # Validation
    
    def _validate_has_repository(self):
        self.root_node._validate_has_repository()

    def _validate_url_notexists(self, url):
        existing_node = self._find_real_node_by_url(url)
        if existing_node is not None:
            error("Cannot add URL '{}'\n    Already exists as {}", url, existing_node)

    def _validate_name_notexists(self, name):
        existing_node = self._find_real_node_by_name(name)
        if existing_node is not None:
            error("Cannot add name '{}'\n    Already exists as {}", name, existing_node)

    # --------------------------------------------------------------------------------
        
    def _build_dependency_tree(self):
        self.root_node._build_dependency_tree()
        self.root_node._add_implicit_children()
        if self.record_mode:
            for top_node in self.top_nodes:
                top_node._record_disk()
            for top_node in self.top_nodes:
                top_node.write_config()
            self.root_node.write_config()
        
    def _refresh_disk(self, node):
        if self.refresh_mode:
            node._refresh_disk()

    def _create_root_node_for_path(self, root_path):
        root_node = RootNode(self, root_path)
        return root_node

    def _create_top_node_for_dep(self, dep):
        top_node = TopNode(self, dep, self.root_node)
        self.top_nodes.append(top_node)
        self._refresh_disk(top_node)
        return top_node

    def _create_link_node(self, top_node, parent):
        link_node = LinkNode(top_node, parent)
        self._refresh_disk(link_node)        
        return link_node

    def _move_top_node_to_front(self, top_node):
        self.root_node.move_child_to_front(top_node)
        self.top_nodes.remove(top_node)
        self.top_nodes.insert(0, top_node)

    def _find_local_real_node(self):
        local_work_dir = find_local_work_dir()
        if local_work_dir is None:
            error("Cannot find local dependency working directory from '{}'", os.getcwd())
        local_real_path = os.path.realpath(local_work_dir)
        return self._find_real_node_by_abs_path(local_real_path)

    def _find_real_node_by_abs_path(self, abs_path):
        if self.root_node.abs_path == abs_path:
            return self.root_node
        for top_node in self.top_nodes:
            if top_node.abs_path == abs_path:
                return top_node
        return None

    def _find_real_node_by_url(self, url):
        if self.root_node.url == url:
            return self.root_node
        for top_node in self.top_nodes:
            if top_node.url == url:
                return top_node
        return None

    def _find_real_node_by_name(self, name):
        if self.root_node.name == name:
            return self.root_node
        for top_node in self.top_nodes:
            if top_node.name == name:
                return top_node
        return None
    
    def __str__(self):
        return "Tree '{}' at {}".format(self.root_node.name, self.root_node.abs_path)

    def debug_dump_brief(self, node, prefix=""):
        flag = ("explicit" if node.explicit is True else "implicit")
        style = ("link" if isinstance(node, LinkNode) else
                 ("top" if isinstance(node, TopNode) else "root"))
        debug("{}{} {} {} {}", prefix, node.name, flag, style, node.abs_path)
        for child in node.children:
            self.debug_dump_brief(child, prefix + "  ")
    
    def debug_dump(self, prefix=""):
        debug("{}--- {} ---", prefix, self)
        debug("{}Brief:", prefix)
        self.debug_dump_brief(self.root_node, prefix)
        debug("{}root_node = ", prefix)
        self.root_node.debug_dump(prefix + "    ", True)
        debug("{}top_nodes = {{", prefix)
        for i, c in enumerate(self.top_nodes):
            if i > 0:
                debug("{},".format(prefix))
            c.debug_dump("{}[{}] ".format(prefix, i))
        debug("{}}}", prefix)
