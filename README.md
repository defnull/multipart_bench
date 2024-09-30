# Benchmark for Python multipart/form-data parsers

This repository contains scenarios and parser test functions for different Python
based multipart/form-data parsers, both for blocking and non-blocking APIs (if
available).

## Contestants

* [multipart](https://pypi.org/project/multipart/) v1.0.1
  * Will be used in [Bottle](https://pypi.org/project/bottle/). Disclaimer: I am the author of both *multipart* and *Bottle*.
* [werkzeug](https://pypi.org/project/Werkzeug/) v3.0.4
  * Used by [Flask](https://pypi.org/project/Flask/) and others.
* [python-multipart](https://pypi.org/project/python-multipart/) v0.0.12
  * Used by [Starlette](https://pypi.org/project/starlette/) and thus [FastAPI](https://pypi.org/project/fastapi/)
* [cgi](https://docs.python.org/3.12/library/cgi.html) CPython 3.12.3
  * Deprecated and will be removed in Python 3.13
* [email](https://docs.python.org/3.12/library/email.parser.html#email.message_from_binary_file) CPython 3.12.3
  * Buffers everything in memory and is unsuitable for large file uploads.
  * Not a specialized `multipart/form-data` parser, but a general purpose parser for emails.

## Updates

* **30.09.2024** python-multipart v0.0.11 fixed some of the edge-cases and now
  has better throughput in some tests, especially in the worst-case scenarios.
* **30.09.2024** There was an issue with the `email` parser that caused it to
  skip over the actual parsing and also not do any IO in the blocking test.
  Throughput was way higher than expected. This is fixed now.
* **30.09.2024** Default size for in-memory buffers is different for each parser,
  resulting in an unfair comparison. The tests now configure a limit of 500K for
  each parser, which is the hard-coded value in werkzeug and also a sensible
  default.

## Method

All tests were performed on a pretty old "AMD Ryzen 5 3600" running Linux 6.8.0
and Python 3.12.3 with highest possible priority and pinned to a single core.

For each test, the parser is created with default¹ settings and the results are
thrown away. Some parsers buffer to disk, but `TEMP` points to a ram-disk to
reduce disk IO from the equation. Each test was repeated at least 100 times or
60 seconds and only the best result is used to compute a theoretical maximum
parser throughput per core.

¹) There is one exception: The limit for in-memory buffered files is set to
500KB (hard-coded in werkzeug) to ensure a fair comparison.

## Results

Higher throughput is better, obviously.

### Scenario: simple

A simple form with just two small text fields.

| Parser           | Blocking (MB/s)   | Non-Blocking (MB/s)   |
|------------------|-------------------|-----------------------|
| multipart        | 10.57 MB/s (100%) | 14.09 MB/s (100%)     |
| werkzeug         | 5.05 MB/s (48%)   | 6.13 MB/s (43%)       |
| python-multipart | 3.45 MB/s (33%)   | 5.68 MB/s (40%)       |
| cgi              | 4.30 MB/s (41%)   | -                     |
| email            | 3.58 MB/s (34%)   | 3.89 MB/s (28%)       |

This scenario is so small that it shows initialization overhead more than actual
parsing performance. Small forms like these should better be transmitted as
`application/x-www-form-urlencoded`, which has a lot less overhead compared to
`multipart/form-data` and should be a lot faster.

Update **30.09.2024**: The `email` parser was surprisingly fast for small text
fields. This turned out to be a bug in the test code. The results now are more
realistic.

### Scenario: large

A large form with 100 small text fields.

| Parser           | Blocking (MB/s)   | Non-Blocking (MB/s)   |
|------------------|-------------------|-----------------------|
| multipart        | 24.30 MB/s (100%) | 30.67 MB/s (100%)     |
| werkzeug         | 10.19 MB/s (42%)  | 12.71 MB/s (41%)      |
| python-multipart | 5.04 MB/s (21%)   | 8.95 MB/s (29%)       |
| cgi              | 6.36 MB/s (26%)   | -                     |
| email            | 11.17 MB/s (46%)  | 12.88 MB/s (42%)      |

Large forms show a slightly higher throughput because initialization overhead
is no longer the main factor. `email` is designed for this type of line based
text input, but `multipart` is still faster.

Update **30.09.2024**: The `email` parser was surprisingly fast for small text
fields. This turned out to be a bug in the test code. The results now are more
realistic.


### Scenario: upload

A file upload with a single large (32MB) file.

| Parser           | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|------------------|---------------------|-----------------------|
| multipart        | 1498.41 MB/s (100%) | 6094.32 MB/s (100%)   |
| werkzeug         | 912.74 MB/s (61%)   | 2643.83 MB/s (43%)    |
| python-multipart | 1386.15 MB/s (93%)  | 4624.38 MB/s (76%)    |
| cgi              | 131.17 MB/s (9%)    | -                     |
| email            | 51.80 MB/s (3%)     | 59.98 MB/s (1%)       |

Now it gets interesting. When dealing with actual file uploads, `multipart` is
the clear winner with `python-multipart` as a close second. `werkzeug` also
performs pretty well compared to the line-based `cgi` and `email` parsers. Both
struggle a lot, probably because there are line-breaks in the input. This can
get even worse, though. See below.

### Scenario: mixed

A form with two text fields and two small file uploads (1MB and 2MB).

| Parser           | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|------------------|---------------------|-----------------------|
| multipart        | 1445.70 MB/s (100%) | 6906.77 MB/s (100%)   |
| werkzeug         | 939.68 MB/s (65%)   | 2678.41 MB/s (39%)    |
| python-multipart | 1198.17 MB/s (83%)  | 4675.59 MB/s (68%)    |
| cgi              | 130.80 MB/s (9%)    | -                     |
| email            | 65.51 MB/s (5%)     | 69.36 MB/s (1%)       |

This is the most realistic test and shows very similar results to the upload
test above. As soon as an actual file upload is involved, `multipart` and
`python-multipart` outperform the others. `werkzeug` is significantly slower,
but still way better than the line-based `cgi` and `email` parsers.

### Scenario: worstcase_crlf

A 1MB upload that contains nothing but windows line-breaks.

| Parser           | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|------------------|---------------------|-----------------------|
| multipart        | 1487.82 MB/s (100%) | 6538.67 MB/s (100%)   |
| werkzeug         | 1052.91 MB/s (71%)  | 3927.89 MB/s (60%)    |
| python-multipart | 726.70 MB/s (49%)   | 1348.81 MB/s (21%)    |
| cgi              | 3.75 MB/s (0%)      | -                     |
| email            | 4.25 MB/s (0%)      | 4.27 MB/s (0%)        |

This is the first worst-case scenario, which should not happen under normal
circumstances but is still an important factor if you want to prevent malicious
uploads from slowing down your web service. Both `multipart` and `werkzeug` are
unaffected and produce consistent results. `python-multipart` slows down, but
still performs well. The line-based parsers however are practically unusable.

Update **30.09.2024** python-multipart v0.0.11 fixed this edge-cases and no
longer chokes on this scenario. It previously showed down to 0.75 MB/s or less
on this test, even slower than `cgi` or `email`.

### Scenario: worstcase_lf

A 1MB upload that contains nothing but linux line-breaks.

| Parser           | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|------------------|---------------------|-----------------------|
| multipart        | 1496.03 MB/s (100%) | 6594.33 MB/s (100%)   |
| werkzeug         | 1024.30 MB/s (68%)  | 3608.61 MB/s (55%)    |
| python-multipart | 1259.46 MB/s (84%)  | 4654.28 MB/s (71%)    |
| cgi              | 1.70 MB/s (0%)      | -                     |
| email            | 2.55 MB/s (0%)      | 2.57 MB/s (0%)        |

Similar results compared to the windows line-break test above, but `cgi` and
`email` are even worse this time. Throughput is roughly halved, probably because
there are twice as many line breaks (and thus lines) in this scenario. 

Update **30.09.2024** python-multipart v0.0.11 fixed this edge-cases and no
longer chokes on this scenario. It previously showed down to 0.75 MB/s or less
on this test, even slower than `cgi` or `email`.

### Scenario: worstcase_bchar

A 1MB upload that contains parts of the boundary.

| Parser           | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|------------------|---------------------|-----------------------|
| multipart        | 1463.16 MB/s (100%) | 5794.98 MB/s (100%)   |
| werkzeug         | 1012.12 MB/s (69%)  | 3497.55 MB/s (60%)    |
| python-multipart | 1230.30 MB/s (84%)  | 4242.27 MB/s (73%)    |
| cgi              | 1433.57 MB/s (98%)  | -                     |
| email            | 144.75 MB/s (10%)   | 163.05 MB/s (3%)      |

This test was originally added to show a second issue with the `python-multipart`
parser, but that's fixed now. There is another anomaly, though: Since the file
does not contain any newlines, `cgi` is suddenly competitive again. Its internal
`file.readline(1<<16)` call can read large chunks at a time and the parser logic
runs less often.

Update **30.09.2024** python-multipart v0.0.11 fixed this edge-cases and no
longer chokes on this scenario. It previously showed down to 0.75 MB/s or less
on this test, even slower than `cgi` or `email`.

## Conclusions:

All three modern parsers (`multipart`, `werkzeug` and `python-multipart`) are
fast and behave correctly. All three offer non-blocking APIs for asnycio/ASGI
environments with very little overhead and a high level of control. There are
differences in API design, code quality, maturity and documentation, but that's
not the focus of this test suite.

Some aspects should still be mentioned. For example the
[naming conflict](https://github.com/twisted/treq/issues/399) caused by
`python-multipart`, or the fact that `python-multipart` is mostly undocumented
and may be [merged into starlette and abandoned](https://github.com/Kludex/python-multipart/issues/16)
in the future. This makes it hard to recommend it to anyone, and I really hope
the naming conflict gets resolved, one way ot the other.

I probably do not need to talk much about `email` or `cgi`. Both perform very
poorly and are vulnerable to malicious inputs. `cgi` is deprecated (for good
reasons) and `email` is not designed for `multipart/form-data` or large uploads
at all, rendering both useless or even dangerous for web applications.

