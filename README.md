# Benchmark for Python multipart/form-data parsers

This repository contains scenarios and parser tests for different Python based
`multipart/form-data` parsers, comparing both blocking and non-blocking APIs (if
available).

## Contestants

* [multipart](https://pypi.org/project/multipart/) v1.1
  * Will be used in [Bottle](https://pypi.org/project/bottle/). Disclaimer: I am the author of both *multipart* and *Bottle*.
  * [CPython docs](https://docs.python.org/3.12/library/cgi.html) recommend it as a `cgi.FieldStorage` replacement.
* [werkzeug](https://pypi.org/project/Werkzeug/) v3.0.4
  * Used in [Flask](https://pypi.org/project/Flask/) and others.
  * Does a lot more than *just* multipart parsing.
* [python-multipart](https://pypi.org/project/python-multipart/) v0.0.12
  * Used in [Starlette](https://pypi.org/project/starlette/) and thus [FastAPI](https://pypi.org/project/fastapi/).
  * Causes import name conflicts with `multipart`.
* [streaming-form-data](https://pypi.org/project/streaming-form-data/) v1.17.0 
  * Streaming parser partly written in Cython.
* [cgi.FieldStorage](https://docs.python.org/3.12/library/cgi.html) CPython 3.12.3
  * Deprecated in Python 3.11 and removed in Python 3.13
* [email.parser.BytesFeedParser](https://docs.python.org/3.12/library/email.parser.html#email.parser.BytesFeedParser) CPython 3.12.3
  * Designed as a parser for emails, not `multipart/form-data`.
  * Buffers everything in memory, including large file uploads.

## Updates

* **30.09.2024** `python-multipart` v0.0.11 fixed a bug that caused extreme
  slowdowns (as low as 0.75MB/s) in all three worst-case scenarios.
* **30.09.2024** There was an issue with the `email` parser that caused it to
  skip over the actual parsing and also not do any IO in the blocking test.
  Throughput was way higher than expected. This is fixed now.
* **30.09.2024** Default size for in-memory buffers is different for each parser,
  resulting in an unfair comparison. The tests now configure a limit of 500K for
  each parser, which is the hard-coded value in `werkzeug` and also a sensible
  default.
* **03.10.2024** New version of `multipart` with slightly better results in some tests.
* **05.10.2024** Added results for `streaming-form-data` parser.

## Method

All tests were performed on a pretty old "AMD Ryzen 5 3600" running Linux 6.8.0
and Python 3.12.3 with highest possible priority and pinned to a single core.

For each test, the parser is created with default¹ settings and the results are
thrown away. Some parsers buffer to disk, but `TEMP` points to a ram-disk to
reduce disk IO from the equation. Each test is repeated until there is no
improvement for at least 100 runs in a row, then the best run is used to compute
the theoretical maximum throughput per core.

¹) There is one exception: The limit for in-memory buffered files is set to
500KB (hard-coded in `werkzeug`) to ensure a fair comparison.


## Results

Parser throughput is measured in MB/s (input size / time). Higher throughput is
better.


### Scenario: simple

A simple form with just two small text fields.

| Parser              | Blocking (MB/s)   | Non-Blocking (MB/s)   |
|---------------------|-------------------|-----------------------|
| multipart           | 13.80 MB/s (100%) | 19.50 MB/s (100%)     |
| werkzeug            | 5.71 MB/s (41%)   | 7.19 MB/s (37%)       |
| python-multipart    | 3.64 MB/s (26%)   | 6.12 MB/s (31%)       |
| streaming-form-data | 0.81 MB/s (6%)    | 0.84 MB/s (4%)        |
| cgi                 | 4.87 MB/s (35%)   | -                     |
| email               | 3.85 MB/s (28%)   | 4.25 MB/s (22%)       |

This scenario is so small that it shows initialization overhead more than actual
parsing performance, which hurts `streaming-form-data` the most. Small forms like
these should better be transmitted as `application/x-www-form-urlencoded`, which
has a lot less overhead compared to `multipart/form-data` and should be a lot
faster.


### Scenario: large

A large form with 100 small text fields.

| Parser              | Blocking (MB/s)   | Non-Blocking (MB/s)   |
|---------------------|-------------------|-----------------------|
| multipart           | 24.05 MB/s (100%) | 30.44 MB/s (100%)     |
| werkzeug            | 10.16 MB/s (42%)  | 12.91 MB/s (42%)      |
| python-multipart    | 5.00 MB/s (21%)   | 8.91 MB/s (29%)       |
| streaming-form-data | 1.13 MB/s (5%)    | 1.15 MB/s (4%)        |
| cgi                 | 6.28 MB/s (26%)   | -                     |
| email               | 11.14 MB/s (46%)  | 12.87 MB/s (42%)      |

Large forms show a slightly higher throughput because initialization overhead
is no longer the main factor. `email` is designed for this type of line based
text input and shines here, but `multipart` is still faster.


### Scenario: upload

A file upload with a single large (32MB) file.

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1442.95 MB/s (100%) | 6041.18 MB/s (100%)   |
| werkzeug            | 913.24 MB/s (63%)   | 2659.65 MB/s (44%)    |
| python-multipart    | 1339.99 MB/s (93%)  | 4581.02 MB/s (76%)    |
| streaming-form-data | 1124.27 MB/s (78%)  | 4897.96 MB/s (82%)    |
| cgi                 | 127.05 MB/s (9%)    | -                     |
| email               | 51.87 MB/s (4%)     | 59.47 MB/s (1%)       |

Now it gets interesting. When dealing with actual file uploads, both
`python-multipart` and `streaming-form-data` catch up and are now better than
`werkzeug`. All three are still slower than `multipart`, but the results are
still impressive. The line-based `cgi` and `email` parsers on the other hand
struggle a lot, probably because there are some line-breaks in the test file
input. This flaw shows even more in some of the tests below.


### Scenario: mixed

A form with two text fields and two small file uploads (1MB and 2MB).

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1430.26 MB/s (100%) | 6977.32 MB/s (100%)   |
| werkzeug            | 917.39 MB/s (64%)   | 2679.26 MB/s (38%)    |
| python-multipart    | 1128.61 MB/s (79%)  | 4615.28 MB/s (66%)    |
| streaming-form-data | 925.11 MB/s (65%)   | 2581.52 MB/s (37%)    |
| cgi                 | 128.15 MB/s (9%)    | -                     |
| email               | 58.29 MB/s (4%)     | 63.71 MB/s (1%)       |

This is the most realistic test and shows very similar results to the upload
test above. In this scenario, `multipart` and `python-multipart` outperform the
others. `werkzeug` and `streaming-form-data` are significantly slower, but still
way faster than the line-based `cgi` and `email` parsers.


### Scenario: worstcase_crlf

A 1MB upload that contains nothing but windows line-breaks.

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1410.88 MB/s (100%) | 6692.77 MB/s (100%)   |
| werkzeug            | 1030.43 MB/s (73%)  | 3919.79 MB/s (59%)    |
| python-multipart    | 701.90 MB/s (50%)   | 1341.29 MB/s (20%)    |
| streaming-form-data | 50.46 MB/s (4%)     | 52.22 MB/s (1%)       |
| cgi                 | 3.73 MB/s (0%)      | -                     |
| email               | 4.21 MB/s (0%)      | 4.25 MB/s (0%)        |

This is the first scenario that should not happen under normal circumstances
but is still an important factor if you want to prevent malicious uploads from
slowing down your web service. Both `multipart` and `werkzeug` are
unaffected and produce consistent results. `python-multipart` slows down, but
still performs well. `streaming-form-data` seems to struggle, but not as much as
the line-based parsers however. Those are practically unusable.


### Scenario: worstcase_lf

A 1MB upload that contains nothing but linux line-breaks.

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1423.84 MB/s (100%) | 6768.29 MB/s (100%)   |
| werkzeug            | 1006.21 MB/s (71%)  | 3687.33 MB/s (54%)    |
| python-multipart    | 1184.65 MB/s (83%)  | 4741.15 MB/s (70%)    |
| streaming-form-data | 902.49 MB/s (64%)   | 2401.63 MB/s (36%)    |
| cgi                 | 1.71 MB/s (0%)      | -                     |
| email               | 2.58 MB/s (0%)      | 2.58 MB/s (0%)        |

Linux line breaks are not valid in segment headers or boundaries, which benefits
parsers that do not try to parse invalid input. `streaming-form-data` is not
affected this time and performs well. The two lime-based parsers on the other
hand are even worse than before. Throughput is roughly halved, probably because
there are twice as many line breaks (and thus lines) in this scenario. 


### Scenario: worstcase_bchar

A 1MB upload that contains parts of the boundary.

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1425.87 MB/s (100%) | 5804.10 MB/s (100%)   |
| werkzeug            | 991.47 MB/s (70%)   | 3514.40 MB/s (61%)    |
| python-multipart    | 1204.74 MB/s (84%)  | 4207.84 MB/s (72%)    |
| streaming-form-data | 900.59 MB/s (64%)   | 2402.50 MB/s (42%)    |
| cgi                 | 1381.71 MB/s (97%)  | -                     |
| email               | 111.99 MB/s (8%)    | 122.23 MB/s (2%)      |

This test was originally added to show a second issue with the `python-multipart`
parser, but that's fixed now. There is another anomaly, though: Since the file
does not contain any newlines, `cgi` is suddenly competitive again. Its internal
`file.readline(1<<16)` call can read large chunks very quickly and the slow 
parser logic is triggered less often.


## Conclusions:

All modern parsers (`multipart`, `werkzeug`, `python-multipart` and
`streaming-form-data`) are fast and behave correctly. All three offer
non-blocking APIs for asnycio/ASGI environments with very little overhead and a
high level of control. There are differences in API design, code quality,
maturity and documentation, but that's not the focus of this benchmark.

For me, `streaming-form-data` was a bit of a surprise. It's really fast for
large file uploads, but not as fast as you might expect from a parser that is
partly written in Cython. It also shows significant overhead per segment, which
hurts performance when parsing small (e.g. text) fields. It's a mixed bag, but
still an interesting approach.

I probably do not need to talk much about `email` or `cgi`. Both show mixed
performance and are vulnerable to malicious inputs. `cgi` is deprecated (for
good reasons) and `email` is not designed for form data or large uploads at all.
Both are unsuitable or even dangerous to use in modern web applications.

