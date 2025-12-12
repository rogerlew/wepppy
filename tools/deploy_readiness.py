#!/usr/bin/env python3
"""Gate `scripts/deploy-production.sh` by checking for active users."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

VENV_PYTHON = Path("/opt/venv/bin/python")


def _maybe_reexec_with_venv() -> None:
    """Re-exec into the baked /opt/venv interpreter when available."""
    if os.environ.get("DEPLOY_READINESS_REEXECUTED") == "1":
        return
    if (
        VENV_PYTHON.exists()
        and VENV_PYTHON.is_file()
        and VENV_PYTHON != Path(sys.executable)
    ):
        env = os.environ.copy()
        env["DEPLOY_READINESS_REEXECUTED"] = "1"
        os.execve(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv], env)


_maybe_reexec_with_venv()

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

# Lazily-loaded dependencies so `--help` works even if packages are missing.
redis = None
requests = None
Queue = None
Job = None
StartedJobRegistry = None


def ensure_dependencies() -> None:
    """Import runtime dependencies with a clear error when missing."""
    global redis, requests, Queue, Job, StartedJobRegistry
    if all([redis, requests, Queue, Job, StartedJobRegistry]):
        return
    try:
        import redis as redis_mod
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: redis. Run inside the WEPPcloud environment or pip install redis."
        ) from exc
    try:
        import requests as requests_mod
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: requests. Run inside the WEPPcloud environment or pip install requests."
        ) from exc
    from rq import Queue as rq_queue
    from rq.job import Job as rq_job
    from rq.registry import StartedJobRegistry as rq_started_registry

    redis = redis_mod
    requests = requests_mod
    Queue = rq_queue
    Job = rq_job
    StartedJobRegistry = rq_started_registry


@dataclass
class JobSnapshot:
    id: str
    queue: str
    runid: str | None
    description: str | None


@dataclass
class QueueSnapshot:
    name: str
    running: List[JobSnapshot]
    queued: int
    scheduled: int
    deferred: int

    @property
    def running_count(self) -> int:
        return len(self.running)


@dataclass
class RQSnapshot:
    queues: List[QueueSnapshot]

    @property
    def running_jobs(self) -> List[JobSnapshot]:
        jobs: List[JobSnapshot] = []
        for snapshot in self.queues:
            jobs.extend(snapshot.running)
        return jobs

    @property
    def total_running(self) -> int:
        return sum(q.running_count for q in self.queues)

    @property
    def total_queued(self) -> int:
        return sum(q.queued for q in self.queues)


def _queue_names(raw: Sequence[str]) -> List[str]:
    names: List[str] = []
    for name in raw:
        trimmed = name.strip()
        if trimmed and trimmed not in names:
            names.append(trimmed)
    return names


def _first_arg(job: Job) -> str | None:
    try:
        if job.args:
            return str(job.args[0])
    except Exception:
        return None
    return None


def _running_jobs(queue: Queue) -> List[JobSnapshot]:
    registry = StartedJobRegistry(queue=queue)
    job_ids = registry.get_job_ids()
    running: List[JobSnapshot] = []

    for job_id in job_ids:
        try:
            job = Job.fetch(job_id, connection=queue.connection)
        except Exception as exc:
            running.append(
                JobSnapshot(
                    id=str(job_id),
                    queue=queue.name,
                    runid=None,
                    description=f"error loading job: {exc}",
                )
            )
            continue

        runid = None
        if isinstance(job.meta, dict):
            runid = job.meta.get("runid")
        if runid is None:
            runid = _first_arg(job)

        running.append(
            JobSnapshot(
                id=str(job.id),
                queue=queue.name,
                runid=str(runid) if runid else None,
                description=job.description,
            )
        )
    return running


def snapshot_rq(queues: Sequence[str]) -> RQSnapshot:
    ensure_dependencies()
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    redis_conn = redis.Redis(**conn_kwargs)

    snapshots: List[QueueSnapshot] = []
    for name in _queue_names(queues):
        queue = Queue(name, connection=redis_conn)
        scheduled = queue.scheduled_job_registry
        deferred = queue.deferred_job_registry

        snapshot = QueueSnapshot(
            name=name,
            running=_running_jobs(queue),
            queued=queue.count,
            scheduled=len(scheduled.get_job_ids()),
            deferred=len(deferred.get_job_ids()),
        )
        snapshots.append(snapshot)

    return RQSnapshot(queues=snapshots)


def fetch_preflight_connections(metrics_url: str) -> float:
    ensure_dependencies()
    response = requests.get(metrics_url, timeout=3)
    response.raise_for_status()

    for line in response.text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith("preflight2_connections_active"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        return float(parts[1])

    raise RuntimeError("preflight2_connections_active not found in metrics output")


def _default_metrics_url() -> str:
    return "http://127.0.0.1:9001/metrics"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Checks for active users before running scripts/deploy-production.sh. "
            "Exit codes: 0=GO, 1=NO-GO (activity detected), 2=UNKNOWN (checks failed)."
        )
    )
    parser.add_argument(
        "--queues",
        default="high,default,low",
        help="Comma-separated list of RQ queues to inspect (default: high,default,low).",
    )
    parser.add_argument(
        "--allow-queued",
        action="store_true",
        help="Do not block on queued jobs; only running jobs trigger NO-GO.",
    )
    parser.add_argument(
        "--preflight-metrics-url",
        default=_default_metrics_url(),
        help="URL for preflight2 /metrics endpoint (default: http://127.0.0.1:9001/metrics).",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip the preflight2 connection check.",
    )
    parser.add_argument(
        "--require-preflight",
        action="store_true",
        help="Treat preflight metrics failures as blocking (UNKNOWN) instead of a warning.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON summary for automation.",
    )
    return parser


def format_queue(snapshot: QueueSnapshot) -> str:
    bits = [
        f"{snapshot.name}: running={snapshot.running_count}",
        f"queued={snapshot.queued}",
        f"scheduled={snapshot.scheduled}",
        f"deferred={snapshot.deferred}",
    ]
    return ", ".join(bits)


def print_human(
    status: str,
    reasons: list[str],
    errors: list[str],
    warnings: list[str],
    rq_snapshot: RQSnapshot | None,
    preflight_connections: float | None,
    metrics_url: str | None,
) -> None:
    print(f"Status: {status}")
    if reasons:
        print("Reasons:")
        for reason in reasons:
            print(f"- {reason}")
    if errors:
        print("Errors:")
        for err in errors:
            print(f"- {err}")
    if warnings:
        print("Warnings:")
        for warn in warnings:
            print(f"- {warn}")

    if rq_snapshot:
        print("\nRQ queues:")
        for snapshot in rq_snapshot.queues:
            print(f"- {format_queue(snapshot)}")
            if snapshot.running:
                for job in snapshot.running:
                    details = f"    job={job.id}"
                    if job.runid:
                        details += f" runid={job.runid}"
                    if job.description:
                        details += f" desc={job.description}"
                    print(details)

    if metrics_url:
        if preflight_connections is not None:
            print(
                f"\nPreflight connections: {preflight_connections} "
                f"(metrics: {metrics_url})"
            )
        else:
            print(f"\nPreflight connections: unavailable (metrics: {metrics_url})")


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    ensure_dependencies()

    queue_names = [name.strip() for name in args.queues.split(",") if name.strip()]
    reasons: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []

    rq_snapshot: RQSnapshot | None = None
    preflight_connections: float | None = None

    try:
        rq_snapshot = snapshot_rq(queue_names)
        if rq_snapshot.total_running > 0:
            job_ids = ", ".join(job.id for job in rq_snapshot.running_jobs)
            reasons.append(f"RQ running jobs detected ({rq_snapshot.total_running}): {job_ids}")
        elif not args.allow_queued and rq_snapshot.total_queued > 0:
            reasons.append(f"RQ queued jobs detected ({rq_snapshot.total_queued})")
    except Exception as exc:
        errors.append(f"RQ inspection failed: {exc}")

    if not args.skip_preflight:
        try:
            preflight_connections = fetch_preflight_connections(args.preflight_metrics_url)
            if preflight_connections > 0:
                reasons.append(f"preflight2 active connections: {preflight_connections}")
        except Exception as exc:
            message = f"Preflight metrics check failed: {exc}"
            if args.require_preflight:
                errors.append(message)
            else:
                warnings.append(message)

    if reasons:
        status = "NO-GO"
        exit_code = 1
    elif errors:
        status = "UNKNOWN"
        exit_code = 2
    else:
        status = "GO"
        exit_code = 0

    if args.json:
        payload = {
            "status": status,
            "exit_code": exit_code,
            "reasons": reasons,
            "errors": errors,
            "warnings": warnings,
            "rq": asdict(rq_snapshot) if rq_snapshot else None,
            "preflight": {
                "connections_active": preflight_connections,
                "metrics_url": args.preflight_metrics_url if not args.skip_preflight else None,
            },
        }
        json.dump(payload, sys.stdout, indent=2)
        print()
    else:
        print_human(
            status=status,
            reasons=reasons,
            errors=errors,
            warnings=warnings,
            rq_snapshot=rq_snapshot,
            preflight_connections=preflight_connections,
            metrics_url=None if args.skip_preflight else args.preflight_metrics_url,
        )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
