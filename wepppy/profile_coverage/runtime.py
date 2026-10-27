"""Runtime helpers for propagating profile coverage context across modules."""

from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from functools import wraps
from typing import Any, Callable, Optional

try:  # coverage instrumentation only requires rq when enqueuing jobs
    from rq import Queue
except ImportError:  # pragma: no cover - rq is available in production images
    Queue = None  # type: ignore[assignment]

_LOGGER = logging.getLogger(__name__)
_PROFILE_TRACE_SLUG: ContextVar[Optional[str]] = ContextVar(
    "profile_trace_slug", default=None
)


def current_profile_trace_slug() -> Optional[str]:
    """Return the active profile coverage slug, if any."""

    return _PROFILE_TRACE_SLUG.get()


def set_profile_trace_slug(slug: Optional[str]) -> Token:
    """Push ``slug`` into the context variable stack and return the token."""

    return _PROFILE_TRACE_SLUG.set(slug)


def reset_profile_trace_slug(token: Token) -> None:
    """Reset the context variable to the value represented by ``token``."""

    try:
        _PROFILE_TRACE_SLUG.reset(token)
    except ValueError:
        # Token already reset; nothing to do.
        _LOGGER.debug("Profile trace token already reset", exc_info=True)


def install_rq_hooks() -> None:
    """Patch rq queues so enqueued jobs capture the active profile slug."""

    if Queue is None:
        return
    if getattr(Queue, "_profile_trace_wrapped", False):
        return

    def _wrap_enqueue(func: Callable[..., Any], method_name: str) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            slug = _PROFILE_TRACE_SLUG.get()
            if slug and method_name == "enqueue_call":
                # RQ 1.16 and 2.12 accept meta at position 11. Keep profile
                # metadata in RQ's enqueue transaction, including caller-owned
                # pipelines, rather than publishing an independent hash write.
                meta = dict((args[11] if len(args) > 11 else kwargs.get("meta")) or {})
                meta["profile_trace_slug"] = slug
                if len(args) > 11:
                    args = (*args[:11], meta, *args[12:])
                else:
                    kwargs["meta"] = meta
            return func(self, *args, **kwargs)

        return wrapper

    Queue.enqueue_call = _wrap_enqueue(Queue.enqueue_call, "enqueue_call")
    Queue.enqueue = _wrap_enqueue(Queue.enqueue, "enqueue")
    setattr(Queue, "_profile_trace_wrapped", True)


__all__ = [
    "current_profile_trace_slug",
    "install_rq_hooks",
    "reset_profile_trace_slug",
    "set_profile_trace_slug",
]
