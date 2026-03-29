from __future__ import annotations

import json
import logging
import os
from pathlib import Path

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
    resolve_download_artifact_path,
)
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.features_export_rq import (
    run_features_export_cache_hit_rq,
    run_features_export_rq,
)
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


def _features_export_download_url(runid: str, config: str, job_id: str) -> str:
    return f"/rq-engine/api/runs/{runid}/{config}/export/features/{job_id}/download"


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
        from wepppy.export import gpkg_export

        wd = _resolve_export_wd(runid, request)
        ron = Ron.getInstance(wd)
        gpkg_path = Path(ron.export_arc_dir) / f"{runid}.gpkg"

        if not gpkg_path.exists():
            await _run_sync(gpkg_export, wd)

        _require_file(gpkg_path, label="GeoPackage export")
        return FileResponse(path=gpkg_path, filename=gpkg_path.name)
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
        from wepppy.export import gpkg_export

        wd = _resolve_export_wd(runid, request)
        ron = Ron.getInstance(wd)
        gdb_path = Path(ron.export_arc_dir) / f"{runid}.gdb.zip"

        if not gdb_path.exists():
            await _run_sync(gpkg_export, wd)

        _require_file(gdb_path, label="Geodatabase export")
        return FileResponse(path=gdb_path, filename=gdb_path.name)
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
        from wepppy.export import archive_project
        from wepppy.export.prep_details import (
            export_channels_prep_details,
            export_hillslopes_prep_details,
        )

        wd = _resolve_export_wd(runid, request)
        await _run_sync(export_hillslopes_prep_details, wd)
        channels_fn = await _run_sync(export_channels_prep_details, wd)
        channels_path = _require_file(Path(channels_fn), label="Prep details export")

        if request.query_params.get("no_retrieve") is not None:
            return JSONResponse({"status": "ok"})

        archive_path = await _run_sync(archive_project, str(channels_path.parent))
        archive_file = _require_file(Path(archive_path), label="Prep details archive")
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
    summary="Resolve features export profile text",
    description=(
        "Requires JWT Bearer scope `rq:export` and run access via `authorize_run_access`. "
        "Parses profile text (`profile_text`) as YAML, validates it against the "
        "features-export planner, and returns a normalized request mapping."
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
    "/runs/{runid}/{config}/export/features/{job_id}/download",
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
        claims = require_jwt(request, required_scopes=EXPORT_SCOPES)
        authorize_run_access(claims, runid)
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


__all__ = ["router"]
