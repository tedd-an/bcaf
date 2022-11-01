import os
import sys
import shutil

sys.path.insert(0, '../libs')
from libs import cmd_run

from ci import Base, Verdict, submit_pw_check

class BuildKernel32(Base):
    """Build 32bit Kernel class
    This class is used to build the 32bit kernel for Bluetooth
    There are two different build type:
    Simple Build (simple_build=True) - Compile the bluetooth sources only in
    net/bluetooth and drivers/bluetooth.
    Full Build (simple_build=False) - Full build based on the config that
    enables all Bluetooth features.
    """

    def __init__(self, pw, series, src_dir, config=None, dry_run=False,
                 simple_build=True):

        super().__init__()

        # Common
        self.name = "BuildKernel32"
        self.desc = "Build 32bit Kernel for Bluetooth"

        # Set the default build config.
        if config:
            self.config = config
        else:
            self.config = '/bluetooth_build.config'

        self.pw = pw
        self.series = series
        self.dry_run = dry_run
        self.src_dir = src_dir
        self.simple_build = simple_build

        self.patch_1 = self.series['patches'][0]

        self.log_dbg("Initialization completed")

    def run(self):
        self.log_dbg("Run")

        self.start_timer()

        # Copy the build config to source dir
        self.log_info(f"Copying {self.config} to source dir")
        shutil.copy(self.config, os.path.join(self.src_dir, ".config"))

        # Update .config
        self.log_info("Run make ARCH=i386 olddefconfig")
        cmd = ["make", "ARCH=i386", "olddefconfig"]
        (ret, stdout, stderr) = cmd_run(cmd, cwd=self.src_dir)
        if ret:
            self.log_err("Failed to config the kernel")
            submit_pw_check(self.pw, self.patch_1, self.name, Verdict.FAIL,
                            "BuildKernel32: make olddefconfig FAIL: " + stderr,
                            None, self.dry_run)
            self.add_failure_end_test(stderr)

        # make
        self.log_info("Run make")
        if self.simple_build:
            self.log_info("Simple build - Bluetooth only")
            cmd = ["make", "ARCH=i386", "-j2", "W=1", "net/bluetooth/"]
            (ret, stdout, stderr) = cmd_run(cmd, cwd=self.src_dir)
            if ret:
                submit_pw_check(self.pw, self.patch_1, self.name, Verdict.FAIL,
                                "BuildKernel32: make FAIL: " + stderr,
                                None, self.dry_run)
                self.add_failure_end_test(stderr)

            cmd = ["make", "ARCH=i386", "-j2", "W=1", "drivers/bluetooth/"]
            (ret, stdout, stderr) = cmd_run(cmd, cwd=self.src_dir)
            if ret:
                submit_pw_check(self.pw, self.patch_1, self.name, Verdict.FAIL,
                                "BuildKernel32: make FAIL: " + stderr,
                                None, self.dry_run)
                self.add_failure_end_test(stderr)
        else:
            # full build
            self.log_info("Full build")
            cmd = ["make", "ARCH=i386", "-j2"]
            (ret, stdout, stderr) = cmd_run(cmd, cwd=self.src_dir)
            if ret:
                submit_pw_check(self.pw, self.patch_1, self.name, Verdict.FAIL,
                                "BuildKernel32: make FAIL: " + stderr,
                                None, self.dry_run)
                self.add_failure_end_test(stderr)

        submit_pw_check(self.pw, self.patch_1, self.name, Verdict.PASS,
                            "BuildKernel32 PASS", None, self.dry_run)
        self.success()

    def post_run(self):
        self.log_dbg("Post Run...")
