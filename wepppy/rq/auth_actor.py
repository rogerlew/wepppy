from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from contextvars import ContextVar, Token
from typing import Any, Mapping

import redis
from rq import Queue, get_current_job

_LOGGER = logging.getLogger(__name__)
_AUTH_ACTOR: ContextVar[dict[str, Any] | None] = ContextVar("auth_actor", default=None)
_ENQUEUE_TRACE_DEPTH: ContextVar[int] = ContextVar("enqueue_trace_depth", default=0)
_TRACE_ENQUEUE_ENV = "WEPPPY_RQ_TRACE_ENQUEUE"
_TRACE_PATH_ENV = "WEPPPY_RQ_TRACE_PATH"
_DEFAULT_TRACE_PATH = "/tmp/wepppy_rq_enqueue_trace.jsonl"


def _is_truthy_env(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _trace_enabled() -> bool:
    return _is_truthy_env(os.getenv(_TRACE_ENQUEUE_ENV))


def _callable_label(target: Any) -> str:
    if target is None:
        return "<unknown>"
    if isinstance(target, str):
        return target
    if hasattr(target, "__qualname__"):
        return str(getattr(target, "__qualname__"))
    if hasattr(target, "__name__"):
        return str(getattr(target, "__name__"))
    return target.__class__.__name__


def _resolve_enqueue_target(method_name: str, args: tuple[Any, ...], kwargs: Mapping[str, Any]) -> Any:
    if method_name == "enqueue_call":
        if "func" in kwargs:
            return kwargs.get("func")
        if args:
            return args[0]
        return None
    if args:
        return args[0]
    if "func" in kwargs:
        return kwargs.get("func")
    return kwargs.get("f")


def _to_job_id(value: Any) -> str:
    candidate = getattr(value, "id", None)
    if candidate is not None:
        return str(candidate)
    return str(value)


def _normalize_depends_on(depends_on: Any) -> list[str]:
    if depends_on is None:
        return []
    if isinstance(depends_on, (list, tuple, set)):
        return [_to_job_id(item) for item in depends_on if item is not None]
    return [_to_job_id(depends_on)]


def _append_enqueue_trace(
    queue: Queue,
    *,
    method_name: str,
    args: tuple[Any, ...],
    kwargs: Mapping[str, Any],
    child_job: Any,
) -> None:
    if not _trace_enabled() or child_job is None:
        return

    parent_job = get_current_job()

    record = {
        "child_job_id": _to_job_id(child_job),
        "depends_on_job_ids": _normalize_depends_on(kwargs.get("depends_on")),
        "enqueue_target": _callable_label(_resolve_enqueue_target(method_name, args, kwargs)),
        "method": method_name,
        "parent_enqueue_target": getattr(parent_job, "func_name", None),
        "parent_job_id": getattr(parent_job, "id", None),
        "queue_name": getattr(queue, "name", "default"),
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    trace_path = Path(os.getenv(_TRACE_PATH_ENV, _DEFAULT_TRACE_PATH))
    try:
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")
    except (OSError, TypeError, ValueError) as exc:  # pragma: no cover - logging only
        _LOGGER.debug("Unable to write RQ enqueue trace record: %s", exc, exc_info=True)


def current_auth_actor() -> dict[str, Any] | None:
    """Return the active auth actor payload for the current context."""
    return _AUTH_ACTOR.get()


def set_auth_actor(actor: Mapping[str, Any] | None) -> Token:
    """Push an auth actor payload into the current context."""
    return _AUTH_ACTOR.set(dict(actor) if actor is not None else None)


def reset_auth_actor(token: Token) -> None:
    """Restore the auth actor payload to the previous value."""
    try:
        _AUTH_ACTOR.reset(token)
    except ValueError:
        _LOGGER.debug("Auth actor token already reset", exc_info=True)


def install_rq_auth_actor_hook() -> None:
    """Patch rq queues so enqueued jobs capture the active auth actor."""
    if getattr(Queue, "_auth_actor_wrapped", False):
        return

    def _wrap_enqueue(func, method_name: str):
        def wrapper(self, *args, **kwargs):
            depth_token = _ENQUEUE_TRACE_DEPTH.set(_ENQUEUE_TRACE_DEPTH.get() + 1)
            try:
                job = func(self, *args, **kwargs)
                actor = _AUTH_ACTOR.get()
                if actor and job is not None:
                    try:
                        meta = dict(job.meta or {})
                    except AttributeError:  # pragma: no cover - defensive guard
                        meta = None
                    if isinstance(meta, dict):
                        if "auth_actor" not in meta:
                            meta["auth_actor"] = actor
                            job.meta = meta
                            try:
                                job.save_meta()
                            except (redis.exceptions.RedisError, OSError) as exc:  # pragma: no cover - logging only
                                _LOGGER.debug(
                                    "Unable to persist auth actor for job %s: %s", getattr(job, "id", "?"), exc
                                )
                if job is None:
                    return job
                # Log only once at the outermost enqueue wrapper invocation.
                if _ENQUEUE_TRACE_DEPTH.get() == 1:
                    _append_enqueue_trace(self, method_name=method_name, args=args, kwargs=kwargs, child_job=job)
                return job
            finally:
                try:
                    _ENQUEUE_TRACE_DEPTH.reset(depth_token)
                except ValueError:  # pragma: no cover - defensive guard
                    _LOGGER.debug("enqueue trace depth token already reset", exc_info=True)

        return wrapper

    Queue.enqueue_call = _wrap_enqueue(Queue.enqueue_call, "enqueue_call")
    Queue.enqueue = _wrap_enqueue(Queue.enqueue, "enqueue")
    setattr(Queue, "_auth_actor_wrapped", True)


__all__ = [
    "current_auth_actor",
    "install_rq_auth_actor_hook",
    "reset_auth_actor",
    "set_auth_actor",
]
