from __future__ import annotations

import os
from contextvars import ContextVar
from functools import wraps
from typing import Any, Dict, Mapping, Optional

from rq import Queue

try:
    from flask import g, has_request_context
except ImportError:  # pragma: no cover - Flask always available in runtime env
    g = None  # type: ignore
    has_request_context = lambda: False  # type: ignore

_PROFILE_TRACE_SLUG: ContextVar[Optional[str]] = ContextVar(
    "profile_trace_slug", default=None
)
_QUEUE_PATCHED: bool = False
_ORIGINAL_ENQUEUE_CALL = Queue.enqueue_call


def set_profile_trace_slug(slug: Optional[str]) -> None:
    """Persist the active profile trace slug in the current context."""
    _PROFILE_TRACE_SLUG.set(slug)


def clear_profile_trace_slug() -> None:
    """Clear the active profile trace slug from the current context."""
    _PROFILE_TRACE_SLUG.set(None)


def get_current_profile_trace_slug() -> Optional[str]:
    """Return the active profile slug from context, Flask, or env state."""
    slug = _PROFILE_TRACE_SLUG.get()
    if slug:
        return slug
    if has_request_context():
        flask_slug = getattr(g, "profile_trace_slug", None)
        if flask_slug:
            return flask_slug
    return os.getenv("PROFILE_TRACE_SLUG")


def apply_profile_trace_to_job(job) -> None:
    """Attach the active profile slug to an RQ job, if available."""
    slug = get_current_profile_trace_slug()
    if not slug:
        return
    job.meta = job.meta or {}
    job.meta["profile_trace_slug"] = slug
    job.save()


def inject_profile_trace_env(
    base_env: Optional[Mapping[str, str]] = None
) -> Dict[str, str]:
    """Return a copy of the env mapping with PROFILE_TRACE_SLUG when present."""
    slug = get_current_profile_trace_slug()
    if not slug:
        return dict(base_env or {})
    env: Dict[str, str] = dict(base_env or {})
    env["PROFILE_TRACE_SLUG"] = slug
    return env


def install_profile_trace_queue_hook() -> None:
    """Monkey patch Queue.enqueue_call to capture profile trace metadata."""
    global _QUEUE_PATCHED
    if _QUEUE_PATCHED:
        return

    @wraps(_ORIGINAL_ENQUEUE_CALL)
    def _enqueue_call_with_profile_trace(self, *args: Any, **kwargs: Any):
        job = _ORIGINAL_ENQUEUE_CALL(self, *args, **kwargs)
        apply_profile_trace_to_job(job)
        return job

    Queue.enqueue_call = _enqueue_call_with_profile_trace  # type: ignore[assignment]
    _QUEUE_PATCHED = True
