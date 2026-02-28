"""Structured runtime path errors for directory-only execution."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "NoDirError",
    "nodir_mixed_state",
    "nodir_invalid_archive",
    "nodir_locked",
    "nodir_limit_exceeded",
    "nodir_migration_required",
]


@dataclass(slots=True)
class NoDirError(Exception):
    """Structured error payload retained for compatibility."""

    http_status: int
    code: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code} ({self.http_status}): {self.message}"


def nodir_mixed_state(message: str) -> NoDirError:
    return NoDirError(http_status=409, code="NODIR_MIXED_STATE", message=message)


def nodir_invalid_archive(message: str) -> NoDirError:
    return NoDirError(http_status=500, code="NODIR_INVALID_ARCHIVE", message=message)


def nodir_locked(message: str) -> NoDirError:
    return NoDirError(http_status=503, code="NODIR_LOCKED", message=message)


def nodir_limit_exceeded(message: str) -> NoDirError:
    return NoDirError(http_status=413, code="NODIR_LIMIT_EXCEEDED", message=message)


def nodir_migration_required(message: str) -> NoDirError:
    return NoDirError(http_status=409, code="NODIR_MIGRATION_REQUIRED", message=message)
