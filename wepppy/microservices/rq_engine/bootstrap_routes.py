from __future__ import annotations

import logging
import os
from collections.abc import Sequence
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
from wepppy.weppcloud.bootstrap.api_shared import (
    BootstrapOperationError,
    bootstrap_checkout_operation,
    bootstrap_commits_operation,
    bootstrap_current_ref_operation,
    enable_bootstrap_operation,
    mint_bootstrap_token_operation,
)
from wepppy.weppcloud.utils.auth_tokens import get_jwt_config
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .responses import error_response

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]

BOOTSTRAP_ENABLE_SCOPE = "bootstrap:enable"
BOOTSTRAP_TOKEN_MINT_SCOPE = "bootstrap:token:mint"
BOOTSTRAP_READ_SCOPE = "bootstrap:read"
BOOTSTRAP_CHECKOUT_SCOPE = "bootstrap:checkout"


def _extract_scopes(claims: Mapping[str, Any]) -> set[str]:
    raw = claims.get("scope")
    separator = get_jwt_config().scope_separator

    def _split_scope_text(text: str) -> set[str]:
        parts: list[str] = []
        for chunk in text.split(separator):
            parts.extend(chunk.split())
        return {part for part in parts if part}

    if raw is None:
        return set()
    if isinstance(raw, str):
        return _split_scope_text(raw)
    if isinstance(raw, Sequence):
        scopes: set[str] = set()
        for item in raw:
            if isinstance(item, str):
                scopes.update(_split_scope_text(item))
        return scopes
    return set()


def _require_bootstrap_claims(request: Request, *, required_scope: str) -> Mapping[str, Any]:
    claims = require_jwt(request)
    scopes = _extract_scopes(claims)
    if required_scope in scopes:
        return claims

    raise AuthError(f"Token missing required scope(s): {required_scope}", status_code=403, code="forbidden")


def _authorize_bootstrap_request(request: Request, *, runid: str, required_scope: str) -> Mapping[str, Any]:
    claims = _require_bootstrap_claims(request, required_scope=required_scope)
    authorize_run_access(claims, runid)
    return claims


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
        claims = _authorize_bootstrap_request(request, runid=runid, required_scope=BOOTSTRAP_ENABLE_SCOPE)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine bootstrap-enable auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        result = enable_bootstrap_operation(
            runid,
            actor=_resolve_bootstrap_actor(claims),
        )
        return JSONResponse(result.payload, status_code=result.status_code)
    except BootstrapOperationError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine bootstrap-enable enqueue failed")
        return error_response("Error Handling Request", status_code=500)


@router.post("/runs/{runid}/{config}/bootstrap/mint-token")
async def bootstrap_mint_token(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = _authorize_bootstrap_request(request, runid=runid, required_scope=BOOTSTRAP_TOKEN_MINT_SCOPE)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine bootstrap mint-token auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        result = mint_bootstrap_token_operation(
            runid,
            user_email=str(claims.get("email") or "").strip(),
            user_id=str(claims.get("sub") or "").strip(),
        )
        return JSONResponse(result.payload, status_code=result.status_code)
    except BootstrapOperationError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine bootstrap mint-token failed")
        return error_response("Error Handling Request", status_code=500)


@router.get("/runs/{runid}/{config}/bootstrap/commits")
async def bootstrap_commits(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        _authorize_bootstrap_request(request, runid=runid, required_scope=BOOTSTRAP_READ_SCOPE)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine bootstrap commits auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        result = bootstrap_commits_operation(runid)
        return JSONResponse(result.payload, status_code=result.status_code)
    except BootstrapOperationError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine bootstrap commits failed")
        return error_response("Error Handling Request", status_code=500)


@router.get("/runs/{runid}/{config}/bootstrap/current-ref")
async def bootstrap_current_ref(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        _authorize_bootstrap_request(request, runid=runid, required_scope=BOOTSTRAP_READ_SCOPE)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine bootstrap current-ref auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        result = bootstrap_current_ref_operation(runid)
        return JSONResponse(result.payload, status_code=result.status_code)
    except BootstrapOperationError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine bootstrap current-ref failed")
        return error_response("Error Handling Request", status_code=500)


@router.post("/runs/{runid}/{config}/bootstrap/checkout")
async def bootstrap_checkout(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = _authorize_bootstrap_request(request, runid=runid, required_scope=BOOTSTRAP_CHECKOUT_SCOPE)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine bootstrap checkout auth failed")
        return error_response("Failed to authorize request", status_code=401)

    payload = await _safe_json(request)
    try:
        result = bootstrap_checkout_operation(
            runid,
            sha=payload.get("sha"),
            actor=_resolve_bootstrap_actor(claims),
        )
        return JSONResponse(result.payload, status_code=result.status_code)
    except BootstrapOperationError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
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
