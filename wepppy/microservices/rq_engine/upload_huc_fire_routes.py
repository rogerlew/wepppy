from __future__ import annotations

import logging
import os
from pathlib import Path
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.datastructures import UploadFile
from werkzeug.utils import secure_filename

from wepppy.nodb.core import Ron
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.weppcloud.user_preferences import (
    PreferenceIdentityError,
    PreferenceValidationError,
    RunRegistrationReceipt,
    StoredPreferenceError,
    apply_creation_preference_overrides,
    cleanup_new_run_directory,
    delete_registered_run,
    register_owned_run,
    resolve_creation_preferences,
)

from .auth import AuthError, require_jwt
from .responses import error_response
from .upload_helpers import UploadError, save_upload_file, upload_failure

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_UPLOAD_SCOPES = ["rq:enqueue"]
UPLOAD_HUC_FIRE_SBS_ALLOWED_EXTENSIONS = ("tif", "tiff", "img", "vrt")
UPLOAD_HUC_FIRE_SBS_MAX_BYTES = 100 * 1024 * 1024


def _extract_upload(form, key: str) -> UploadFile | None:
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


def _cleanup_failed_run(
    receipt: RunRegistrationReceipt | None,
    runid: str,
    wd: str,
    error_id: str,
) -> None:
    if receipt is not None:
        try:
            delete_registered_run(receipt)
        except (PreferenceIdentityError, SQLAlchemyError):
            logger.exception(
                "rq-engine huc-fire SQL cleanup failed",
                extra={"error_id": error_id, "runid": runid},
            )
    try:
        cleanup_new_run_directory(runid, wd)
    except (OSError, RuntimeError, ValueError):
        logger.exception(
            "rq-engine huc-fire directory cleanup failed",
            extra={"error_id": error_id, "runid": runid},
        )


@router.post("/huc-fire/tasks/upload-sbs/")
async def upload_huc_fire_sbs(request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_UPLOAD_SCOPES)
        if claims.get("token_class") == "session":
            return error_response("Session token not allowed for this endpoint", status_code=403)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine huc-fire upload auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    runid: str | None = None
    wd: str | None = None
    receipt: RunRegistrationReceipt | None = None
    try:
        from wepppy.weppcloud.routes.run_0.run_0_bp import create_run_dir

        form = await request.form()
        upload = _extract_upload(form, "input_upload_sbs")
        if upload is None:
            return upload_failure("input_upload_sbs must be provided")
        if not upload.filename:
            return upload_failure("no filename specified")

        filename = secure_filename(upload.filename)
        if not filename:
            return upload_failure("Could not obtain filename")

        try:
            snapshot = resolve_creation_preferences(claims)
            token_class = str(claims.get("token_class") or "")
            if snapshot is None and token_class not in {"service", "mcp"}:
                raise PreferenceIdentityError("Authenticated user identity is required.")
            effective_values = apply_creation_preference_overrides({}, snapshot)
        except (
            PreferenceIdentityError,
            PreferenceValidationError,
            StoredPreferenceError,
            SQLAlchemyError,
        ):
            error_id = uuid.uuid4().hex
            logger.exception(
                "rq-engine huc-fire preference resolution failed",
                extra={"error_id": error_id},
            )
            return error_response(
                "Could not resolve account preferences.",
                code="preference_resolution_failed",
                error_id=error_id,
                log_exception=False,
            )

        runid, wd = create_run_dir(snapshot)

        config = "disturbed9002"
        cfg = f"{config}.cfg"
        overrides = [
            f"{key}={value}"
            for key, value in effective_values.items()
            if value is not None and value != ""
        ]
        if overrides:
            cfg = f"{cfg}?{'&'.join(overrides)}"

        try:
            Ron(wd, cfg)
        except Exception:  # broad-except: initialization boundary
            error_id = uuid.uuid4().hex
            logger.exception(
                "rq-engine huc-fire Ron initialization failed",
                extra={"error_id": error_id, "runid": runid},
            )
            _cleanup_failed_run(receipt, runid, wd, error_id)
            return error_response(
                "Could not create run",
                code="run_initialization_failed",
                error_id=error_id,
                log_exception=False,
            )

        try:
            from wepppy.weppcloud.utils.run_ttl import initialize_ttl

            initialize_ttl(wd)
        except Exception:  # broad-except: boundary contract
            logger.exception("rq-engine huc-fire TTL initialization failed")

        if snapshot is not None:
            try:
                receipt = register_owned_run(runid, config, snapshot.user_id)
            except (PreferenceIdentityError, SQLAlchemyError):
                error_id = uuid.uuid4().hex
                logger.exception(
                    "rq-engine huc-fire ownership registration failed",
                    extra={"error_id": error_id, "runid": runid},
                )
                _cleanup_failed_run(None, runid, wd, error_id)
                return error_response(
                    "Could not register project ownership.",
                    code="run_ownership_failed",
                    error_id=error_id,
                    log_exception=False,
                )

        disturbed = Disturbed.getInstance(wd)
        file_path = os.path.join(disturbed.disturbed_dir, filename)
        try:
            save_upload_file(
                upload,
                allowed_extensions=UPLOAD_HUC_FIRE_SBS_ALLOWED_EXTENSIONS,
                dest_dir=Path(disturbed.disturbed_dir),
                filename_transform=lambda _value: filename,
                overwrite=True,
                max_bytes=UPLOAD_HUC_FIRE_SBS_MAX_BYTES,
            )
        except UploadError as exc:
            status_code = int(getattr(exc, "status_code", 400))
            error_id = uuid.uuid4().hex
            _cleanup_failed_run(receipt, runid, wd, error_id)
            return error_response(
                str(exc),
                status_code=status_code,
                error_id=error_id,
                log_exception=False,
            )

        try:
            disturbed.validate(filename, mode=0)
        except Exception as exc:  # broad-except: validation boundary
            error_id = uuid.uuid4().hex
            logger.exception(
                "rq-engine huc-fire disturbed validation failed",
                extra={"error_id": error_id, "runid": runid},
            )
            os.remove(file_path)
            _cleanup_failed_run(receipt, runid, wd, error_id)
            return error_response(
                "SBS validation failed.",
                status_code=400,
                code="validation_error",
                details="The uploaded SBS raster did not pass validation.",
                error_id=error_id,
                log_exception=False,
            )

        return JSONResponse({"runid": runid})
    except Exception:  # broad-except: boundary contract
        error_id = uuid.uuid4().hex
        logger.exception(
            "rq-engine huc-fire upload failed",
            extra={"error_id": error_id, "runid": runid},
        )
        if runid is not None and wd is not None:
            _cleanup_failed_run(receipt, runid, wd, error_id)
        return error_response(
            "Could not save file.",
            status_code=500,
            code="upload_failed",
            error_id=error_id,
            log_exception=False,
        )


__all__ = ["router"]
