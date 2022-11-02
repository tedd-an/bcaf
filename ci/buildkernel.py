import os
import sys
import shutil

sys.path.insert(0, '../libs')
from libs import cmd_run

from ci import Base, Verdict, submit_pw_check

class BuildKernel(Base):
    """Build Kernel class
    This class is used to build the kernel for Bluetooth
    There are two different build type:
    Simple Build (simple_build=True) - Compile the bluetooth sources only in
    net/bluetooth and drivers/bluetooth.
    Full Build (simple_build=False) - Full build based on the config that
    enables all Bluetooth features.
    """

    def __init__(self, ci_data, kernel_config=None, simple_build=True,
                 dry_run=None):

        # Common
        self.name = "BuildKernel"
        self.desc = "Build Kernel for Bluetooth"
        self.ci_data = ci_data
        self.simple_build = simple_build

        # Set the default build config.
        if kernel_config:
            self.kernel_config = kernel_config
        else:
            self.kernel_config = '/bluetooth_build.config'

        # Override the dry_run flag.
        self.dry_run = self.ci_data.config['dry_run']
        if dry_run:
            self.log_dbg(f"Override the dry_run flag: {dry_run}")
            self.dry_run = dry_run

        super().__init__()

        self.log_dbg("Initialization completed")

    def run(self):
        self.log_dbg("Run")

        self.start_timer()

        # Copy the build config to source dir
        self.log_info(f"Copying {self.kernel_config} to source dir")
        shutil.copy(self.kernel_config, os.path.join(self.ci_data.src_dir,
                                                     ".config"))

        # Update .config
        self.log_info("Run make olddefconfig")
        cmd = ["make", "olddefconfig"]
        (ret, stdout, stderr) = cmd_run(cmd,
                                        cwd=self.ci_data.src_dir)
        if ret:
            self.log_err("Failed to config the kernel")
            submit_pw_check(self.ci_data.pw, self.ci_data.patch_1,
                            self.name, Verdict.FAIL,
                            "BuildKernel: make olddefconfig FAIL: " + stderr,
                            None, self.dry_run)
            self.add_failure_end_test(stderr)

        # make
        self.log_info("Run make")
        if self.simple_build:
            self.log_info("Simple build - Bluetooth only")
            cmd = ["make", "-j2", "W=1", "net/bluetooth/"]
            (ret, stdout, stderr) = cmd_run(cmd,
                                            cwd=self.ci_data.src_dir)
            if ret:
                submit_pw_check(self.ci_data.pw, self.ci_data.patch_1,
                                self.name, Verdict.FAIL,
                                "BuildKernel: make FAIL: " + stderr,
                                None, self.dry_run)
                self.add_failure_end_test(stderr)

            cmd = ["make", "-j2", "W=1", "drivers/bluetooth/"]
            (ret, stdout, stderr) = cmd_run(cmd,
                                            cwd=self.ci_data.src_dir)
            if ret:
                submit_pw_check(self.ci_data.pw, self.ci_data.patch_1,
                                self.name, Verdict.FAIL,
                                "BuildKernel: make FAIL: " + stderr,
                                None, self.dry_run)
                self.add_failure_end_test(stderr)
        else:
            # full build
            self.log_info("Full build")
            cmd = ["make", "-j2"]
            (ret, stdout, stderr) = cmd_run(cmd,
                                            cwd=self.ci_data.src_dir)
            if ret:
                submit_pw_check(self.ci_data.pw, self.ci_data.patch_1,
                                self.name, Verdict.FAIL,
                                "BuildKernel: make FAIL: " + stderr,
                                None, self.dry_run)
                self.add_failure_end_test(stderr)

        submit_pw_check(self.ci_data.pw, self.ci_data.patch_1,
                        self.name, Verdict.PASS,
                        "BuildKernel PASS",
                        None, self.dry_run)
        self.success()

    def post_run(self):
        self.log_dbg("Post Run...")
