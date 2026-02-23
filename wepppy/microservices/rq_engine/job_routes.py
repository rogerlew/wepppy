from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Request, status

from wepppy.rq.cancel_job import cancel_jobs
from wepppy.rq.job_info import (
    get_wepppy_rq_job_info,
    get_wepppy_rq_job_status,
    get_wepppy_rq_jobs_info,
)
from wepppy.rq.jobinfo_payloads import extract_job_ids

from .auth import AuthError, require_jwt, require_session_marker
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

POLL_SCOPE = "rq:status"
CANCELJOB_SCOPES = ("rq:status", "culvert:batch:submit")
POLL_AUTH_MODE_ENV = "RQ_ENGINE_POLL_AUTH_MODE"
POLL_AUTH_MODES = {"open", "token_optional", "required"}
POLL_RATE_LIMIT_COUNT_ENV = "RQ_ENGINE_POLL_RATE_LIMIT_COUNT"
POLL_RATE_LIMIT_WINDOW_ENV = "RQ_ENGINE_POLL_RATE_LIMIT_WINDOW_SECONDS"
SCOPE_MISSING_PREFIX = "Token missing required scope(s):"

_POLL_RATE_LIMIT_LOCK = threading.Lock()
_POLL_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = {}


def _safe_int_env(name: str, *, default: int, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return max(minimum, parsed)


def _poll_auth_mode() -> str:
    mode = (os.getenv(POLL_AUTH_MODE_ENV) or "open").strip().lower()
    if mode not in POLL_AUTH_MODES:
        return "open"
    return mode


def _poll_rate_limit_count() -> int:
    return _safe_int_env(POLL_RATE_LIMIT_COUNT_ENV, default=400, minimum=1)


def _poll_rate_limit_window_seconds() -> int:
    return _safe_int_env(POLL_RATE_LIMIT_WINDOW_ENV, default=60, minimum=1)


def _poll_client_ip(request: Request) -> str:
    forwarded_for = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _poll_caller(claims: Mapping[str, Any] | None) -> str:
    if claims is None:
        return "anonymous"
    for key in ("sub", "session_id", "email"):
        value = claims.get(key)
        if value:
            return str(value)
    return "authenticated"


def _audit_polling_request(
    *,
    endpoint: str,
    request: Request,
    claims: Mapping[str, Any] | None,
    job_id: str,
    status_code: int,
    success: bool,
    reason: str,
) -> None:
    logger.info(
        "rq_engine_poll_audit endpoint=%s status_code=%s success=%s reason=%s auth_mode=%s job_id=%s caller=%s ip=%s",
        endpoint,
        status_code,
        success,
        reason,
        _poll_auth_mode(),
        job_id,
        _poll_caller(claims),
        _poll_client_ip(request),
    )


def _authorize_polling_request(request: Request) -> Mapping[str, Any] | None:
    mode = _poll_auth_mode()
    if mode == "open":
        return None

    has_authorization = bool((request.headers.get("Authorization") or "").strip())
    if mode == "token_optional" and not has_authorization:
        return None

    return require_jwt(request, required_scopes=[POLL_SCOPE])


def _is_scope_missing_error(exc: AuthError) -> bool:
    return (
        exc.status_code == status.HTTP_403_FORBIDDEN
        and exc.code == "forbidden"
        and exc.message.startswith(SCOPE_MISSING_PREFIX)
    )


def _authorize_cancel_request(request: Request) -> Mapping[str, Any]:
    for scope in CANCELJOB_SCOPES:
        try:
            return require_jwt(request, required_scopes=[scope])
        except AuthError as exc:
            if _is_scope_missing_error(exc):
                continue
            raise

    raise AuthError(
        f"Token missing required scope(s): {' or '.join(CANCELJOB_SCOPES)}",
        status_code=403,
        code="forbidden",
    )


def _is_poll_rate_limited(endpoint: str, *, request: Request, claims: Mapping[str, Any] | None) -> tuple[bool, int, int]:
    limit_count = _poll_rate_limit_count()
    window_seconds = _poll_rate_limit_window_seconds()
    caller = _poll_caller(claims)
    ip_address = _poll_client_ip(request)
    bucket_key = f"{endpoint}:{caller}:{ip_address}"

    now = time.monotonic()
    cutoff = now - float(window_seconds)

    with _POLL_RATE_LIMIT_LOCK:
        bucket = _POLL_RATE_LIMIT_BUCKETS.setdefault(bucket_key, deque())
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= limit_count:
            return True, limit_count, window_seconds

        bucket.append(now)
        return False, limit_count, window_seconds


async def _safe_json(request: Request) -> Any:
    try:
        return await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _polling_guard(
    *, endpoint: str, request: Request, job_id: str
) -> tuple[Mapping[str, Any] | None, Any | None]:
    claims: Mapping[str, Any] | None = None

    try:
        claims = _authorize_polling_request(request)
    except AuthError as exc:
        _audit_polling_request(
            endpoint=endpoint,
            request=request,
            claims=claims,
            job_id=job_id,
            status_code=exc.status_code,
            success=False,
            reason=exc.code,
        )
        return None, error_response(exc.message, status_code=exc.status_code, code=exc.code)

    limited, limit_count, window_seconds = _is_poll_rate_limited(endpoint, request=request, claims=claims)
    if limited:
        details = f"Rate limit exceeded: {limit_count} requests per {window_seconds} seconds."
        _audit_polling_request(
            endpoint=endpoint,
            request=request,
            claims=claims,
            job_id=job_id,
            status_code=429,
            success=False,
            reason="rate_limited",
        )
        return None, error_response(
            "Too many polling requests",
            status_code=429,
            code="rate_limited",
            details=details,
        )

    return claims, None


@router.get(
    "/jobstatus/{job_id}",
    summary="Get job status",
    description=(
        "Read-only polling endpoint. Open by default (`RQ_ENGINE_POLL_AUTH_MODE=open`); "
        "token modes validate JWT scope `rq:status`. Applies in-memory poll rate limiting."
    ),
    tags=["rq-engine", "jobs"],
    operation_id=rq_operation_id("jobstatus"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Job status payload returned.",
        extra={
            404: "Job not found. Returns the canonical error payload.",
            429: "Polling rate limit exceeded. Returns the canonical error payload.",
        },
    ),
)
def jobstatus(job_id: str, request: Request):
    claims, guard_response = _polling_guard(endpoint="jobstatus", request=request, job_id=job_id)
    if guard_response is not None:
        return guard_response

    try:
        payload = get_wepppy_rq_job_status(job_id)
        if payload.get("status") == "not_found":
            _audit_polling_request(
                endpoint="jobstatus",
                request=request,
                claims=claims,
                job_id=job_id,
                status_code=status.HTTP_404_NOT_FOUND,
                success=False,
                reason="not_found",
            )
            return error_response(
                "Job not found",
                status_code=status.HTTP_404_NOT_FOUND,
                code="not_found",
                details=f"Job {job_id} not found.",
            )

        _audit_polling_request(
            endpoint="jobstatus",
            request=request,
            claims=claims,
            job_id=job_id,
            status_code=200,
            success=True,
            reason="ok",
        )
        return payload
    except Exception:
        logger.exception("rq-engine jobstatus failed")
        _audit_polling_request(
            endpoint="jobstatus",
            request=request,
            claims=claims,
            job_id=job_id,
            status_code=500,
            success=False,
            reason="exception",
        )
        return error_response_with_traceback("Error Handling Request")


@router.get(
    "/jobinfo/{job_id}",
    summary="Get job info",
    description=(
        "Read-only polling endpoint. Open by default (`RQ_ENGINE_POLL_AUTH_MODE=open`); "
        "token modes validate JWT scope `rq:status`. Applies in-memory poll rate limiting."
    ),
    tags=["rq-engine", "jobs"],
    operation_id=rq_operation_id("jobinfo"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Detailed job info payload returned.",
        extra={
            404: "Job not found. Returns the canonical error payload.",
            429: "Polling rate limit exceeded. Returns the canonical error payload.",
        },
    ),
)
def jobinfo(job_id: str, request: Request):
    claims, guard_response = _polling_guard(endpoint="jobinfo", request=request, job_id=job_id)
    if guard_response is not None:
        return guard_response

    try:
        payload = get_wepppy_rq_job_info(job_id)
        if payload.get("status") == "not_found":
            _audit_polling_request(
                endpoint="jobinfo",
                request=request,
                claims=claims,
                job_id=job_id,
                status_code=status.HTTP_404_NOT_FOUND,
                success=False,
                reason="not_found",
            )
            return error_response(
                "Job not found",
                status_code=status.HTTP_404_NOT_FOUND,
                code="not_found",
                details=f"Job {job_id} not found.",
            )

        _audit_polling_request(
            endpoint="jobinfo",
            request=request,
            claims=claims,
            job_id=job_id,
            status_code=200,
            success=True,
            reason="ok",
        )
        return payload
    except Exception:
        logger.exception("rq-engine jobinfo failed")
        _audit_polling_request(
            endpoint="jobinfo",
            request=request,
            claims=claims,
            job_id=job_id,
            status_code=500,
            success=False,
            reason="exception",
        )
        return error_response_with_traceback("Error Handling Request")


@router.post(
    "/jobinfo",
    summary="Get batch job info",
    description=(
        "Read-only polling endpoint for multiple job IDs. Open by default "
        "(`RQ_ENGINE_POLL_AUTH_MODE=open`); token modes validate JWT scope `rq:status`. "
        "Applies in-memory poll rate limiting."
    ),
    tags=["rq-engine", "jobs"],
    operation_id=rq_operation_id("jobinfo_batch"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Batch job info payload returned.",
        extra={
            429: "Polling rate limit exceeded. Returns the canonical error payload.",
        },
    ),
)
async def jobinfo_batch(request: Request):
    claims, guard_response = _polling_guard(endpoint="jobinfo_batch", request=request, job_id="batch")
    if guard_response is not None:
        return guard_response

    try:
        payload = await _safe_json(request)
        job_ids = extract_job_ids(payload=payload, query_args=request.query_params)
        if not job_ids:
            _audit_polling_request(
                endpoint="jobinfo_batch",
                request=request,
                claims=claims,
                job_id="batch",
                status_code=200,
                success=True,
                reason="empty",
            )
            return {"jobs": {}, "job_ids": []}

        job_info_map = get_wepppy_rq_jobs_info(job_ids)
        ordered_ids = [job_id for job_id in job_ids if job_id in job_info_map]
        _audit_polling_request(
            endpoint="jobinfo_batch",
            request=request,
            claims=claims,
            job_id=f"batch:{len(job_ids)}",
            status_code=200,
            success=True,
            reason="ok",
        )
        return {"jobs": job_info_map, "job_ids": ordered_ids}
    except Exception:
        logger.exception("rq-engine batch jobinfo failed")
        _audit_polling_request(
            endpoint="jobinfo_batch",
            request=request,
            claims=claims,
            job_id="batch",
            status_code=500,
            success=False,
            reason="exception",
        )
        return error_response_with_traceback("Failed to retrieve batch job info")


@router.post(
    "/canceljob/{job_id}",
    summary="Cancel a queued or running job",
    description=(
        "Requires JWT Bearer scope `rq:status` or `culvert:batch:submit`. If job metadata contains a run ID, "
        "enforces session marker access for that run. Synchronously cancels existing job(s); no enqueue."
    ),
    tags=["rq-engine", "jobs"],
    operation_id=rq_operation_id("canceljob"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Cancellation request accepted and current job cancellation status returned.",
        extra={
            404: "Job not found. Returns the canonical error payload.",
        },
    ),
)
def canceljob(job_id: str, request: Request):
    try:
        claims = _authorize_cancel_request(request)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine canceljob auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        job_info = get_wepppy_rq_job_info(job_id)
        if job_info.get("status") == "not_found":
            return error_response(
                "Job not found",
                status_code=404,
                code="not_found",
                details=f"Job {job_id} not found.",
            )

        runid = job_info.get("runid")
        if runid:
            require_session_marker(claims, runid)

        payload = cancel_jobs(job_id)
        if "error" in payload:
            return error_response(
                payload["error"],
                status_code=404,
                code="not_found",
                details=str(payload["error"]),
            )
        return payload
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine canceljob failed")
        return error_response_with_traceback("Failed to cancel job")


__all__ = ["router"]
