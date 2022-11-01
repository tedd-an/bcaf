import os
import sys

sys.path.insert(0, '../libs')
from libs import cmd_run

from ci import Base, Verdict, EndTest, submit_pw_check

class CheckPatch(Base):
    """Check Patch class
    This class runs the checkpatch.pl with the patches in the series.
    """

    def __init__(self, pw, series, src_dir, checkpatch_pl=None, ignore=None,
                 dry_run=False):

        super().__init__()

        self.name = "CheckPatch"
        self.desc = "Run checkpatch.pl script"

        # Set the checkpatch.pl script
        if checkpatch_pl:
            self.checkpatch_pl = checkpatch_pl
        else:
            self.checkpatch_pl = '/home/han1/work/dev/bluetooth-next/scripts/checkpatch.pl'

        self.pw = pw
        self.series = series
        self.dry_run = dry_run
        self.src_dir = src_dir
        self.ignore = ignore

        self.log_dbg("Initialization completed")


    def run(self):

        self.log_dbg("Run")
        self.start_timer()

        # Get patches from patchwork series
        for patch in self.series['patches']:
            self.log_dbg(f"Patch ID: {patch['id']}")

            (ret, stdout, stderr) = self._checkpatch(patch)
            if ret == 0:
                # CheckPatch PASS
                self.log_dbg("Test result PASSED")
                submit_pw_check(self.pw, patch, self.name, Verdict.PASS,
                                "CheckPatch PASS", None, self.dry_run)
                continue

            msg = f"{patch['name']}\n{stderr}"
            if stderr.find("ERROR:") != -1:
                self.log_dbg("Test result FAIL")
                submit_pw_check(self.pw, patch, self.name, Verdict.FAIL,
                                msg, None, self.dry_run)
                self.add_failure(msg)
                continue

            if stderr.find("WARNING:") != -1:
                self.log_dbg("Test result WARNING")
                submit_pw_check(self.pw, patch, self.name, Verdict.WARNING,
                                msg, None, self.dry_run)
                self.add_failure(msg)
                continue

        if self.verdict == Verdict.FAIL:
            self.log_info(f"Test Verdict: {self.verdict.name}")
            raise EndTest

        self.success()
        self.log_info(f"Test Verdict: {self.verdict.name}")

    def _checkpatch(self, patch):
        cmd = [self.checkpatch_pl]
        if self.ignore:
            cmd.append('--ignore')
            cmd.append(self.ignore)

        patch_file = self.pw.save_patch_mbox(patch['id'],
                            os.path.join(self.src_dir, f"{patch['id']}.patch"))
        self.log_dbg(f"Patch file: {patch_file}")
        cmd.append(patch_file)
        return cmd_run(cmd, cwd=self.src_dir)

    def post_run(self):
        self.log_dbg("Post Run...")