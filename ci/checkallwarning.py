import os
import sys
import re

from ci import Verdict, EndTest, submit_pw_check
from ci import GenericKernelBuild

class CheckAllWarning(GenericKernelBuild):
    """Run kernel build with all warning enabled
    This class runs the kernel build with all warning enabled.
    """

    def __init__(self, ci_data, kernel_config=None, src_dir=None, dry_run=None):

        self.name = "CheckAllWarning"
        self.desc = "Run linux kernel with all warning enabled"

        self.kernel_config = kernel_config
        self.ci_data = ci_data

        # Override the src dir
        self.src_dir = ci_data.src_dir
        if src_dir:
            self.log_dbg(f"Override src_dir {src_dir}")
            self.src_dir = src_dir

        # Override the dry_run flag.
        self.dry_run = self.ci_data.config['dry_run']
        if dry_run:
            self.log_dbg(f"Override the dry_run flag: {dry_run}")
            self.dry_run = dry_run

        super().__init__(kernel_config=kernel_config, simple_build=True,
                         make_params=['W=1'], work_dir=self.src_dir)

        self.log_dbg("Initialization completed")

    def run(self):

        self.log_dbg("Run")

        try:
            super().run()
        except EndTest as e:
            self.log_err("Test ended with an error")
        finally:
            self.log_info(f"Test verdict: {self.verdict}")

        self.log_info(f"Test Verdict: {self.verdict.name}")

        # Reposrt the result to Patchwork if the build itself failed
        if self.verdict == Verdict.FAIL:
            submit_pw_check(self.ci_data.pw, self.ci_data.patch_1,
                            self.name, Verdict.FAIL,
                            "CheckAllWarning: FAIL: " + self.output,
                            None, self.dry_run)
            # Test verdict and output is already set by the super().run().
            # Just raising EndTest exception is enough here
            raise EndTest

        # self.stderr contains the error messages to process
        output_dict = self.parse_output(self.stderr)
        if output_dict == None:
            # Build success
            submit_pw_check(self.ci_data.pw, self.ci_data.patch_1,
                            self.name, Verdict.PASS,
                            "CheckAllWarning PASS",
                            None, self.dry_run)
            # Actually no need to call success() here. But add it here just for
            # reference
            self.success()
            return

        # Check files in the patch
        (_file_list, _new_file_list) = self.ci_data.pw.series_get_file_list(
                                                        self.ci_data.series)
        # Combine two lists into one
        file_list = _file_list + _new_file_list

        # File exist in otput_dict?
        output_str = ""
        for fn in file_list:
            if fn in output_dict:
                self.log_dbg("Found file in the output_dict")
                output_str += "".join(output_dict[fn])

        if output_str != "":
            # Found error and return warning
            submit_pw_check(self.ci_data.pw, self.ci_data.patch_1,
                            self.name, Verdict.WARNING,
                            "CheckSparse WARNING " + output_str,
                            None, self.dry_run)
            self.warning(output_str)
            return

        # Build success
        submit_pw_check(self.ci_data.pw, self.ci_data.patch_1,
                        self.name, Verdict.PASS,
                        "CheckSparse PASS",
                        None, self.dry_run)
        # Actually no need to call success() here. But add it here just for
        # reference
        self.success()

    def post_run(self):
        self.log_dbg("Post Run...")

        self.log_dbg("Clean the source")
        super().post_run()

    def parse_output(self, output):
        """Read output log and creates the dict whcih has key with file path
        and the value is the output log in list
        """

        # Convert output log to list
        output_line = output.splitlines()

        # if empty, return None
        if not len(output_line):
            self.log_dbg("Empty output. Nothing to do")
            return None

        output_dict = {}
        curr_key = None

        for line in output_line:
            self.log_dbg(f"LINE: {line}")
            # If line is empty, skip
            if line.strip() == "":
                continue

            # Read file name from the string
            fn = line.split(':')[0]
            self.log_dbg(f"PROCESS: {fn}")

            # if it is .c file, ignore inc_file flag and curr_key.
            if fn.find(".c") != -1:
                self.log_dbg("Found .C file. Set key string")
                curr_key = fn

            # Insert the line
            if curr_key not in output_dict:
                output_dict[curr_key] = [line]
            else:
                output_dict[curr_key].append(line)

        return output_dict
