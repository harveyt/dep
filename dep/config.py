#
# Configuration File
# ==================
#
# %%LICENSE%%
#
import sys
import os
import re
from dep import opts
from dep.helpers import *

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
        if opts.args.dry_run:
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
