from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import redis
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.land_and_soil_rq import land_and_soil_rq

from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
LANDUSE_ARCHIVE_ROOTS = (
    Path("/wc1/land_and_soil_rq"),
    Path("/geodata/wc1/land_and_soil_rq"),
)


async def _safe_json(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except (UnicodeDecodeError, ValueError, RuntimeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_archive_path(job_id: str) -> Path | None:
    filename = f"{job_id}.tar.gz"
    for root in LANDUSE_ARCHIVE_ROOTS:
        candidate = root / filename
        if candidate.is_file():
            return candidate
    return None


@router.post("/landuse-and-soils")
async def build_landuse_and_soils(request: Request) -> JSONResponse:
    try:
        payload = await _safe_json(request)
        extent = payload.get("extent")
        if extent is None:
            return error_response("Expecting extent", status_code=400)

        cfg = payload.get("cfg")
        nlcd_db = payload.get("nlcd_db")
        ssurgo_db = payload.get("ssurgo_db")

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                land_and_soil_rq,
                (None, extent, cfg, nlcd_db, ssurgo_db),
                timeout=RQ_TIMEOUT,
            )
    except Exception:
        logger.exception("rq-engine landuse/soils enqueue failed")
        return error_response_with_traceback("land_and_soil_rq Failed")

    return JSONResponse({"job_id": job.id})


@router.get("/landuse-and-soils/{job_id}.tar.gz")
def download_landuse_and_soils(job_id: str):
    if "." in job_id or "/" in job_id:
        return error_response("Invalid uuid", status_code=400)

    archive_path = _resolve_archive_path(job_id)
    if archive_path is None:
        return error_response("File not found", status_code=404)

    return FileResponse(
        archive_path,
        media_type="application/gzip",
        filename=f"{job_id}.tar.gz",
    )


__all__ = ["router"]
