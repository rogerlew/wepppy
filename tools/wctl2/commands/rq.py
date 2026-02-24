from __future__ import annotations

import subprocess
from typing import List

import typer

from ..context import CLIContext
from ..docker import compose_exec
from ..util import quote_args

_RQ_BINARY = "/opt/venv/bin/rq"
_RQ_DEFAULT_QUEUES = ("default", "batch")
_PYTHON_BIN = "/opt/venv/bin/python"
_RQ_DETAIL_MODULE = "wepppy.rq.job_summary"
_RQ_REGISTRY_SYNC_SNIPPET = """
import inspect
import re

import redis
from rq import Queue, Worker, worker_registration
from rq.job import Job
from rq.utils import utcformat, utcnow

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

queue_names = ("default", "batch")
conn = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
prefix = Worker.redis_worker_namespace_prefix
queue_prefix = worker_registration.WORKERS_BY_QUEUE_KEY.split("%s", 1)[0]


def _decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _scan(pattern):
    return sorted({_decode(key).strip() for key in conn.scan_iter(match=pattern) if key})


def _get_started_job_ids(registry):
    params = inspect.signature(registry.get_job_ids).parameters
    if "cleanup" in params:
        return registry.get_job_ids(start=0, end=-1, cleanup=False)
    return registry.get_job_ids(start=0, end=-1)


worker_keys = _scan(f"{prefix}*")
queue_set_keys = _scan(f"{queue_prefix}*")
conn.delete(Worker.redis_workers_keys, *queue_set_keys)
for key in worker_keys:
    worker = Worker.find_by_key(key, connection=conn)
    if worker is None:
        continue
    worker_registration.register(worker)

if conn.scard(Worker.redis_workers_keys) == 0:
    now = utcformat(utcnow())
    uuid_pattern = re.compile(r"^[0-9a-f]{32}$")
    recovered = set()
    for queue_name in queue_names:
        queue = Queue(queue_name, connection=conn)
        job_ids = list(_get_started_job_ids(queue.started_job_registry))
        if not job_ids:
            continue
        jobs = Job.fetch_many(job_ids, connection=conn)
        for job in jobs:
            if job is None:
                continue
            worker_name = _decode(getattr(job, "worker_name", "")).strip()
            if not worker_name or not uuid_pattern.match(worker_name):
                continue
            recovered.add(worker_name)

    for worker_name in sorted(recovered):
        worker_key = f"{prefix}{worker_name}"
        if not conn.exists(worker_key):
            conn.hset(
                worker_key,
                mapping={
                    "birth": now,
                    "last_heartbeat": now,
                    "queues": ",".join(queue_names),
                    "state": "busy",
                    "hostname": "unknown",
                    "ip_address": "unknown",
                    "pid": "0",
                    "version": "unknown",
                    "python_version": "unknown",
                },
            )
        conn.sadd(Worker.redis_workers_keys, worker_key)
        for queue_name in queue_names:
            conn.sadd(worker_registration.WORKERS_BY_QUEUE_KEY % queue_name, worker_key)
"""
_RQ_REDIS_URL_SNIPPET = (
    "from wepppy.config.redis_settings import redis_url, RedisDB; "
    "print(redis_url(RedisDB.RQ))"
)


def _context(ctx: typer.Context) -> CLIContext:
    context = ctx.obj
    if not isinstance(context, CLIContext):
        raise RuntimeError("CLIContext is not initialized.")
    return context


def _exit_from_result(result: subprocess.CompletedProcess) -> None:
    raise typer.Exit(result.returncode)


def _compose_python_command(args: List[str]) -> str:
    quoted = quote_args(args)
    return f"cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy {quoted}"


def _compose_rq_redis_url_command() -> str:
    """
    Resolve the RQ Redis URL inside the container.

    We intentionally avoid constructing an authenticated URL on the host so the
    password never appears in the host command line. The wepppy config helper
    supports both legacy env vars (REDIS_PASSWORD) and secret files
    (REDIS_PASSWORD_FILE).
    """
    args = [_PYTHON_BIN, "-c", _RQ_REDIS_URL_SNIPPET]
    return _compose_python_command(args)


def _compose_rq_registry_sync_command() -> str:
    args = [_PYTHON_BIN, "-c", _RQ_REGISTRY_SYNC_SNIPPET]
    return _compose_python_command(args)


def _compose_rq_info_command(extra_args: List[str]) -> str:
    registry_sync_command = _compose_rq_registry_sync_command()
    redis_url_command = _compose_rq_redis_url_command()
    rq_args = quote_args([*_RQ_DEFAULT_QUEUES, *extra_args])
    return (
        "set -euo pipefail; "
        f"{registry_sync_command}; "
        f'redis_url="$({redis_url_command})"; '
        f'exec {_RQ_BINARY} info -u "$redis_url" {rq_args}'
    )


def register(app: typer.Typer) -> None:
    @app.command(
        "rq-info",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
        help="Show RQ worker and queue stats for default and batch queues.",
    )
    def rq_info(
        ctx: typer.Context,
        detail: bool = typer.Option(
            False,
            "--detail",
            help="Append job details (runid, description, auth actor) after rq info output.",
        ),
        detail_limit: int = typer.Option(
            50,
            "--detail-limit",
            help="Maximum jobs per state and queue for --detail (0 for unlimited).",
        ),
    ) -> None:
        context = _context(ctx)
        command = _compose_rq_info_command(list(ctx.args))
        result = compose_exec(context, "rq-worker", command, check=False)
        if result.returncode != 0:
            _exit_from_result(result)

        if detail:
            detail_args = [
                _PYTHON_BIN,
                "-m",
                _RQ_DETAIL_MODULE,
                "--queues",
                ",".join(_RQ_DEFAULT_QUEUES),
                "--limit",
                str(detail_limit),
            ]
            detail_command = _compose_python_command(detail_args)
            detail_result = compose_exec(context, "rq-worker", detail_command, check=False)
            _exit_from_result(detail_result)
        _exit_from_result(result)
