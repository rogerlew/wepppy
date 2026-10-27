"""Safe, correlated failure responses shared by file delivery services."""

import logging

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from wepppy.config.secrets import SecretConfigurationError
from wepppy.observability.correlation import generate_correlation_id, normalize_correlation_id

LOGGER = logging.getLogger(__name__)


class PublicHTTPException(HTTPException):
    """A deliberately authored operational message, never raw exception text."""


def nodir_server_exception(err) -> PublicHTTPException:
    """Retain legacy runtime-path codes without publishing private paths."""
    message = {
        'NODIR_LOCKED': 'Project files are temporarily locked. Retry after the active operation finishes.',
        'NODIR_INVALID_ARCHIVE': 'The project archive could not be read. Report this error to the service operator.',
    }.get(err.code, 'Project files are unavailable. Report this error to the service operator.')
    return PublicHTTPException(
        status_code=err.http_status,
        detail={"error": {"code": err.code, "message": message, "details": message}},
    )


def request_id(request: Request) -> str:
    if not getattr(request.state, "download_request_id", None):
        request.state.download_request_id = (
            normalize_correlation_id(request.headers.get("X-Request-Id"))
            or normalize_correlation_id(request.headers.get("X-Correlation-Id"))
            or generate_correlation_id()
        )
    return request.state.download_request_id


def failure_payload(request: Request, exc: Exception) -> dict:
    reference = request_id(request)
    code = "internal_error"
    message = (
        "The server could not complete the file request. "
        "Report this message and request ID to the service operator."
    )
    if isinstance(exc, SecretConfigurationError):
        code, message = "server_configuration_error", exc.public_message
    LOGGER.error(
        "File request failed request_id=%s method=%s path=%s",
        reference, request.method, request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return {"error": {"code": code, "message": message, "details": message},
            "request_id": reference}


async def download_exception_handler(request: Request, exc: Exception):
    payload = failure_payload(request, exc)
    return JSONResponse(payload, status_code=500,
                        headers={"X-Request-Id": payload["request_id"]})


async def download_http_exception_handler(request: Request, exc: HTTPException):
    reference = request_id(request)
    detail = exc.detail
    if exc.status_code < 500:
        return PlainTextResponse(str(detail), status_code=exc.status_code,
                                 headers=exc.headers)
    if not isinstance(exc, PublicHTTPException):
        payload = failure_payload(request, exc)
        return JSONResponse(payload, status_code=exc.status_code,
                            headers={**(exc.headers or {}), "X-Request-Id": reference})
    payload = dict(detail) if isinstance(detail, dict) else {
        "error": {"code": "internal_error" if exc.status_code >= 500 else "http_error",
                  "message": str(detail), "details": str(detail)}
    }
    payload["request_id"] = reference
    if exc.status_code >= 500:
        LOGGER.error("File request rejected request_id=%s status=%s path=%s detail=%s",
                     reference, exc.status_code, request.url.path, detail,
                     exc_info=(type(exc), exc, exc.__traceback__))
    headers = dict(exc.headers or {})
    headers["X-Request-Id"] = reference
    return JSONResponse(payload, status_code=exc.status_code, headers=headers)
