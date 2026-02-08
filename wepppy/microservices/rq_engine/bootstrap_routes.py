from __future__ import annotations

import logging
import os

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Wepp
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.wepp_rq import run_wepp_noprep_rq, run_wepp_watershed_noprep_rq
from wepppy.rq.swat_rq import run_swat_noprep_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


def _ensure_bootstrap_enabled(wepp: Wepp) -> None:
    if not wepp.bootstrap_enabled:
        raise ValueError("Bootstrap is not enabled for this run")


def _enqueue_no_prep_job(runid: str, *, job_fn, job_key: str, reset_tasks: list[TaskEnum]) -> JSONResponse:
    wd = get_wd(runid)
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


@router.post("/runs/{runid}/{config}/run-wepp-npprep")
async def run_wepp_npprep(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-wepp-npprep auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

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
        return error_response_with_traceback("Error Handling Request")


@router.post("/runs/{runid}/{config}/run-wepp-watershed-no-prep")
async def run_wepp_watershed_noprep(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-wepp-watershed-no-prep auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

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
        return error_response_with_traceback("Error Handling Request")


@router.post("/runs/{runid}/{config}/run-swat-noprep")
async def run_swat_noprep(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-swat-noprep auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

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
        return error_response_with_traceback("Error Handling Request")


__all__ = ["router"]
