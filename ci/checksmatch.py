import os
import sys
import re

from ci import Base, Verdict, EndTest, submit_pw_check
from ci import BuildBluez, BuildKernel

class CheckSmatch(Base):
    """Run smatch with Kernel or user space.
    This class runs the smatch tool with linux kernel or bluez.
    Note that the make parameters are different for kernel and bluez.
    For user space(bluez)
    $ make CHECK="<path/to/smatch/smatch> --full-path" \
              CC=<path/to/smatch/cgcc>
    For kernel(bluetooth-next)
    $ make CHECK="<path/to/smatch/smatch -p=kernel" C=1 
              <path/to/src...>
    """

    def __init__(self, ci_data, space, tool_dir, kernel_config=None,
                 src_dir=None, dry_run=None):

        self.name = "CheckSmatch"
        self.desc = "Run smatch tool with source"

        self.ci_data = ci_data
        self.space = space
        self.tool_dir = tool_dir

        self.kernel_config = kernel_config

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

        self.target = None
        make_params = []
        if self.space == "kernel":
            make_params.append(f"CHECK={self.tool_dir}/smatch -p=kernel")
            make_params.append("C=1")
            # Set the dry_run=True so it won't submit the result to the pw
            self.target = BuildKernel(self.ci_data, kernel_config=kernel_config,
                                      make_params=make_params, dry_run=True)
        elif self.space == "user":
            config_params = ["--disable-asan", "--disable-lsan",
                             "--disable-ubsan", "--disable-android"]
            make_params.append(f"CHECK={self.tool_dir}/smatch --full-path")
            make_params.append(f"CC={self.tool_dir}/cgcc")
            # Set the dry_run=True so it won't submit the result to the pw
            self.target = BuildBluez(self.ci_data, config_params=config_params,
                                     make_params=make_params, dry_run=True)
        else:
            self.target = None

        super().__init__()

        self.log_dbg("Initialization completed")

    def run(self):

        self.log_dbg("Run")

        self.start_timer()

        if not self.target:
            self.log_err(f"Invalid setup: space: {self.space}")
            self.add_failure_end_test("Invalid setup")

        try:
            self.target.run()
        except EndTest as e:
            self.log_err("Test ended with an error")
        finally:
            self.log_info(f"Test verdict: {self.target.verdict.name}")

        # Report the result to Patchwork if the build itself failed
        if self.target.verdict == Verdict.FAIL:
            submit_pw_check(self.ci_data.pw, self.ci_data.patch_1,
                            self.name, Verdict.FAIL,
                            "CheckSparse: FAIL: " + self.target.output,
                            None, self.dry_run)
            self.add_failure_end_test(self.target.output)

        # self.stderr contains the error messages to process
        output_dict = self.parse_output(self.target.stderr)
        if output_dict == None:
            # Build success
            submit_pw_check(self.ci_data.pw, self.ci_data.patch_1,
                            self.name, Verdict.PASS,
                            "CheckSparse PASS",
                            None, self.dry_run)
            # Actually no need to call success() here. But add it here just for
            # reference
            self.success()
            return
        self.log_dbg(f"Output files: {output_dict}")

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
        self.log_dbg(f"Output String: {output_str}")

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
        self.target.post_run()

    def parse_output(self, output):
        """Read output log and creates the dict whcih has key with file path
        and the value is the output log in list
        """

        # Convert output log to list
        output_line = output.splitlines()

        # if empty, return None
        if not len(output_line):
            return None

        output_dict = {}
        inc_file = False
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
                self.log_dbg("Found .C file. reset flag")
                inc_file = False
                curr_key = None
            if inc_file:
                self.log_dbg("Include file")
                output_dict[curr_key].append(line)
                continue

            # Check output_dict if it is already exist.
            if fn not in output_dict:
                output_dict[fn] = [line]
            else:
                output_dict[fn].append(line)

            # Special case. If the line contains "in included file",
            # the following .H files belong here.
            if line.find('note: in included file:') != -1:
                self.log_dbg("Found include file string")
                curr_key = fn
                inc_file = True

        return output_dict
