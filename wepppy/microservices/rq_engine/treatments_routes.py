from __future__ import annotations

import logging
import os
import shutil
from os.path import exists as _exists
from os.path import join as _join
from typing import Any

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue
from starlette.datastructures import UploadFile
from werkzeug.utils import secure_filename

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Landuse, Watershed, WatershedNotAbstractedError
from wepppy.nodb.mods.treatments import Treatments, TreatmentsMode
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.project_rq import build_landuse_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


def _extract_upload(form: Any, key: str) -> UploadFile | None:
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


@router.post("/runs/{runid}/{config}/build-treatments")
async def build_treatments(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine build-treatments auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        treatments = Treatments.getInstance(wd)
        landuse = Landuse.getInstance(wd)

        if treatments.mode == TreatmentsMode.UserDefinedMap:
            watershed = Watershed.getInstance(wd)
            payload = await parse_request_payload(request)

            def _first(value: Any) -> Any:
                if isinstance(value, (list, tuple)):
                    return value[0] if value else None
                return value

            mapping = _first(payload.get("landuse_management_mapping_selection"))
            if isinstance(mapping, str):
                mapping = mapping.strip() or None
            if mapping is None:
                return error_response(
                    "landuse_management_mapping_selection must be provided",
                    status_code=400,
                )
            landuse.mapping = mapping

            form = await request.form()
            upload = _extract_upload(form, "input_upload_landuse")
            if upload is None:
                return error_response("Could not find file", status_code=400)
            if not upload.filename:
                return error_response("no filename specified", status_code=400)

            try:
                filename = secure_filename(upload.filename)
            except Exception:
                return error_response_with_traceback("Could not obtain filename", status_code=400)
            if not filename:
                return error_response("Could not obtain filename", status_code=400)

            user_defined_fn = _join(landuse.lc_dir, f"_{filename}")
            try:
                with open(user_defined_fn, "wb") as dest:
                    shutil.copyfileobj(upload.file, dest)
            except Exception:
                return error_response_with_traceback("Could not save file")

            try:
                from wepppy.all_your_base.geo import raster_stacker

                raster_stacker(user_defined_fn, watershed.subwta, landuse.lc_fn)
            except Exception:
                return error_response_with_traceback(
                    "Failed validating file", status_code=400
                )

            if not _exists(landuse.lc_fn):
                return error_response("Failed creating landuse file", status_code=400)

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_landuse)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(build_landuse_rq, (runid,), timeout=RQ_TIMEOUT)
            prep.set_rq_job_id("build_landuse_rq", job.id)
        return JSONResponse({"job_id": job.id})
    except WatershedNotAbstractedError as exc:
        return error_response(
            exc.__name__ or "Watershed Not Abstracted Error",
            status_code=400,
        )
    except Exception:
        logger.exception("rq-engine build-treatments enqueue failed")
        return error_response_with_traceback("Building Landuse Failed")


__all__ = ["router"]
