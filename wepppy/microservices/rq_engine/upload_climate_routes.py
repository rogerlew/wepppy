from __future__ import annotations

import logging
import os
from pathlib import Path

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue
from starlette.datastructures import UploadFile

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Climate, Ron
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as _nodir_resolve
from wepppy.runtime_paths.thaw_freeze import maintenance_lock as nodir_maintenance_lock
from wepppy.rq.project_rq import upload_cli_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response, error_response_with_traceback
from .upload_helpers import UploadError, save_upload_file, upload_failure, upload_success

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_UPLOAD_SCOPES = ["rq:enqueue"]
RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))


def _maybe_nodir_error_response(exc: Exception):
    if isinstance(exc, NoDirError):
        return error_response(exc.message, status_code=exc.http_status, code=exc.code)
    return None


def _extract_upload(form, key: str) -> UploadFile | None:
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


def mutate_root(
    wd: str,
    root: str,
    callback,
    *,
    purpose: str = "rq-upload",
):
    _require_directory_root(wd, root)
    with nodir_maintenance_lock(wd, root, purpose=purpose):
        _require_directory_root(wd, root)
        return callback()


def nodir_resolve(wd: str, root: str, *, view: str = "effective"):
    return _nodir_resolve(wd, root, view=view)


def _require_directory_root(wd: str, root: str) -> None:
    resolved = nodir_resolve(wd, root, view="effective")
    if resolved is not None and getattr(resolved, "form", "dir") != "dir":
        raise NoDirError(
            http_status=409,
            code="NODIR_ARCHIVE_ACTIVE",
            message=f"{root} root is archive-backed; directory root required",
        )


@router.post(
    "/runs/{runid}/{config}/tasks/upload-cli/",
    summary="Upload climate file and enqueue validation",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Synchronously saves uploaded `.cli` input, then asynchronously enqueues climate upload validation."
    ),
    tags=["rq-engine", "uploads"],
    operation_id=rq_operation_id("upload_cli"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Upload accepted and climate upload `job_id` returned.",
        extra={
            400: "Upload validation failed. Returns the canonical error payload.",
        },
    ),
)
async def upload_cli(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_UPLOAD_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine upload-cli auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        _require_directory_root(wd, "climate")
        Ron.getInstance(wd)
        climate = Climate.getInstance(wd)

        form = await request.form()
        upload = _extract_upload(form, "input_upload_cli")
        if upload is None:
            return upload_failure("Could not find file")

        saved_path = mutate_root(
            wd,
            "climate",
            lambda: save_upload_file(
                upload,
                allowed_extensions=("cli",),
                dest_dir=Path(climate.cli_dir),
                filename_transform=lambda value: value,
                overwrite=True,
            ),
            purpose="rq-upload-cli-save",
        )
    except UploadError as exc:
        return upload_failure(str(exc))
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine upload-cli save failed")
        return error_response_with_traceback("Could not save file", status_code=500)

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_climate)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(upload_cli_rq, (runid, saved_path.name), timeout=RQ_TIMEOUT)
            prep.set_rq_job_id("upload_cli_rq", job.id)
        return upload_success(job_id=job.id)
    except UploadError as exc:
        return upload_failure(str(exc))
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine upload-cli enqueue failed")
        return error_response_with_traceback("Failed validating file", status_code=500)


__all__ = ["router"]
