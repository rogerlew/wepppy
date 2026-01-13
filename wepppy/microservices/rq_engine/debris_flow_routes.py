from __future__ import annotations

import logging
import os
from typing import Any

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.project_rq import run_debris_flow_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


def _first_value(value: Any) -> Any:
    if isinstance(value, (list, tuple, set)):
        for candidate in value:
            if candidate not in (None, ""):
                return candidate
        return None
    return value


@router.post("/runs/{runid}/{config}/run-debris-flow")
async def run_debris_flow(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-debris-flow auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        payload = await parse_request_payload(request)

        clay_pct = _first_value(payload.get("clay_pct"))
        liquid_limit = _first_value(payload.get("liquid_limit"))
        datasource = _first_value(payload.get("datasource"))

        if clay_pct is not None:
            try:
                clay_pct = float(clay_pct)
            except (TypeError, ValueError):
                return error_response("clay_pct must be numeric", status_code=400)

        if liquid_limit is not None:
            try:
                liquid_limit = float(liquid_limit)
            except (TypeError, ValueError):
                return error_response("liquid_limit must be numeric", status_code=400)

        if datasource is not None:
            datasource = str(datasource).strip() or None

        wd = get_wd(runid)
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_debris)

        job_kwargs = None
        if any(value is not None for value in (clay_pct, liquid_limit, datasource)):
            job_options: dict[str, Any] = {}
            if clay_pct is not None:
                job_options["clay_pct"] = clay_pct
            if liquid_limit is not None:
                job_options["liquid_limit"] = liquid_limit
            if datasource is not None:
                job_options["datasource"] = datasource
            job_kwargs = {"payload": job_options}

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                run_debris_flow_rq,
                (runid,),
                kwargs=job_kwargs,
                timeout=RQ_TIMEOUT,
            )
            prep.set_rq_job_id("run_debris_flow_rq", job.id)
        return JSONResponse({"job_id": job.id})
    except Exception:
        logger.exception("rq-engine run-debris-flow enqueue failed")
        return error_response_with_traceback("Error Running Debris Flow")


__all__ = ["router"]
