from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from wepppy.rq.cancel_job import cancel_jobs
from wepppy.rq.job_info import (
    get_wepppy_rq_job_info,
    get_wepppy_rq_job_status,
    get_wepppy_rq_jobs_info,
)
from wepppy.rq.jobinfo_payloads import extract_job_ids

from .auth import AuthError, require_jwt, require_session_marker
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()


async def _safe_json(request: Request) -> Any:
    try:
        return await request.json()
    except Exception:
        return None


@router.get("/jobstatus/{job_id}")
def jobstatus(job_id: str):
    try:
        payload = get_wepppy_rq_job_status(job_id)
        if payload.get("status") == "not_found":
            return JSONResponse(payload, status_code=status.HTTP_404_NOT_FOUND)
        return payload
    except Exception:
        logger.exception("rq-engine jobstatus failed")
        return error_response_with_traceback("Error Handling Request")


@router.get("/jobinfo/{job_id}")
def jobinfo(job_id: str):
    try:
        payload = get_wepppy_rq_job_info(job_id)
        if payload.get("status") == "not_found":
            return JSONResponse(payload, status_code=status.HTTP_404_NOT_FOUND)
        return payload
    except Exception:
        logger.exception("rq-engine jobinfo failed")
        return error_response_with_traceback("Error Handling Request")


@router.post("/jobinfo")
async def jobinfo_batch(request: Request):
    try:
        payload = await _safe_json(request)
        job_ids = extract_job_ids(payload=payload, query_args=request.query_params)
        if not job_ids:
            return {"jobs": {}, "job_ids": []}

        job_info_map = get_wepppy_rq_jobs_info(job_ids)
        ordered_ids = [job_id for job_id in job_ids if job_id in job_info_map]
        return {"jobs": job_info_map, "job_ids": ordered_ids}
    except Exception:
        logger.exception("rq-engine batch jobinfo failed")
        return error_response_with_traceback("Failed to retrieve batch job info")


@router.post("/canceljob/{job_id}")
def canceljob(job_id: str, request: Request):
    try:
        claims = require_jwt(request, required_scopes=["rq:status"])
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine canceljob auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        job_info = get_wepppy_rq_job_info(job_id)
        if job_info.get("status") == "not_found":
            return error_response("Job not found", status_code=404)

        runid = job_info.get("runid")
        if runid:
            require_session_marker(claims, runid)

        payload = cancel_jobs(job_id)
        if "error" in payload:
            return error_response(payload["error"], status_code=404)
        return payload
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine canceljob failed")
        return error_response_with_traceback("Failed to cancel job")


__all__ = ["router"]
