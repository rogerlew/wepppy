from __future__ import annotations

import logging
import os

import redis
from .payloads import PayloadRoute
from wepppy.request_payload import RequestPayloadError

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.project_rq import run_rhem_rq
from wepppy.rq.submission_recovery import RqSubmissionConflict, enqueue_tracked_rq_job
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback
from .webhooks import reject_unsupported as reject_unsupported_webhook

logger = logging.getLogger(__name__)

router = APIRouter(route_class=PayloadRoute)

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


@router.post(
    "/runs/{runid}/{config}/run-rhem",
    summary="Run RHEM model",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates RHEM run flags from payload and asynchronously enqueues RHEM processing."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("run_rhem"),
    responses=agent_route_responses(
        success_code=200,
        success_description="RHEM job accepted and `job_id` returned.",
    ),
)
async def run_rhem(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine run-rhem auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    webhook_error = await reject_unsupported_webhook(request)
    if webhook_error is not None:
        return webhook_error

    try:
        wd = get_wd(runid)
        payload = await parse_request_payload(
            request,
            blank_false_fields=("clean", "prep", "run", "clean_hillslopes", "prep_hillslopes", "run_hillslopes"),
            boolean_fields=(
                "clean",
                "clean_hillslopes",
                "prep",
                "prep_hillslopes",
                "run",
                "run_hillslopes",
            ),
        )

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_rhem)

        job_kwargs = {"payload": payload} if payload else None

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = enqueue_tracked_rq_job(
                q,
                run_rhem_rq,
                prep=prep,
                job_key="run_rhem_rq",
                runid=runid,
                args=(runid,),
                kwargs=job_kwargs,
                timeout=RQ_TIMEOUT,
            )
        return JSONResponse({"job_id": job.id})
    except RqSubmissionConflict as exc:
        return error_response(str(exc), status_code=409, code="conflict")
    except RequestPayloadError:
        raise
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine run-rhem enqueue failed")
        return error_response_with_traceback("Error Running RHEM")


__all__ = ["router"]
