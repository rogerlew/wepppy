from __future__ import annotations

import traceback
from typing import Any

from fastapi.responses import JSONResponse


def error_response(message: str) -> JSONResponse:
    stacktrace = traceback.format_exc().splitlines()
    payload = {
        "Success": False,
        "success": False,
        "Error": message,
        "StackTrace": stacktrace,
        "error": {"message": message},
        "stacktrace": stacktrace,
    }
    return JSONResponse(payload, status_code=500)


def validation_error_response(errors: list[dict[str, Any]]) -> JSONResponse:
    payload = {
        "Success": False,
        "success": False,
        "Error": "Validation failed",
        "StackTrace": [],
        "errors": errors,
        "error": {"message": "Validation failed", "code": "validation_error"},
        "stacktrace": [],
    }
    return JSONResponse(payload, status_code=400)


__all__ = ["error_response", "validation_error_response"]
