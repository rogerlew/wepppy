from __future__ import annotations

import logging
import sys
import traceback
import uuid
from typing import Any

from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

_DEFAULT_ERROR_CODE_BY_STATUS: dict[int, str] = {
    400: "validation_error",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    502: "bad_gateway",
    503: "service_unavailable",
    504: "gateway_timeout",
}


def _default_error_code(status_code: int) -> str:
    if status_code in _DEFAULT_ERROR_CODE_BY_STATUS:
        return _DEFAULT_ERROR_CODE_BY_STATUS[status_code]
    if 400 <= status_code < 500:
        return "validation_error"
    if status_code >= 500:
        return "internal_error"
    return "error"


def error_response(
    message: str,
    *,
    status_code: int = 500,
    code: str | None = None,
    details: Any | None = None,
    errors: list[dict[str, Any]] | None = None,
    error_id: str | None = None,
    log_exception: bool | None = None,
) -> JSONResponse:
    resolved_error_id = error_id or uuid.uuid4().hex
    resolved_code = code or _default_error_code(status_code)
    if details is None:
        if errors is not None:
            details = "Validation failed."
        else:
            details = message
    error_payload: dict[str, Any] = {
        "message": message,
        "details": details,
        "code": resolved_code,
    }
    payload: dict[str, Any] = {
        "error": error_payload,
        "error_id": resolved_error_id,
    }
    if errors is not None:
        payload["errors"] = errors

    if log_exception is None:
        log_exception = status_code >= 500 and sys.exc_info()[0] is not None
    if log_exception:
        traceback_text = traceback.format_exc()
        logger.error(
            "rq-engine error response emitted [error_id=%s code=%s status=%s]: %s\n%s",
            resolved_error_id,
            resolved_code,
            status_code,
            message,
            traceback_text,
            extra={
                "error_id": resolved_error_id,
                "error_code": resolved_code,
                "status_code": status_code,
            },
        )

    return JSONResponse(payload, status_code=status_code)


def error_response_with_traceback(
    message: str,
    *,
    status_code: int = 500,
    code: str | None = None,
    details: Any | None = None,
    errors: list[dict[str, Any]] | None = None,
    error_id: str | None = None,
) -> JSONResponse:
    traceback_text = traceback.format_exc()
    return error_response(
        message,
        status_code=status_code,
        code=code,
        details=traceback_text if details is None else details,
        errors=errors,
        error_id=error_id,
        log_exception=True,
    )


def validation_error_response(errors: list[dict[str, Any]]) -> JSONResponse:
    detail = "Validation failed."
    if errors:
        first_error = errors[0]
        if isinstance(first_error, dict) and first_error.get("message"):
            detail = str(first_error["message"])
    return error_response(
        "Validation failed",
        status_code=400,
        code="validation_error",
        details=detail,
        errors=errors,
    )


__all__ = ["error_response", "error_response_with_traceback", "validation_error_response"]
