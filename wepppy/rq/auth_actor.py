from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from typing import Any, Mapping

from rq import Queue

_LOGGER = logging.getLogger(__name__)
_AUTH_ACTOR: ContextVar[dict[str, Any] | None] = ContextVar("auth_actor", default=None)


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

    def _wrap_enqueue(func):
        def wrapper(self, *args, **kwargs):
            job = func(self, *args, **kwargs)
            actor = _AUTH_ACTOR.get()
            if not actor or job is None:
                return job
            try:
                meta = dict(job.meta or {})
            except AttributeError:  # pragma: no cover - defensive guard
                return job
            if "auth_actor" in meta:
                return job
            meta["auth_actor"] = actor
            job.meta = meta
            try:
                job.save_meta()
            except Exception as exc:  # pragma: no cover - logging only
                _LOGGER.debug(
                    "Unable to persist auth actor for job %s: %s", getattr(job, "id", "?"), exc
                )
            return job

        return wrapper

    Queue.enqueue_call = _wrap_enqueue(Queue.enqueue_call)
    Queue.enqueue = _wrap_enqueue(Queue.enqueue)
    setattr(Queue, "_auth_actor_wrapped", True)


__all__ = [
    "current_auth_actor",
    "install_rq_auth_actor_hook",
    "reset_auth_actor",
    "set_auth_actor",
]
