import os
import sys

sys.path.insert(0, '../libs')
from libs import cmd_run

from ci import Base, Verdict, EndTest, submit_pw_check

class GitLint(Base):
    """Git Lint class
    This class runs gitlint with the patches in the series
    """

    def __init__(self, pw, series, src_dir, config=None, dry_run=False):

        super().__init__()

        self.name = "GitLint"
        self.desc = "Run gitlint"

        # Set the gitlint config file
        if config:
            self.config = config
        else:
            self.config = './.gitlint'

        self.pw = pw
        self.series = series
        self.dry_run = dry_run
        self.src_dir = src_dir

        self.log_dbg("Initialization completed")

    def run(self):
        self.log_dbg("Run")

        self.start_timer()

        # Get patches from patchwork series
        for patch in self.series['patches']:
            self.log_dbg(f"Patch ID: {patch['id']}")

            (ret, stdout, stderr) = self._gitlint(patch)
            if ret == 0:
                # GitLint PASS
                self.log_dbg("Test result PASSED")
                submit_pw_check(self.pw, patch, self.name, Verdict.PASS,
                                "Gitlint PASS", None, self.dry_run)
                continue

            msg = f"{patch['name']}\n{stderr}"
            submit_pw_check(self.pw, patch, self.name, Verdict.FAIL,
                                msg, None, self.dry_run)
            self.log_dbg("Test result FAIL")
            self.add_failure(msg)

        if self.verdict == Verdict.FAIL:
            self.log_info(f"Test Verdict: {self.verdict.name}")
            raise EndTest

        self.success()
        self.log_info(f"Test Verdict: {self.verdict.name}")

    def _gitlint(self, patch):
        patch_msg = self.pw.save_patch_msg(patch['id'],
                            os.path.join(self.src_dir, f"{patch['id']}.msg"))
        self.log_dbg(f"Patch msg: {patch_msg}")
        cmd = ['gitlint', '-C', self.config, '--msg-filename', patch_msg]
        return cmd_run(cmd, cwd=self.src_dir)

    def post_run(self):
        self.log_dbg("Post Run...")