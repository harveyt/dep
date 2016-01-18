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

    def read_children_from_config(self, abs_path):
        children = []
        conf = config.Config(os.path.join(abs_path, ".depconfig"))
        if conf.exists():
            conf.read()
        for section in conf.sections_named("dep"):
            child = Dependency(section.subname, self)
            child._populate_from_config_section(section)            
            children.append(child)
        return children

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
    def __init__(self, tree, dep, parent=None):
        self.tree = tree
        self.dep = dep
        self.abs_path = None
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

    def read_dependency_tree(self):
        child_deps = self.dep.read_children_from_config(self.abs_path)
        for child_dep in reversed(child_deps):
            child_node = self.tree.resolve_dep_to_node(child_dep, self)
            child_node.read_dependency_tree()

    def add_implicit_children(self):
        explicit_children = [c for c in self.children if c.explicit is True]
        for child_node in explicit_children:
            if child_node.explicit is False:
                continue
            child_node.add_implicit_children()
            for child_child_node in reversed(child_node.children):
                existing_child = self.find_child_node_by_name(child_child_node.name)
                if existing_child is not None:
                    continue
                implicit_real_child = child_child_node.real_node
                implicit_child = LinkNode(implicit_real_child, self)
                self.move_child_to_front(implicit_child)

    def move_child_to_front(self, child):
        self.children.remove(child)
        self.children.insert(0, child)
        
    def find_child_node_by_name(self, name):
        return next((c for c in self.children if c.name == name), None)
    
    def __str__(self):
        return "Node '{}' at {}".format(self.name, self.abs_path)
                         
    def debug_dump(self, prefix="", recurse=False):
        debug("{}--- {} ---", prefix, self)
        debug("{}tree = {}", prefix, self.tree)
        if recurse:
            debug("{}dep =", prefix)
            self.dep.debug_dump(prefix + "    ")
        else:
            debug("{}dep = {}", prefix, self.dep)
        debug("{}abs_path = {}", prefix, self.abs_path)
        debug("{}explicit = {}", prefix, self.explicit)
        debug("{}real_node = {}", prefix, self.real_node)        
        if recurse:
            debug("{}parent = {}", prefix, self.parent)
            debug("{}children[] = {{", prefix)
            for i, c in enumerate(self.children):
                if i > 0:
                    debug("{},".format(prefix))
                c.debug_dump("{}[{}] ".format(prefix, i), recurse)
            debug("{}}}", prefix)

# --------------------------------------------------------------------------------
class RealNode(Node):
    def __init__(self, tree, dep, parent=None):
        Node.__init__(self, tree, dep, parent)
        self.real_node = self
        
    def __str__(self):
        return "RealNode '{}' at {}".format(self.name, self.abs_path)
                 
# --------------------------------------------------------------------------------
class RootNode(RealNode):
    def __init__(self, tree, root_path):
        root_path = os.path.realpath(root_path)
        root_dep = Dependency.create_root(root_path)
        RealNode.__init__(self, tree, root_dep)
        self.abs_path = root_path
        self.explicit = True

    def __str__(self):
        return "RootNode '{}' at {}".format(self.name, self.abs_path)

# --------------------------------------------------------------------------------
class TopNode(RealNode):
    def __init__(self, tree, dep, parent):
        RealNode.__init__(self, tree, dep, parent)
        self.abs_path = os.path.join(tree.root_node.abs_path, self.rel_path)
        
    def __str__(self):
        return "TopNode '{}' at {}".format(self.name, self.abs_path)

# --------------------------------------------------------------------------------
class LinkNode(Node):
    def __init__(self, top_node, parent):
        Node.__init__(self, top_node.tree, top_node.dep, parent)
        self.abs_path = os.path.join(self.parent.real_node.abs_path, top_node.rel_path)
        self.real_node = top_node
        
    def __str__(self):
        return "LinkNode '{}' at {}".format(self.name, self.abs_path)
    
# --------------------------------------------------------------------------------
class Tree:
    def __init__(self, root_path):
        self.root_node = RootNode(self, root_path)
        self.top_nodes = []

    def read_dependency_tree(self):
        self.root_node.read_dependency_tree()
        self.root_node.add_implicit_children()

    def find_top_node_by_name(self, name):
        return next((c for c in self.top_nodes if c.name == name), None)

    def _move_top_node_to_front(self, top_node):
        self.root_node.move_child_to_front(top_node)
        self.top_nodes.remove(top_node)
        self.top_nodes.insert(0, top_node)
    
    def resolve_dep_to_top_node(self, dep):
        top_node = self.find_top_node_by_name(dep.name)
        if top_node is None:
            top_node = TopNode(self, dep, self.root_node)
            self.top_nodes.insert(0, top_node)
        self._move_top_node_to_front(top_node)
        return top_node

    def resolve_dep_to_node(self, dep, parent_node):
        top_node = self.resolve_dep_to_top_node(dep)
        if parent_node is self.root_node:
            top_node.explicit = True
            return top_node
        link_node = LinkNode(top_node, parent_node)
        link_node.explicit = True
        return link_node

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
    tree.read_dependency_tree()
    tree.debug_dump()

    

