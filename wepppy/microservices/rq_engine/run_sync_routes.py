from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.registry import DeferredJobRegistry, FailedJobRegistry, FinishedJobRegistry, StartedJobRegistry

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.migrations_rq import migrations_rq
from wepppy.rq.run_sync_rq import DEFAULT_TARGET_ROOT, STATUS_CHANNEL_SUFFIX, run_sync_rq

from .auth import AuthError, require_jwt, require_roles
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RUN_SYNC_TIMEOUT = int(os.getenv("RQ_ENGINE_RUN_SYNC_TIMEOUT", "86400"))
MIGRATIONS_TIMEOUT = int(os.getenv("RQ_ENGINE_MIGRATIONS_TIMEOUT", "7200"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


@contextmanager
def _redis_conn():
    conn = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
    try:
        yield conn
    finally:
        close = getattr(conn, "close", None)
        if not callable(close):
            return
        try:
            close()
        except (OSError, redis.exceptions.RedisError) as exc:
            logger.debug("rq-engine failed to close Redis connection", exc_info=exc)


def _as_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _job_is_run_sync(job: Job) -> bool:
    name = getattr(job, "func_name", "") or ""
    return name.endswith("run_sync_rq") or "run_sync_rq" in name


def _serialize_job(job: Job, status_label: str) -> Dict[str, Any]:
    meta = job.meta or {}
    args = list(job.args or [])
    runid = meta.get("runid") or (args[0] if len(args) > 0 else None)
    config = meta.get("config") or (args[1] if len(args) > 1 else None)
    source_host = meta.get("source_host") or (args[2] if len(args) > 2 else None)
    return {
        "id": job.id,
        "status": status_label,
        "job_status": job.get_status(refresh=False),
        "runid": runid,
        "config": config,
        "source_host": source_host,
        "enqueued_at": _as_iso(getattr(job, "enqueued_at", None)),
        "started_at": _as_iso(getattr(job, "started_at", None)),
        "ended_at": _as_iso(getattr(job, "ended_at", None)),
    }


def _resolve_job(redis_conn: redis.Redis, job_id: str, status_label: str) -> Dict[str, Any] | None:
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except NoSuchJobError:
        return None

    if not _job_is_run_sync(job):
        return None

    return _serialize_job(job, status_label)


def _collect_run_sync_jobs(redis_conn: redis.Redis) -> List[Dict[str, Any]]:
    queue = Queue(connection=redis_conn)
    registries = [
        ("queued", queue.get_job_ids()),
        ("started", StartedJobRegistry(queue=queue).get_job_ids()),
        ("failed", FailedJobRegistry(queue=queue).get_job_ids()),
        ("finished", FinishedJobRegistry(queue=queue).get_job_ids()),
        ("deferred", DeferredJobRegistry(queue=queue).get_job_ids()),
    ]

    jobs: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for status_label, job_ids in registries:
        for job_id in job_ids[:50]:
            if job_id in seen:
                continue
            seen.add(job_id)
            job_payload = _resolve_job(redis_conn, job_id, status_label)
            if job_payload is None:
                continue
            jobs.append(job_payload)
    return jobs


def _serialize_migration(record: Any) -> Dict[str, Any]:
    return {
        "id": record.id,
        "runid": record.runid,
        "config": record.config,
        "local_path": record.local_path,
        "source_host": record.source_host,
        "original_url": record.original_url,
        "pulled_at": _as_iso(record.pulled_at),
        "owner_email": record.owner_email,
        "version_at_pull": record.version_at_pull,
        "last_status": record.last_status,
        "archive_before": record.archive_before,
        "archive_after": record.archive_after,
        "is_fixture": record.is_fixture,
        "created_at": _as_iso(record.created_at),
        "updated_at": _as_iso(record.updated_at),
    }


def _load_migrations() -> list[Dict[str, Any]]:
    from wepppy.weppcloud.app import RunMigration, app as flask_app

    with flask_app.app_context():
        records = RunMigration.query.order_by(RunMigration.updated_at.desc()).limit(50).all()
        return [_serialize_migration(record) for record in records]


@router.post("/run-sync")
async def run_sync(request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        require_roles(claims, ["Admin"])
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-sync auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        payload = await parse_request_payload(
            request,
            boolean_fields={"run_migrations", "archive_before"},
        )
    except (UnicodeDecodeError, ValueError, RuntimeError) as exc:
        logger.info("rq-engine run-sync invalid payload: %s", exc)
        return error_response("Invalid payload", status_code=400, code="validation_error", details=str(exc))

    runid = payload.get("runid")
    if not runid:
        return error_response("runid is required", status_code=400)

    source_host = payload.get("source_host") or "wepp.cloud"
    target_root = payload.get("target_root") or DEFAULT_TARGET_ROOT
    owner_email = payload.get("owner_email") or None
    config = payload.get("config") or None
    run_migrations = payload.get("run_migrations", True)
    archive_before = payload.get("archive_before", False)

    try:
        with _redis_conn() as redis_conn:
            queue = Queue(connection=redis_conn)
            sync_job = queue.enqueue_call(
                run_sync_rq,
                (runid, source_host, owner_email, target_root, config),
                timeout=RUN_SYNC_TIMEOUT,
            )

            jobs_info: Dict[str, Any] = {
                "sync_job_id": sync_job.id,
                "job_id": sync_job.id,
            }
            job_ids = [sync_job.id]

            if run_migrations:
                prefix = str(runid)[:2].lower()
                wd = f"{target_root}/{prefix}/{runid}"

                migration_job = queue.enqueue_call(
                    migrations_rq,
                    (wd, runid),
                    {"archive_before": archive_before},
                    timeout=MIGRATIONS_TIMEOUT,
                    depends_on=sync_job,
                )
                jobs_info["migration_job_id"] = migration_job.id
                job_ids.append(migration_job.id)
                jobs_info["job_ids"] = job_ids
    except Exception:
        logger.exception("rq-engine run-sync enqueue failed")
        return error_response_with_traceback("Failed to enqueue run sync job", status_code=500)

    StatusMessenger.publish(
        f"{runid}:{STATUS_CHANNEL_SUFFIX}",
        f"rq:{sync_job.id} ENQUEUED run_sync_rq({runid})",
    )

    return JSONResponse(jobs_info)


@router.get("/run-sync/status")
def run_sync_status(request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request)
        require_roles(claims, ["Admin"])
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-sync status auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        with _redis_conn() as redis_conn:
            jobs = _collect_run_sync_jobs(redis_conn)
        migrations = _load_migrations()
        return JSONResponse({"jobs": jobs, "migrations": migrations})
    except Exception:
        logger.exception("rq-engine run-sync status failed")
        return error_response_with_traceback("Failed to load run sync status", status_code=500)


__all__ = ["router"]
