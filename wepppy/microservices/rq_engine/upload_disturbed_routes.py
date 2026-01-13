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
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .responses import error_response, error_response_with_traceback
from .upload_helpers import UploadError, save_upload_file, upload_failure, upload_success

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_UPLOAD_SCOPES = ["rq:enqueue"]


def _extract_upload(form, key: str) -> UploadFile | None:
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


@router.post("/runs/{runid}/{config}/tasks/upload-sbs/")
async def upload_sbs(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_UPLOAD_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine upload-sbs auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

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
            allowed_extensions=(),
            dest_dir=dest_dir,
            filename_transform=lambda value: filename,
            overwrite=True,
        )

        ret, description = sbs_map_sanity_check(str(saved_path))
        if ret != 0:
            return error_response(description, status_code=400)
        baer.validate(filename, mode=0)
        return upload_success(result={"disturbed_fn": baer.disturbed_fn})
    except UploadError as exc:
        return upload_failure(str(exc))
    except Exception:
        logger.exception("rq-engine upload-sbs failed")
        return error_response_with_traceback("Failed validating file", status_code=500)


@router.post("/runs/{runid}/{config}/tasks/upload-cover-transform")
async def upload_cover_transform(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_UPLOAD_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine upload-cover-transform auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        from wepppy.nodb.mods.revegetation import Revegetation

        wd = get_wd(runid)
        reveg = Revegetation.getInstance(wd)

        form = await request.form()
        upload = _extract_upload(form, "input_upload_cover_transform")
        if upload is None:
            return upload_failure("Could not find file")

        saved_path = save_upload_file(
            upload,
            allowed_extensions=("csv",),
            dest_dir=Path(wd) / "revegetation",
            filename_transform=lambda value: value,
            overwrite=True,
        )

        res = reveg.validate_user_defined_cover_transform(saved_path.name)
        return upload_success(result=res)
    except UploadError as exc:
        return upload_failure(str(exc))
    except Exception:
        logger.exception("rq-engine upload-cover-transform failed")
        return error_response_with_traceback("Failed validating file", status_code=500)


__all__ = ["router"]
