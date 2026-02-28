from __future__ import annotations

import logging
import os
import shutil
from os.path import join as _join
from typing import Any

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue
from starlette.datastructures import UploadFile
from werkzeug.utils import secure_filename

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Landuse, WatershedNotAbstractedError
from wepppy.nodb.mods.treatments import Treatments, TreatmentsMode
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as _nodir_resolve
from wepppy.rq.project_rq import build_treatments_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


def _maybe_nodir_error_response(exc: Exception):
    if isinstance(exc, NoDirError):
        return error_response(exc.message, status_code=exc.http_status, code=exc.code)
    return None


def nodir_resolve(_wd: str, _root: str, *, view: str = "effective") -> None:
    return _nodir_resolve(_wd, _root, view=view)


def _require_directory_root(wd: str, root: str) -> None:
    resolved = nodir_resolve(wd, root, view="effective")
    if resolved is not None and getattr(resolved, "form", "dir") != "dir":
        raise NoDirError(
            http_status=409,
            code="NODIR_ARCHIVE_ACTIVE",
            message=f"{root} root is archive-backed; directory root required",
        )


def _extract_upload(form: Any, key: str) -> UploadFile | None:
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


def _preflight_treatments_roots(wd: str) -> None:
    _require_directory_root(wd, "landuse")
    _require_directory_root(wd, "soils")


@router.post(
    "/runs/{runid}/{config}/build-treatments",
    summary="Build treatment inputs",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates treatment configuration/files and asynchronously enqueues treatment building."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("build_treatments"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Treatment inputs accepted and `job_id` returned.",
        extra={
            400: "Treatment validation/business-rule error. Returns the canonical error payload.",
        },
    ),
)
async def build_treatments(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine build-treatments auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        _preflight_treatments_roots(wd)
        treatments = Treatments.getInstance(wd)
        landuse = Landuse.getInstance(wd)
        payload = await parse_request_payload(request)
        mode_value = payload.get("mode")
        if mode_value is None:
            mode_value = payload.get("treatments_mode")
        if mode_value is not None:
            try:
                treatments.mode = int(mode_value)
            except (TypeError, ValueError):
                return error_response("treatments_mode must be an integer", status_code=400)

        if treatments.mode == TreatmentsMode.UserDefinedMap:

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
            except TypeError as exc:
                return error_response(f"Could not obtain filename: {exc}", status_code=400)
            if not filename:
                return error_response("Could not obtain filename", status_code=400)

            user_defined_fn = _join(treatments.treatments_dir, filename)
            try:
                with open(user_defined_fn, "wb") as dest:
                    shutil.copyfileobj(upload.file, dest)
            except OSError:
                logger.exception("rq-engine build-treatments failed to save file", extra={"runid": runid, "config": config})
                return error_response_with_traceback("Could not save file")

            try:
                treatments.validate(user_defined_fn)
            except ValueError as exc:
                return error_response(str(exc), status_code=400)

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_treatments)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(build_treatments_rq, (runid,), timeout=RQ_TIMEOUT)
            prep.set_rq_job_id("build_treatments_rq", job.id)
        return JSONResponse({"job_id": job.id})
    except WatershedNotAbstractedError as exc:
        return error_response(
            exc.__name__ or "Watershed Not Abstracted Error",
            status_code=400,
        )
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine build-treatments enqueue failed")
        return error_response_with_traceback("Building Landuse Failed")


__all__ = ["router"]
