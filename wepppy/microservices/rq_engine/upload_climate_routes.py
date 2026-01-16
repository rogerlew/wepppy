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
from wepppy.rq.project_rq import upload_cli_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .responses import error_response, error_response_with_traceback
from .upload_helpers import UploadError, save_upload_file, upload_failure, upload_success

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_UPLOAD_SCOPES = ["rq:enqueue"]
RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))


def _extract_upload(form, key: str) -> UploadFile | None:
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


@router.post("/runs/{runid}/{config}/tasks/upload-cli/")
async def upload_cli(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_UPLOAD_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine upload-cli auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        Ron.getInstance(wd)
        climate = Climate.getInstance(wd)

        form = await request.form()
        upload = _extract_upload(form, "input_upload_cli")
        if upload is None:
            return upload_failure("Could not find file")

        saved_path = save_upload_file(
            upload,
            allowed_extensions=("cli",),
            dest_dir=Path(climate.cli_dir),
            filename_transform=lambda value: value,
            overwrite=True,
        )
    except UploadError as exc:
        return upload_failure(str(exc))
    except Exception:
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
    except Exception:
        logger.exception("rq-engine upload-cli enqueue failed")
        return error_response_with_traceback("Failed validating file", status_code=500)


__all__ = ["router"]
