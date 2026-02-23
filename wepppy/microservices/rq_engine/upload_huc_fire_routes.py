from __future__ import annotations

import logging
import os
import shutil

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile
from werkzeug.utils import secure_filename

from wepppy.nodb.core import Ron
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodir.mutations import enable_default_archive_roots

from .auth import AuthError, require_jwt
from .responses import error_response, error_response_with_traceback
from .upload_helpers import upload_failure

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_UPLOAD_SCOPES = ["rq:enqueue"]


def _extract_upload(form, key: str) -> UploadFile | None:
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


def _resolve_user_from_claims(claims: dict[str, object]) -> tuple[object | None, object | None, object | None]:
    from wepppy.weppcloud.utils.helpers import get_user_models
    from wepppy.weppcloud.app import app as flask_app

    Run, User, user_datastore = get_user_models()
    user = None
    sub = claims.get("sub")
    email = claims.get("email")

    with flask_app.app_context():
        if sub is not None:
            try:
                user_id = int(str(sub))
            except (TypeError, ValueError):
                user_id = None
            if user_id is not None:
                user = User.query.filter(User.id == user_id).first()

        if user is None and email:
            if hasattr(user_datastore, "find_user"):
                try:
                    user = user_datastore.find_user(email=str(email))
                except Exception:
                    # Boundary catch: preserve contract behavior while logging unexpected failures.
                    __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/microservices/rq_engine/upload_huc_fire_routes.py:56", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                    user = None

        if user is None and email:
            try:
                user = User.query.filter(User.email == str(email)).first()
            except Exception:
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/microservices/rq_engine/upload_huc_fire_routes.py:62", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                user = None

    return user, user_datastore, flask_app


@router.post("/huc-fire/tasks/upload-sbs/")
async def upload_huc_fire_sbs(request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_UPLOAD_SCOPES)
        if claims.get("token_class") == "session":
            return error_response("Session token not allowed for this endpoint", status_code=403)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine huc-fire upload auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        from wepppy.weppcloud.routes.run_0.run_0_bp import create_run_dir

        form = await request.form()
        upload = _extract_upload(form, "input_upload_sbs")
        if upload is None:
            return upload_failure("Could not find file")
        if not upload.filename:
            return upload_failure("no filename specified")

        filename = secure_filename(upload.filename)
        if not filename:
            return upload_failure("Could not obtain filename")

        user, user_datastore, flask_app = _resolve_user_from_claims(claims)
        if user is None or user_datastore is None or flask_app is None:
            return error_response("User not found", status_code=403, code="forbidden")

        runid, wd = create_run_dir(user)

        config = "disturbed9002"
        cfg = f"{config}.cfg"

        ron = Ron(wd, cfg)
        if ron.config_get_bool("nodb", "apply_nodir", False):
            enable_default_archive_roots(wd)

        try:
            from wepppy.weppcloud.utils.run_ttl import initialize_ttl

            initialize_ttl(wd)
        except Exception:
            logger.exception("rq-engine huc-fire TTL initialization failed")

        with flask_app.app_context():
            user_datastore.create_run(runid, config, user)

        disturbed = Disturbed.getInstance(wd)
        file_path = os.path.join(disturbed.disturbed_dir, filename)
        with open(file_path, "wb") as dest:
            shutil.copyfileobj(upload.file, dest)

        try:
            disturbed.validate(filename, mode=0)
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/microservices/rq_engine/upload_huc_fire_routes.py:123", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            os.remove(file_path)
            return error_response_with_traceback("Failed validating file", status_code=500)

        return JSONResponse({"runid": runid})
    except Exception:
        logger.exception("rq-engine huc-fire upload failed")
        return error_response_with_traceback("Could not save file", status_code=500)


__all__ = ["router"]
