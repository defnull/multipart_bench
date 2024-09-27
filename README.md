# Benchmark for Python multipart/form-data parsers

This repository contains scenarios and parser test functions for different Python
based multipart/form-data parsers, both for blocking and non-blocking APIs (if
available).

Contestants:

* [multipart](https://pypi.org/project/multipart/) 1.0.0
  * Will be used in [Bottle](https://pypi.org/project/bottle/)
* [werkzeug](https://pypi.org/project/Werkzeug/) 3.0.4
  * Used by [Flask](https://pypi.org/project/Flask/) and many others.
* [python-multipart](https://pypi.org/project/python-multipart/) 0.0.10
  * Used by [Starlette](https://pypi.org/project/starlette/) and thus [FastAPI](https://pypi.org/project/fastapi/)
* [cgi](https://docs.python.org/3.12/library/cgi.html) CPython 3.12.3
  * Deprecated and will be removed in Python 3.13
* [email](https://docs.python.org/3.12/library/email.parser.html#email.message_from_binary_file) CPython 3.12.3
  * Not a `multipart/form-data` parser, but a general purpose `multipart` parser for emails. May be risky to use for
    public facing web services.


## Results

The results shown here were computed on a pretty old "AMD Ryzen 5 3600" running
Linux 6.8.0 and Python 3.12.3 with highest priority and pinned to a single core.
For each test, the parser is created with default settings and the results are
thrown away. Some parsers buffer to disk, but `TEMP` points to a ram-disk to
remove any disk IO from the equation. Each test was repeated at least 100 times
or 60 seconds and only the best result is used to compute a theoretical maximum
parser throughput per core.

Higher throughput is better, obviously.

### Scenario: simple

A simple form with just two small text fields.

| Parser           | Blocking (MB/s)   | Non-Blocking (MB/s)   |
|------------------|-------------------|-----------------------|
| multipart        | 6.53 MB/s         | 11.74 MB/s            |
| werkzeug         | 5.14 MB/s         | 6.20 MB/s             |
| python-multipart | 2.04 MB/s         | 2.64 MB/s             |
| cgi              | 4.34 MB/s         | -                     |
| email            | 11.20 MB/s        | -                     |

The `email` parser is surprisingly fast for small text fields, but will have more
problems later when larger file uploads are involved. Small forms like these should
be transmitted as `application/x-www-form-urlencoded` anyway, which has a lot less
overhead compared to `multipart/form-data`.

### Scenario: large

A large form with 100 small text fields.

| Parser           | Blocking (MB/s)   | Non-Blocking (MB/s)   |
|------------------|-------------------|-----------------------|
| multipart        | 11.36 MB/s        | 22.54 MB/s            |
| werkzeug         | 10.38 MB/s        | 13.17 MB/s            |
| python-multipart | 2.42 MB/s         | 3.05 MB/s             |
| cgi              | 6.52 MB/s         | -                     |
| email            | 94.33 MB/s        | -                     |

Again, `email` shines when parsing lots of simple text fields. No idea how these
numbers are even possible. Better view these results with a grain of salt.

== Scenario: upload

A file upload with a single large (32MB) file.

| Parser           | Blocking (MB/s)   | Non-Blocking (MB/s)   |
|------------------|-------------------|-----------------------|
| multipart        | 1150.00 MB/s      | 6015.66 MB/s          |
| werkzeug         | 895.60 MB/s       | 2631.91 MB/s          |
| python-multipart | 430.46 MB/s       | 600.15 MB/s           |
| cgi              | 130.00 MB/s       | -                     |
| email            | 111.47 MB/s       | -                     |

Now we are talking. When dealing with actual file uploads, `multipart` is the
clear winner and `werkzeug` also performs really well. Note that some parsers
may show different results with specifically crafted file content. See the
worst-case scenarios further down below. In this test, the file consists of 
`string.printable` characters.

### Scenario: mixed

A form with two text fields and two small file uploads (1MB and 2MB).

| Parser           | Blocking (MB/s)   | Non-Blocking (MB/s)   |
|------------------|-------------------|-----------------------|
| multipart        | 1217.45 MB/s      | 6869.47 MB/s          |
| werkzeug         | 936.99 MB/s       | 2673.46 MB/s          |
| python-multipart | 453.49 MB/s       | 587.44 MB/s           |
| cgi              | 132.04 MB/s       | -                     |
| email            | 137.90 MB/s       | -                     |

This is the most realistic test and shows very similar results to the upload
test above. As soon as an actual file upload is involved, `multipart` and
`werkzeug` outperform the others.

### Scenario: worstcase_crlf

A 1MB upload that contains nothing but windows line-breaks.

| Parser           | Blocking (MB/s)   | Non-Blocking (MB/s)   |
|------------------|-------------------|-----------------------|
| multipart        | 1216.12 MB/s      | 6504.70 MB/s          |
| werkzeug         | 1056.70 MB/s      | 3904.44 MB/s          |
| python-multipart | 0.67 MB/s         | 0.75 MB/s             |
| cgi              | 3.78 MB/s         | -                     |
| email            | 8.03 MB/s         | -                     |

This is the first worst-case scenario, which should not happen under normal
circumstances but is still an important factor if you want to prevent malicious
uploads from slowing down your web service. Both `multipart` and `werkzeug` are
unaffected and produce consistent results, but all parsers that consume input
line-by-line slow down to a crawl. `python-multipart` is special here, because
it is not actually line-based like `email` or `cgi`, but still suffers greatly
from this kind of input. The issue is already reported and will hopefully be 
fixed in a future version of the parser.

### Scenario: worstcase_lf

A 1MB upload that contains nothing but linux line-breaks.

| Parser           | Blocking (MB/s)   | Non-Blocking (MB/s)   |
|------------------|-------------------|-----------------------|
| multipart        | 1214.42 MB/s      | 6484.41 MB/s          |
| werkzeug         | 1028.76 MB/s      | 3574.04 MB/s          |
| python-multipart | 2.01 MB/s         | 2.01 MB/s             |
| cgi              | 1.69 MB/s         | -                     |
| email            | 3.94 MB/s         | -                     |

For reasons only the developers may know, `python-multipart` performs slightly
better than with CRLF line-breaks but still way worse than expected. Both `cgi`
and `email` are even worse than before, probably because we have twice as many
line breaks (and thus lines) in this scenario. Throughput is roughly halved.
Both `multipart` and `werkzeug` are stable and fast.

### Scenario: worstcase_bchar

A 1MB upload that contains parts of the boundary.

| Parser           | Blocking (MB/s)   | Non-Blocking (MB/s)   |
|------------------|-------------------|-----------------------|
| multipart        | 1175.73 MB/s      | 5631.51 MB/s          |
| werkzeug         | 1006.72 MB/s      | 3434.27 MB/s          |
| python-multipart | 46.72 MB/s        | 47.93 MB/s            |
| cgi              | 1425.05 MB/s      | -                     |
| email            | 624.73 MB/s       | -                     |

Most parsers are unaffected by this special scenario, because they search for
the whole boundary and do not care about partial matches. With two exceptions:
`cgi` benefits from an input that does not contain any newlines and is faster
than usual, and `python-multipart` tanks completely. I'm not sure why, but as
soon as the upload body consists mainly of characters that are also present in
the boundary, which is not unlikely, throughput is way worse. This was also
reported to the maintainers and the benchmark will be corrected once the issue
is fixed. 

## Conclusions:

* Both `multipart` and `werkzeug` are fast and stable. Both offer non-blocking
  parsers for asnycio/ASGI environments that have very little overhead.
* Both `email` and `cgi` are surprisingly fast in certain scenarios (small text
  fields and ASCII input without any newlines), but very slow in others. Both
  rely on blocking APIs, which makes them simpler, but also unsuitable for
  asyncio/ASGI environments. And the most pressing issues: `cgi` is deprecated 
  and will be removed from python, and `email` is not designed for
  `multipart/form-data` and accepts input a form parser should not accept. Web
  applications or frameworks should not rely on those.
* The `python-multipart` parser is slower than expected, and has some serious
  issues with certain inputs. It also needs special care if used in projects
  that also (maybe indirectly) depend on `multipart` because of a module name
  conflict. In it's current state I would not recommend it. 