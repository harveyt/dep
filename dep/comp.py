#
# Components
# ==========
#
# %%LICENSE%%
#
import os;
from dep import config, opts
from dep.helpers import *

class Root:
    def __init__(self):
        self.abs_path = os.getcwd()
        self.config = config.Config(os.path.join(self.abs_path, ".depconfig"))

    def __str__(self):
        return "{} '{}'".format(self.__class__.__name__, self.abs_path)

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

    def debug_dump(self, prefix=""):
        if not opts.args.debug or opts.args.quiet:
            return
        debug("{}--- {} ---", prefix, self)
        debug("{}abs_path = {}", prefix, self.abs_path)

        
