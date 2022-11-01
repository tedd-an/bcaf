import sys

sys.path.insert(0, '../libs')
from libs import cmd_run

from ci import Verdict, EndTest, submit_pw_check
from ci import GenericBuild

class BuildEll(GenericBuild):
    """Build ELL class
    This class build and install the ELL
    """

    def __init__(self, pw, series, src_dir, dry_run=False):

        super().__init__(src_dir=src_dir, install=True)

        # Common
        self.name = "BuildEll"
        self.desc = "Build and Install ELL"

        self.pw = pw
        self.series = series
        self.dry_run = dry_run
        self.src_dir = src_dir

        self.patch_1 = self.series['patches'][0]

        self.log_dbg("Initialization completed")

    def run(self):

        self.log_dbg("Run")

        try:
            super().run()
        except EndTest as e:
            self.log_err("Test ended with an error")
        finally:
            self.log_info(f"Test Verdict: {self.verdict.name}")

        # Report the result to Patchwork
        if self.verdict == Verdict.FAIL:
            submit_pw_check(self.pw, self.patch_1, self.name, Verdict.FAIL,
                            "Build ELL FAIL: " + self.output,
                            None, self.dry_run)
            # Test verdict and output is already set by the super().run().
            # Just raise the EndTest enough
            raise EndTest

        # Build success
        submit_pw_check(self.pw, self.patch_1, self.name, Verdict.PASS,
                        "Build ELL PASS", None, self.dry_run)
        # Actually no need to call success() here. But add it here just for
        # reference
        self.success()

    def post_run(self):
        self.log_dbg("Post Run...")
