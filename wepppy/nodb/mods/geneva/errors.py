from __future__ import annotations

from typing import Any


class GenevaNoDbError(RuntimeError):
    """Base typed error carrying canonical envelope metadata."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        details: Any | None = None,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.message = str(message)
        self.code = str(code)
        self.details = details if details is not None else self.message
        self.status_code = int(status_code)

    def to_error_payload(self) -> dict[str, Any]:
        return {
            "error": {
                "message": self.message,
                "code": self.code,
                "details": self.details,
            }
        }


class GenevaGuardrailError(GenevaNoDbError):
    """Raised when Geneva guardrails reject the run context."""


class GenevaKernelError(GenevaNoDbError):
    """Raised when the Geneva Rust boundary rejects or fails a call."""


class GenevaValidationError(GenevaNoDbError):
    """Raised when Geneva request payloads violate local contracts."""


__all__ = [
    "GenevaNoDbError",
    "GenevaGuardrailError",
    "GenevaKernelError",
    "GenevaValidationError",
]
