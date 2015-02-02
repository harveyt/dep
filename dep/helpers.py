#
# Helper Functions
# ================
#
# %%LICENSE%%
#
import sys
import os
import subprocess
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

def run(*cmd, **kw):
    status = 0
    cmd = filter(None, cmd)
    cmd_text = ' '.join(cmd)
    cwd = kw.get('cwd')
    if cwd == os.getcwd():
        cwd = None
    query = kw.get('query')
    pipe = kw.get('pipe')
    if not query and not pipe:
        if cwd:
            verbose("-> pushd {}", cwd)
        verbose("-> {}", cmd_text)
        if cwd:
            verbose("-> popd")
    if opts.args.dry_run and not query and not pipe:
        return
    try:
        if query:
            return subprocess.check_output(cmd, stderr=subprocess.STDOUT, cwd=cwd)
        elif pipe:
            return subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=cwd)            
        elif opts.args.quiet:
            with open(os.devnull, "wb") as dev_null:
                status = subprocess.call(cmd, stdout=dev_null, cwd=cwd)
        else:
            status = subprocess.call(cmd, cwd=cwd)
        if status != 0:
            error("Execution of '{}' returned exit status {}", cmd_text, status)
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
        if path == os.path.sep:
            return None
