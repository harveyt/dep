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
            parent.children.append(self)

    def __str__(self):
        return "{} '{}'".format(self.__class__.__name__, self.name)

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
    
class Root(BasicComponent):
    def __init__(self):
        cwd = find_root_work_dir()
        if cwd is None:
            cwd = os.getcwd()
        name = scm.Repository.determine_name_from_url(cwd)
        BasicComponent.__init__(self, name, cwd, None)
        self.config = config.Config(os.path.join(self.abs_path, ".depconfig"))

    def _has_config(self):
        return self.config.exists()
        
    def _read_config(self):
        self.config.read()

    def _write_config(self):
        self.config.write()
        
    def initialize_new_config(self):
        verbose("Initializing {}", self)
        validate_file_notexists(self.config.path)
        core = self.config.add_section("core")
        core["default-dep-dir"] = "dep"
        self.config.need_read = False
        self._write_config()
        self.debug_dump("init post: ")

    def _debug_dump_content(self, prefix=""):
        self.config.debug_dump(prefix)


        
