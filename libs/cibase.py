from abc import ABC, abstractmethod
from enum import Enum
import time

class Verdict(Enum):
    PENDING = 0
    PASS = 1
    FAIL = 2
    ERROR = 3
    SKIP = 4
    WARNING = 5


class EndTest(Exception):
    """
    End of Test
    """


class CiBase(ABC):
    """
    Base class for CI Tests.
    """
    name = None
    display_name = None
    desc = None
    start_time = 0
    end_time = 0

    verdict = Verdict.PENDING
    output = ""

    def __init__(self):
        self.name = None
        self.display_name = None
        self.desc = None
        self.start_time = 0
        self.end_time = 0
        self.verdict = Verdict.PENDING
        self.output = ""

    def success(self):
        self.end_timer()
        self.verdict = Verdict.PASS

    def error(self, msg):
        self.verdict = Verdict.ERROR
        self.output = msg
        self.end_timer()
        raise EndTest

    def warning(self, msg):
        self.verdict = Verdict.WARNING
        self.output = msg
        self.end_timer()

    def skip(self, msg):
        self.verdict = Verdict.SKIP
        self.output = msg
        self.end_timer()
        raise EndTest

    def add_failure(self, msg):
        self.verdict = Verdict.FAIL
        if not self.output:
            self.output = msg
        else:
            self.output += "\n" + msg

    def add_failure_end_test(self, msg):
        self.add_failure(msg)
        self.end_timer()
        raise EndTest

    def start_timer(self):
        self.start_time = time.time()

    def end_timer(self):
        self.end_time = time.time()

    def elapsed(self):
        if self.start_time == 0:
            return 0
        if self.end_time == 0:
            self.end_timer()
        return self.end_time - self.start_time

    def verdict_to_patchwork_state(self, verdict):
        """
        Convert verdict to patchwork state
        """
        if verdict == Verdict.PASS:
            return 1
        if verdict == Verdict.WARNING:
            return 2
        if verdict == Verdict.FAIL:
            return 3

        return 0

    @abstractmethod
    def run(self):
        """
        The child class should implement run() method
        """
        pass
