"""Error contracts for the shape-converter service."""

from __future__ import annotations

from dataclasses import dataclass

from starlette.responses import JSONResponse


@dataclass(slots=True)
class ShapeConverterError(Exception):
    """Typed service error mapped to canonical HTTP responses."""

    code: str
    message: str
    details: str
    status_code: int = 400

    def __str__(self) -> str:
        return f"{self.code}: {self.message} ({self.details})"


def error_payload(*, code: str, message: str, details: str) -> dict[str, dict[str, str]]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }


def error_response(exc: ShapeConverterError, *, request_id: str | None = None) -> JSONResponse:
    payload = error_payload(code=exc.code, message=exc.message, details=exc.details)
    if request_id is not None:
        payload["error"]["request_id"] = request_id
    return JSONResponse(payload, status_code=exc.status_code)


__all__ = ["ShapeConverterError", "error_payload", "error_response"]
