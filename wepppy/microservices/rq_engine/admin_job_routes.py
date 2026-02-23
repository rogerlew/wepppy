from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.job_listings import (
    DEFAULT_RECENT_LOOKBACK_SECONDS,
    DEFAULT_RECENT_SCAN_LIMIT,
    DEFAULT_QUEUES,
    list_active_jobs,
    list_recently_completed_jobs,
)

from .auth import AuthError, require_jwt, require_roles
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

ADMIN_SCOPE = "rq:status"

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


def _parse_queues(raw: str | None) -> Sequence[str]:
    if not raw:
        return DEFAULT_QUEUES
    tokens = [token.strip() for token in str(raw).split(",") if token.strip()]
    return tokens or DEFAULT_QUEUES


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_roles(raw: Any) -> set[str]:
    if raw is None:
        return set()
    if isinstance(raw, str):
        return {role.strip().lower() for role in raw.split(",") if role.strip()}
    if isinstance(raw, Sequence):
        roles: set[str] = set()
        for item in raw:
            if isinstance(item, dict) and "name" in item:
                candidate = item.get("name")
            else:
                candidate = item
            if candidate is None:
                continue
            roles.add(str(candidate).strip().lower())
        return {role for role in roles if role}
    return set()


def _token_allows_admin(claims: Mapping[str, Any]) -> bool:
    roles = _normalize_roles(claims.get("roles"))
    return "admin" in roles or "root" in roles


def _format_auth_actor(auth_actor: Any) -> str | None:
    if not isinstance(auth_actor, dict) or not auth_actor:
        return None
    token_class = str(auth_actor.get("token_class") or "").strip().lower()
    if token_class == "user":
        user_id = auth_actor.get("user_id")
        return f"user:{user_id}" if user_id is not None else None
    if token_class == "session":
        session_id = auth_actor.get("session_id")
        return f"session:{session_id}" if session_id else None
    if token_class == "service":
        sub = str(auth_actor.get("sub") or "").strip()
        return f"service:{sub}" if sub else None
    if token_class == "mcp":
        sub = str(auth_actor.get("sub") or "").strip()
        return f"mcp:{sub}" if sub else None
    return token_class or None


def _hydrate_submitter_fields(jobs: list[dict[str, Any]]) -> None:
    """Best-effort attach submitter email/ip using auth_actor user_id or run owners."""

    if not jobs:
        return

    try:
        from flask import has_app_context
        from sqlalchemy.exc import SQLAlchemyError
        from wepppy.weppcloud.app import User, app as flask_app, get_run_owners
    except Exception:
        logger.exception("Unable to import Flask app/user models for submitter hydration")
        return

    def _run() -> None:
        user_cache: dict[int, Any] = {}
        run_owner_cache: dict[str, Any] = {}

        def _user_by_id(user_id: Any) -> Any | None:
            if user_id is None or isinstance(user_id, bool):
                return None
            try:
                parsed = int(str(user_id).strip())
            except (TypeError, ValueError):
                return None
            if parsed in user_cache:
                return user_cache[parsed]
            user = User.query.filter(User.id == parsed).first()
            user_cache[parsed] = user
            return user

        def _owner_for_run(runid: str) -> Any | None:
            if runid in run_owner_cache:
                return run_owner_cache[runid]
            try:
                owners = get_run_owners(runid)
            except SQLAlchemyError as exc:
                logger.exception("rq-engine submitter hydration owner lookup failed", extra={"runid": runid})
                owners = []
            owner = owners[0] if owners else None
            run_owner_cache[runid] = owner
            return owner

        for job in jobs:
            submitter_email = None
            submitter_ip = None

            auth_actor = job.get("auth_actor")
            if isinstance(auth_actor, dict):
                token_class = str(auth_actor.get("token_class") or "").strip().lower()
                if token_class == "user":
                    user = _user_by_id(auth_actor.get("user_id"))
                    if user is not None:
                        submitter_email = getattr(user, "email", None) or None
                        submitter_ip = (
                            getattr(user, "current_login_ip", None)
                            or getattr(user, "last_login_ip", None)
                            or None
                        )

            if not submitter_email:
                runid = job.get("runid")
                if isinstance(runid, str) and runid:
                    owner = _owner_for_run(runid)
                    if owner is not None:
                        submitter_email = getattr(owner, "email", None) or None
                        submitter_ip = (
                            getattr(owner, "current_login_ip", None)
                            or getattr(owner, "last_login_ip", None)
                            or None
                        )

            if submitter_email:
                job["submitter_email"] = submitter_email
            if submitter_ip:
                job["submitter_ip"] = submitter_ip

            if not submitter_email and not submitter_ip:
                actor_text = _format_auth_actor(auth_actor)
                if actor_text:
                    job["submitter_actor"] = actor_text

    if has_app_context():
        _run()
        return

    with flask_app.app_context():
        _run()


@router.get(
    "/admin/recently-completed-jobs",
    summary="List recently completed RQ jobs (admin)",
    description=(
        "Admin-only debugging endpoint. Requires JWT Bearer scope `rq:status` plus role `Admin`/`Root`. "
        "Returns jobs that ended within a lookback window across the default and batch queues."
    ),
    tags=["rq-engine", "jobs"],
    operation_id=rq_operation_id("admin_recently_completed_jobs"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Recently completed job list returned.",
    ),
)
def recently_completed_jobs(
    request: Request,
    lookback_seconds: int = DEFAULT_RECENT_LOOKBACK_SECONDS,
    scan_limit: int = DEFAULT_RECENT_SCAN_LIMIT,
    queues: str | None = None,
) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=[ADMIN_SCOPE])
        if _token_allows_admin(claims):
            pass
        else:
            require_roles(claims, ["Admin"])
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine admin recently-completed-jobs auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        queue_names = _parse_queues(queues)
        with _redis_conn() as redis_conn:
            jobs = list_recently_completed_jobs(
                redis_conn,
                queue_names=queue_names,
                lookback_seconds=int(lookback_seconds),
                scan_limit=int(scan_limit),
            )
        _hydrate_submitter_fields(jobs)
        return JSONResponse(
            {
                "generated_at": _utc_iso_now(),
                "lookback_seconds": int(lookback_seconds),
                "scan_limit": int(scan_limit),
                "queues": list(queue_names),
                "jobs": jobs,
            }
        )
    except Exception:
        logger.exception("rq-engine admin recently-completed-jobs failed")
        return error_response_with_traceback("Failed to list recently completed jobs", status_code=500)


@router.get(
    "/admin/jobs-detail",
    summary="List active RQ jobs (admin)",
    description=(
        "Admin-only debugging endpoint. Requires JWT Bearer scope `rq:status` plus role `Admin`/`Root`. "
        "Returns the complete set of started + queued jobs across the default and batch queues."
    ),
    tags=["rq-engine", "jobs"],
    operation_id=rq_operation_id("admin_jobs_detail"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Active job list returned.",
    ),
)
def jobs_detail(request: Request, queues: str | None = None) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=[ADMIN_SCOPE])
        if _token_allows_admin(claims):
            pass
        else:
            require_roles(claims, ["Admin"])
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine admin jobs-detail auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        queue_names = _parse_queues(queues)
        with _redis_conn() as redis_conn:
            jobs = list_active_jobs(redis_conn, queue_names=queue_names)
        _hydrate_submitter_fields(jobs)
        return JSONResponse(
            {
                "generated_at": _utc_iso_now(),
                "queues": list(queue_names),
                "jobs": jobs,
            }
        )
    except Exception:
        logger.exception("rq-engine admin jobs-detail failed")
        return error_response_with_traceback("Failed to list active jobs", status_code=500)


__all__ = ["router"]
