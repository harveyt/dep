#
# Source Code Management
# ======================
#
# %%LICENSE%%
#
import os
import re
from dep import opts
from dep.helpers import *

class Repository:
    def __init__(self, work_dir, url, vcs, name):
        self.work_dir = work_dir
        self.url = url
        self.vcs = vcs
        self.name = name
        self.branch = None
        self.commit = None

    def write_state_to_config_section(self, section):
        section["url"] = self.url
        section["vcs"] = self.vcs
        if self.branch:
            section["branch"] = self.branch
        if self.commit:
            section["commit"] = self.commit

    def read_state_from_config_section(self, section):
        self.branch = section["branch"] if section.has_key("branch") else None
        self.commit = section["commit"] if section.has_key("commit") else None

    def read_state_from_disk(self):
        pass
        
    @staticmethod
    def determine_vcs_from_url(url):
        # TODO: Hard coded for now
        return "git"

    @staticmethod
    def determine_vcs_from_work_dir(work_dir):
        # TODO: Hard coded for now                
        if GitRepository.is_present(work_dir):
            return "git"
        else:
            return "file"
        
    @staticmethod
    def determine_name_from_url(url):
        # TODO: Hard coded for now        
        name = os.path.basename(url)
        name = re.sub(r"\.git$", "", name)        
        return name
    
    @staticmethod
    def create(work_dir, url):
        if not url:
            url = "file://{}".format(work_dir)
            vcs = Repository.determine_vcs_from_work_dir(work_dir)
        else:
            vcs = Repository.determine_vcs_from_url(url)
        # TODO: Support more VCS
        if vcs == "git":
            return GitRepository(work_dir, url)
        elif vcs == "file":
            return FileRepository(work_dir, url)
        else:
            error("Cannot determine VCS from repository URL '{}'", url)

    def debug_dump(self, prefix=""):
        if not opts.args.debug or opts.args.quiet:
            return
        debug("{}--- {} ---", prefix, self)
        debug("{}work_dir = {}", prefix, self.work_dir)
        debug("{}url = {}", prefix, self.url)
        debug("{}vcs = {}", prefix, self.vcs)
        debug("{}name = {}", prefix, self.name)        
        debug("{}branch = {}", prefix, self.branch)
        debug("{}commit = {}", prefix, self.commit)        

class FileRepository(Repository):
    def __init__(self, work_dir, url):
        name = Repository.determine_name_from_url(url)
        Repository.__init__(self, work_dir, url, "file", name)

    def __str__(self):
        return "{} '{}'".format(self.__class__.__name__, self.work_dir)

    def register(self, path):
        pass

    def unregister(self, path):
        pass

    def pre_edit(self, path):
        pass

    def post_edit(self, path):
        pass

    def download(self):
        pass

    def checkout(self, branch=None, commit=None):
        pass
    
    def has_ignore(self, path):
        return False

    def add_ignore(self, path):
        pass

    def remove_ignore(self, path):
        pass

    def has_local_modifications(self):
        return True
   
    def refresh(self):
        pass

    def record(self):
        pass

    def status(self, path, kw):
        pass

    def create_branch(self, name, startpoint):
        pass

class GitRepository(Repository):
    def __init__(self, work_dir, url):
        name = Repository.determine_name_from_url(url)
        Repository.__init__(self, work_dir, url, "git", name)
        # TODO: Better way to find this?
        self.git_dir = os.path.join(work_dir, ".git")
        self.ignore_file = os.path.join(work_dir, ".gitignore")
        self.quiet_flag = "--quiet" if opts.args.quiet else None

    def __str__(self):
        return "{} '{}'".format(self.__class__.__name__, self.git_dir)

    def read_state_from_disk(self):
        if os.path.exists(self.git_dir):
            self.branch = self._get_branch()
            self.commit = self._get_commit()
    
    @staticmethod
    def is_present(work_dir):
        git_dir = os.path.join(work_dir, ".git")
        return os.path.exists(git_dir)
        
    def register(self, path):
        run("git", "add", path, cwd=self.work_dir)

    def unregister(self, path):
        run("git", "rm", "--cached", path, cwd=self.work_dir)

    def pre_edit(self, path):
        pass

    def post_edit(self, path):
        run("git", "add", path, cwd=self.work_dir)

    def download(self):
        validate_dir_notexists(self.work_dir)
        validate_dir_notexists(self.git_dir)
        status("Downloading {}\n    from '{}'", self, self.url)
        run("git", "clone", self.quiet_flag, "--no-checkout", self.url, self.work_dir)

    def _is_working_dir_empty(self):
        work_dir_contents = filter(lambda entry: not entry in [".", "..", ".git"], os.listdir(self.work_dir))
        return len(work_dir_contents) == 0
        
    def _need_checkout(self, branch=None, commit=None, force=False):
        debug("_need_checkout: force={}", force)
        if force or self._is_working_dir_empty():
            return True
        if branch is not None:
            cur_branch = self._get_branch()
            debug("_need_checkout: cur_branch={} required={}", cur_branch, branch)
            if cur_branch != branch:
                return True
        if commit is not None:
            cur_commit = self._get_commit()
            debug("_need_checkout: cur_commit={} required={}", cur_commit, commit)
            if cur_commit != commit:
                return True
        return False

    def checkout(self, branch=None, commit=None):
        if not self._need_checkout(branch=branch, commit=commit):
            return
        branch_flag = None if branch is None else "-B"
        branch_name = None if branch is None else self._branch_name_from_ref(branch)
        commit_flag = None if commit is None else commit
        branch_mesg = "" if branch is None else "\n    on branch '{}'".format(branch)        
        commit_mesg = "" if commit is None else "\n    at commit '{}'".format(commit)
        status("Checkout {}{}{}\n    in '{}'", self, branch_mesg, commit_mesg, self.work_dir)
        run("git", "checkout", self.quiet_flag, branch_flag, branch_name, commit_flag, cwd=self.work_dir)

    def _read_ignore(self):
        if not os.path.exists(self.ignore_file):
            return []
        try:
            ignores = []
            with open(self.ignore_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    ignores.append(line)
            return ignores
        except IOError, e:
            error("Cannot open '{}' for reading: {}'", self.ignore_file, e)

    def has_ignore(self, path):
        ignores = self._read_ignore()
        return path in ignores

    def add_ignore(self, path):
        verbose("Adding '{}' to ignore file '{}'", path, self.ignore_file)
        if opts.args.dry_run:
            return
        # TODO: With git we know we can just post_edit the file to do the right thing.
        # TODO: With out vcs we might need register/pre_edit.
        try:
            with open(self.ignore_file, 'a') as f:
                f.write('/{}\n'.format(path))
        except IOError, e:
            error("Cannot open '{}' for writing: {}'", self.ignore_file, e)
        self.post_edit(self.ignore_file)            

    def remove_ignore(self, path):
        verbose("Removing '{}' from ignore file '{}'", path, self.ignore_file)
        if opts.args.dry_run:
            return
        if not os.path.exists(self.ignore_file):
            # TODO: There is no ignore file, so cannot remove?
            return
        # TODO: With git we know we can just post_edit the file to do the right thing.        
        # TODO: With out vcs we might need pre_edit.
        ignores = self._read_ignore()
        try:
            with open(self.ignore_file, 'w') as f:
                for ignore in ignores:
                    if ignore != "/" + path:
                        f.write('{}\n'.format(ignore))
        except IOError, e:
            error("Cannot open '{}' for writing: {}'", self.ignore_file, e)
        self.post_edit(self.ignore_file)
        # TODO: Remove if ignore file is now empty?

    def _get_status(self):
        ahead = 0
        behind = 0
        changes = 0
        with Pipe("git", "status", "--porcelain", "--branch", cwd=self.work_dir) as p:
            for line in p:
                m = re.match(r"##\s+[^[]*(\[(\s*ahead\s+(\d+)\s*)?,?(\s*behind\s+(\d+)\s*)?\])?", line)
                if m:
                    ahead = m.group(3) if m.group(3) else 0
                    behind = m.group(5) if m.group(5) else 0
                else:
                    changes = changes + 1
        return (changes, ahead, behind)    

    def has_local_modifications(self):
        return self._get_status()[0] > 0

    def is_ahead(self):
        return self._get_status()[1] > 0
    
    def refresh(self):
        check_local = True
        if not os.path.exists(self.work_dir):
            check_local = False
        if not os.path.exists(self.git_dir):
            self.download()
        if check_local and self.has_local_modifications():
            error("{} has local modifications, not refreshed", self)
        self.checkout(self.branch, self.commit)

    def _get_branch(self):
        branch = run_query("git", "rev-parse", "--symbolic-full-name", "HEAD", cwd=self.work_dir).rstrip("\n")
        # TODO: Check it is valid!
        if branch == "HEAD":
            # Detached head is not supported (yet), need to checkout a branch.
            # TODO: Support checkout of tag and arbitary commit - pick the first sensible branch containing that commit.
            error("{} is checked out with a detached head, not yet supported; checkout a branch (not a tag)", self)
        return branch

    def _get_commit(self):
        commit = run_query("git", "rev-parse", "HEAD", cwd=self.work_dir).rstrip("\n")
        # TODO: Check it is valid!
        return commit

    def _get_describe(self):
        describe = run_query("git", "describe", "--tags", "--always", cwd=self.work_dir).rstrip("\n")
        # TODO: Check it is valid!
        return describe

    def record(self):
        new_branch = self._get_branch()
        new_commit = self._get_commit()
        if new_branch != self.branch or new_commit != self.commit:
            self.branch = new_branch
            self.commit = new_commit
            status("""Recording {}
    at commit '{}'
    on branch '{}'""", self, self.commit, self.branch)

    def _branch_name_from_ref(self, ref):
        return re.sub(r"refs/heads/", "", ref)

    def status(self, path, kw):
        if kw.get('status_long'):
            self.status_long(path, kw)
        else:
            self.status_short(path, kw)            
            
    def status_short(self, path, kw):
        branch = self.branch
        commit = self.commit
        actual_branch = self._get_branch()
        actual_commit = self._get_commit()
        changes, ahead, behind = self._get_status()
        mod = "?" if changes is None else ("*" if changes else " ")
        if branch is None:
            branch = " " + actual_branch
        else:
            branch = (" " if branch == actual_branch else "*") + actual_branch
        if commit is None:
            commit_diff = " "
        else:
            commit_diff = (" " if commit == actual_commit else "*")
        ahead = "?" if ahead is None else ahead
        behind = "?" if behind is None else behind
        branch = self._branch_name_from_ref(branch)
        if not kw.get('status_commit'):
            actual_commit = self._get_describe()
        commit_value = commit_diff + actual_commit
        lead = ("## " if kw.get('status_long') else "")
        if kw.get('status_first'):
            status("{}M  Branch           Commit                                   Push Pull Path", lead)
            status("{}-  ---------------  ---------------------------------------- ---- ---- --------------------------", lead)
        status("{}{:1} {:16} {:41} {:>4} {:>4} {}", lead, mod, branch, commit_value, ahead, behind, path)
    
    def status_long(self, path, kw):
        status_seperator()
        kw['status_first'] = True
        self.status_short(path, kw)
        status("")        
        run("git", "status", "--long", cwd=self.work_dir)
        status("")

    def create_branch(self, name, startpoint):
        starting = ("\n    with start point '{}'".format(startpoint) if startpoint is not None else "")
        status("Branch {}\n    to branch '{}'{}", self, name, starting)
        run("git", "checkout", "-b", name, startpoint, cwd=self.work_dir)
        
