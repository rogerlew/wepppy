from __future__ import annotations

import argparse
import inspect
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import redis
from rq import Queue, Worker
from rq.job import Job
from rq.registry import StartedJobRegistry

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

DEFAULT_QUEUES = ("default", "batch")
DEFAULT_STATES = ("started", "queued")
DEFAULT_LIMIT = 50
MAX_COLUMN_WIDTHS = (12, 8, 8, 20, 28, 32, 24)


@dataclass(frozen=True)
class JobRow:
    job_id: str
    queue: str
    state: str
    worker: str
    runid: str
    description: str
    auth_actor: str


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _truncate(value: str, width: int) -> str:
    if width <= 0 or len(value) <= width:
        return value
    if width <= 3:
        return value[:width]
    return f"{value[: width - 3]}..."


def _format_worker(worker: Worker | None) -> str:
    if worker is None:
        return "-"
    hostname = getattr(worker, "hostname", "") or ""
    pid = getattr(worker, "pid", None)
    if hostname and pid:
        return f"{hostname}:{pid}"
    return worker.name


def _format_auth_actor(auth_actor: Any) -> str:
    if not isinstance(auth_actor, dict) or not auth_actor:
        return "-"
    token_class = str(auth_actor.get("token_class") or "").strip().lower()
    if token_class == "user":
        user_id = auth_actor.get("user_id")
        return f"user:{user_id}" if user_id is not None else "-"
    if token_class == "session":
        session_id = auth_actor.get("session_id")
        return f"session:{session_id}" if session_id else "-"
    if token_class == "service":
        sub = str(auth_actor.get("sub") or "").strip()
        groups = auth_actor.get("service_groups") or []
        if isinstance(groups, (list, tuple, set)):
            group_text = ", ".join(str(item) for item in groups if item)
        else:
            group_text = str(groups)
        if group_text:
            return f"service:{sub} [{group_text}]".strip()
        return f"service:{sub}" if sub else "-"
    if token_class == "mcp":
        sub = str(auth_actor.get("sub") or "").strip()
        return f"mcp:{sub}" if sub else "-"
    return token_class or "-"


def _resolve_runid(job: Job) -> str:
    meta = job.meta if isinstance(job.meta, dict) else {}
    runid = meta.get("runid")
    if runid:
        return str(runid)
    args = list(job.args or [])
    if args and isinstance(args[0], str):
        return args[0]
    return "-"


def _resolve_description(job: Job) -> str:
    description = job.description
    if description:
        return str(description)
    func_name = getattr(job, "func_name", None)
    if func_name:
        return str(func_name)
    return "-"


def _collect_job_ids(
    queues: Sequence[Queue],
    states: Sequence[str],
    limit: int,
) -> list[tuple[str, str]]:
    job_ids: list[tuple[str, str]] = []
    seen: set[str] = set()
    queue_length = limit if limit > 0 else -1
    registry_end = limit - 1 if limit > 0 else -1

    def _add(job_id: str, state: str) -> None:
        if job_id in seen:
            return
        seen.add(job_id)
        job_ids.append((job_id, state))

    if "started" in states:
        for queue in queues:
            registry = StartedJobRegistry(queue=queue)
            get_job_ids = registry.get_job_ids
            params = inspect.signature(get_job_ids).parameters
            if "cleanup" in params:
                job_iter = get_job_ids(start=0, end=registry_end, cleanup=False)
            else:
                job_iter = get_job_ids(start=0, end=registry_end)
            for job_id in job_iter:
                _add(job_id, "started")

    if "queued" in states:
        for queue in queues:
            for job_id in queue.get_job_ids(offset=0, length=queue_length):
                _add(job_id, "queued")

    return job_ids


def _build_worker_map(redis_conn: redis.Redis) -> dict[str, Worker]:
    mapping: dict[str, Worker] = {}
    for worker in Worker.all(connection=redis_conn):
        job_id = worker.get_current_job_id()
        if job_id:
            mapping[job_id] = worker
    return mapping


def _build_rows(
    redis_conn: redis.Redis,
    queue_names: Sequence[str],
    states: Sequence[str],
    limit: int,
) -> list[JobRow]:
    queues = [Queue(name, connection=redis_conn) for name in queue_names]
    worker_map = _build_worker_map(redis_conn)
    rows: list[JobRow] = []

    job_refs = _collect_job_ids(queues, states, limit)
    if not job_refs:
        return rows

    job_ids = [job_id for job_id, _state in job_refs]
    jobs = Job.fetch_many(job_ids, connection=redis_conn)

    for (job_id, state), job in zip(job_refs, jobs):
        if job is None:
            continue
        runid = _resolve_runid(job)
        description = _resolve_description(job)
        auth_actor = _format_auth_actor(job.meta.get("auth_actor") if isinstance(job.meta, dict) else None)
        worker = _format_worker(worker_map.get(job_id) if state == "started" else None)
        rows.append(
            JobRow(
                job_id=job.id,
                queue=job.origin or "-",
                state=state,
                worker=worker,
                runid=runid,
                description=description,
                auth_actor=auth_actor,
            )
        )

    return rows


def _render_table(rows: Iterable[JobRow], states: Sequence[str]) -> None:
    rows = list(rows)
    state_label = ", ".join(states)
    print("")
    print(f"Jobs ({state_label})")
    if not rows:
        print("  (none)")
        return

    headers = ["job_id", "queue", "state", "worker", "runid", "description", "auth_actor"]
    raw_rows = [
        [
            row.job_id,
            row.queue,
            row.state,
            row.worker,
            row.runid,
            row.description,
            row.auth_actor,
        ]
        for row in rows
    ]

    truncated_rows: list[list[str]] = []
    for row in raw_rows:
        truncated_rows.append(
            [_truncate(str(value), MAX_COLUMN_WIDTHS[index]) for index, value in enumerate(row)]
        )

    widths = [
        max(len(headers[index]), max(len(row[index]) for row in truncated_rows))
        for index in range(len(headers))
    ]

    header_line = " ".join(headers[index].ljust(widths[index]) for index in range(len(headers)))
    separator_line = " ".join("-" * widths[index] for index in range(len(headers)))
    print(header_line)
    print(separator_line)
    for row in truncated_rows:
        line = " ".join(row[index].ljust(widths[index]) for index in range(len(headers)))
        print(line)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize active RQ jobs with auth metadata.")
    parser.add_argument(
        "--queues",
        default=",".join(DEFAULT_QUEUES),
        help="Comma-separated list of queues to inspect.",
    )
    parser.add_argument(
        "--states",
        default=",".join(DEFAULT_STATES),
        help="Comma-separated job states to include (started, queued).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Maximum jobs per state and queue (0 for unlimited).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    queue_names = _parse_csv(args.queues) or list(DEFAULT_QUEUES)
    states = _parse_csv(args.states) or list(DEFAULT_STATES)
    limit = int(args.limit) if args.limit is not None else DEFAULT_LIMIT

    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        rows = _build_rows(redis_conn, queue_names, states, limit)
        _render_table(rows, states)


if __name__ == "__main__":
    main()


__all__ = ["main"]
