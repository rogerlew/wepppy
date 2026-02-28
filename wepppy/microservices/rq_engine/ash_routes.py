from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue
from starlette.datastructures import FormData, UploadFile
from werkzeug.utils import secure_filename

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.mods.ash_transport import Ash, AshSpatialMode
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as _nodir_resolve
from wepppy.rq.project_rq import run_ash_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]
ASH_ALLOWED_EXTENSIONS = ("tif", "tiff", "img")
ASH_MAX_BYTES = 100 * 1024 * 1024


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


def _is_base_project_context(runid: str, config: str) -> bool:
    runid_leaf = runid.split(";;")[-1].strip().lower() if runid else ""
    config_token = str(config).strip().lower() if config is not None else ""
    return runid_leaf == "_base" or config_token == "_base"


def _extract_upload(form: FormData, key: str) -> UploadFile | None:
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


def _normalize_extensions(allowed_extensions: tuple[str, ...]) -> set[str]:
    normalized: set[str] = set()
    for ext in allowed_extensions:
        if not ext:
            continue
        cleaned = ext.lower().lstrip(".")
        if cleaned:
            normalized.add(cleaned)
    return normalized


def _validate_upload_filename(upload: UploadFile) -> str:
    raw_name = upload.filename or ""
    if raw_name.strip() == "":
        raise ValueError("no filename specified")
    safe_name = secure_filename(raw_name)
    if not safe_name:
        raise ValueError("Invalid filename")
    safe_name = safe_name.lower().strip()
    if not safe_name:
        raise ValueError("Invalid filename")
    return safe_name


def _enforce_extension(filename: str, allowed_extensions: set[str]) -> None:
    if not allowed_extensions:
        return
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in allowed_extensions:
        allowed_list = ", ".join(sorted(f".{ext}" for ext in allowed_extensions))
        raise ValueError(f"Invalid file extension. Allowed: {allowed_list}")


def _enforce_max_bytes(upload: UploadFile, max_bytes: int | None) -> None:
    if max_bytes is None:
        return
    upload.file.seek(0, os.SEEK_END)
    size = upload.file.tell()
    upload.file.seek(0)
    if size > max_bytes:
        raise ValueError("File exceeds maximum allowed size")


def _save_upload(
    upload: UploadFile,
    *,
    destination_dir: Path,
    allowed_extensions: set[str],
    max_bytes: int | None,
    overwrite: bool,
) -> Path:
    filename = _validate_upload_filename(upload)
    _enforce_extension(filename, allowed_extensions)
    _enforce_max_bytes(upload, max_bytes)

    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / filename
    if destination.exists():
        if not overwrite:
            raise ValueError("File already exists")
        destination.unlink()

    with destination.open("wb") as dest:
        shutil.copyfileobj(upload.file, dest)

    return destination


def _task_upload_ash_map(
    *,
    runid: str,
    form: FormData,
    file_input_id: str,
    required: bool,
    overwrite: bool,
) -> str | None:
    upload = _extract_upload(form, file_input_id)
    if upload is None or not upload.filename:
        if required:
            raise ValueError(f"Missing file for {file_input_id}")
        return None

    allowed_extensions = _normalize_extensions(ASH_ALLOWED_EXTENSIONS)
    destination_dir = Path(get_wd(runid)) / "ash"
    saved_path = _save_upload(
        upload,
        destination_dir=destination_dir,
        allowed_extensions=allowed_extensions,
        max_bytes=ASH_MAX_BYTES,
        overwrite=overwrite,
    )
    return saved_path.name


def _first_value(value: Any) -> Any:
    if isinstance(value, (list, tuple, set)):
        for candidate in value:
            if candidate not in (None, ""):
                return candidate
        return None
    return value


def _preflight_ash_roots(wd: str) -> None:
    _require_directory_root(wd, "climate")
    _require_directory_root(wd, "watershed")
    _require_directory_root(wd, "landuse")


@router.post(
    "/runs/{runid}/{config}/run-ash",
    summary="Run ash transport",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Validates ash inputs/uploads, mutates ash settings, and, outside batch mode, "
        "asynchronously enqueues ash transport."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("run_ash"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Ash inputs accepted; returns batch update message or enqueued `job_id`.",
        extra={
            400: "Ash payload or file validation failed. Returns the canonical error payload.",
        },
    ),
)
async def run_ash(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine run-ash auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        _preflight_ash_roots(wd)
        payload = await parse_request_payload(request)

        mode_raw = _first_value(payload.get("ash_depth_mode"))
        if mode_raw is None:
            return error_response(
                "ash_depth_mode is required (0=loads, 1=depths, 2=maps)",
                status_code=400,
            )
        try:
            ash_depth_mode = int(mode_raw)
        except (TypeError, ValueError):
            return error_response(
                "ash_depth_mode must be an integer (0, 1, or 2)",
                status_code=400,
            )
        if ash_depth_mode not in (0, 1, 2):
            return error_response("ash_depth_mode must be 0, 1, or 2", status_code=400)
        payload["ash_depth_mode"] = ash_depth_mode

        fire_date = _first_value(payload.get("fire_date"))

        def _require_float(name: str) -> float:
            value = _first_value(payload.get(name))
            if value is None:
                raise KeyError(name)
            try:
                numeric = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(name) from exc
            payload[name] = numeric
            return numeric

        if ash_depth_mode == 1:
            try:
                ini_black_ash_depth_mm = _require_float("ini_black_depth")
                ini_white_ash_depth_mm = _require_float("ini_white_depth")
            except KeyError as exc:
                missing = exc.args[0]
                return error_response(
                    f"Missing field: {missing} when ash_depth_mode=1",
                    status_code=400,
                )
            except ValueError as exc:
                invalid = exc.args[0]
                return error_response(f"Field must be numeric: {invalid}", status_code=400)
        elif ash_depth_mode == 0:
            required = (
                "ini_black_load",
                "ini_white_load",
                "field_black_bulkdensity",
                "field_white_bulkdensity",
            )
            missing = [name for name in required if _first_value(payload.get(name)) is None]
            if missing:
                return error_response(
                    f"Missing fields for ash_depth_mode=0: {', '.join(missing)}",
                    status_code=400,
                )
            try:
                ini_black_load = _require_float("ini_black_load")
                ini_white_load = _require_float("ini_white_load")
                field_black_bulkdensity = _require_float("field_black_bulkdensity")
                field_white_bulkdensity = _require_float("field_white_bulkdensity")
                ini_black_ash_depth_mm = ini_black_load / field_black_bulkdensity
                ini_white_ash_depth_mm = ini_white_load / field_white_bulkdensity
            except ValueError as exc:
                invalid = exc.args[0]
                return error_response(f"Field must be numeric: {invalid}", status_code=400)
            except ZeroDivisionError:
                return error_response("Bulk density cannot be zero", status_code=400)
        else:
            ini_black_ash_depth_mm = 3.0
            ini_white_ash_depth_mm = 3.0

        ash = Ash.getInstance(wd)
        ash.parse_inputs(payload)

        if ash_depth_mode == 2:
            form = await request.form()
            with ash.locked():
                ash._spatial_mode = AshSpatialMode.Gridded
                try:
                    ash._ash_load_fn = _task_upload_ash_map(
                        runid=runid,
                        form=form,
                        file_input_id="input_upload_ash_load",
                        required=True,
                        overwrite=True,
                    )
                except ValueError as exc:
                    return error_response(str(exc), status_code=400)

                try:
                    ash._ash_type_map_fn = _task_upload_ash_map(
                        runid=runid,
                        form=form,
                        file_input_id="input_upload_ash_type_map",
                        required=False,
                        overwrite=True,
                    )
                except ValueError as exc:
                    return error_response(str(exc), status_code=400)

            if ash.ash_load_fn is None:
                return error_response("Expecting ashload map", status_code=400)

        ash.ash_depth_mode = ash_depth_mode

        if getattr(ash, "run_group", "") == "batch" or _is_base_project_context(runid, config):
            return JSONResponse({"message": "Set ash inputs for batch processing"})

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_watar)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                run_ash_rq,
                (
                    runid,
                    fire_date,
                    float(ini_white_ash_depth_mm),
                    float(ini_black_ash_depth_mm),
                ),
                timeout=RQ_TIMEOUT,
            )
            prep.set_rq_job_id("run_ash_rq", job.id)

        return JSONResponse({"job_id": job.id})
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine run-ash enqueue failed")
        return error_response_with_traceback("Error Running Ash Transport")


__all__ = ["router"]
