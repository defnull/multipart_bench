from .scenarios import Scenario

PARSERS = []


def add_parser(func):
    PARSERS.append(func)
    return func


try:
    import multipart

    @add_parser
    def multipart_sansio(scenario: Scenario):
        read = scenario.payload.read
        chunksize = scenario.chunksize
        mps = multipart.MultipartSegment
        with multipart.PushMultipartParser(scenario.boundary) as parser:
            parse = parser.parse
            while not parser.closed:
                for event in parse(read(chunksize)):
                    if isinstance(event, mps):
                        pass
                    elif event:
                        pass
                    else:
                        pass

    @add_parser
    def multipart_blocking(scenario: Scenario):
        list(
            multipart.MultipartParser(
                scenario.payload,
                boundary=scenario.boundary,
                buffer_size=scenario.chunksize,
            )
        )

except ImportError:
    multipart_sansio = None
    multipart_blocking = None

try:
    import werkzeug.sansio.multipart as wsans
    import werkzeug.formparser as wstream

    @add_parser
    def werkzeug_sansio(scenario: Scenario):
        read = scenario.payload.read
        chunksize = scenario.chunksize
        parser = wsans.MultipartDecoder(boundary=scenario.boundary)
        for chunk in iter(lambda: read(chunksize), b""):
            parser.receive_data(chunk)
            while True:
                event = parser.next_event()
                if isinstance(event, wsans.NeedData):
                    break
                if isinstance(event, wsans.Epilogue):
                    return

    @add_parser
    def werkzeug_blocking(scenario: Scenario):
        parser = wstream.MultiPartParser(buffer_size=scenario.chunksize)
        parser.parse(scenario.payload, scenario.boundary, -1)

except ImportError:
    werkzeug_sansio = None
    werkzeug_blocking = None
    pass

try:
    import python_multipart

    @add_parser
    def python_multipart_sansio(scenario: Scenario):
        parser = python_multipart.MultipartParser(
            scenario.boundary,
            callbacks={
                "on_part_begin": lambda *a, **ka: None,
                "on_part_data": lambda *a, **ka: None,
                "on_part_end": lambda *a, **ka: None,
                "on_header_field": lambda *a, **ka: None,
                "on_header_value": lambda *a, **ka: None,
                "on_header_end": lambda *a, **ka: None,
                "on_headers_finished": lambda *a, **ka: None,
                "on_end": lambda *a, **ka: None,
            },
        )

        read = scenario.payload.read
        while True:
            chunk = read(scenario.chunksize)
            if chunk:
                parser.write(chunk)
            else:
                parser.finalize()
                break

    @add_parser
    def python_multipart_blocking(scenario: Scenario):
        def on_field(f):
            pass

        def on_file(f):
            pass

        def on_end():
            pass

        parser = python_multipart.FormParser(
            "multipart/form-data",
            on_field,
            on_file,
            on_end,
            boundary=scenario.boundary,
            config={},
        )
        read = scenario.payload.read

        while True:
            chunk = read(scenario.chunksize)
            if chunk:
                parser.write(chunk)
            else:
                parser.finalize()
                break

except ImportError:
    python_multipart_sansio = None
    python_multipart_blocking = None

try:
    import cgi

    @add_parser
    def stdlib_cgi_blocking(scenario: Scenario):
        fs = cgi.FieldStorage(
            scenario.payload,
            environ={
                "REQUEST_METHOD": "POST",
                "QUERY_STRING": "",
                "CONTENT_TYPE": f'multipart/form-data; boundary={scenario.boundary.decode("ASCII")}',
            },
        )
        list(fs)

except ImportError:
    stdlib_cgi_blocking = None

import email


@add_parser
def stdlib_email_blocking(scenario: Scenario):
    email.message_from_binary_file(scenario.payload)


parser_table = {
    "multipart": [multipart_blocking, multipart_sansio],
    "werkzeug": [werkzeug_blocking, werkzeug_sansio],
    "python-multipart": [python_multipart_blocking, python_multipart_sansio],
    "cgi": [stdlib_cgi_blocking, None],
    "email": [stdlib_email_blocking, None],
}
