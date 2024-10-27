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
* [django](https://pypi.org/project/Django/) v5.1.2
  * Full featured web framework, not just a parser.
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

Not included: Some parsers *cheat* by loading the entire request body into memory
(e.g. sanic or litestar). Those are obviously very fast in benchmarks but also
very unpractical when dealing with large file uploads.

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
* **25.10.2024** Added results for `django` parser.


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
| multipart           | 13.79 MB/s (100%) | 19.72 MB/s (100%)     |
| werkzeug            | 5.69 MB/s (41%)   | 7.16 MB/s (36%)       |
| django              | 2.99 MB/s (22%)   | -                     |
| python-multipart    | 3.63 MB/s (26%)   | 6.09 MB/s (31%)       |
| streaming-form-data | 0.83 MB/s (6%)    | 0.86 MB/s (4%)        |
| cgi                 | 4.78 MB/s (35%)   | -                     |
| email               | 3.95 MB/s (29%)   | 4.33 MB/s (22%)       |

This scenario is so small that it shows initialization overhead more than actual
parsing performance, which hurts `streaming-form-data` the most. Small forms like
these should better be transmitted as `application/x-www-form-urlencoded`, which
has a lot less overhead compared to `multipart/form-data` and should be a lot
faster.


### Scenario: large

A large form with 100 small text fields.

| Parser              | Blocking (MB/s)   | Non-Blocking (MB/s)   |
|---------------------|-------------------|-----------------------|
| multipart           | 23.85 MB/s (100%) | 30.56 MB/s (100%)     |
| werkzeug            | 10.24 MB/s (43%)  | 12.77 MB/s (42%)      |
| django              | 5.48 MB/s (23%)   | -                     |
| python-multipart    | 5.04 MB/s (21%)   | 8.92 MB/s (29%)       |
| streaming-form-data | 1.13 MB/s (5%)    | 1.17 MB/s (4%)        |
| cgi                 | 6.34 MB/s (27%)   | -                     |
| email               | 11.15 MB/s (47%)  | 12.96 MB/s (42%)      |

Large forms show a higher throughput because initialization overhead is no longer
the main factor. Parsing many small fields is still a lot of work for parsers,
and there are significant differences between implementations. `email` is
designed for this type of line based text input, but `multipart` is still twice
as fast.


### Scenario: upload

A file upload with a single large (32MB) file.

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1445.68 MB/s (100%) | 6048.42 MB/s (100%)   |
| werkzeug            | 904.58 MB/s (63%)   | 2658.58 MB/s (44%)    |
| django              | 954.25 MB/s (66%)   | -                     |
| python-multipart    | 1270.15 MB/s (88%)  | 4602.17 MB/s (76%)    |
| streaming-form-data | 1084.81 MB/s (75%)  | 4927.08 MB/s (81%)    |
| cgi                 | 127.75 MB/s (9%)    | -                     |
| email               | 51.96 MB/s (4%)     | 59.73 MB/s (1%)       |

Now it gets interesting. When dealing with actual file uploads, both
`python-multipart` and `streaming-form-data` catch up and are now faster than 
`werkzeug` or `django`. All four are slower than `multipart`, but the results
are still impressive. The line-based `cgi` and `email` parsers on the other hand
struggle a lot, probably because there are some line-breaks in the test file
input. This flaw shows even more in some of the tests below.


### Scenario: mixed

A form with two text fields and two small file uploads (1MB and 2MB).

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1393.63 MB/s (100%) | 6932.10 MB/s (100%)   |
| werkzeug            | 922.54 MB/s (66%)   | 2680.75 MB/s (39%)    |
| django              | 934.86 MB/s (67%)   | -                     |
| python-multipart    | 1109.66 MB/s (80%)  | 4647.66 MB/s (67%)    |
| streaming-form-data | 930.12 MB/s (67%)   | 2592.41 MB/s (37%)    |
| cgi                 | 127.69 MB/s (9%)    | -                     |
| email               | 64.72 MB/s (5%)     | 68.16 MB/s (1%)       |

This is the most realistic test and shows very similar results to the upload
test above. In this scenario, `multipart` and `python-multipart` outperform the
others. `werkzeug`, `django` and `streaming-form-data` are a bit slower, but
still way faster than the line-based `cgi` and `email` parsers.


### Scenario: worstcase_crlf

A 1MB upload that contains nothing but windows line-breaks.

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1392.83 MB/s (100%) | 6765.45 MB/s (100%)   |
| werkzeug            | 1028.09 MB/s (74%)  | 3992.00 MB/s (59%)    |
| django              | 992.70 MB/s (71%)   | -                     |
| python-multipart    | 700.70 MB/s (50%)   | 1340.66 MB/s (20%)    |
| streaming-form-data | 50.42 MB/s (4%)     | 52.34 MB/s (1%)       |
| cgi                 | 3.81 MB/s (0%)      | -                     |
| email               | 4.23 MB/s (0%)      | 4.27 MB/s (0%)        |

This is the first scenario that should not happen under normal circumstances
but is still an important factor if you want to prevent malicious uploads from
slowing down your web service. `multipart`, `werkzeug` and `django` are
mostly unaffected and produce consistent results. `python-multipart` slows down,
but still performs well. `streaming-form-data` seems to struggle, but not as
much as the line-based parsers. Those choke on the high number of line-endings
and are practically unusable.


### Scenario: worstcase_lf

A 1MB upload that contains nothing but linux line-breaks.

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1395.76 MB/s (100%) | 6782.10 MB/s (100%)   |
| werkzeug            | 1001.55 MB/s (72%)  | 3697.27 MB/s (55%)    |
| django              | 953.28 MB/s (68%)   | -                     |
| python-multipart    | 1152.93 MB/s (83%)  | 4707.50 MB/s (69%)    |
| streaming-form-data | 897.26 MB/s (64%)   | 2420.21 MB/s (36%)    |
| cgi                 | 1.71 MB/s (0%)      | -                     |
| email               | 2.60 MB/s (0%)      | 2.60 MB/s (0%)        |

Linux line breaks are not valid in segment headers or boundaries, which benefits
parsers that do not try to parse invalid input. `streaming-form-data` is less
affected this time and performs well. The two line-based parsers on the other
hand are even worse than before. Throughput is roughly halved, probably because
there are twice as many line-breaks (and thus lines) in this scenario. 


### Scenario: worstcase_bchar

A 1MB upload that contains parts of the boundary.

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1333.45 MB/s (97%)  | 5853.86 MB/s (100%)   |
| werkzeug            | 996.17 MB/s (72%)   | 3533.90 MB/s (60%)    |
| django              | 998.89 MB/s (72%)   | -                     |
| python-multipart    | 1132.91 MB/s (82%)  | 4246.49 MB/s (73%)    |
| streaming-form-data | 902.56 MB/s (65%)   | 2404.69 MB/s (41%)    |
| cgi                 | 1379.35 MB/s (100%) | -                     |
| email               | 146.24 MB/s (11%)   | 163.16 MB/s (3%)      |

This test was originally added to show a second issue with the `python-multipart`
parser, but that's fixed now. There is another interesting anomaly, though: Since
the file does not contain any newlines, `cgi` is suddenly competitive again. Its
internal `file.readline(1<<16)` call can read large chunks very quickly and the
slow parser logic is triggered less often.



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

