# Benchmark for Python multipart/form-data parsers

This repository contains scenarios and parser tests for different Python based
`multipart/form-data` parsers, comparing both blocking and non-blocking APIs (if
available). The [multipart](https://pypi.org/project/multipart/) library is used
as a baseline, because it is currently the fastest pure-python parser tested and
also the reason I'm benchmarking parsers in the first place.

## Contestants

* [multipart](https://pypi.org/project/multipart/) v1.2.1
  * Used in [Bottle](https://pypi.org/project/bottle/), [LiteStar](https://litestar.dev/), [Zope](https://zope.readthedocs.io/) and others.
  * [CPython docs](https://docs.python.org/3.12/library/cgi.html) recommend it as a `cgi.FieldStorage` replacement.
  * Disclaimer: I am the author and maintainer of this library.
* [werkzeug](https://pypi.org/project/Werkzeug/) v3.1.3
  * Used in [Flask](https://pypi.org/project/Flask/) and others.
  * Does a lot more than *just* multipart parsing.
* [django](https://pypi.org/project/Django/) v5.1.4
  * Full featured web framework, not just a parser.
* [python-multipart](https://pypi.org/project/python-multipart/) v0.0.20
  * Used in [Starlette](https://pypi.org/project/starlette/) and thus [FastAPI](https://pypi.org/project/fastapi/).
* [streaming-form-data](https://pypi.org/project/streaming-form-data/) v1.19.0 
  * Partly written in Cython.
* [emmett-core](https://pypi.org/project/emmett-core/) 1.0.5
  * Mostly written in Rust.
  * Similar to Django or werkzeug, this library does a lot more than *just* multipart parsing. It is not a stand-alone parser, but a support library for the [emmett](https://emmett.sh/) framework and rarely used outside of this context. 
* [cgi.FieldStorage](https://docs.python.org/3.12/library/cgi.html) CPython 3.12.3
  * Deprecated in Python 3.11 and removed in Python 3.13
* [email.parser.BytesFeedParser](https://docs.python.org/3.12/library/email.parser.html#email.parser.BytesFeedParser) CPython 3.12.3
  * Designed as a parser for emails, not `multipart/form-data`.
  * Buffers everything in memory, including large file uploads.

**Not included:** Some parsers *cheat* by loading the entire request body into memory
(e.g. sanic or litestar before they switched to multipart). Those are obviously
very fast in benchmarks but also very unpractical when dealing with large file
uploads.



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
* **06.11.2024** Added results for `emett-core` parser.
* **24.12.2024** Added "worstcase_junk" scenario but waiting for a fix in the most
  affected libraries before publishing results, as this may qualify as a security
  issue and could be abused for denial of service attacks.


## Method

All tests were performed on a pretty old "AMD Ryzen 5 3600" running Linux 6.8.0
and Python 3.12.3 with highest possible priority and pinned to a single core.

For each test, the parser is created with default¹ settings and the results are
thrown away. Some parsers buffer to disk, but `TEMP` points to a ram-disk to
reduce disk IO from the equation. Each test is repeated until there is no
improvement for at least 100 runs in a row, then the best run is used to compute
the theoretical maximum throughput per core.

The fastest pure-python parser (currently `multipart`) is used as the 100% baseline
for each test. This ensures that pure python parsers are always easy to compare
against each other, and compiled parsers can be included without screwing with
the results too much.

¹) There is one exception: The limit for in-memory buffered files is set to
500KB (hard-coded in `werkzeug`) to ensure a fair comparison.


## Results

Parser throughput is measured in MB/s (input size / time). Higher throughput is
better.


### Scenario: simple

A simple form with just two small text fields.

| Parser              | Blocking (MB/s)   | Non-Blocking (MB/s)   |
|---------------------|-------------------|-----------------------|
| multipart           | 15.57 MB/s (100%) | 23.24 MB/s (100%)     |
| werkzeug            | 5.55 MB/s (36%)   | 7.11 MB/s (31%)       |
| django              | 3.08 MB/s (20%)   | -                     |
| python-multipart    | 3.66 MB/s (23%)   | 6.14 MB/s (26%)       |
| streaming-form-data | 0.80 MB/s (5%)    | 0.84 MB/s (4%)        |
| emmett-core         | 71.14 MB/s (457%) | -                     |
| cgi                 | 4.79 MB/s (31%)   | -                     |
| email               | 3.95 MB/s (25%)   | 4.36 MB/s (19%)       |

This scenario is so small that it shows initialization and interpreter overhead
more than actual parsing performance, which benefits `emmett-core` the most
because everything happens in Rust and outside of the python runtime. The results
for `streaming-form-data` are a bit surprising though, given that it is partly
written in Cython and compiled to native code. My guess is that there is some
significant overhead when calling Python callbacks from Cython, which happens a
lot in this test. When comparing the pure-python parsers, `multipart` is the
clear winner.

**Note:** Small forms like these should better be transmitted as
`application/x-www-form-urlencoded`, which has a lot less overhead compared to
`multipart/form-data` and should be a lot faster to parse, so take this benchmark
with a large grain of salt. This is an uncommon and artificial scenario.


### Scenario: large

A large form with 100 small text fields.

| Parser              | Blocking (MB/s)    | Non-Blocking (MB/s)   |
|---------------------|--------------------|-----------------------|
| multipart           | 28.09 MB/s (100%)  | 36.37 MB/s (100%)     |
| werkzeug            | 9.65 MB/s (34%)    | 12.49 MB/s (34%)      |
| django              | 5.53 MB/s (20%)    | -                     |
| python-multipart    | 5.11 MB/s (18%)    | 9.25 MB/s (25%)       |
| streaming-form-data | 1.13 MB/s (4%)     | 1.17 MB/s (3%)        |
| emmett-core         | 131.14 MB/s (467%) | -                     |
| cgi                 | 6.43 MB/s (23%)    | -                     |
| email               | 11.18 MB/s (40%)   | 12.95 MB/s (36%)      |

This scenario benefits parsers with low per-field overhead or a line-based
parser design (like `cgi` and `email`) because each field is just a single line,
and there are a lot of them. Initialization overhead is less important here
compared to the 'simple' scenario above.

No surprise that `emmett-core` performs well here, because the payload still
fits in a small number of chunks and other than `streaming-form-data` the parser
does not have to call into Python code for each field. The Rust parser thus
completely bypasses the python interpreter overhead. `email` also performs
reasonably well, as it is designed for this type of line-based text input and
even surpasses many of the other pure-python parsers, but `multipart` is still
more than twice as fast.


### Scenario: upload

A file upload with a single large (32MB) file.

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1202.36 MB/s (100%) | 6193.85 MB/s (100%)   |
| werkzeug            | 758.72 MB/s (63%)   | 2654.56 MB/s (43%)    |
| django              | 788.98 MB/s (66%)   | -                     |
| python-multipart    | 1119.54 MB/s (93%)  | 4537.55 MB/s (73%)    |
| streaming-form-data | 1048.11 MB/s (87%)  | 4895.12 MB/s (79%)    |
| emmett-core         | 292.10 MB/s (24%)   | -                     |
| cgi                 | 107.48 MB/s (9%)    | -                     |
| email               | 55.58 MB/s (5%)     | 64.37 MB/s (1%)       |

Now it gets interesting! When dealing with actual file uploads, both
`python-multipart` and `streaming-form-data` catch up and are now faster than 
`werkzeug` or `django`. All four are slower than `multipart`, but the results
are still impressive. The line-based `cgi` and `email` parsers on the other hand
struggle a lot, probably because there are some line-breaks in the test file
input. This flaw shows even more in some of the tests below.

What really surprised me here was the poor performance of `emmett-core`. It
should be the fastest parser in all scenarios (because "Rust") but in the first
test that actually moves some bytes, it falls back significantly. My best guess
is that the context translation overhead between Python and the native Rust code
is to blame. The parser is fed chunks of bytes and each round involves call-overhead
and expensive copy operations. Pure python code can work directly with the
provided byte string and can avoid a copy in most cases. But that's just a guess.


### Scenario: mixed

A form with two text fields and two small file uploads (1MB and 2MB).

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1222.65 MB/s (100%) | 7096.61 MB/s (100%)   |
| werkzeug            | 785.09 MB/s (64%)   | 2668.64 MB/s (38%)    |
| django              | 753.48 MB/s (62%)   | -                     |
| python-multipart    | 961.94 MB/s (79%)   | 4593.43 MB/s (65%)    |
| streaming-form-data | 783.71 MB/s (64%)   | 2583.91 MB/s (36%)    |
| emmett-core         | 294.25 MB/s (24%)   | -                     |
| cgi                 | 107.25 MB/s (9%)    | -                     |
| email               | 68.35 MB/s (6%)     | 72.71 MB/s (1%)       |

This is the most realistic test and shows similar results to the upload
test above, with two notable exceptions: `python-multipart` and
`streaming-form-data` fall back a bit and are now more close to `werkzeug` and
`django`. `emett-core` is unexpectedly slow again, slower than most modern
pure-python parsers, but still way faster than the line-based `cgi` and `email`
parsers. `multipart` outperforms all of them by a significant margin.


### Scenario: worstcase_crlf

A 1MB upload that contains nothing but windows line-breaks.

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1277.10 MB/s (100%) | 6776.64 MB/s (100%)   |
| werkzeug            | 862.28 MB/s (68%)   | 3930.37 MB/s (58%)    |
| django              | 791.83 MB/s (62%)   | -                     |
| python-multipart    | 632.24 MB/s (50%)   | 1371.32 MB/s (20%)    |
| streaming-form-data | 48.49 MB/s (4%)     | 50.76 MB/s (1%)       |
| emmett-core         | 295.85 MB/s (23%)   | -                     |
| cgi                 | 3.78 MB/s (0%)      | -                     |
| email               | 4.27 MB/s (0%)      | 4.31 MB/s (0%)        |

This is the first scenario that should not happen under normal circumstances
but is still an important factor if you want to prevent malicious uploads from
slowing down your web service. `multipart`, `werkzeug`, `django` and `emett-core`
are mostly unaffected and produce consistent results. `python-multipart` slows
down compared to the non-malicious tests, but still performs reasonably well.
`streaming-form-data` seem to struggle a lot here, but not as much as the
line-based parsers. Those choke on the high number of line-endings and are
practically unusable.


### Scenario: worstcase_lf

A 1MB upload that contains nothing but linux line-breaks.

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1269.47 MB/s (100%) | 6747.33 MB/s (100%)   |
| werkzeug            | 844.68 MB/s (67%)   | 3675.44 MB/s (54%)    |
| django              | 914.33 MB/s (72%)   | -                     |
| python-multipart    | 1053.97 MB/s (83%)  | 4600.36 MB/s (68%)    |
| streaming-form-data | 771.28 MB/s (61%)   | 2353.16 MB/s (35%)    |
| emmett-core         | 294.77 MB/s (23%)   | -                     |
| cgi                 | 1.71 MB/s (0%)      | -                     |
| email               | 2.58 MB/s (0%)      | 2.61 MB/s (0%)        |

Linux line breaks are not valid in segment headers or boundaries, which benefits
parsers that do not try to be nice and parse invalid input for compatibility
reasons. `streaming-form-data` is less affected this time and performs well. The
two line-based parsers on the other hand are even worse than before. Throughput
is roughly halved, probably because there are twice as many line-breaks (and thus
lines) in this scenario. 


### Scenario: worstcase_bchar

A 1MB upload that contains parts of the boundary.

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 1239.48 MB/s (100%) | 5849.90 MB/s (100%)   |
| werkzeug            | 836.65 MB/s (68%)   | 3502.45 MB/s (60%)    |
| django              | 791.79 MB/s (64%)   | -                     |
| python-multipart    | 1024.75 MB/s (83%)  | 4183.56 MB/s (72%)    |
| streaming-form-data | 767.22 MB/s (62%)   | 2346.70 MB/s (40%)    |
| emmett-core         | 294.68 MB/s (24%)   | -                     |
| cgi                 | 1155.09 MB/s (93%)  | -                     |
| email               | 168.06 MB/s (14%)   | 194.91 MB/s (3%)      |

This test was originally added to show an issue with the `python-multipart`
parser, but that was fixed quickly after reporting. There is another interesting
anomaly, though: Since the file does not contain any newlines, `cgi` is suddenly
competitive again. Its internal `file.readline(1<<16)` call can read large chunks
very quickly and the slow parser logic is triggered less often.


### Scenario: worstcase_junk
Junk before the first and after the last boundary (1MB each)

| Parser              | Blocking (MB/s)     | Non-Blocking (MB/s)   |
|---------------------|---------------------|-----------------------|
| multipart           | 6434.06 MB/s (100%) | 6746.04 MB/s (100%)   |
| werkzeug            | 23.45 MB/s (0%)     | 23.45 MB/s (0%)       |
| django              | 993.23 MB/s (15%)   | -                     |
| python-multipart    | 10.82 MB/s (0%)     | 10.77 MB/s (0%)       |
| streaming-form-data | 47.15 MB/s (1%)     | 49.34 MB/s (1%)       |
| emmett-core         | *(fails)*           | -                     |
| cgi                 | 12.74 MB/s (0%)     | -                     |
| email               | 3.03 MB/s (0%)      | 3.00 MB/s (0%)        |

The multipart protocol allows arbitrary junk before the first and after the last
boundary, and requires parsers to ignore it. This protocol 'feature' has no
practical use and no browser or HTTP client would ever do that, but parsers
still have to deal with it, one way or the other.

When this was first discovered, `multipart` was the only implementation not
showing a drastic slowdown in this test. All the other parsers spent way too
much time parsing and the discarding junk. Some were so slow that I waited for
the most affected libraries to release fixes before I published any results, as
this may be abused for denial of service attacks and qualify as a security issue.
The results are still really bad for most of the parsers, but not as catastrophic
as a couple of weeks ago. Update your dependencies!

**Note:** `emmett-core` fails here, which is good! Malicious input can and should
be rejected. `multipart` will also bail out very quickly in *strict* mode, but
these tests are run in default mode which accepts some amounts of unusual input
for compatibility reasons. It's still unaffected, even in non-strict mode, as it
manages to skip junk fast enough.


## Conclusion

All modern pure-python parsers (`multipart`, `werkzeug`, `python-multipart`) are
fast and behave correctly. All three offer non-blocking APIs for asnycio/ASGI
environments with very little overhead and a high level of control. There are
differences in API design, code quality, maturity, support and documentation,
but that's not the focus of this benchmark. The `django` parser is also pretty
solid, but hard to use outside of Django applications. 

For me, both `streaming-form-data` and `emmett-core` were a bit of a surprise.
Both are reasonably fast for large file uploads, but not as fast as you might
expect from parsers written in Cython or Rust. I would have never guessed that a
pure python parser can outperform both in the upload tests. The overhead
introduced by those Python/native compatibility layers seems to be significant.
The results for those two parsers were also very different. Lessons learned:
Always measure. Just because something is implemented in a faster language does
not mean it's actually faster.

I probably do not need to talk much about `email` or `cgi`. Both show mixed
performance and are vulnerable to malicious inputs. `cgi` is deprecated (for
good reasons) and `email` is not designed for form data or large uploads at all.
Both are unsuitable or even dangerous to use in modern web applications.

All in all, `multipart` seems to be a good choice for new projects. It's fast,
small, well tested, has no dependencies and behaves correctly when presented with
malicious inputs. But don't just take my word for it, I'm obviously biased as the
author of that library. Look at the results, look at the test cases, check out
the projects, try them out and make up your own mind.
