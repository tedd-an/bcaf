import os
from typing import List

import libs


class RepoToolNotRepo(Exception):
    pass


class RepoTool:

    def __init__(self, name, path, remote=None):
        self._name = name
        self._path = os.path.abspath(path)
        self._remote = "origin"
        self._branch = "master"

        if remote:
            self._remote = remote

        self._verify_repo()
        libs.log_info(f'Git Repo({self._name}) verified: {self._path}')

    def git(self, args: List[str]):
        return libs.cmd_run(["git"] + args, cwd=self._path)

    def _verify_repo(self):
        cmd = ["branch", "--show-current"]
        try:
            stdout, stderr = self.git(cmd)
        except:
            libs.log_error("Failed to verify repo")
            raise RepoToolNotRepo
        return stdout

    def git_checkout(self, branch, create_branch=False):
        cmd = ["checkout"]
        if create_branch:
            cmd += ["-b"]
        cmd += [branch]
        return self.git(cmd)

    def git_push(self, branch, remote=None, force=False):
        cmd = ["push"]
        if force:
            cmd += ["-f"]
        if remote:
            cmd += [remote]
        else:
            cmd += [self._remote]
        return self.git(cmd)

    def git_reset(self, target, hard=False):
        cmd = ["reset", target]
        if hard:
            cmd += ["--hard"]
        return self.git(cmd)

    def git_am(self, patch=None, abort=False):
        cmd = ["am", patch]
        if abort:
            cmd += ["--abort"]
        else:
            cmd += [patch]
        return self.git(cmd)

