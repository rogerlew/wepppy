from __future__ import annotations

import json
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
from wepppy.nodb.mods.omni import Omni, OmniScenario
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.omni_rq import run_omni_scenarios_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]
SBS_ALLOWED_EXTENSIONS = ("tif", "tiff", "img")
SBS_MAX_BYTES = 100 * 1024 * 1024


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
) -> Path:
    filename = _validate_upload_filename(upload)
    _enforce_extension(filename, allowed_extensions)
    _enforce_max_bytes(upload, max_bytes)

    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / filename
    if destination.exists():
        destination.unlink()

    with destination.open("wb") as dest:
        shutil.copyfileobj(upload.file, dest)

    return destination


def _coerce_omni_scenario_list(payload: dict[str, Any], raw_json: Any) -> list[dict[str, Any]] | None:
    if isinstance(raw_json, list):
        return raw_json

    scenarios_raw = payload.get("scenarios")
    if scenarios_raw is None:
        return None

    if isinstance(scenarios_raw, list):
        if len(scenarios_raw) == 1 and isinstance(scenarios_raw[0], str):
            scenarios_raw = scenarios_raw[0]
        else:
            return scenarios_raw  # type: ignore[return-value]

    if isinstance(scenarios_raw, dict):
        return [scenarios_raw]

    if isinstance(scenarios_raw, str):
        try:
            parsed = json.loads(scenarios_raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Scenarios data must be valid JSON") from exc
        if not isinstance(parsed, list):
            raise ValueError("Scenarios data must be a list")
        return parsed

    raise ValueError("Scenarios data must be a list")


def _extract_upload(form: FormData, key: str) -> UploadFile | None:
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


def _prepare_omni_scenarios(
    payload: dict[str, Any],
    raw_json: Any,
    form: FormData,
    *,
    runid: str,
    config: str,
    wd: str,
) -> list[tuple[OmniScenario, dict[str, Any]]]:
    scenarios_payload = _coerce_omni_scenario_list(payload, raw_json)
    if scenarios_payload is None:
        raise ValueError("Missing scenarios data")
    if not isinstance(scenarios_payload, list):
        raise ValueError("Scenarios data must be a list")

    limbo_dir = Path(wd) / "omni" / "_limbo"
    limbo_dir.mkdir(parents=True, exist_ok=True)

    allowed_extensions = _normalize_extensions(SBS_ALLOWED_EXTENSIONS)
    parsed_inputs: list[tuple[OmniScenario, dict[str, Any]]] = []
    for idx, scenario in enumerate(scenarios_payload):
        if not isinstance(scenario, dict):
            raise ValueError(f"Scenario {idx} must be an object")

        scenario_type = scenario.get("type")
        if not scenario_type:
            raise ValueError(f"Scenario {idx} is missing type")

        scenario_enum = OmniScenario.parse(scenario_type)
        scenario_params: dict[str, Any] = dict(scenario)
        scenario_params["type"] = scenario_type

        if scenario_enum == OmniScenario.SBSmap:
            file_key = f"scenarios[{idx}][sbs_file]"
            upload = _extract_upload(form, file_key)
            if upload and upload.filename:
                try:
                    upload_path = _save_upload(
                        upload,
                        destination_dir=limbo_dir / f"{idx:02d}",
                        allowed_extensions=allowed_extensions,
                        max_bytes=SBS_MAX_BYTES,
                    )
                except ValueError as exc:
                    raise ValueError(f"Invalid SBS file for scenario {idx}: {exc}") from exc
                scenario_params["sbs_file_path"] = str(upload_path)
            elif scenario_params.get("sbs_file_path"):
                scenario_params["sbs_file_path"] = str(scenario_params["sbs_file_path"])
            else:
                raise ValueError(f"Missing SBS file for scenario {idx}")

            scenario_params.pop("sbs_file", None)

        parsed_inputs.append((scenario_enum, scenario_params))

    return parsed_inputs


async def _run_omni(
    runid: str,
    config: str,
    request: Request,
) -> JSONResponse:
    wd = get_wd(runid)
    omni = Omni.getInstance(wd)

    payload = await parse_request_payload(request)
    try:
        raw_json = await request.json()
    except Exception:
        raw_json = None
    form = await request.form()

    try:
        parsed_inputs = _prepare_omni_scenarios(
            payload,
            raw_json,
            form,
            runid=runid,
            config=config,
            wd=wd,
        )
        omni.parse_scenarios(parsed_inputs)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        return error_response_with_traceback(f"Error parsing omni inputs: {exc}")

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_omni_scenarios)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue("batch", connection=redis_conn)
            job = q.enqueue_call(run_omni_scenarios_rq, (runid,), timeout=RQ_TIMEOUT)
            prep.set_rq_job_id("run_omni_rq", job.id)
    except Exception:
        logger.exception("rq-engine run-omni enqueue failed")
        return error_response_with_traceback("Error Handling Request")

    return JSONResponse({"job_id": job.id})


@router.post("/runs/{runid}/{config}/run-omni")
async def run_omni(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-omni auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    return await _run_omni(runid, config, request)


@router.post("/runs/{runid}/{config}/run-omni-contrasts")
async def run_omni_contrasts(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-omni-contrasts auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    return await _run_omni(runid, config, request)


__all__ = ["router"]
