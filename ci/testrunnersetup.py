import os
import sys
import shutil

from ci import Base, Verdict, EndTest, submit_pw_check
from ci import BuildKernel, BuildBluez

class TestRunnerSetup(Base):
    """Test Runner Setup class
    This class builds the bluez and kernel for test-runner
    """

    def __init__(self, pw, series, src_dir, bluez_src_dir, tester_config=None,
                 dry_run=False):

        super().__init__()

        # Common
        self.name = "TestRunnerSetup"
        self.desc = "Setup kernel and bluez for test-runner"

        self.pw = pw
        self.series = series
        self.dry_run = dry_run
        self.src_dir = src_dir
        self.bluez_src_dir = bluez_src_dir

        self.patch_1 = self.series['patches'][0]

        if tester_config:
            self.tester_config = tester_config
        else:
            self.tester_config = "/tester.config"

        # BlueZ build object
        _params = ["--disable-lsan", "--disable-asan", "--disable-ubsan",
                   "--disable-android"]
        self.bluez_build = BuildBluez(pw, series, self.bluez_src_dir,
                                      config_params=_params, dry_run=True)

        # Kernel build object
        self.kernel_build = BuildKernel(pw, series, self.src_dir,
                                        config=self.tester_config, dry_run=True,
                                        simple_build=False)

        self.log_dbg("Initialization completed")

    def run(self):

        self.log_dbg("Run")
        self.start_timer()

        self.log_info("Building BlueZ")
        try:
            self.bluez_build.run()
        except EndTest as e:
            self.log_err("Failed to build BlueZ")

        if self.bluez_build.verdict == Verdict.FAIL:
            submit_pw_check(self.pw, self.patch_1, self.name, Verdict.FAIL,
                            "BlueZ Make FAIL: " + self.bluez_build.output,
                            None, self.dry_run)
            self.add_failure_end_test("Bluez: " + self.bluez_build.output)
        self.log_info("Building BlueZ success")

        # Check test-runner
        self.log_dbg("Checking test-runner binary")
        tester_path = os.path.join(self.bluez_src_dir, "tools/test-runner")
        if not os.path.exists(tester_path):
            submit_pw_check(self.pw, self.patch_1, self.name, Verdict.FAIL,
                            "BlueZ Make FAIL: No test-runner found",
                            None, self.dry_run)
            self.add_failure_end_test("Build Error: No test-runner found")
        self.log_info("Found test-runner binary")

        self.log_info("Building test kernel image")
        try:
            self.kernel_build.run()
        except EndTest as e:
            self.log_err("Failed to build kernel")

        if self.kernel_build.verdict == Verdict.FAIL:
            submit_pw_check(self.pw, self.patch_1, self.name, Verdict.FAIL,
                            "Kernel Build FAIL: " + self.kernel_build.output,
                            None, self.dry_run)
            self.add_failure_end_test("Kernel: " + self.kernel_build.output)
        self.log_info("Building kernel success")

        # Check kernel image
        self.log_dbg("Checking kernel image")
        bzimage_path = os.path.join(self.src_dir, "arch/x86/boot/bzImage")
        if not os.path.exists(bzimage_path):
            submit_pw_check(self.pw, self.patch_1, self.name, Verdict.FAIL,
                            "Kernel Build FAIL: No bzImage found",
                            None, self.dry_run)
            self.add_failure_end_test("Build Error: No bzImage found")
        self.log_info("Found test kernel image")

        # Setup success
        submit_pw_check(self.pw, self.patch_1, self.name, Verdict.PASS,
                        "TestRunnerSetup PASS", None, self.dry_run)
        self.log_info("TestRunnerSetup PASS")
        self.success()

    def post_run(self):
        self.log_dbg("Post Run...")
