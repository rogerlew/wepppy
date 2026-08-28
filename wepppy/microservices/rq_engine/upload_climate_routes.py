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
from wepppy.nodb.project_config_capabilities import (
    BuilderRegistryUnavailableError,
    LocaleAuthorityInvalidError,
    resolve_run_capability_authority,
)
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as _nodir_resolve
from wepppy.runtime_paths.thaw_freeze import maintenance_lock as nodir_maintenance_lock
from wepppy.rq.project_rq import build_climate_rq, upload_cli_rq
from wepppy.rq.submission_recovery import RqSubmissionConflict, enqueue_tracked_rq_job
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response, error_response_with_traceback
from .upload_helpers import UploadError, save_upload_file, upload_failure, upload_success

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_UPLOAD_SCOPES = ["rq:enqueue"]
RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
UPLOAD_CLI_ALLOWED_EXTENSIONS = ("cli",)
UPLOAD_CLI_MAX_BYTES = 25 * 1024 * 1024


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
        try:
            authority = resolve_run_capability_authority(climate).graph
        except LocaleAuthorityInvalidError as exc:
            return error_response(
                "Run locale authority is invalid.",
                status_code=409,
                code="locale_authority_invalid",
                details=str(exc),
            )
        except BuilderRegistryUnavailableError as exc:
            response = error_response(
                "Builder registry is unavailable.",
                status_code=503,
                code="builder_registry_error",
                details=str(exc),
            )
            response.headers["Retry-After"] = "5"
            return response
        except ValueError as exc:
            return error_response(
                "Project capability authority is invalid.",
                status_code=409,
                code="capability_authority_invalid",
                details=str(exc),
            )
        if authority is not None and "user_defined_cli" not in authority.climate_datasets:
            return error_response(
                "User-defined climate is not supported by this project.",
                status_code=400,
                code="unsupported_capability",
                details="capabilities.climate_datasets does not allow user_defined_cli",
            )

        form = await request.form()
        upload = _extract_upload(form, "input_upload_cli")
        if upload is None:
            return upload_failure("input_upload_cli must be provided")

        saved_path = mutate_root(
            wd,
            "climate",
            lambda: save_upload_file(
                upload,
                allowed_extensions=UPLOAD_CLI_ALLOWED_EXTENSIONS,
                dest_dir=Path(climate.cli_dir),
                filename_transform=lambda value: value,
                overwrite=True,
                max_bytes=UPLOAD_CLI_MAX_BYTES,
            ),
            purpose="rq-upload-cli-save",
        )
    except UploadError as exc:
        return upload_failure(str(exc), status=int(getattr(exc, "status_code", 400)))
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
            job = enqueue_tracked_rq_job(
                q,
                upload_cli_rq,
                prep=prep,
                job_key="upload_cli_rq",
                runid=runid,
                args=(runid, saved_path.name),
                timeout=RQ_TIMEOUT,
                conflict_keys=("build_climate_rq", "upload_cli_rq"),
                allowed_root_funcs=(build_climate_rq, upload_cli_rq),
            )
        return upload_success(job_id=job.id)
    except RqSubmissionConflict as exc:
        return error_response(str(exc), status_code=409, code="job_active")
    except UploadError as exc:
        return upload_failure(str(exc), status=int(getattr(exc, "status_code", 400)))
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine upload-cli enqueue failed")
        return error_response_with_traceback("Failed validating file", status_code=500)


__all__ = ["router"]
