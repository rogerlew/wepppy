from __future__ import annotations

import traceback
from typing import Any

from fastapi.responses import JSONResponse


def error_response(message: str) -> JSONResponse:
    stacktrace = traceback.format_exc().splitlines()
    payload = {
        "Success": False,
        "Error": message,
        "StackTrace": stacktrace,
    }
    return JSONResponse(payload, status_code=500)


def validation_error_response(errors: list[dict[str, Any]]) -> JSONResponse:
    payload = {"success": False, "errors": errors}
    return JSONResponse(payload, status_code=400)


__all__ = ["error_response", "validation_error_response"]
