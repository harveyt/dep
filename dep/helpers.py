#
# Helper Functions
# ================
#
# %%LICENSE%%
#
import sys
import os
import subprocess
import re
from dep import opts

def get_program_path():
    return os.path.realpath(__file__)

def error(fmt, *a):
    sys.stderr.write("dep: ")
    sys.stderr.write(fmt.format(*a))
    sys.stderr.write("\n")
    sys.exit(1)

def debug(fmt, *a):
    if not opts.args.debug:
        return
    status(fmt, *a)

def verbose(fmt, *a):
    if not opts.args.verbose:
        return
    status(fmt, *a)

def status(fmt, *a):
    if opts.args.quiet:
        return
    sys.stdout.write(fmt.format(*a))
    sys.stdout.write("\n")

def status_seperator():
    columns = int(os.environ["COLUMNS"])
    if columns is None:
        columns = 80
    status("##" + '=' * (columns - 3))

def validate_path_notexists(path):
    if os.path.exists(path):
        error("Path '{}' already exists", path)

def validate_path_exists(path):
    if not os.path.exists(path):
        error("Path '{}' does not exist", path)
        
def validate_file_notexists(file):
    if os.path.exists(file):
        error("File '{}' already exists", file)
    
def validate_file_exists(file):
    if not os.path.isfile(file):
        error("File '{}' does not exist", file)

def validate_file_notexists(file):
    if os.path.exists(file):
        error("File '{}' already exists", file)

def validate_dir_exists(dir):
    if not os.path.isdir(dir):
        error("Directory '{}' does not exist", dir)

def validate_dir_notexists(dir):
    if os.path.exists(dir):
        error("Directory '{}' already exists", dir)

def validate_dir_notexists_or_empty(dir):
    valid = False
    if os.path.exists(dir):
        if os.path.isdir(dir) and not os.listdir(dir):
            valid = True
    else:
        valid = True
    if not valid:
        error("Directory '{}' exists but is not an empty directory", dir)
        
def quote(arg):
    if re.search(r'\s', arg):
        if '"' in arg:
            return "'{}'".format(arg)
        else:
            return '"{}"'.format(arg)
    return arg

def quote_cmd(cmd):
    return ' '.join([quote(arg) for arg in cmd])

def run(*cmd, **kw):
    exit_status = 0
    cmd = filter(None, cmd)
    cmd_text = quote_cmd(cmd)
    cwd = kw.get('cwd')
    if cwd == os.getcwd():
        cwd = None
    query = kw.get('query')
    pipe = kw.get('pipe')
    allow_failure = kw.get('allow_failure')
    if not query and not pipe:
        if cwd:
            verbose("-> pushd {}", cwd)
        verbose("-> {}", cmd_text)
        if cwd:
            verbose("-> popd")
    if opts.args.dry_run and not query and not pipe:
        status("{}", cmd_text)
        return
    try:
        if query:
            return subprocess.check_output(cmd, stderr=subprocess.STDOUT, cwd=cwd)
        elif pipe:
            return subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=cwd)            
        elif opts.args.quiet:
            with open(os.devnull, "wb") as dev_null:
                exit_status = subprocess.call(cmd, stdout=dev_null, cwd=cwd)
        else:
            exit_status = subprocess.call(cmd, cwd=cwd)
        if exit_status != 0:
            msg = "Execution of '{}' returned exit status {}".format(cmd_text, exit_status)
            if allow_failure:
                status("{}", msg)
            else:
                error("{}", msg)
    except OSError, e:
        error("Cannot execute '{}': {}'", cmd_text, e)
    except Exception, e:
        error("{}", e)

def run_query(*cmd, **kw):
    return run(*cmd, query=True, **kw)

def make_dirs(dir):
    if os.path.isdir(dir):
        return
    verbose("-> mkdir -p {}", dir)
    if opts.args.dry_run:
        return
    try:
        os.makedirs(dir)
    except OSError, e:
        error("Cannot make directory path '{}'", dir)

class Pipe:
    def __init__(self, *cmd, **kw):
        self.process = run(*cmd, pipe=True, **kw)
        self.cmd_text = ' '.join(filter(None, cmd))        

    def __enter__(self):
        return self.process.stdout

    def __exit__(self, type, value, traceback):
        exit_status = self.process.wait()
        if exit_status != 0:
            error("{} returned exit code {}", self.cmd_text, exit_status)

def find_local_work_dir(path=None):
    if path is None:
        path = os.getcwd()
    path.rstrip(os.path.sep)
    while True:
        config_path = os.path.join(path, ".depconfig")
        if os.path.isfile(config_path):
            return path
        path = os.path.dirname(path)
        if path == os.path.sep:
                return None

def find_root_work_dir(path=None):
    last_work_dir = None
    while True:
        work_dir = find_local_work_dir(path)
        if work_dir is None:
            return last_work_dir
        last_work_dir = work_dir
        path = os.path.dirname(work_dir)
        # If .deproot exists in directory then only directories from here or under can be roots.
        deproot_path = os.path.join(path, ".deproot")
        if os.path.isfile(deproot_path):
            return last_work_dir
        if path == os.path.sep:
            return None

def make_relative_symlink(src, dst):
    # Example: make_relative_symlink("/a/b/c", "/a/d/e")
    # e -> ../b/c
    if os.path.exists(dst):
        error("Cannot make relative symlink from '{}' to '{}', as destination already exists", src, dst)
    dstdir = os.path.dirname(dst)
    relpath = os.path.relpath(src, dstdir)
    make_dirs(dstdir)
    verbose("-> ln -s {} {}", relpath, dst)
    if opts.args.dry_run:
        return
    try:
        os.symlink(relpath, dst)
    except OSError, e:
        error("Cannot make relative symlink from '{}' to '{}': {}", src, dst, e)

def add_local_arguments(parser):
    parser.add_argument("-l", "--local", dest="local", action="store_true",
                        help="Add the new dependency under the local dependency.")
    parser.add_argument("--root", dest="local", action="store_false",
                        help="Add the new dependency under the root dependency (default).")
    
def add_list_arguments(parser):
    parser.add_argument("--no-root", dest="list_root", action="store_false",
                        help="Do not include the root project in list of dependencies")
    parser.add_argument("--root", dest="list_root", action="store_true",
                        help="Include the root project in list of dependencies (default)")
    parser.add_argument("-t", "--top", dest="list_top", action="store_true",
                        help="Include all top explicit dependencies (default)")
    parser.add_argument("-c", "--children", dest="list_children", action="store_true",
                        help="Include only explicit child dependencies of the local working directory")
    parser.add_argument("-i", "--implicit-children", dest="list_implicit_children", action="store_true",
                        help="Include all explicit and implicit child dependencies of the local working directory")
    parser.add_argument("-l", "--local", dest="list_local", action="store_true",
                        help="Include the local dependency and all explicit and implicit child dependencies")    
