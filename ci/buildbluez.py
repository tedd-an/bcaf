from ci import Verdict, EndTest, submit_pw_check
from ci import GenericBuild

class BuildBluez(GenericBuild):
    """Class for building the BlueZ
    This class is to configure and make the bluez. Actual work is done by the
    GenericBuild class. After finishing the actual run() from the GenericBuiuld
    class, it checks the verdict and reports the result.
    """

    def __init__(self, pw, series, src_dir, config_params=None, dry_run=False):

        super().__init__(config_params=config_params, src_dir=src_dir)

        # Common
        self.name = "BluezMake"
        self.desc = "Build BlueZ"

        self.pw = pw
        self.series = series
        self.src_dir = src_dir
        self.dry_run = dry_run

        # The first patch in the series
        self.patch_1 = self.series['patches'][0]

        self.log_dbg("Initialization completed")

    def run(self):

        self.log_dbg("Run")

        try:
            super().run()
        except EndTest as e:
            self.log_err("Test ended with an error")
        finally:
            self.log_info(f"Test Verdict: {self.verdict}")

        self.log_info(f"Test Verdict: {self.verdict.name}")

        # Report the result to Patchwork
        if self.verdict == Verdict.FAIL:
            submit_pw_check(self.pw, self.patch_1, self.name, Verdict.FAIL,
                            "BluezMake FAIL: " + self.output,
                            None, self.dry_run)
            # Test verdict and output is already set by the super().run().
            # Just raise the EndTest enough
            raise EndTest

        # Build success
        submit_pw_check(self.pw, self.patch_1, self.name, Verdict.PASS,
                        "Bluez Make PASS", None, self.dry_run)
        # Actually no need to call success() here. But add it here just for
        # reference
        self.success()

    def post_run(self):
        self.log_dbg("Post Run...")