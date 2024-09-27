from collections import namedtuple
import io
import timeit
import time
import string
import random


class Scenario:
    def __init__(
        self,
        name,
        description,
        boundary=b"------------------------WqclBHaXe8KIsoSum4zfZ6",
        chunksize=2**16,
    ):
        self.name = name
        self.description = description
        self.boundary = boundary
        self.payload = io.BytesIO()
        self.chunksize = chunksize
        self._end_written = False

    def write(self, data):
        self.payload.write(data)

    def _write_boundary(self):
        if self.payload.tell() > 0:
            self.write(b"\r\n")
        self.write(b"--%s\r\n" % (self.boundary,))

    def _write_terminator(self):
        if self.payload.tell() > 0:
            self.write(b"\r\n")
        self.write(b"--%s--" % (self.boundary,))

    def _write_header(self, name, value):
        self.write(name.encode("utf8") + b": " + value.encode("utf8") + b"\r\n")

    def field(self, name, filename=None, headers=None):
        self._write_boundary()
        disposition = f'form-data; name="{name}"'
        if filename:
            disposition += f'; filename="{filename}"'
        self._write_header("Content-Disposition", disposition)
        for header, value in headers or []:
            self._write_header(header, value)
        self.write(b"\r\n")
        return self

    def pattern(self, pattern, size):
        if isinstance(pattern, str):
            pattern = pattern.encode("utf8")
        plen = len(pattern)
        self.write(pattern * int(size // plen))
        if size % plen:
            self.write(pattern[: size % plen])
        return self

    def end(self):
        if not self._end_written:
            self._end_written = True
            self._write_terminator()
            self.size = self.payload.tell()
        return self

    def reset(self):
        self.payload.seek(0)

    def run_once(self, func):
        self.reset()
        return timeit.timeit(lambda: func(self), "pass", number=1)

    def timeit(self, func, mintime=10, minrepeat=5, confidence=5):
        """Benchmark a single function that takes a scenario.

        :param func: Function to test.
        :param mintime: Repeat for at least this many seconds.
        :param minrepeat: Repeat for at least this many times.
        :param confidence: Repeat until at least this many runs could not beat the current best time.
        """
        start = time.time()
        results = []
        best = 2**64
        loose_count = 0
        while (
            time.time() - start < mintime
            or len(results) < minrepeat
            or loose_count < confidence
        ):
            r = self.run_once(func)
            results.append(r)
            if r < best:
                best = r
                loose_count = 0
            else:
                loose_count += 1

        return Result(self, func, results)


class Result(namedtuple("Result", "scenario func results")):
    @property
    def min(self):
        return min(self.results)

    @property
    def avg(self):
        return sum(self.results) / len(self.results)

    @property
    def mean(self):
        return self.results[len(self.results) // 2]

    @property
    def throughput(self):
        return self.scenario.size / self.min

    @property
    def count(self):
        return len(self.results)

    @property
    def name(self):
        return self.func.__name__

    def as_dict(self):
        return {
            "scenario": {
                "name": self.scenario.name,
                "description": self.scenario.description,
                "size": self.scenario.size,
            },
            "parser": {
                "name": self.func.__name__,
                "description": self.func.__doc__ or "",
            },
            "results": self.results,
        }

    def __str__(self):
        return f"{self.scenario.name} {self.name} {self.min*1000:.2f}ms {self.throughput/1024/1024:.2f}MB/s"


##
### Scenarios
##

SCENARIOS = []


def add_scenario(func):
    scenario = Scenario(func.__name__, func.__doc__.strip())
    func(scenario)
    scenario.end()
    scenario.reset()
    SCENARIOS.append(scenario)
    return scenario


@add_scenario
def simple(payload):
    "A simple form with just two small text fields"
    payload.field("email").pattern(string.printable, 24)
    payload.field("password").pattern(string.printable, 16)


@add_scenario
def large(payload):
    "A large form with 100 small text fields"
    for i in range(100):
        payload.field(f"field{i}").pattern(string.printable, i)


@add_scenario
def upload(payload):
    "A file upload with a single large (32MB) file"
    payload.field("foo", "bar.bin").pattern(string.printable, 1024 * 1024 * 32)


@add_scenario
def mixed(payload):
    "A form with two text fields and two small file uploads (1MB and 2MB)"
    payload.field("field").pattern(string.printable, 16)
    payload.field("file", "file.bin").pattern(string.printable, 1024 * 1024 * 1)
    payload.field("field2").pattern(string.printable, 32)
    payload.field("file2", "file2.bin").pattern(string.printable, 1024 * 1024 * 2)


@add_scenario
def worstcase_crlf(payload):
    "A 1MB upload that contains nothing but windows line-breaks"
    payload.field("file", "file.bin").pattern("\r\n", 1024 * 1024)


@add_scenario
def worstcase_lf(payload):
    "A 1MB upload that contains nothing but linux line-breaks"
    payload.field("file", "file.bin").pattern("\n", 1024 * 1024)


@add_scenario
def worstcase_bchar(payload):
    "A 1MB upload that contains parts of the boundary"
    # boundary is ------------------------WqclBHaXe8KIsoSum4zfZ6
    payload.field("file", "file.bin").pattern("Wgcl", 1024 * 1024)
