from ci import Base, Verdict, EndTest, submit_pw_check

class SubjectPrefix(Base):
    """Check Subject Prefix class
    This class checks the prefix of the patch if it contains the 'Bluetooth'
    """

    def __init__(self, pw, series, src_dir, dry_run=False):

        super().__init__()

        # Common
        self.name = "SubjectPrefix"
        self.desc = "Check subject contains \"Bluetooth\" prefix"

        # This class specific
        self.pw = pw
        self.series = series
        self.dry_run = dry_run
        self.src_dir = src_dir

        self.log_dbg("Initialization completed")

    def run(self):
        self.log_dbg("Run")

        self.start_timer()

        # Get patches from patchwork series
        for patch in self.series['patches']:
            self.log_dbg(f"Patch ID: {patch['id']}")

            s = patch['name'].find('Bluetooth: ')
            if s < 0:
                # No prefix found.
                msg = "\"Bluetooth: \" prefix is not specified in the subject"
                submit_pw_check(self.pw, patch, self.name, Verdict.FAIL,
                                msg, None, self.dry_run)
                self.add_failure(msg)
                continue

            submit_pw_check(self.pw, patch, self.name, Verdict.PASS,
                            "Gitlint PASS", None, self.dry_run)

        if self.verdict == Verdict.FAIL:
            raise EndTest

        self.success()

    def post_run(self):
        self.log_dbg("Post Run...")