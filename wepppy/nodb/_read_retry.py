"""Opt-in retries for initial controller reads, never for controller mutations."""
from __future__ import annotations

import errno
import logging
import os
import socket
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Callable, Iterator, TypeVar

__all__ = ["initial_read_retry", "read_retry_active", "read_text", "stat_path"]

_LOG = logging.getLogger(__name__)
_RETRY_ERRNOS = frozenset((errno.ENOENT, errno.ESTALE))
_T = TypeVar("_T")


@dataclass(frozen=True)
class _ReadBudget:
    deadline: float
    runid: str
    job_id: str
    host: str


_BUDGET: ContextVar[_ReadBudget | None] = ContextVar("nodb_initial_read_budget", default=None)


@contextmanager
def initial_read_retry(*, runid: str, job_id: str) -> Iterator[None]:
    """Share a 120-second retry budget across initial, read-only hydration."""
    existing = _BUDGET.get()
    token = _BUDGET.set(existing or _ReadBudget(time.monotonic() + 120.0, runid, job_id, socket.gethostname()))
    try:
        yield
    finally:
        _BUDGET.reset(token)


def read_retry_active() -> bool:
    return _BUDGET.get() is not None


def _call(operation: str, path: str, action: Callable[[], _T], *, allow_missing: bool) -> _T | None:
    budget = _BUDGET.get()
    started = time.monotonic()
    attempts = 0
    delay = 2.0
    last_errno = None
    while True:
        attempts += 1
        try:
            result = action()
        except OSError as exc:
            if allow_missing and exc.errno == errno.ENOENT:
                return None
            if budget is None:
                raise
            elapsed = time.monotonic() - started
            remaining = budget.deadline - time.monotonic()
            retry = exc.errno in _RETRY_ERRNOS and remaining > delay
            _LOG.warning(
                "NoDb initial read %s operation=%s errno=%s path=%s attempts=%s elapsed_s=%.3f host=%s runid=%s job_id=%s",
                "retry" if retry else ("exhausted" if exc.errno in _RETRY_ERRNOS else "failed"),
                operation, exc.errno, path, attempts,
                elapsed, budget.host, budget.runid, budget.job_id,
            )
            if not retry:
                raise
            last_errno = exc.errno
            time.sleep(delay)
            # The original syscall error is retained if scheduler delay used up
            # the budget. This deadline cannot interrupt a blocked NFS syscall.
            if time.monotonic() >= budget.deadline:
                _LOG.warning(
                    "NoDb initial read exhausted operation=%s errno=%s path=%s attempts=%s elapsed_s=%.3f host=%s runid=%s job_id=%s",
                    operation, exc.errno, path, attempts, time.monotonic() - started,
                    budget.host, budget.runid, budget.job_id,
                )
                raise
            delay = min(delay * 2, 10.0)
        else:
            if budget is not None and attempts > 1:
                _LOG.info(
                    "NoDb initial read recovered operation=%s errno=%s path=%s attempts=%s elapsed_s=%.3f host=%s runid=%s job_id=%s",
                    operation, last_errno, path, attempts, time.monotonic() - started,
                    budget.host, budget.runid, budget.job_id,
                )
            return result


def stat_path(path: str, *, allow_missing: bool = False) -> os.stat_result | None:
    return _call("stat", path, lambda: os.stat(path), allow_missing=allow_missing)


def read_text(path: str, *, allow_missing: bool = False) -> str | None:
    def read() -> str:
        with open(path) as stream:
            return stream.read()

    return _call("open/read", path, read, allow_missing=allow_missing)
