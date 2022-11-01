from ctypes import util
import os
import sys

sys.path.insert(0, '../libs')
from libs import RepoTool, cmd_run

from ci import Base, Verdict, EndTest, submit_pw_check
from ci import BuildKernel, BuildBluez

class IncrementalBuild(Base):
    """Incremental Build class
    This class build the targe after applying the each patch in the series
    """

    def __init__(self, pw, series, space, src_dir, kernel_config=None,
                 dry_run=False):

        super().__init__()

        self.name = "IncrementalBuild"
        self.desc = "Incremental build with the patches in the series"

        self.pw = pw
        self.series = series
        self.dry_run = dry_run
        self.src_dir = src_dir
        self.kernel_config = kernel_config
        self.space = space

        if self.space == "kernel":
            # Set the dry_run=True so it won't submit the result to the pw.
            self.target = BuildKernel(pw, series, src_dir, config=kernel_config,
                                      dry_run=True)
        elif self.space == "user":
            _params = ["--disable-android"]
            # Set the dry_run=True so it won't submit the result to the pw.
            self.target = BuildBluez(pw, series, src_dir, config_params=_params,
                                     dry_run=True)
        else:
            self.target = None

        self.log_dbg(f"SRC: {src_dir}")
        self.src_repo = RepoTool("src_dir", src_dir)

        self.log_dbg("Initialization completed")

    def run(self):
        self.log_dbg("Run")

        self.start_timer()

        if not self.target:
            self.log_err(f"Invalid setup: space: {self.space}")
            self.add_failure_end_test("Invalid setup")

        # Make the source base to workflow branch
        if self.src_repo.git_checkout("origin/workflow"):
            self.log_err(f"Failed to checkout: {self.src_repo.stderr}")
            self.add_failure_end_test(self.src_repo.stderr)

        # Get patches from patchwork series
        for patch in self.series['patches']:
            self.log_dbg(f"Patch ID: {patch['id']}")

            # Save patch mbox to file
            patch_file = self.pw.save_patch_mbox(patch['id'],
                            os.path.join(self.src_dir, f"{patch['id']}.patch"))
            self.log_dbg(f"Save patch: {patch_file}")

            # Apply patch
            if self.src_repo.git_am(patch_file):
                self.log_err("Failed to apply patch")
                msg = self.src_repo.stderr
                self.src_repo.git_am(abort=True)
                self.add_failure_end_test(msg)

            # Test Build
            try:
                self.target.run()
            except EndTest as e:
                self.log_err("Build failed")
            finally:
                self.log_info(f"Test Verdict: {self.target.verdict.name}")

            # Update the verdict from self.target to this object
            if self.target.verdict == Verdict.FAIL:
                # submit error log pw
                msg = f"{patch['name']}\n{self.target.output}"
                submit_pw_check(self.pw, patch, self.name, Verdict.FAIL,
                                msg, None, self.dry_run)
                self.add_failure_end_test(msg)

            # Build Passed
            submit_pw_check(self.pw, patch, self.name, Verdict.PASS,
                            "Incremental Build PASS", None, self.dry_run)
            self.success()

    def post_run(self):
        self.log_dbg("Post Run...")

        if self.verdict == Verdict.PENDING:
            self.log_info("No verdict. skip post-run")
            return

        if self.space == 'user':
            cmd = ["make", "maintainer-clean"]
        else: # kernel
            cmd = ['make', 'clean']

        (ret, stdout, stderr) = cmd_run(cmd, cwd=self.src_dir)
        if ret:
            self.log_err("Fail to clean the source")

        # AR: hum... should it continue the test?
