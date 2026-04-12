from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile
from werkzeug.utils import secure_filename

from wepppy.nodb.core import Ron
from wepppy.nodb.mods.baer import Baer
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response
from .upload_helpers import UploadError, save_upload_file, upload_failure, upload_success

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_UPLOAD_SCOPES = ["rq:enqueue"]
UPLOAD_SBS_ALLOWED_EXTENSIONS = ("tif", "tiff", "img", "vrt")
UPLOAD_SBS_MAX_BYTES = 100 * 1024 * 1024
UPLOAD_COVER_TRANSFORM_ALLOWED_EXTENSIONS = ("csv",)
UPLOAD_COVER_TRANSFORM_MAX_BYTES = 10 * 1024 * 1024


def _extract_upload(form, key: str) -> UploadFile | None:
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


def _upload_status_from_message(message: str) -> int:
    if "maximum allowed size" in message.lower():
        return 413
    return 400


def _validation_reason(exc: Exception) -> str:
    detail = str(exc).strip()
    if detail:
        return detail
    return exc.__class__.__name__


@router.post(
    "/runs/{runid}/{config}/tasks/upload-sbs/",
    summary="Upload SBS disturbed map",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Synchronously uploads and validates the disturbed SBS map; no queue enqueue."
    ),
    tags=["rq-engine", "uploads"],
    operation_id=rq_operation_id("upload_sbs"),
    responses=agent_route_responses(
        success_code=200,
        success_description="SBS upload accepted and disturbed map state updated.",
        extra={
            400: "Upload or SBS validation failed. Returns the canonical error payload.",
        },
    ),
)
async def upload_sbs(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_UPLOAD_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine upload-sbs auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        from wepppy.nodb.mods.baer.sbs_map import sbs_map_sanity_check

        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        if "baer" in ron.mods:
            baer = Baer.getInstance(wd)
        else:
            baer = Disturbed.getInstance(wd)

        form = await request.form()
        upload = _extract_upload(form, "input_upload_sbs")
        if upload is None or not upload.filename:
            return upload_failure("input_upload_sbs must be provided")

        filename = secure_filename(upload.filename)
        if not filename:
            return upload_failure("input_upload_sbs must have a valid filename")
        if filename.lower() == "baer.cropped.tif":
            filename = "_baer.cropped.tif"

        dest_dir = Path(baer.baer_dir)
        saved_path = save_upload_file(
            upload,
            allowed_extensions=UPLOAD_SBS_ALLOWED_EXTENSIONS,
            dest_dir=dest_dir,
            filename_transform=lambda value: filename,
            overwrite=True,
            max_bytes=UPLOAD_SBS_MAX_BYTES,
        )

        ret, description = sbs_map_sanity_check(str(saved_path))
        if ret != 0:
            return error_response(description, status_code=400)
        try:
            baer.validate(filename, mode=0)
        except Exception as exc:  # broad-except: validation boundary
            logger.exception("rq-engine upload-sbs validation failed")
            reason = _validation_reason(exc)
            return error_response(f"SBS validation failed: {reason}", status_code=400)
        RedisPrep.getInstance(wd).remove_timestamp(TaskEnum.build_rusle)
        return upload_success(result={"disturbed_fn": baer.disturbed_fn})
    except UploadError as exc:
        return upload_failure(str(exc), status=_upload_status_from_message(str(exc)))
    except Exception as exc:  # broad-except: boundary contract
        logger.exception("rq-engine upload-sbs failed")
        reason = _validation_reason(exc)
        return error_response(f"Upload failed: {reason}", status_code=500)


@router.post(
    "/runs/{runid}/{config}/tasks/upload-cover-transform",
    summary="Upload revegetation cover transform",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Synchronously uploads and validates cover-transform CSV content; no queue enqueue."
    ),
    tags=["rq-engine", "uploads"],
    operation_id=rq_operation_id("upload_cover_transform"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Cover-transform upload accepted.",
        extra={
            400: "Upload or cover-transform validation failed. Returns the canonical error payload.",
        },
    ),
)
async def upload_cover_transform(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_UPLOAD_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine upload-cover-transform auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    try:
        from wepppy.nodb.mods.revegetation import Revegetation

        wd = get_wd(runid)
        form = await request.form()
        upload = _extract_upload(form, "input_upload_cover_transform")
        if upload is None:
            return upload_failure("input_upload_cover_transform must be provided")

        reveg = Revegetation.getInstance(wd)

        saved_path = save_upload_file(
            upload,
            allowed_extensions=UPLOAD_COVER_TRANSFORM_ALLOWED_EXTENSIONS,
            dest_dir=Path(wd) / "revegetation",
            filename_transform=lambda value: value,
            overwrite=True,
            max_bytes=UPLOAD_COVER_TRANSFORM_MAX_BYTES,
        )

        try:
            res = reveg.validate_user_defined_cover_transform(saved_path.name)
        except Exception as exc:  # broad-except: validation boundary
            logger.exception("rq-engine upload-cover-transform validation failed")
            reason = _validation_reason(exc)
            return error_response(f"Cover transform validation failed: {reason}", status_code=400)
        return upload_success(result=res)
    except UploadError as exc:
        return upload_failure(str(exc), status=_upload_status_from_message(str(exc)))
    except Exception as exc:  # broad-except: boundary contract
        logger.exception("rq-engine upload-cover-transform failed")
        reason = _validation_reason(exc)
        return error_response(f"Upload failed: {reason}", status_code=500)


__all__ = ["router"]
