from __future__ import annotations

import logging
import os
from typing import Any, Mapping
from uuid import uuid4

import redis
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.base import lock_statuses
from wepppy.nodb.core.ron import Ron
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.job_id import new_rq_job_id
from wepppy.rq.migrations_rq import migrations_rq
from wepppy.weppcloud.utils.helpers import get_run_owners_lazy, get_wd

from .auth import AuthError, authorize_run_access, require_jwt, require_roles, require_session_marker
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()
RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]
MIGRATION_JOB_KEY = "migrations"
MIGRATION_SUBMIT_LOCK_TTL_SECONDS = 30


class MigrationJobConflict(RuntimeError):
    """Raised when one run already has an active migration submission."""


def _is_admin(claims: Mapping[str, Any]) -> bool:
    try:
        require_roles(claims, ["Admin"])
    except AuthError:
        return False
    return True


def _is_run_owner(claims: Mapping[str, Any], runid: str) -> bool:
    token_user_id = str(claims.get("user_id") or claims.get("sub") or "").strip()
    token_email = str(claims.get("email") or "").strip().lower()
    if not token_user_id and not token_email:
        return False

    owners = get_run_owners_lazy(runid)
    for owner in owners or []:
        if token_user_id and str(getattr(owner, "id", "")) == token_user_id:
            return True
        if token_email and str(getattr(owner, "email", "")).strip().lower() == token_email:
            return True
    return False


def _ensure_run_access(claims: Mapping[str, Any], runid: str) -> None:
    if _is_admin(claims):
        return

    token_class = claims.get("token_class")
    if token_class == "session":
        require_session_marker(claims, runid)
    elif token_class == "user":
        authorize_run_access(claims, runid)
    else:
        raise AuthError(
            "Only user or session tokens may run migrations",
            status_code=403,
            code="forbidden",
        )

    if not _is_run_owner(claims, runid):
        raise AuthError(
            "Only a project owner or administrator can run migrations",
            status_code=403,
            code="forbidden",
        )


async def _safe_json(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except (UnicodeDecodeError, ValueError, RuntimeError):
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _enqueue_migration_job(
    *,
    wd: str,
    runid: str,
    create_archive: bool,
    was_readonly: bool,
    prep: RedisPrep,
) -> Job:
    submit_owner = f"{MIGRATION_JOB_KEY}:{uuid4().hex}"
    submit_lock_key = f"migrations:submit_lock:{runid}"
    with redis.Redis(
        **redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    ) as lock_conn:
        if not lock_conn.set(
            submit_lock_key,
            submit_owner,
            nx=True,
            ex=MIGRATION_SUBMIT_LOCK_TTL_SECONDS,
        ):
            raise MigrationJobConflict("Another migration submission is in progress")
        try:
            with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
                existing_job_id = prep.get_rq_job_ids().get(MIGRATION_JOB_KEY)
                if existing_job_id:
                    try:
                        existing_job = Job.fetch(existing_job_id, connection=redis_conn)
                        status_value = existing_job.get_status(refresh=True)
                    except (NoSuchJobError, OSError, redis.exceptions.RedisError):
                        status_value = None
                    if status_value in {"queued", "started", "deferred", "scheduled"}:
                        raise MigrationJobConflict(
                            "A migration job is already running for this project"
                        )

                job_id = new_rq_job_id()
                prep.set_rq_job_id(MIGRATION_JOB_KEY, job_id)
                queue = Queue(connection=redis_conn)
                job = queue.enqueue_call(
                    func=migrations_rq,
                    args=[wd, runid],
                    kwargs={
                        "archive_before": create_archive,
                        "restore_readonly": was_readonly,
                    },
                    timeout=RQ_TIMEOUT,
                    job_id=job_id,
                )
                return job
        finally:
            try:
                if lock_conn.get(submit_lock_key) == submit_owner:
                    lock_conn.delete(submit_lock_key)
            except redis.exceptions.RedisError:
                logger.warning(
                    "rq-engine migration submit lock release failed",
                    exc_info=True,
                    extra={"runid": runid},
                )


@router.post("/runs/{runid}/{config}/migrate-run")
async def migrate_run(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        _ensure_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine migrate-run auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        if not os.path.exists(wd):
            return error_response(
                "Run not found",
                status_code=404,
                code="not_found",
                details=f"Run {runid} not found.",
            )

        ron = Ron.getInstance(wd)

        locked = [
            name for name, state in lock_statuses(runid).items() if name.endswith(".nodb") and state
        ]
        if locked:
            return error_response(
                f"Cannot migrate while files are locked: {', '.join(locked)}",
                status_code=409,
            )

        prep = RedisPrep.getInstance(wd)
        data = await _safe_json(request)
        create_archive = bool(data.get("create_archive", False))

        was_readonly = ron.readonly

        try:
            job = _enqueue_migration_job(
                wd=wd,
                runid=runid,
                create_archive=create_archive,
                was_readonly=was_readonly,
                prep=prep,
            )
            StatusMessenger.publish(
                f"{runid}:{MIGRATION_JOB_KEY}",
                f"rq:{job.id} ENQUEUED migrations_rq({runid})",
            )

            return JSONResponse(
                {
                    "job_id": job.id,
                    "status_url": f"/rq-engine/api/jobstatus/{job.id}",
                    "message": "Migration job enqueued.",
                    "result": {"was_readonly": was_readonly},
                },
                status_code=status.HTTP_202_ACCEPTED,
            )
        except MigrationJobConflict as exc:
            return error_response(str(exc), status_code=409)
        except Exception as exc:
            # API boundary: enqueue failure must return canonical rq-engine error payload.
            logger.exception("rq-engine migrate-run enqueue failed", extra={"runid": runid, "config": config})
            return error_response_with_traceback(
                f"Failed to enqueue migration job: {exc}",
                status_code=500,
            )
    except Exception:
        logger.exception("rq-engine migrate-run failed")
        return error_response_with_traceback("Failed to enqueue migration job")


__all__ = ["router"]
