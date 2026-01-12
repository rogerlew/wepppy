from __future__ import annotations

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
    error_payload: dict[str, Any] = {"message": message}
    if code:
        error_payload["code"] = code
    if details is not None:
        error_payload["details"] = details
    payload = {
        "error": error_payload,
    }
    if errors is not None:
        payload["errors"] = errors
    return JSONResponse(payload, status_code=status_code)


def validation_error_response(errors: list[dict[str, Any]]) -> JSONResponse:
    payload = {
        "errors": errors,
        "error": {"message": "Validation failed", "code": "validation_error"},
    }
    return JSONResponse(payload, status_code=400)


__all__ = ["error_response", "validation_error_response"]
