from __future__ import annotations

from typing import Any, Iterable

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.datastructures import FormData
from starlette.formparsers import MultiPartException, MultiPartParser
from python_multipart.exceptions import MultipartParseError

from wepppy.request_payload import (
    RequestPayloadError, decode_json, is_json_media, media_type,
    normalize_payload, normalize_value, scalar_boolean, validate_form_encoding,
)


def payload_error_response(exc: RequestPayloadError) -> JSONResponse:
    return JSONResponse(exc.envelope(), status_code=400)


class PayloadRoute(APIRoute):
    """Translate typed input failures after the owning route's authorization."""
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def handle(request):
            try:
                return await handler(request)
            except RequestPayloadError as exc:
                return payload_error_response(exc)
            finally:
                if request._form is not None:
                    await request._form.close()
        return handle


class _CompleteMultipartParser(MultiPartParser):
    finished = False

    def on_end(self):
        self.finished = True
        super().on_end()


async def request_payload(request: Request, *, allow_list: bool = False):
    """Read once using the declared transport; never turn a decoder failure into {}."""
    content_type = media_type(request.headers.get("content-type", ""))
    if content_type in {"multipart/form-data", "application/x-www-form-urlencoded"} and request._form is not None:
        if content_type == "multipart/form-data" and not getattr(request.state, "payload_form_complete", False):
            raise RequestPayloadError()
        return request._form
    if content_type == "multipart/form-data":
        if request._form is not None:
            return request._form
        parser = _CompleteMultipartParser(request.headers, request.stream())
        try:
            form = await parser.parse()
            if not parser.finished:
                raise RequestPayloadError()
        except (MultiPartException, MultipartParseError, UnicodeError) as exc:
            for handle in parser._files_to_close_on_error:
                handle.close()
            raise RequestPayloadError() from exc
        except BaseException:
            # Transport resource boundary: close spools even on disconnect/cancel.
            for handle in parser._files_to_close_on_error:
                handle.close()
            raise
        request._form = form
        request.state.payload_form_complete = True
        return form
    body = await request.body()
    if content_type == "application/x-www-form-urlencoded":
        validate_form_encoding(body)
        return await request.form()
    if not body:
        return {}
    if content_type and not is_json_media(content_type):
        raise RequestPayloadError()
    value = decode_json(body, allow_list=allow_list)
    request._json = value
    return value



async def request_form(request: Request) -> FormData:
    raw = await request_payload(request, allow_list=isinstance(getattr(request, "_json", None), list))
    return raw if isinstance(raw, FormData) else FormData()


def _normalize_scalar(value: Any, *, coerce_boolean: bool, trim_strings: bool) -> Any:
    return normalize_value(value, coerce_boolean=coerce_boolean, trim_strings=trim_strings)


_normalize_payload_value = normalize_value


def _form_to_dict(form: FormData) -> dict[str, Any]:
    return {key: form.getlist(key) if len(form.getlist(key)) > 1 else form[key] for key in form}


async def parse_request_payload(request: Request, *, boolean_fields: Iterable[str] | None = None,
                                trim_strings: bool = True, allow_list: bool = False,
                                preserve_structure: bool = False, extra_boolean_tokens: bool = False, blank_false_fields: Iterable[str] = ()) -> dict[str, Any]:
    try:
        raw = await request_payload(request, allow_list=allow_list)
    except (MultiPartException, MultipartParseError, UnicodeError) as exc:
        raise RequestPayloadError() from exc
    if isinstance(raw, list):
        # Omni owns the supported top-level scenario-list adapter and reads _json.
        return {}
    form = isinstance(raw, FormData)
    data = _form_to_dict(raw) if form else raw
    if preserve_structure and not form:
        flags = normalize_payload({key: data[key] for key in boolean_fields or () if key in data},
                                  boolean_fields=boolean_fields or (), trim_strings=trim_strings)
        return {**data, **flags}
    try:
        return normalize_payload(data, boolean_fields=boolean_fields or (), trim_strings=trim_strings,
                                 form=form, extra_boolean_tokens=extra_boolean_tokens, blank_false_fields=blank_false_fields)
    except RequestPayloadError:
        if form:
            await raw.close()
        raise


__all__ = ["parse_request_payload"]
