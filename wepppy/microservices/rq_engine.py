"""FastAPI microservice for RQ job polling endpoints."""

from __future__ import annotations

import logging
import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from wepppy.rq.job_info import (
    get_wepppy_rq_job_info,
    get_wepppy_rq_job_status,
    get_wepppy_rq_jobs_info,
)
from wepppy.rq.jobinfo_payloads import extract_job_ids

logger = logging.getLogger(__name__)

app = FastAPI(title="WEPPcloud RQ Engine", version="0.1.0")


def _error_response(message: str) -> JSONResponse:
    stacktrace = traceback.format_exc().splitlines()
    payload = {
        "Success": False,
        "Error": message,
        "StackTrace": stacktrace,
    }
    return JSONResponse(payload, status_code=500)


async def _safe_json(request: Request) -> Any:
    try:
        return await request.json()
    except Exception:
        return None


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "scope": "rq-engine",
    }


@app.get("/api/jobstatus/{job_id}")
def jobstatus(job_id: str):
    try:
        return get_wepppy_rq_job_status(job_id)
    except Exception:
        logger.exception("rq-engine jobstatus failed")
        return _error_response("Error Handling Request")


@app.get("/api/jobinfo/{job_id}")
def jobinfo(job_id: str):
    try:
        return get_wepppy_rq_job_info(job_id)
    except Exception:
        logger.exception("rq-engine jobinfo failed")
        return _error_response("Error Handling Request")


@app.post("/api/jobinfo")
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
        return _error_response("Failed to retrieve batch job info")


__all__ = ["app"]
