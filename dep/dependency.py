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
    def __init__(self, name, parent=None):
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
            child = Dependency(section.subname, self)
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
        self.tree._move_top_node_to_front(top_node)
        return top_node

    def resolve_child_by_dep(self, dep):
        top_node = self._resolve_child_top_node_by_dep(dep)
        if isinstance(self, RootNode):
            top_node.explicit = True
            return top_node
        link_node = self.tree._create_link_node(top_node, self)
        link_node.explicit = True
        return link_node

    def find_child_config_section(self, child_node):
        child_name = child_node.name
        if not self.config.has_section("dep", child_name):
            return None
        return self.config["dep.{}".format(child_name)]

    def _refresh_disk(self):
        pass

    def _record_disk(self):
        pass
    
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

    def _record_disk(self):
        verbose("Record {}", self)
        self.repository.branch = self.branch
        self.repository.commit = self.commit
        self.repository.record()
        parent_section = self.parent.find_child_config_section(self)
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
class Tree:
    def __init__(self, root_path):
        self.root_node = self._create_root_node_for_path(root_path)
        self.top_nodes = []
        self.refresh_mode = False
        self.record_mode = False

    def _build_dependency_tree(self):
        self.root_node._build_dependency_tree()
        self.root_node._add_implicit_children()
        if self.record_mode:
            for top_node in self.top_nodes:
                top_node._record_disk()
            for top_node in self.top_nodes:
                top_node.write_config()
            self.root_node.write_config()
            
    def read_dependency_tree(self):
        self.refresh_mode = False
        self.record_mode = False
        self._build_dependency_tree()

    def refresh_dependency_tree(self):
        self.refresh_mode = True
        self.record_mode = False
        self._build_dependency_tree()

    def record_dependency_tree(self):
        self.refresh_mode = False
        self.record_mode = True        
        self._build_dependency_tree()

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

# --------------------------------------------------------------------------------
def test_dependency(root_path):
    tree = Tree(root_path)
    tree.record_dependency_tree()
    tree.debug_dump()
