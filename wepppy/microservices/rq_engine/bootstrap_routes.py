from __future__ import annotations

import logging
import os
from typing import Any, Mapping

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Wepp
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.swat_rq import run_swat_noprep_rq
from wepppy.rq.wepp_rq import run_wepp_noprep_rq, run_wepp_watershed_noprep_rq
from wepppy.weppcloud.bootstrap.enable_jobs import BootstrapLockBusyError, enqueue_bootstrap_enable
from wepppy.weppcloud.bootstrap.git_lock import (
    acquire_bootstrap_git_lock,
    release_bootstrap_git_lock,
)
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .responses import error_response

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


def _safe_json_load_run(runid: str) -> dict[str, Any] | None:
    try:
        from wepppy.weppcloud.app import Run, app as flask_app
    except Exception:
        logger.exception("Failed to import weppcloud app for bootstrap run lookup")
        return None

    with flask_app.app_context():
        run = Run.query.filter(Run.runid == runid).first()
        if run is None:
            return None
        return {
            "runid": str(run.runid),
            "owner_id": str(run.owner_id) if run.owner_id else None,
            "bootstrap_disabled": bool(getattr(run, "bootstrap_disabled", False)),
        }


def _ensure_bootstrap_eligibility(
    runid: str,
    *,
    require_owner: bool,
    enforce_not_disabled: bool = True,
) -> None:
    run_record = _safe_json_load_run(runid)
    if run_record is None:
        raise ValueError("run not found")
    if enforce_not_disabled and run_record.get("bootstrap_disabled"):
        raise ValueError("bootstrap disabled")
    if require_owner and not run_record.get("owner_id"):
        raise ValueError("anonymous runs cannot enable bootstrap")


def _ensure_bootstrap_enabled(wepp: Wepp) -> None:
    if not wepp.bootstrap_enabled:
        raise ValueError("Bootstrap is not enabled for this run")


def _resolve_bootstrap_actor(claims: Mapping[str, Any]) -> str:
    token_class = str(claims.get("token_class") or "").strip()
    subject = str(claims.get("sub") or "").strip()
    email = str(claims.get("email") or "").strip().lower()
    if token_class and (subject or email):
        identity = email or subject
        return f"{token_class}:{identity}"
    if email:
        return email
    if subject:
        return subject
    return "unknown"


def _job_status_url(job_id: str) -> str:
    return f"/rq-engine/api/jobstatus/{job_id}"


async def _safe_json(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _enqueue_no_prep_job(runid: str, *, job_fn, job_key: str, reset_tasks: list[TaskEnum]) -> JSONResponse:
    wd = get_wd(runid, prefer_active=False)
    wepp = Wepp.getInstance(wd)
    _ensure_bootstrap_enabled(wepp)

    prep = RedisPrep.getInstance(wd)
    for task in reset_tasks:
        prep.remove_timestamp(task)

    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        q = Queue(connection=redis_conn)
        job = q.enqueue_call(job_fn, (runid,), timeout=RQ_TIMEOUT)
        prep.set_rq_job_id(job_key, job.id)
    return JSONResponse({"job_id": job.id})


@router.post("/runs/{runid}/{config}/bootstrap/enable")
async def bootstrap_enable(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine bootstrap-enable auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        _ensure_bootstrap_eligibility(runid, require_owner=True)
        payload, status_code = enqueue_bootstrap_enable(runid, actor=_resolve_bootstrap_actor(claims))
        job_id = str(payload.get("job_id") or "").strip()
        if job_id:
            payload["status_url"] = _job_status_url(job_id)
        return JSONResponse(payload, status_code=status_code)
    except BootstrapLockBusyError as exc:
        return error_response(str(exc), status_code=409, code="conflict")
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        logger.exception("rq-engine bootstrap-enable enqueue failed")
        return error_response("Error Handling Request", status_code=500)


@router.post("/runs/{runid}/{config}/bootstrap/mint-token")
async def bootstrap_mint_token(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine bootstrap mint-token auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        _ensure_bootstrap_eligibility(runid, require_owner=True)
        user_email = str(claims.get("email") or "").strip()
        user_id = str(claims.get("sub") or "").strip()
        if not user_email or not user_id:
            return error_response(
                "User identity claims are required to mint bootstrap tokens",
                status_code=403,
                code="forbidden",
            )

        wd = get_wd(runid, prefer_active=False)
        wepp = Wepp.getInstance(wd)
        _ensure_bootstrap_enabled(wepp)
        return JSONResponse({"clone_url": wepp.mint_bootstrap_jwt(user_email, user_id)})
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        logger.exception("rq-engine bootstrap mint-token failed")
        return error_response("Error Handling Request", status_code=500)


@router.get("/runs/{runid}/{config}/bootstrap/commits")
async def bootstrap_commits(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine bootstrap commits auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        _ensure_bootstrap_eligibility(runid, require_owner=False, enforce_not_disabled=False)
        wd = get_wd(runid, prefer_active=False)
        wepp = Wepp.getInstance(wd)
        _ensure_bootstrap_enabled(wepp)
        return JSONResponse({"commits": wepp.get_bootstrap_commits()})
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        logger.exception("rq-engine bootstrap commits failed")
        return error_response("Error Handling Request", status_code=500)


@router.get("/runs/{runid}/{config}/bootstrap/current-ref")
async def bootstrap_current_ref(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine bootstrap current-ref auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        _ensure_bootstrap_eligibility(runid, require_owner=False, enforce_not_disabled=False)
        wd = get_wd(runid, prefer_active=False)
        wepp = Wepp.getInstance(wd)
        _ensure_bootstrap_enabled(wepp)
        return JSONResponse({"ref": wepp.get_bootstrap_current_ref()})
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        logger.exception("rq-engine bootstrap current-ref failed")
        return error_response("Error Handling Request", status_code=500)


@router.post("/runs/{runid}/{config}/bootstrap/checkout")
async def bootstrap_checkout(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine bootstrap checkout auth failed")
        return error_response("Failed to authorize request", status_code=401)

    payload = await _safe_json(request)
    sha = str(payload.get("sha") or "").strip()
    if not sha:
        return error_response("sha required", status_code=400)

    try:
        _ensure_bootstrap_eligibility(runid, require_owner=False, enforce_not_disabled=False)
        wd = get_wd(runid, prefer_active=False)
        wepp = Wepp.getInstance(wd)
        _ensure_bootstrap_enabled(wepp)

        lock_conn_kwargs = redis_connection_kwargs(RedisDB.LOCK)
        with redis.Redis(**lock_conn_kwargs) as lock_conn:
            lock = acquire_bootstrap_git_lock(
                lock_conn,
                runid=runid,
                operation="checkout",
                actor=_resolve_bootstrap_actor(claims),
            )
            if lock is None:
                return error_response("bootstrap lock busy", status_code=409, code="conflict")
            try:
                if not wepp.checkout_bootstrap_commit(sha):
                    return error_response("checkout failed", status_code=400)
            finally:
                release_bootstrap_git_lock(lock_conn, runid=runid, token=lock.token)
        return JSONResponse({"checked_out": sha})
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        logger.exception("rq-engine bootstrap checkout failed")
        return error_response("Error Handling Request", status_code=500)


@router.post("/runs/{runid}/{config}/run-wepp-npprep")
async def run_wepp_npprep(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-wepp-npprep auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        return _enqueue_no_prep_job(
            runid,
            job_fn=run_wepp_noprep_rq,
            job_key="run_wepp_noprep_rq",
            reset_tasks=[
                TaskEnum.run_wepp_hillslopes,
                TaskEnum.run_wepp_watershed,
                TaskEnum.run_omni_scenarios,
                TaskEnum.run_path_cost_effective,
            ],
        )
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        logger.exception("rq-engine run-wepp-npprep enqueue failed")
        return error_response("Error Handling Request", status_code=500)


@router.post("/runs/{runid}/{config}/run-wepp-watershed-no-prep")
async def run_wepp_watershed_noprep(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-wepp-watershed-no-prep auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        return _enqueue_no_prep_job(
            runid,
            job_fn=run_wepp_watershed_noprep_rq,
            job_key="run_wepp_watershed_noprep_rq",
            reset_tasks=[TaskEnum.run_wepp_watershed],
        )
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        logger.exception("rq-engine run-wepp-watershed-no-prep enqueue failed")
        return error_response("Error Handling Request", status_code=500)


@router.post("/runs/{runid}/{config}/run-swat-noprep")
async def run_swat_noprep(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-swat-noprep auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        return _enqueue_no_prep_job(
            runid,
            job_fn=run_swat_noprep_rq,
            job_key="run_swat_noprep_rq",
            reset_tasks=[],
        )
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception:
        logger.exception("rq-engine run-swat-noprep enqueue failed")
        return error_response("Error Handling Request", status_code=500)


__all__ = ["router"]
