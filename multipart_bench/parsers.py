from tempfile import SpooledTemporaryFile
from .scenarios import Scenario

PARSERS = []
# Size limit for memory-buffered files is hard-coded in werkzeug, so we
# set it to other parsers to be fair.
SPOOL_LIMIT = 1024*500

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
                spool_limit=SPOOL_LIMIT,
            )
        )

except ImportError:
    multipart_sansio = None
    multipart_blocking = None


try:
    from django.http.multipartparser import MultiPartParser
    from django.http.request import HttpRequest
    from django.core.files import uploadhandler
    from django.conf import global_settings, settings
    from django.core.files.uploadhandler import MemoryFileUploadHandler
    from django.core.files.uploadhandler import TemporaryFileUploadHandler

    settings.configure(
        DEFAULT_CHARSET="utf8",
        FILE_UPLOAD_MAX_MEMORY_SIZE=SPOOL_LIMIT,
        DATA_UPLOAD_MAX_MEMORY_SIZE=SPOOL_LIMIT)
    fake_request = HttpRequest()
    handers = [
        MemoryFileUploadHandler(fake_request),
        TemporaryFileUploadHandler(fake_request)
    ]

    @add_parser
    def django_blocking(scenario: Scenario):
        MemoryFileUploadHandler.chunk_size = scenario.chunksize
        MultiPartParser(
            {"CONTENT_TYPE": f"multipart/form-data; boundary={str(scenario.boundary, 'ASCII')}",
             "CONTENT_LENGTH": str(scenario.size)},
            scenario.payload,
            [uploadhandler.load_handler(handler, fake_request)
            for handler in settings.FILE_UPLOAD_HANDLERS],
            "utf8"
        ).parse()

except ImportError:
    django_sansio = None
    django_blocking = None


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
            config={"MAX_MEMORY_FILE_SIZE": SPOOL_LIMIT},
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
    from streaming_form_data import StreamingFormDataParser
    from streaming_form_data.targets import BaseTarget, NullTarget

    class SpooledTarget(BaseTarget):
        def __init__(self, *a, **ka):
            BaseTarget.__init__(self, *a, **ka)
            self.file = SpooledTemporaryFile(max_size=SPOOL_LIMIT)

        def on_data_received(self, chunk):
            self.file.write(chunk)

    @add_parser
    def streaming_sansio(scenario: Scenario):
        headers = {"Content-Type": f"multipart/form-data; boundary={str(scenario.boundary, 'ASCII')}"}
        parser = StreamingFormDataParser(headers=headers)
        read = scenario.payload.read

        for name in scenario.names:
            parser.register(name, NullTarget())

        while True:
            chunk = read(scenario.chunksize)
            if chunk:
                parser.data_received(chunk)
            else:
                break

    @add_parser
    def streaming_blocking(scenario: Scenario):
        headers = {"Content-Type": f"multipart/form-data; boundary={str(scenario.boundary, 'ASCII')}"}
        parser = StreamingFormDataParser(headers=headers)
        read = scenario.payload.read

        for name in scenario.names:
            parser.register(name, SpooledTarget())

        while True:
            chunk = read(scenario.chunksize)
            if chunk:
                parser.data_received(chunk)
            else:
                break

except ImportError:
    streaming_sansio = None
    streaming_blocking = None


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

import email.parser

@add_parser
def stdlib_email_sansio(scenario: Scenario):
    parser = email.parser.BytesFeedParser()
    parser.feed(b"MIME-Version: 1.0\r\n" + b"Content-Type: multipart/form-data; boundary=" + scenario.boundary + b"\r\n")
    read = scenario.payload.read
    chunksize = scenario.chunksize
    while data := read(chunksize):
        parser.feed(data)
    return parser.close().get_payload()

# Payload is always memory-buffered, which makes this parser unsuitable for 
# large file uploads and unsafe to use in a web application. To get comparable
# results for a blocking version, we assume that someone subclasses Message
# in a way that buffers to disk.

@add_parser
def stdlib_email_blocking(scenario: Scenario):
    for part in stdlib_email_sansio(scenario):
        target = SpooledTemporaryFile(max_size=SPOOL_LIMIT)
        target.write(part.get_payload().encode("utf8"))
        target.close()

parser_table = {
    "multipart": [multipart_blocking, multipart_sansio],
    "werkzeug": [werkzeug_blocking, werkzeug_sansio],
    "django": [django_blocking, None],
    "python-multipart": [python_multipart_blocking, python_multipart_sansio],
    "streaming-form-data": [streaming_blocking, streaming_sansio],
    "cgi": [stdlib_cgi_blocking, None],
    "email": [stdlib_email_blocking, stdlib_email_sansio],
}
