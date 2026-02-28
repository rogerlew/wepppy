from __future__ import annotations

import logging
from pathlib import Path

import anyio
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from wepppy.nodb.core import Ron
from wepppy.runtime_paths.errors import NoDirError
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

EXPORT_SCOPES = ["rq:export"]


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


__all__ = ["router"]
