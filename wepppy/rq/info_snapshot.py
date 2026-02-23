from __future__ import annotations

import argparse
import inspect
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

import redis
from rq import Queue, Worker
from rq.job import Job
from rq.registry import FailedJobRegistry, FinishedJobRegistry, StartedJobRegistry

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

DEFAULT_QUEUES = ("default", "batch")


@dataclass(frozen=True)
class QueueSnapshot:
    name: str
    queued: int
    started: int
    finished: int
    failed: int


def _parse_csv(value: str) -> list[str]:
    return _normalize_queue_names(item.strip() for item in value.split(","))


def _normalize_queue_names(names: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_name in names:
        name = str(raw_name or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def _discover_queue_names(redis_conn: redis.Redis) -> list[str]:
    names = _normalize_queue_names(queue.name for queue in Queue.all(connection=redis_conn))
    return sorted(names)


def _queue_names_for_iteration(redis_conn: redis.Redis, requested_queue_names: Sequence[str]) -> list[str]:
    if requested_queue_names:
        return _normalize_queue_names(requested_queue_names)
    discovered = _discover_queue_names(redis_conn)
    if discovered:
        return discovered
    return list(DEFAULT_QUEUES)


def _registry_job_ids(registry: StartedJobRegistry) -> list[str]:
    get_job_ids = registry.get_job_ids
    params = inspect.signature(get_job_ids).parameters
    if "cleanup" in params:
        raw_ids = get_job_ids(start=0, end=-1, cleanup=False)
    else:
        raw_ids = get_job_ids(start=0, end=-1)

    job_ids: list[str] = []
    for raw in raw_ids:
        if raw is None:
            continue
        job_id = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        job_id = job_id.strip()
        if job_id:
            job_ids.append(job_id)
    return job_ids


def _queue_snapshot(redis_conn: redis.Redis, queue_name: str) -> tuple[QueueSnapshot, list[str]]:
    queue = Queue(queue_name, connection=redis_conn)
    started_registry = StartedJobRegistry(queue=queue)
    finished_registry = FinishedJobRegistry(queue=queue)
    failed_registry = FailedJobRegistry(queue=queue)

    started_ids = _registry_job_ids(started_registry)
    snapshot = QueueSnapshot(
        name=queue_name,
        queued=int(queue.count),
        started=len(started_ids),
        finished=int(redis_conn.zcard(finished_registry.key)),
        failed=int(redis_conn.zcard(failed_registry.key)),
    )
    return snapshot, started_ids


def _worker_identity(worker: Worker) -> str:
    host = getattr(worker, "hostname", "") or ""
    pid = getattr(worker, "pid", None)
    if host and pid:
        return f"{host}:{pid}"
    return worker.name


def _started_worker_map(redis_conn: redis.Redis, started_ids: Sequence[str]) -> dict[str, list[str]]:
    if not started_ids:
        return {}

    mapping: dict[str, list[str]] = {}
    jobs = Job.fetch_many(list(started_ids), connection=redis_conn)
    for job_id, job in zip(started_ids, jobs):
        if job is None:
            continue
        worker_name = str(getattr(job, "worker_name", "") or "").strip()
        if not worker_name:
            continue
        mapping.setdefault(worker_name, []).append(job_id)
    return mapping


def _worker_status(worker: Worker, fallback_ids: Sequence[str]) -> str:
    current_job_id = worker.get_current_job_id()
    if current_job_id:
        return "busy"
    worker_state = str(worker.get_state() or "").strip().lower()
    if worker_state == "busy":
        return "busy"
    if fallback_ids:
        return "busy"
    return "idle"


def _render_once(redis_conn: redis.Redis, queue_names: Sequence[str]) -> None:
    queue_snapshots: list[QueueSnapshot] = []
    started_ids_all: list[str] = []
    for queue_name in queue_names:
        snapshot, started_ids = _queue_snapshot(redis_conn, queue_name)
        queue_snapshots.append(snapshot)
        started_ids_all.extend(started_ids)

    started_worker_map = _started_worker_map(redis_conn, started_ids_all)

    total_queued = sum(item.queued for item in queue_snapshots)
    total_started = sum(item.started for item in queue_snapshots)
    total_finished = sum(item.finished for item in queue_snapshots)
    total_failed = sum(item.failed for item in queue_snapshots)
    for item in queue_snapshots:
        print(
            f"{item.name:<12} | {item.queued} queued, {item.started} executing, "
            f"{item.finished} finished, {item.failed} failed"
        )
    print(
        f"{len(queue_snapshots)} queues | {total_queued} queued | {total_started} executing | "
        f"{total_finished} finished | {total_failed} failed"
    )
    print("")

    workers = sorted(Worker.all(connection=redis_conn), key=lambda worker: worker.name)
    for worker in workers:
        fallback_ids = started_worker_map.get(worker.name, [])
        derived_status = _worker_status(worker, fallback_ids)
        success_count = int(getattr(worker, "successful_job_count", 0) or 0)
        failure_count = int(getattr(worker, "failed_job_count", 0) or 0)
        identity = _worker_identity(worker)
        print(
            f"{worker.name} ({identity}): {derived_status}. "
            f"jobs: {success_count} finished, {failure_count} failed"
        )

    print(f"{len(workers)} workers, {len(queue_snapshots)} queues")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f%z")
    print(f"Updated: {stamp}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render registry-backed RQ queue and worker status snapshots."
    )
    parser.add_argument(
        "--queues",
        default="",
        help="Comma-separated queue names to inspect. Defaults to all discovered queues.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.0,
        help="Refresh interval in seconds (<= 0 prints one snapshot).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    requested_queue_names = _parse_csv(args.queues)
    interval = float(args.interval or 0.0)

    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        while True:
            queue_names = _queue_names_for_iteration(redis_conn, requested_queue_names)
            _render_once(redis_conn, queue_names)
            if interval <= 0:
                return
            time.sleep(interval)


if __name__ == "__main__":
    main()
