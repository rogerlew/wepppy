"""Shared request/job correlation helpers for logging and propagation."""

from __future__ import annotations

import logging
import re
from contextvars import ContextVar, Token
from threading import Lock
from typing import Final
from uuid import uuid4
from collections.abc import Mapping

CORRELATION_ID_HEADER: Final[str] = "X-Correlation-ID"
LOG_FALLBACK_CORRELATION_ID: Final[str] = "-"
_MAX_CORRELATION_ID_LENGTH: Final[int] = 128
_CORRELATION_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

_LOGGER = logging.getLogger(__name__)
_CORRELATION_ID: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_FACTORY_LOCK = Lock()
_FACTORY_INSTALLED = False
_MISSING: Final[object] = object()


def generate_correlation_id() -> str:
    """Return a new correlation identifier."""
    return uuid4().hex


def normalize_correlation_id(value: str | None) -> str | None:
    """Return a normalized correlation identifier, or None when invalid."""
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if len(candidate) > _MAX_CORRELATION_ID_LENGTH:
        return None
    if not _CORRELATION_ID_PATTERN.match(candidate):
        return None
    return candidate


def is_valid_correlation_id(value: str | None) -> bool:
    """Return True when `value` passes canonical correlation-id validation."""
    return normalize_correlation_id(value) is not None


def current_correlation_id() -> str | None:
    """Return the active correlation ID for the current context."""
    return _CORRELATION_ID.get()


def set_correlation_id(value: str | None) -> Token:
    """Set the active correlation ID using normalized value semantics."""
    return _CORRELATION_ID.set(normalize_correlation_id(value))


def bind_correlation_id(candidate: str | None) -> tuple[str, Token]:
    """Bind a valid correlation ID to context and return `(value, token)`."""
    correlation_id = normalize_correlation_id(candidate) or generate_correlation_id()
    token = _CORRELATION_ID.set(correlation_id)
    return correlation_id, token


def reset_correlation_id(token: Token) -> None:
    """Restore the correlation context to a previous token value."""
    try:
        _CORRELATION_ID.reset(token)
    except ValueError:
        _LOGGER.debug("Correlation token already reset", exc_info=True)


def correlation_id_for_log() -> str:
    """Return correlation ID for log records with safe fallback."""
    return current_correlation_id() or LOG_FALLBACK_CORRELATION_ID


def select_inbound_correlation_id(
    header_value: str | None,
    *,
    prefer_current_context: bool = False,
) -> str | None:
    """Select inbound correlation source from header/context with explicit precedence."""
    current = current_correlation_id()
    if prefer_current_context:
        return current or header_value
    return header_value or current


def install_correlation_log_record_factory() -> None:
    """Install logging hooks that inject `correlation_id` and `trace_id`."""
    global _FACTORY_INSTALLED
    if _FACTORY_INSTALLED:
        return

    with _FACTORY_LOCK:
        if _FACTORY_INSTALLED:
            return

        previous_make_record = logging.Logger.makeRecord

        def _make_record_with_correlation(
            self,
            name,
            level,
            fn,
            lno,
            msg,
            args,
            exc_info,
            func=None,
            extra=None,
            sinfo=None,
        ):
            correlation_override = _MISSING
            trace_override = _MISSING
            passthrough_extra = extra

            # Strip reserved correlation fields from `extra` before core logger processing.
            # This avoids KeyError when callers pass `extra={"correlation_id": ...}`.
            if isinstance(extra, Mapping):
                if "correlation_id" in extra or "trace_id" in extra:
                    passthrough_extra = dict(extra)
                    correlation_override = passthrough_extra.pop("correlation_id", _MISSING)
                    trace_override = passthrough_extra.pop("trace_id", _MISSING)

            record = previous_make_record(
                self,
                name,
                level,
                fn,
                lno,
                msg,
                args,
                exc_info,
                func,
                passthrough_extra,
                sinfo,
            )

            if correlation_override is not _MISSING:
                record.correlation_id = correlation_override
            correlation_id = getattr(record, "correlation_id", None)
            if not correlation_id:
                correlation_id = correlation_id_for_log()
                record.correlation_id = correlation_id

            if trace_override is not _MISSING:
                record.trace_id = trace_override
            if not getattr(record, "trace_id", None):
                record.trace_id = correlation_id

            return record

        logging.Logger.makeRecord = _make_record_with_correlation
        _FACTORY_INSTALLED = True


__all__ = [
    "CORRELATION_ID_HEADER",
    "LOG_FALLBACK_CORRELATION_ID",
    "bind_correlation_id",
    "correlation_id_for_log",
    "current_correlation_id",
    "generate_correlation_id",
    "install_correlation_log_record_factory",
    "is_valid_correlation_id",
    "normalize_correlation_id",
    "reset_correlation_id",
    "select_inbound_correlation_id",
    "set_correlation_id",
]
