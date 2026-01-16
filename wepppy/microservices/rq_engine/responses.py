from __future__ import annotations

import traceback
from typing import Any

from fastapi.responses import JSONResponse


def error_response(
    message: str,
    *,
    status_code: int = 500,
    code: str | None = None,
    details: Any | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    if details is None:
        if errors is not None:
            details = "Validation failed."
        else:
            details = message
    error_payload: dict[str, Any] = {"message": message, "details": details}
    if code:
        error_payload["code"] = code
    payload = {
        "error": error_payload,
    }
    if errors is not None:
        payload["errors"] = errors
    return JSONResponse(payload, status_code=status_code)


def error_response_with_traceback(
    message: str,
    *,
    status_code: int = 500,
    code: str | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    return error_response(
        message,
        status_code=status_code,
        code=code,
        details=traceback.format_exc(),
        errors=errors,
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
