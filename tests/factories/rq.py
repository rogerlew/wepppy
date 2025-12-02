"""Shared factories for Redis/RQ testing scaffolding."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple


@dataclass
class JobStub:
    """Simple stand-in for :class:`rq.job.Job`."""

    id: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueueCall:
    """Record of a queue enqueue invocation."""

    func: Callable[..., Any]
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]
    timeout: Optional[int]
    job: JobStub


class RQRecorder:
    """Captures Redis + enqueue activity for assertions."""

    def __init__(self, job_ids: Optional[Iterable[str]] = None) -> None:
        self.redis_entries: List[str] = []
        self.queue_calls: List[QueueCall] = []
        self.queue_connections: List[Any] = []
        self._job_id_iterator: Iterator[str]
        if job_ids is None:
            self._job_id_iterator = iter(())
        else:
            self._job_id_iterator = iter(job_ids)

    def next_job_id(self, default: str = "job-123") -> str:
        try:
            return next(self._job_id_iterator)
        except StopIteration:
            return default

    def reset(self) -> None:
        self.redis_entries.clear()
        self.queue_calls.clear()
        self.queue_connections.clear()


def make_redis_conn(recorder: RQRecorder, label: str = "redis-conn"):
    """Return a context manager stub that records entry/exit."""

    class _RedisConn:
        def __enter__(self) -> str:
            recorder.redis_entries.append("enter")
            return label

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
            recorder.redis_entries.append("exit")

    return _RedisConn()


def make_queue(recorder: RQRecorder, *, default_job_id: str = "job-123"):
    """Return a Queue stub that records every enqueue call."""

    class _Queue:
        def __init__(self, connection: Any) -> None:
            self.connection = connection
            recorder.queue_connections.append(connection)

        def enqueue_call(
            self,
            func: Callable[..., Any],
            args: Tuple[Any, ...] = (),
            kwargs: Optional[Dict[str, Any]] = None,
            timeout: Optional[int] = None,
            **options: Any,
        ) -> JobStub:
            job_id = recorder.next_job_id(default_job_id)
            job = JobStub(job_id)
            call_kwargs: Dict[str, Any] = dict(options)
            # Mirror RQ: always carry the provided kwargs (can be None)
            call_kwargs["kwargs"] = kwargs
            recorder.queue_calls.append(
                QueueCall(func=func, args=args, kwargs=call_kwargs, timeout=timeout, job=job)
            )
            return job

    return _Queue
