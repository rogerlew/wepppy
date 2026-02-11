from __future__ import annotations

"""Admin-oriented helpers for listing jobs across RQ queues.

These helpers are intentionally read-only and do not enforce auth. Callers must
gate access (admin UI, admin FastAPI routes, etc.) because the payloads may be
augmented with user/run metadata at higher layers.
"""

from datetime import datetime, timedelta
from typing import Any, Iterable, Mapping, Sequence

import redis
from rq import Queue, Worker
from rq.job import Job
from rq.registry import FailedJobRegistry, FinishedJobRegistry, StartedJobRegistry
from rq.utils import utcnow

DEFAULT_QUEUES: tuple[str, ...] = ("default", "batch")
DEFAULT_RECENT_LOOKBACK_SECONDS = 2 * 60 * 60  # 2 hours
DEFAULT_RECENT_SCAN_LIMIT = 2000


def _as_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _decode_job_ids(values: Iterable[Any]) -> list[str]:
    job_ids: list[str] = []
    for raw in values:
        if raw is None:
            continue
        if isinstance(raw, bytes):
            text = raw.decode("utf-8", errors="replace")
        else:
            text = str(raw)
        text = text.strip()
        if text:
            job_ids.append(text)
    return job_ids


def _format_worker(worker: Worker | None) -> str | None:
    if worker is None:
        return None
    hostname = getattr(worker, "hostname", "") or ""
    pid = getattr(worker, "pid", None)
    if hostname and pid:
        return f"{hostname}:{pid}"
    return getattr(worker, "name", None) or None


def _build_worker_map(redis_conn: redis.Redis) -> dict[str, Worker]:
    mapping: dict[str, Worker] = {}
    for worker in Worker.all(connection=redis_conn):
        job_id = worker.get_current_job_id()
        if job_id:
            mapping[str(job_id)] = worker
    return mapping


def _resolve_runid(job: Job) -> str | None:
    meta = job.meta if isinstance(job.meta, dict) else {}
    runid = meta.get("runid")
    if runid:
        return str(runid)
    args = list(job.args or [])
    if args and isinstance(args[0], str):
        token = args[0].strip()
        if token:
            return token
    return None


def _resolve_config(job: Job) -> str | None:
    meta = job.meta if isinstance(job.meta, dict) else {}
    config = meta.get("config")
    if config:
        return str(config)
    args = list(job.args or [])
    if len(args) > 1 and isinstance(args[1], str):
        token = args[1].strip()
        if token:
            return token
    return None


def _resolve_func_name(job: Job) -> str | None:
    func_name = getattr(job, "func_name", None)
    if func_name:
        return str(func_name)
    description = getattr(job, "description", None)
    if description:
        return str(description)
    return None


def _resolve_auth_actor(job: Job) -> Mapping[str, Any] | None:
    meta = job.meta if isinstance(job.meta, dict) else {}
    actor = meta.get("auth_actor")
    if isinstance(actor, Mapping) and actor:
        return actor
    return None


def list_active_jobs(
    redis_conn: redis.Redis,
    *,
    queue_names: Sequence[str] = DEFAULT_QUEUES,
) -> list[dict[str, Any]]:
    """Return a complete list of started + queued jobs across the given queues."""

    queues = [Queue(name, connection=redis_conn) for name in queue_names]
    worker_map = _build_worker_map(redis_conn)

    job_refs: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    def _add(job_id: str, state: str, queue_name: str) -> None:
        if not job_id or job_id in seen:
            return
        seen.add(job_id)
        job_refs.append((job_id, state, queue_name))

    for queue in queues:
        for job_id in StartedJobRegistry(queue=queue).get_job_ids(start=0, end=-1):
            _add(str(job_id), "started", queue.name)
        for job_id in queue.get_job_ids(offset=0, length=-1):
            _add(str(job_id), "queued", queue.name)

    if not job_refs:
        return []

    jobs = Job.fetch_many([job_id for job_id, _state, _queue in job_refs], connection=redis_conn)
    payloads: list[dict[str, Any]] = []

    for (job_id, state, queue_name), job in zip(job_refs, jobs):
        if job is None:
            continue

        auth_actor = _resolve_auth_actor(job)
        worker = None
        if state == "started":
            worker = _format_worker(worker_map.get(job_id))

        payloads.append(
            {
                "job_id": job.id,
                "queue": (job.origin or queue_name or "-").strip() or "-",
                "state": state,
                "status": job.get_status(refresh=False),
                "worker": worker,
                "worker_name": getattr(job, "worker_name", None),
                "func_name": _resolve_func_name(job),
                "description": getattr(job, "description", None),
                "runid": _resolve_runid(job),
                "config": _resolve_config(job),
                "enqueued_at": _as_iso(getattr(job, "enqueued_at", None)),
                "started_at": _as_iso(getattr(job, "started_at", None)),
                "ended_at": _as_iso(getattr(job, "ended_at", None)),
                "auth_actor": dict(auth_actor) if auth_actor is not None else None,
            }
        )

    def _sort_key(item: dict[str, Any]) -> tuple[int, str]:
        state_rank = 0 if item.get("state") == "started" else 1
        return state_rank, str(item.get("queue") or "")

    payloads.sort(key=_sort_key)
    return payloads


def list_recently_completed_jobs(
    redis_conn: redis.Redis,
    *,
    queue_names: Sequence[str] = DEFAULT_QUEUES,
    lookback_seconds: int = DEFAULT_RECENT_LOOKBACK_SECONDS,
    scan_limit: int = DEFAULT_RECENT_SCAN_LIMIT,
) -> list[dict[str, Any]]:
    """Return jobs that ended within ``lookback_seconds`` across the given queues.

    The underlying registries are keyed by expiry timestamp, not ended-at, so we
    scan the most recent entries and filter by ``job.ended_at``.
    """

    now = utcnow()
    cutoff = now - timedelta(seconds=int(lookback_seconds))

    queues = [Queue(name, connection=redis_conn) for name in queue_names]
    job_refs: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    def _add(job_id: str, registry_label: str, queue_name: str) -> None:
        if not job_id or job_id in seen:
            return
        seen.add(job_id)
        job_refs.append((job_id, registry_label, queue_name))

    for queue in queues:
        finished_registry = FinishedJobRegistry(queue=queue)
        failed_registry = FailedJobRegistry(queue=queue)
        for registry, label in (
            (finished_registry, "finished"),
            (failed_registry, "failed"),
        ):
            raw_ids = redis_conn.zrevrange(registry.key, 0, max(0, int(scan_limit) - 1))
            for job_id in _decode_job_ids(raw_ids):
                _add(job_id, label, queue.name)

    if not job_refs:
        return []

    jobs = Job.fetch_many([job_id for job_id, _label, _queue in job_refs], connection=redis_conn)
    payloads: list[dict[str, Any]] = []

    for (job_id, registry_label, queue_name), job in zip(job_refs, jobs):
        if job is None:
            continue
        ended_at = getattr(job, "ended_at", None)
        if ended_at is None or ended_at < cutoff:
            continue

        auth_actor = _resolve_auth_actor(job)
        payloads.append(
            {
                "job_id": job.id,
                "queue": (job.origin or queue_name or "-").strip() or "-",
                "registry": registry_label,
                "status": job.get_status(refresh=False),
                "worker": getattr(job, "worker_name", None),
                "worker_name": getattr(job, "worker_name", None),
                "func_name": _resolve_func_name(job),
                "description": getattr(job, "description", None),
                "runid": _resolve_runid(job),
                "config": _resolve_config(job),
                "enqueued_at": _as_iso(getattr(job, "enqueued_at", None)),
                "started_at": _as_iso(getattr(job, "started_at", None)),
                "ended_at": _as_iso(ended_at),
                "auth_actor": dict(auth_actor) if auth_actor is not None else None,
            }
        )

    def _sort_recent(item: dict[str, Any]) -> str:
        # ended_at is iso; sort descending by string representation.
        return str(item.get("ended_at") or "")

    payloads.sort(key=_sort_recent, reverse=True)
    return payloads


__all__ = [
    "DEFAULT_QUEUES",
    "DEFAULT_RECENT_LOOKBACK_SECONDS",
    "DEFAULT_RECENT_SCAN_LIMIT",
    "list_active_jobs",
    "list_recently_completed_jobs",
]

