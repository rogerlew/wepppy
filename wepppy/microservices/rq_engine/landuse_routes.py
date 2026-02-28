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
from wepppy.nodb.core import Landuse, LanduseMode, Watershed, WatershedNotAbstractedError
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as _nodir_resolve
from wepppy.runtime_paths.thaw_freeze import maintenance_lock as nodir_maintenance_lock
from wepppy.rq.project_rq import build_landuse_rq
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


def mutate_root(
    wd: str,
    root: str,
    callback,
    *,
    purpose: str = "rq-landuse",
):
    _require_directory_root(wd, root)
    with nodir_maintenance_lock(wd, root, purpose=purpose):
        _require_directory_root(wd, root)
        return callback()


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


def _preflight_landuse_mutation_root(wd: str) -> None:
    _require_directory_root(wd, "landuse")


@router.post(
    "/runs/{runid}/{config}/build-landuse",
    summary="Build landuse inputs",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates landuse settings/files and, outside batch mode, asynchronously enqueues landuse building."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("build_landuse"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Landuse inputs accepted; returns batch update message or enqueued `job_id`.",
        extra={
            400: "Landuse validation/business-rule error (including upload validation). Returns the canonical error payload.",
        },
    ),
)
async def build_landuse(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine build-landuse auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        _preflight_landuse_mutation_root(wd)
        landuse = Landuse.getInstance(wd)

        payload = await parse_request_payload(
            request,
            boolean_fields=(
                "checkbox_burn_shrubs",
                "checkbox_burn_grass",
                "burn_shrubs",
                "burn_grass",
            ),
        )

        def _first(value: Any) -> Any:
            if isinstance(value, (list, tuple)):
                return value[0] if value else None
            return value

        try:
            landuse.parse_inputs(payload)
        except ValueError as exc:
            return error_response(str(exc), status_code=400)

        if "disturbed" in landuse.mods:
            disturbed = Disturbed.getInstance(wd)
            burn_shrubs_value = payload.get("checkbox_burn_shrubs")
            if burn_shrubs_value is None:
                burn_shrubs_value = payload.get("burn_shrubs")
            disturbed.burn_shrubs = bool(burn_shrubs_value)

            burn_grass_value = payload.get("checkbox_burn_grass")
            if burn_grass_value is None:
                burn_grass_value = payload.get("burn_grass")
            disturbed.burn_grass = bool(burn_grass_value)

        mapping = _first(payload.get("landuse_management_mapping_selection"))
        if isinstance(mapping, str):
            mapping = mapping.strip() or None

        if landuse.mode == LanduseMode.UserDefined:
            from wepppy.all_your_base.geo import raster_stacker

            watershed = Watershed.getInstance(wd)
            if mapping is None:
                return error_response(
                    "landuse_management_mapping_selection must be provided",
                    status_code=400,
                )
            landuse.mapping = mapping

            form = await request.form()
            upload = _extract_upload(form, "input_upload_landuse")
            filename: str | None = None
            user_defined_fn: str | None = None

            def _mutate_landuse_user_defined() -> None:
                nonlocal filename
                nonlocal user_defined_fn

                if upload is not None:
                    if not upload.filename:
                        raise ValueError("no filename specified")

                    filename = secure_filename(upload.filename)
                    if not filename:
                        raise ValueError("Could not obtain filename")

                    user_defined_fn = _join(landuse.lc_dir, f"_{filename}")
                    with open(user_defined_fn, "wb") as dest:
                        shutil.copyfileobj(upload.file, dest)
                else:
                    filename = landuse.user_defined_landcover_fn
                    if filename:
                        user_defined_fn = _join(landuse.lc_dir, f"_{filename}")
                    if not filename or not user_defined_fn or not _exists(user_defined_fn):
                        raise FileNotFoundError("Could not find file")

                raster_stacker(user_defined_fn, watershed.subwta, landuse.lc_fn)

                if not _exists(landuse.lc_fn):
                    raise RuntimeError("Failed creating landuse file")
                if filename:
                    landuse.user_defined_landcover_fn = filename

            try:
                mutate_root(
                    wd,
                    "landuse",
                    _mutate_landuse_user_defined,
                    purpose="rq-build-landuse-user-defined",
                )
            except ValueError as exc:
                return error_response(str(exc), status_code=400)
            except FileNotFoundError as exc:
                return error_response(str(exc), status_code=400)
            except RuntimeError as exc:
                return error_response(str(exc), status_code=400)

        if landuse.run_group == "batch":
            return JSONResponse({"message": "Set landuse inputs for batch processing"})

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
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine build-landuse enqueue failed")
        return error_response_with_traceback("Building Landuse Failed")


__all__ = ["router"]
