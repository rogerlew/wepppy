"""Bounded multipart transport for the existing landuse/soil build endpoints."""
from __future__ import annotations

from contextlib import asynccontextmanager

from starlette.formparsers import MultiPartException, MultiPartParser
from python_multipart.multipart import parse_options_header

from wepppy.wepp.single_input import MAX_SOURCE_BYTES, SingleInputError
from .payloads import _form_to_dict, _normalize_payload_value, parse_request_payload

__all__ = ["input_payload"]


class _InputParser(MultiPartParser):
    def __init__(self, request, kind):
        self.kind = kind
        self.part_bytes = 0
        self.header_bytes = 0
        self.seen_sources = set()
        self.finished = False
        self.source_field = "input_upload_single_landuse" if kind == "landuse" else "input_upload_single_soil"
        self.file_limits = {self.source_field: MAX_SOURCE_BYTES}
        if kind == "landuse":
            self.file_limits["input_upload_landuse"] = 500 * 1024 * 1024
        _, parameters = parse_options_header(request.headers.get("content-type", ""))
        boundary = parameters.get(b"boundary", b"")
        if not boundary or len(boundary) > 70:
            raise SingleInputError("Invalid multipart boundary.")
        super().__init__(request.headers, self._bounded_stream(request), max_files=1, max_fields=64, max_part_size=16_384)

    async def _bounded_stream(self, request):
        limit = (501 if self.kind == "landuse" else 6) * 1024 * 1024
        consumed = 0
        async for chunk in request.stream():
            consumed += len(chunk)
            if consumed > limit:
                raise SingleInputError("Upload request exceeds its size limit.", code="single_input_too_large", status_code=413)
            # Bound the parser's pending write queue even if ASGI delivers a large chunk.
            for offset in range(0, len(chunk), 65536):
                yield chunk[offset:offset + 65536]
        yield b""

    def on_part_begin(self):
        self.part_bytes = self.header_bytes = 0
        super().on_part_begin()

    def _header(self, count):
        self.header_bytes += count
        if self.header_bytes > 16_384:
            raise MultiPartException("Multipart headers exceed16KiB.")

    def on_header_field(self, data, start, end):
        self._header(end - start)
        super().on_header_field(data, start, end)

    def on_header_value(self, data, start, end):
        self._header(end - start)
        super().on_header_value(data, start, end)

    def on_headers_finished(self):
        _, options = parse_options_header(self._current_part.content_disposition)
        field = options.get(b"name", b"").decode("utf-8", errors="strict")
        if b"filename" in options and field not in self.file_limits:
            raise MultiPartException("Unexpected file field.")
        if field.startswith("input_upload_single_"):
            if field != self.source_field or field in self.seen_sources or b"filename" not in options:
                raise MultiPartException("Duplicate or invalid single-source field.")
            self.seen_sources.add(field)
        super().on_headers_finished()

    def on_part_data(self, data, start, end):
        self.part_bytes += end - start
        limit = self.file_limits.get(self._current_part.field_name, 16_384)
        if self.part_bytes > limit:
            raise SingleInputError("Uploaded file exceeds its size limit.", code="single_input_too_large", status_code=413)
        super().on_part_data(data, start, end)

    def on_end(self):
        self.finished = True
        super().on_end()


@asynccontextmanager
async def input_payload(request, kind, *, boolean_fields=()):
    if "multipart/form-data" not in request.headers.get("content-type", "").lower():
        payload = await parse_request_payload(request, boolean_fields=boolean_fields)
        if any(key.startswith("input_upload_single_") for key in payload):
            raise SingleInputError("Single-input file fields require multipart/form-data.")
        yield payload, None
        return
    parser = _InputParser(request, kind)
    try:
        try:
            form = await parser.parse()
            if not parser.finished:
                raise MultiPartException("Incomplete multipart body.")
        except (MultiPartException, UnicodeDecodeError) as exc:
            raise SingleInputError("Invalid multipart upload request.") from exc
        # Existing raster handling calls request.form(); reuse the bounded parse.
        request._form = form
        payload = {
            key: _normalize_payload_value(value, coerce_boolean=key in boolean_fields, trim_strings=True)
            for key, value in _form_to_dict(form).items()
        }
        yield payload, form
    finally:
        # Starlette only guarantees this cleanup for MultiPartException; own the
        # lifetime for validation errors, disconnects and task cancellation too.
        for handle in parser._files_to_close_on_error:
            handle.close()
