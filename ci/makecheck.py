import sys

sys.path.insert(0, '../libs')
from libs import cmd_run

from ci import Base, Verdict, submit_pw_check

class MakeCheck(Base):
    """BlueZ Make Check class
    This class runs 'make check' with Bluez, and it assumes that the source
    is already compiled
    """

    def __init__(self, pw, series, src_dir, dry_run=False):

        super().__init__()

        # Common
        self.name = "MakeCheck"
        self.desc = "Run Bluez Make Check"

        self.pw = pw
        self.series = series
        self.dry_run = dry_run
        self.src_dir = src_dir

        self.patch_1 = self.series['patches'][0]

        self.log_dbg("Initialization completed")

    def run(self):

        self.log_dbg("Run")
        self.start_timer()

        cmd = ["make", "check"]
        (ret, stdout, stderr) = cmd_run(cmd, cwd=self.src_dir)
        if ret:
            submit_pw_check(self.pw, self.patch_1, self.name, Verdict.FAIL,
                            "BlueZ Make Check FAIL: " + self.output,
                            None, self.dry_run)
            self.log_dbg("Test result FAIL")
            self.add_failure_end_test(stderr)

        # Build success
        submit_pw_check(self.pw, self.patch_1, self.name, Verdict.PASS,
                        "Bluez Make Check PASS", None, self.dry_run)
        self.success()
        self.log_dbg("Test result PASS")

    def post_run(self):
        self.log_dbg("Post Run...")

        if self.verdict == Verdict.PENDING:
            self.log_info("No verdict. skip post-run")
            return

        # Clean the source
        cmd = ["make", "maintainer-clean"]
        (ret, stdout, stderr) = cmd_run(cmd, cwd=self.src_dir)
        if ret:
            self.log_err("Fail to clean the source")

        # AR: hum... should it continue the test?
