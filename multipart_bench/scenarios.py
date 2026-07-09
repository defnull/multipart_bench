from collections import namedtuple
import io
import math
import timeit
import string
import json
import gc
from scipy import stats


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
        self._seek = self.payload.seek
        self.chunksize = chunksize

        self.fields = []  # [[name, filename, headers, size]]
        self._in_body = False
        self._end_written = False

    @property
    def content_type(self):
        return f'multipart/form-data; boundary="{self.boundary.decode("ASCII")}"'

    @property
    def fieldnames(self):
        return [field[0] for field in self.fields]

    def write(self, data):
        if isinstance(data, str):
            data = data.encode("utf8")
        if self._in_body:
            self.fields[-1][3] += len(data)
        self.payload.write(data)

    def _write_boundary(self):
        self._in_body = False
        if self.payload.tell() > 0:
            self.write(b"\r\n")
        self.write(b"--%s\r\n" % (self.boundary,))

    def _write_terminator(self):
        self._in_body = False
        if self.payload.tell() > 0:
            self.write(b"\r\n")
        self.write(b"--%s--\r\n" % (self.boundary,))

    def _write_header(self, name, value):
        self.write(f"{name}: {value}\r\n")

    def field(self, name, filename=None, headers=None):
        self._write_boundary()
        disposition = f'form-data; name="{name}"'
        if filename:
            disposition += f'; filename="{filename}"'
        self._write_header("Content-Disposition", disposition)
        for header, value in headers or []:
            self._write_header(header, value)
        self.write(b"\r\n")
        self.fields.append([name, filename, headers or [], 0])
        self._in_body = True
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

    def name_for(self, func):
        return f"{self.name}-{func.__name__}"

    def run_once(self, func):
        self._seek(0)
        func(self)

    def run_bench(self, func, n=1, null_func=None):
        gc.collect()
        time = timeit.timeit(lambda: self.run_once(func), "pass", number=n) / n
        if null_func:
            time -= (
                timeit.timeit(lambda: self.run_once(null_func), "pass", number=n) / n
            )
        return time


class Result(namedtuple("Result", "name size times")):
    DEFAULT_CONFIDENCE_LEVEL = 0.95
    TRIM_FRACTION = 0.10

    @property
    def min(self):
        return min(self.times)

    @property
    def max(self):
        return max(self.times)

    @property
    def avg(self):
        return stats.tmean(self.trimmed_times)

    @property
    def stdev(self):
        return (
            stats.tstd(self.trimmed_times)
            if len(self.trimmed_times) >= 2
            else float("inf")
        )

    @property
    def stderr(self):
        return (
            stats.sem(self.trimmed_times)
            if len(self.trimmed_times) >= 2
            else float("inf")
        )

    @property
    def trimmed_times(self):
        times = sorted(self.times)
        trim = math.ceil(len(times) * self.TRIM_FRACTION)
        trim = min(trim, (len(times) - 2) // 2)
        return times[trim:-trim] if trim > 0 else times

    @property
    def throughputs(self):
        return [self.size / t for t in self.times]

    def relative_standard_error(self):
        """Relative standard error of the measured runtime mean.

        Lower values mean the collected samples are more stable. A value of 0.01
        means the standard error is about 1% of the average runtime.
        """
        if not self.times:
            return float("inf")
        avg = self.avg
        if avg == 0:
            return 0
        return self.stderr / avg

    @property
    def confidence(self):
        return self.relative_confidence_interval()

    @property
    def median(self):
        times = sorted(self.times)
        return times[len(times) // 2]

    @property
    def throughput(self):
        return self.size / self.avg

    def relative_confidence_interval(self, confidence_level=DEFAULT_CONFIDENCE_LEVEL):
        """Relative confidence interval half-width for throughput.

        A value of 0.01 at 95% confidence means throughput is likely within
        +/-1% of the measured throughput. Small sample counts use Student's t
        critical values to avoid overconfident early results.
        """
        times = self.trimmed_times
        if len(times) < 2:
            return float("inf")
        confidence_level = min(max(confidence_level, 0.01), 0.99)
        avg = self.avg
        if avg == 0:
            return 0
        low_time, high_time = stats.t.interval(
            confidence_level,
            df=len(times) - 1,
            loc=avg,
            scale=self.stderr,
        )
        throughput = self.throughput
        low_throughput = 0 if high_time <= 0 else self.size / high_time
        high_throughput = float("inf") if low_time <= 0 else self.size / low_time
        return (
            max(throughput - low_throughput, high_throughput - throughput) / throughput
        )

    @property
    def count(self):
        return len(self.times)

    def save_to(self, path):
        with open(path, "w") as fp:
            json.dump(self._asdict(), fp)

    @classmethod
    def load(self, path):
        with open(path, "r") as fp:
            obj = json.load(fp)
        return Result(**obj)

    def __str__(self):
        return f"{self.name} {self.avg * 1000:.2f}ms {self.throughput / 1024 / 1024:.2f}MB/s"


##
### Scenarios
##

SCENARIOS: list[Scenario] = []


def add_scenario(func):
    scenario = Scenario(func.__name__, func.__doc__.strip())
    func(scenario)
    scenario.end()
    SCENARIOS.append(scenario)
    return scenario


@add_scenario
def empty(payload):
    "An empty form to measure parser initialization overhead"
    pass


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
    fake_boundary = b"\r\n--" + payload.boundary[:-1]
    payload.field("file", "file.bin").pattern(fake_boundary, 1024 * 1024)


@add_scenario
def worstcase_junk(payload: Scenario):
    "Junk before the first and after the last boundary (1MB each)"
    payload.pattern(string.printable, 1024 * 1024)
    payload.field("file", "file.bin").write(b"Content\r\n")
    payload.end()
    payload.pattern(string.printable, 1024 * 1024)
    payload.size = payload.payload.tell()
