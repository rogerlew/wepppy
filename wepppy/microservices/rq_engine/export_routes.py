from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
from urllib.parse import urlencode
from uuid import uuid4

import anyio
import redis
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Ron
from wepppy.nodb.mods.features_export import (
    FeaturesExportProfileError,
    FeaturesExportValidationError,
    parse_profile_text,
    prepare_export_submission,
)
from wepppy.nodb.mods.features_export.cache_key import get_cache_index_entry
from wepppy.nodb.mods.features_export.service import (
    FeaturesExportServiceError,
    cache_entry_supports_cache_hit,
    execute_features_export,
    normalize_published_profile_id,
    publish_profile_execution_artifacts,
    resolve_download_artifact_path,
    resolve_published_artifact_path,
    resolve_published_profile_request,
)
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.features_export_rq import (
    run_features_export_cache_hit_rq,
    run_features_export_rq,
)
from wepppy.rq.ermit_export_rq import run_ermit_export_rq
from wepppy.rq.job_info import get_wepppy_rq_job_info
from wepppy.runtime_paths.errors import NoDirError
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .responses import (
    error_response,
    error_response_with_traceback,
    validation_error_response,
)

logger = logging.getLogger(__name__)

router = APIRouter()

EXPORT_SCOPES = ["rq:export"]
RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
_DOWNLOAD_FILENAME_TOKEN_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def _maybe_nodir_error_response(exc: Exception):
    if isinstance(exc, NoDirError):
        return error_response(exc.message, status_code=exc.http_status, code=exc.code)
    return None


async def _run_sync(func, *args, **kwargs):
    return await anyio.to_thread.run_sync(func, *args, **kwargs)


def _require_file(path: Path, *, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found at {path}")
    return path


def _resolve_export_wd(runid: str, request: Request) -> str:
    run_root = Path(get_wd(runid, prefer_active=False)).resolve()
    if not run_root.is_dir():
        raise FileNotFoundError(f"Run '{runid}' not found")

    if ";;" in runid:
        return str(run_root)

    pup_relpath = request.query_params.get("pup")
    if not pup_relpath:
        return str(run_root)

    pups_root = (run_root / "_pups").resolve()
    if not pups_root.is_dir():
        raise FileNotFoundError(f"Unknown pup project: {pup_relpath}")

    candidate = (pups_root / pup_relpath).resolve()
    try:
        candidate.relative_to(pups_root)
    except ValueError as exc:
        raise FileNotFoundError(f"Unknown pup project: {pup_relpath}") from exc

    if not candidate.is_dir():
        raise FileNotFoundError(f"Unknown pup project: {pup_relpath}")

    return str(candidate)


def _json_media_type(request: Request) -> str:
    content_type = request.headers.get("content-type", "")
    return content_type.split(";", 1)[0].strip().lower()


def _validation_issue(*, code: str, message: str, path: str) -> dict[str, str]:
    return {"code": code, "message": message, "path": path}


def _safe_download_filename_token(value: str, *, fallback: str) -> str:
    token = _DOWNLOAD_FILENAME_TOKEN_PATTERN.sub("-", str(value).strip()).strip("-._")
    if token:
        return token
    return fallback


def _published_download_filename(runid: str, profile: str) -> str:
    canonical_profile = normalize_published_profile_id(profile)
    profile_token = canonical_profile if canonical_profile is not None else profile
    format_token = "export"
    try:
        _resolved_profile, request_payload = resolve_published_profile_request(profile)
        candidate_format = str(request_payload.get("format") or "").strip().lower()
        if candidate_format:
            format_token = candidate_format
    except FeaturesExportServiceError:
        format_token = "export"
    runid_token = _safe_download_filename_token(runid, fallback="run")
    profile_token_safe = _safe_download_filename_token(profile_token, fallback="profile")
    format_token_safe = _safe_download_filename_token(format_token, fallback="export")
    return f"{runid_token}.{profile_token_safe}.{format_token_safe}.zip"


def _is_public_run_for_download(runid: str) -> bool:
    try:
        wd = get_wd(runid, prefer_active=False)
    except Exception:
        return False
    try:
        return bool(Ron.ispublic(wd))
    except Exception:
        return False


def _authorize_download_or_public(request: Request, *, runid: str) -> None:
    auth_header = request.headers.get("Authorization")
    if not auth_header and _is_public_run_for_download(runid):
        return

    claims = require_jwt(request, required_scopes=EXPORT_SCOPES)
    authorize_run_access(claims, runid)


async def _parse_features_export_submit_payload(request: Request) -> tuple[dict[str, object] | None, JSONResponse | None]:
    if _json_media_type(request) != "application/json":
        return None, error_response(
            "Request body must use application/json.",
            status_code=415,
            code="unsupported_media_type",
            details="Submit features export requests as application/json only.",
        )

    raw_body = await request.body()
    if not raw_body.strip():
        return None, validation_error_response(
            [
                _validation_issue(
                    code="missing_body",
                    message="Request body must not be empty.",
                    path="$",
                )
            ]
        )

    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, validation_error_response(
            [
                _validation_issue(
                    code="invalid_json",
                    message=f"Invalid JSON payload: {exc}",
                    path="$",
                )
            ]
        )

    if not isinstance(payload, dict):
        return None, validation_error_response(
            [
                _validation_issue(
                    code="invalid_type",
                    message="Request payload must be a JSON object.",
                    path="$",
                )
            ]
        )

    if not payload:
        return None, validation_error_response(
            [
                _validation_issue(
                    code="missing_field",
                    message="Request payload must not be empty.",
                    path="$",
                )
            ]
        )

    return payload, None


async def _parse_features_export_profile_resolve_payload(
    request: Request,
) -> tuple[str | None, JSONResponse | None]:
    payload, payload_error = await _parse_features_export_submit_payload(request)
    if payload_error is not None:
        return None, payload_error
    assert payload is not None

    profile_text = payload.get("profile_text")
    if not isinstance(profile_text, str) or not profile_text.strip():
        return None, validation_error_response(
            [
                _validation_issue(
                    code="missing_field",
                    message="profile_text must be a non-empty string.",
                    path="profile_text",
                )
            ]
        )

    return profile_text, None


def _features_export_status_url(job_id: str) -> str:
    return f"/rq-engine/api/jobstatus/{job_id}"


def _ermit_export_status_url(job_id: str) -> str:
    return f"/rq-engine/api/jobstatus/{job_id}"


def _ermit_export_download_url(runid: str, config: str, job_id: str) -> str:
    return f"/rq-engine/api/runs/{runid}/{config}/export/ermit/job/{job_id}/download"


def _append_export_query_params(url: str, request: Request) -> str:
    pup_relpath = request.query_params.get("pup")
    if not pup_relpath:
        return url
    return f"{url}?{urlencode({'pup': pup_relpath})}"


def _features_export_download_url(runid: str, config: str, job_id: str) -> str:
    return f"/rq-engine/api/runs/{runid}/{config}/export/features/job/{job_id}/download"


def _enqueue_ermit_export_job(*, runid: str, config: str, wd: str) -> str:
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
        queue = Queue(connection=redis_conn)
        job = queue.enqueue_call(
            run_ermit_export_rq,
            (runid, config, wd),
            timeout=RQ_TIMEOUT,
        )

    prep = RedisPrep.tryGetInstance(wd)
    if prep is not None:
        try:
            prep.set_rq_job_id("ermit_export", job.id)
        except Exception:
            # Boundary catch: metadata persistence must not mask successful enqueue.
            logger.warning("ERMiT export: failed to persist rq job id", exc_info=True)
    return str(job.id)


def _resolve_ermit_job_artifact_path(wd: str, job_result: dict[str, object] | None) -> Path:
    if not isinstance(job_result, dict):
        raise FileNotFoundError("ERMiT export artifact mapping not found for job.")

    wd_path = Path(wd).resolve()
    relpath = str(job_result.get("artifact_relpath") or "").strip()
    if relpath:
        artifact_path = (wd_path / relpath).resolve()
    else:
        artifact_path = Path(str(job_result.get("artifact_path") or "")).resolve()

    try:
        artifact_path.relative_to(wd_path)
    except ValueError as exc:
        raise FileNotFoundError("ERMiT export artifact path is outside the run directory.") from exc

    return _require_file(artifact_path, label="ERMiT export")


def _execute_features_export_profile(
    *,
    runid: str,
    config: str,
    wd: str | Path,
    profile: str,
    format_override: str | None = None,
    publish_profile: bool,
) -> tuple[dict[str, object], Path]:
    canonical_profile, payload = resolve_published_profile_request(
        profile,
        format_override=format_override,
    )
    job_id = f"route-{canonical_profile}-{uuid4().hex}"
    result = execute_features_export(
        wd,
        runid=runid,
        config=config,
        payload=payload,
        job_id=job_id,
    )
    if publish_profile:
        publish_profile_execution_artifacts(
            wd,
            requested_profile=canonical_profile,
            job_id=job_id,
            job_result=result,
        )
    artifact_path, _artifact_relpath = resolve_download_artifact_path(
        wd,
        job_id=job_id,
        job_result=result,
    )
    return result, artifact_path


def _enqueue_features_export_job(
    *,
    runid: str,
    config: str,
    wd: str,
    payload: dict[str, object],
) -> tuple[str, bool]:
    submission = prepare_export_submission(wd, payload)
    cache_entry = get_cache_index_entry(wd, submission.cache_key_parts.cache_key)

    format_token = ""
    plan = getattr(submission, "plan", None)
    if plan is not None:
        request = getattr(plan, "request", None)
        if request is not None:
            format_token = str(getattr(request, "format", "") or "")
    if not format_token:
        format_token = str(payload.get("format") or "")

    cache_hit_eligible = cache_entry_supports_cache_hit(
        wd,
        cache_entry=cache_entry,
        format_token=format_token,
    )
    target_func = run_features_export_cache_hit_rq if cache_hit_eligible else run_features_export_rq

    prep = RedisPrep.getInstance(wd)
    prep.remove_timestamp(TaskEnum.run_features_export)

    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
        queue = Queue(connection=redis_conn)
        job = queue.enqueue_call(
            target_func,
            (runid, config, payload, wd),
            timeout=RQ_TIMEOUT,
        )

    prep.set_rq_job_id("features_export", job.id)
    return str(job.id), cache_hit_eligible


@router.get(
    "/runs/{runid}/{config}/export/ermit",
    summary="Export ERMiT input",
    description=(
        "Requires JWT Bearer scope `rq:export` and run access via `authorize_run_access`. "
        "Read-only export endpoint that may generate ERMiT artifacts before returning a file response."
    ),
    tags=["rq-engine", "exports"],
    operation_id=rq_operation_id("export_ermit"),
    responses=agent_route_responses(
        success_code=200,
        success_description="ERMiT export file returned.",
        extra={
            404: "Requested run/export artifact was not found. Returns the canonical error payload.",
        },
    ),
)
async def export_ermit(runid: str, config: str, request: Request):
    try:
        claims = require_jwt(request, required_scopes=EXPORT_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine export_ermit auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        from wepppy.export import create_ermit_input

        wd = _resolve_export_wd(runid, request)
        fn = await _run_sync(create_ermit_input, wd)
        file_path = _require_file(Path(fn), label="ERMiT export")
        return FileResponse(path=file_path, filename=file_path.name)
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404, code="not_found")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine export_ermit failed")
        return error_response_with_traceback("Error exporting ERMiT")


@router.post(
    "/runs/{runid}/{config}/export/ermit",
    summary="Submit ERMiT input export",
    description=(
        "Requires JWT Bearer scope `rq:export` and run access via `authorize_run_access`. "
        "Queues ERMiT/Disturbed WEPP batch-input generation and returns job/download URLs."
    ),
    tags=["rq-engine", "exports"],
    operation_id=rq_operation_id("export_ermit_submit"),
    responses=agent_route_responses(
        success_code=202,
        success_description="ERMiT export job enqueued.",
        extra={
            404: "Requested run was not found. Returns the canonical error payload.",
        },
    ),
)
async def export_ermit_submit(runid: str, config: str, request: Request):
    try:
        claims = require_jwt(request, required_scopes=EXPORT_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine export_ermit_submit auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = _resolve_export_wd(runid, request)
        job_id = await _run_sync(
            lambda: _enqueue_ermit_export_job(runid=runid, config=config, wd=wd)
        )
        download_url = _append_export_query_params(
            _ermit_export_download_url(runid, config, job_id),
            request,
        )
        return JSONResponse(
            {
                "job_id": job_id,
                "status_url": _ermit_export_status_url(job_id),
                "download_url": download_url,
                "message": "ERMiT export job enqueued.",
            },
            status_code=202,
        )
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404, code="not_found")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine export_ermit_submit enqueue failed")
        return error_response_with_traceback("Error submitting ERMiT export")


@router.get(
    "/runs/{runid}/{config}/export/ermit/job/{job_id}/download",
    summary="Download completed ERMiT export artifact",
    description=(
        "Requires JWT Bearer scope `rq:export` and run access via `authorize_run_access`. "
        "Returns 409 until the ERMiT export job finishes."
    ),
    tags=["rq-engine", "exports"],
    operation_id=rq_operation_id("export_ermit_download"),
    responses=agent_route_responses(
        success_code=200,
        success_description="ERMiT export artifact file returned.",
        extra={
            404: "Job or artifact mapping not found. Returns the canonical error payload.",
            409: "Job has not reached terminal success (`finished`) yet.",
        },
    ),
)
async def export_ermit_download(runid: str, config: str, job_id: str, request: Request):
    try:
        _authorize_download_or_public(request, runid=runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine export_ermit_download auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = _resolve_export_wd(runid, request)
        job_info = await _run_sync(get_wepppy_rq_job_info, job_id)
        status = str(job_info.get("status") or "")
        if status == "not_found":
            return error_response(
                "Job not found",
                status_code=404,
                code="not_found",
                details=f"Job {job_id} not found.",
            )

        job_runid = job_info.get("runid")
        if isinstance(job_runid, str) and job_runid and job_runid != runid:
            return error_response(
                "ERMiT export artifact mapping not found for job.",
                status_code=404,
                code="not_found",
                details=f"Job {job_id} does not belong to run {runid}.",
            )

        if status != "finished":
            return error_response(
                "ERMiT export job is not finished.",
                status_code=409,
                code="conflict",
                details=f"Job {job_id} status is {status}.",
            )

        job_result = job_info.get("result")
        if not isinstance(job_result, dict):
            job_result = None
        artifact_path = await _run_sync(
            lambda: _resolve_ermit_job_artifact_path(wd, job_result)
        )
        return FileResponse(path=artifact_path, filename=artifact_path.name)
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404, code="not_found")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine export_ermit_download failed")
        return error_response_with_traceback("Error downloading ERMiT export")


@router.get(
    "/runs/{runid}/{config}/export/geopackage",
    summary="Export GeoPackage",
    description=(
        "Requires JWT Bearer scope `rq:export` and run access via `authorize_run_access`. "
        "Read-only export endpoint that may generate geopackage artifacts before returning a file response."
    ),
    tags=["rq-engine", "exports"],
    operation_id=rq_operation_id("export_geopackage"),
    responses=agent_route_responses(
        success_code=200,
        success_description="GeoPackage export file returned.",
        extra={
            404: "Requested run/export artifact was not found. Returns the canonical error payload.",
        },
    ),
)
async def export_geopackage(runid: str, config: str, request: Request):
    try:
        claims = require_jwt(request, required_scopes=EXPORT_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine export_geopackage auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = _resolve_export_wd(runid, request)
        _result, artifact_path = await _run_sync(
            lambda: _execute_features_export_profile(
                runid=runid,
                config=config,
                wd=wd,
                profile="prep-wepp",
                publish_profile=True,
            )
        )
        _require_file(artifact_path, label="GeoPackage export")
        return FileResponse(path=artifact_path, filename=artifact_path.name)
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404, code="not_found")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine export_geopackage failed")
        return error_response_with_traceback("Error exporting geopackage")


@router.get(
    "/runs/{runid}/{config}/export/geodatabase",
    summary="Export geodatabase archive",
    description=(
        "Requires JWT Bearer scope `rq:export` and run access via `authorize_run_access`. "
        "Read-only export endpoint that may generate geodatabase artifacts before returning a file response."
    ),
    tags=["rq-engine", "exports"],
    operation_id=rq_operation_id("export_geodatabase"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Geodatabase export archive returned.",
        extra={
            404: "Requested run/export artifact was not found. Returns the canonical error payload.",
        },
    ),
)
async def export_geodatabase(runid: str, config: str, request: Request):
    try:
        claims = require_jwt(request, required_scopes=EXPORT_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine export_geodatabase auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = _resolve_export_wd(runid, request)

        try:
            artifact_path, _artifact_relpath = await _run_sync(
                lambda: resolve_published_artifact_path(
                    wd,
                    profile="prep-wepp-geodatabase",
                )
            )
        except FeaturesExportServiceError:
            await _run_sync(
                lambda: _execute_features_export_profile(
                    runid=runid,
                    config=config,
                    wd=wd,
                    profile="prep-wepp-gpkg-gdb",
                    publish_profile=True,
                )
            )
            artifact_path, _artifact_relpath = await _run_sync(
                lambda: resolve_published_artifact_path(
                    wd,
                    profile="prep-wepp-geodatabase",
                )
            )

        _require_file(artifact_path, label="Geodatabase export")
        return FileResponse(path=artifact_path, filename=artifact_path.name)
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404, code="not_found")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine export_geodatabase failed")
        return error_response_with_traceback("Error exporting geodatabase")


@router.get(
    "/runs/{runid}/{config}/export/prep_details",
    summary="Export prep details archive",
    description=(
        "Requires JWT Bearer scope `rq:export` and run access via `authorize_run_access`. "
        "Read-only export endpoint that generates prep-details artifacts and returns archive data or status JSON."
    ),
    tags=["rq-engine", "exports"],
    operation_id=rq_operation_id("export_prep_details"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Prep details response returned (archive file or status payload).",
        extra={
            404: "Requested run/export artifact was not found. Returns the canonical error payload.",
        },
    ),
)
@router.get(
    "/runs/{runid}/{config}/export/prep_details/",
    summary="Export prep details archive (trailing slash)",
    description=(
        "Requires JWT Bearer scope `rq:export` and run access via `authorize_run_access`. "
        "Read-only export endpoint equivalent to `/export/prep_details` with trailing-slash path compatibility."
    ),
    tags=["rq-engine", "exports"],
    operation_id=rq_operation_id("export_prep_details_trailing_slash"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Prep details response returned (archive file or status payload).",
        extra={
            404: "Requested run/export artifact was not found. Returns the canonical error payload.",
        },
    ),
)
async def export_prep_details(runid: str, config: str, request: Request):
    try:
        claims = require_jwt(request, required_scopes=EXPORT_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine export_prep_details auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = _resolve_export_wd(runid, request)
        _result, artifact_path = await _run_sync(
            lambda: _execute_features_export_profile(
                runid=runid,
                config=config,
                wd=wd,
                profile="prep-details",
                publish_profile=True,
            )
        )

        if request.query_params.get("no_retrieve") is not None:
            return JSONResponse({"status": "ok"})

        archive_file = _require_file(artifact_path, label="Prep details archive")
        return FileResponse(
            path=archive_file,
            filename=f"{runid}_prep_details.zip",
        )
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404, code="not_found")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine export_prep_details failed")
        return error_response_with_traceback("Error exporting prep details")


@router.post(
    "/runs/{runid}/{config}/export/features",
    summary="Submit features export job",
    description=(
        "Requires JWT Bearer scope `rq:export` and run access via `authorize_run_access`. "
        "Accepts only `application/json`, computes features-export planning/cache context, and enqueues async RQ execution."
    ),
    tags=["rq-engine", "exports"],
    operation_id=rq_operation_id("export_features_submit"),
    responses=agent_route_responses(
        success_code=202,
        success_description="Features export job accepted and `job_id` returned.",
        extra={
            400: "Validation error. Returns the canonical error payload.",
            404: "Run not found. Returns the canonical error payload.",
            409: "Conflict while resolving export artifacts. Returns the canonical error payload.",
            415: "Unsupported media type; JSON body is required.",
        },
    ),
)
async def export_features_submit(runid: str, config: str, request: Request):
    try:
        claims = require_jwt(request, required_scopes=EXPORT_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine export_features_submit auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    payload, payload_error = await _parse_features_export_submit_payload(request)
    if payload_error is not None:
        return payload_error
    assert payload is not None

    try:
        wd = get_wd(runid)
        job_id, _cache_hit = await _run_sync(
            lambda: _enqueue_features_export_job(
                runid=runid,
                config=config,
                wd=wd,
                payload=payload,
            )
        )
        return JSONResponse(
            {
                "job_id": job_id,
                "status_url": _features_export_status_url(job_id),
                "download_url": _features_export_download_url(runid, config, job_id),
                "message": "Features export job enqueued.",
            },
            status_code=202,
        )
    except FeaturesExportValidationError as exc:
        return JSONResponse(exc.to_error_payload(), status_code=exc.status_code)
    except FeaturesExportServiceError as exc:
        return error_response(
            str(exc),
            status_code=exc.status_code,
            code=exc.code,
            details=exc.details,
        )
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404, code="not_found")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine export_features_submit enqueue failed")
        return error_response_with_traceback("Error submitting features export")


@router.post(
    "/runs/{runid}/{config}/export/features/profile/resolve",
    summary="Resolve features export profile",
    description=(
        "Requires JWT Bearer scope `rq:export` and run access via `authorize_run_access`. "
        "Read-only, no queue: parse YAML `profile_text` and return "
        "features-export request mapping."
    ),
    tags=["rq-engine", "exports"],
    operation_id=rq_operation_id("export_features_profile_resolve"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Profile text parsed and normalized.",
        extra={
            400: "Validation error. Returns the canonical error payload.",
            415: "Unsupported media type; JSON body is required.",
        },
    ),
)
async def export_features_profile_resolve(runid: str, config: str, request: Request):
    try:
        claims = require_jwt(request, required_scopes=EXPORT_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine export_features_profile_resolve auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    profile_text, payload_error = await _parse_features_export_profile_resolve_payload(request)
    if payload_error is not None:
        return payload_error
    assert profile_text is not None

    try:
        request_payload = parse_profile_text(profile_text)
        wd = get_wd(runid)
        submission = await _run_sync(lambda: prepare_export_submission(wd, request_payload))
        return JSONResponse(
            {
                "profile": submission.plan.request.to_mapping(),
            },
            status_code=200,
        )
    except FeaturesExportProfileError as exc:
        return validation_error_response(
            [
                _validation_issue(
                    code="invalid_profile_text",
                    message=str(exc),
                    path="profile_text",
                )
            ]
        )
    except FeaturesExportValidationError as exc:
        return JSONResponse(exc.to_error_payload(), status_code=exc.status_code)
    except FeaturesExportServiceError as exc:
        return error_response(
            str(exc),
            status_code=exc.status_code,
            code=exc.code,
            details=exc.details,
        )
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404, code="not_found")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine export_features_profile_resolve failed")
        return error_response_with_traceback("Error resolving features export profile text")


@router.get(
    "/runs/{runid}/{config}/export/features/job/{job_id}/download",
    summary="Download completed features export artifact",
    description=(
        "Requires JWT Bearer scope `rq:export` and run access via `authorize_run_access`. "
        "Read-only endpoint (no queue): returns 409 until job status is `finished`; "
        "on success returns the export artifact file."
    ),
    tags=["rq-engine", "exports"],
    operation_id=rq_operation_id("export_features_download"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Features export artifact file returned.",
        extra={
            404: "Job or artifact mapping not found. Returns the canonical error payload.",
            409: "Job has not reached terminal success (`finished`) yet.",
        },
    ),
)
async def export_features_download(runid: str, config: str, job_id: str, request: Request):
    try:
        _authorize_download_or_public(request, runid=runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine export_features_download auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        job_info = await _run_sync(get_wepppy_rq_job_info, job_id)
        status = str(job_info.get("status") or "")
        if status == "not_found":
            return error_response(
                "Job not found",
                status_code=404,
                code="not_found",
                details=f"Job {job_id} not found.",
            )

        job_runid = job_info.get("runid")
        if isinstance(job_runid, str) and job_runid and job_runid != runid:
            return error_response(
                "Features export artifact mapping not found for job.",
                status_code=404,
                code="not_found",
                details=f"Job {job_id} does not belong to run {runid}.",
            )

        if status != "finished":
            return error_response(
                "Features export job is not finished.",
                status_code=409,
                code="conflict",
                details=f"Job {job_id} status is {status}.",
            )

        job_result = job_info.get("result")
        if not isinstance(job_result, dict):
            job_result = None

        artifact_path, _artifact_relpath = await _run_sync(
            lambda: resolve_download_artifact_path(
                wd,
                job_id=job_id,
                job_result=job_result,
            )
        )
        resolved_path = Path(artifact_path)
        return FileResponse(path=resolved_path, filename=resolved_path.name)
    except FeaturesExportServiceError as exc:
        return error_response(
            str(exc),
            status_code=exc.status_code,
            code=exc.code,
            details=exc.details,
        )
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404, code="not_found")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine export_features_download failed")
        return error_response_with_traceback("Error downloading features export artifact")


@router.get(
    "/runs/{runid}/{config}/export/features/published/{profile}/download",
    summary="Download published features export artifact",
    description=(
        "Requires JWT Bearer scope `rq:export` and run access via `authorize_run_access`. "
        "No queue endpoint: resolves one canonical published profile id through "
        "`export/features/published/index.json`, may repair publication metadata from cache "
        "key state, and returns the artifact file."
    ),
    tags=["rq-engine", "exports"],
    operation_id=rq_operation_id("export_features_download_published"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Published features export artifact file returned.",
        extra={
            404: "Published profile or artifact mapping not found. Returns the canonical error payload.",
            409: "Published mapping is stale relative to registry/cache artifact integrity checks.",
        },
    ),
)
async def export_features_published_download(runid: str, config: str, profile: str, request: Request):
    try:
        _authorize_download_or_public(request, runid=runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine export_features_published_download auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = _resolve_export_wd(runid, request)
        artifact_path, _artifact_relpath = await _run_sync(
            lambda: resolve_published_artifact_path(
                wd,
                profile=profile,
            )
        )
        return FileResponse(
            path=artifact_path,
            filename=_published_download_filename(runid, profile),
        )
    except FeaturesExportServiceError as exc:
        return error_response(
            str(exc),
            status_code=exc.status_code,
            code=exc.code,
            details=exc.details,
        )
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404, code="not_found")
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine export_features_published_download failed")
        return error_response_with_traceback("Error downloading published features export artifact")


__all__ = ["router"]
