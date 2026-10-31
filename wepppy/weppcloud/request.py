"""Keep malformed form evidence when CSRF reads the transport before routes."""
from io import BytesIO
from flask import Request
from werkzeug.datastructures import MultiDict
from werkzeug.formparser import FormDataParser
from werkzeug.exceptions import RequestEntityTooLarge

from wepppy.request_payload import RequestPayloadError, validate_form_encoding


class StrictFormDataParser(FormDataParser):
    def __init__(self, *args, on_invalid=None, **kwargs):
        kwargs["silent"] = False
        super().__init__(*args, **kwargs)
        self.on_invalid = on_invalid
        self._streams = []
        factory = self.stream_factory

        def tracked_stream(*args, **kwargs):
            stream = factory(*args, **kwargs)
            self._streams.append(stream)
            return stream
        self.stream_factory = tracked_stream

    def _parse_urlencoded(self, stream, mimetype, content_length, options):
        limit = self.max_form_memory_size
        if limit is not None and content_length is not None and content_length > limit:
            raise RequestEntityTooLarge()
        body = stream.read() if limit is None else stream.read(limit + 1)
        if limit is not None and len(body) > limit:
            raise RequestEntityTooLarge()
        validate_form_encoding(body)
        return super()._parse_urlencoded(BytesIO(body), mimetype, len(body), options)

    def parse(self, *args, **kwargs):
        try:
            return super().parse(*args, **kwargs)
        except (ValueError, UnicodeError, RequestPayloadError) as exc:
            for stream in self._streams:
                stream.close()
            error = RequestPayloadError()
            if self.on_invalid is None:
                raise error from exc
            # CSRF still decides its own token/auth precedence. The owning route
            # must reject this cached transport failure after authorization.
            self.on_invalid(error)
            return args[0], MultiDict(), MultiDict()
        except BaseException:
            # Resource boundary: preserve size/disconnect/cancellation errors.
            for stream in self._streams:
                stream.close()
            raise


class PayloadRequest(Request):
    def make_form_data_parser(self):
        return StrictFormDataParser(
            stream_factory=self._get_file_stream,
            max_form_memory_size=self.max_form_memory_size,
            max_content_length=self.max_content_length,
            max_form_parts=self.max_form_parts,
            cls=self.parameter_storage_class,
            on_invalid=lambda error: setattr(self, "payload_error", error),
        )
