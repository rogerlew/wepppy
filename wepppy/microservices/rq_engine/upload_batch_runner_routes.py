from __future__ import annotations

import logging
import os
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile
from werkzeug.utils import secure_filename

from wepppy.nodb.base import NoDbAlreadyLockedError, clear_locks
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap, sbs_map_sanity_check
from wepppy.topo.watershed_collection.watershed_collection import WatershedCollection

from .auth import AuthError, require_jwt, require_roles
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_UPLOAD_SCOPES = ["rq:enqueue"]
GEOJSON_MAX_BYTES = 10 * 1024 * 1024


def _geojson_max_bytes() -> int:
    """Resolve the GeoJSON upload cap, honoring Flask config if available."""
    try:
        from wepppy.weppcloud.app import app as flask_app

        raw_limit = flask_app.config.get("BATCH_GEOJSON_MAX_MB")
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/microservices/rq_engine/upload_batch_runner_routes.py:37", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        raw_limit = None

    try:
        limit_mb = int(raw_limit) if raw_limit is not None else None
    except (TypeError, ValueError):
        limit_mb = None

    if limit_mb is None or limit_mb <= 0:
        return GEOJSON_MAX_BYTES
    return int(limit_mb) * 1024 * 1024


def _batch_runner_feature_enabled() -> bool:
    from wepppy.weppcloud.app import app as flask_app

    return bool(flask_app.config.get("BATCH_RUNNER_ENABLED", False))


def _serialize_geojson_state(state: Dict[str, Any]) -> Dict[str, Any]:
    resource = deepcopy(state)
    resource.pop("_geojson_filepath", None)
    return resource


def _build_batch_runner_snapshot(batch_runner: BatchRunner) -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {
        "state_version": 1,
        "batch_name": batch_runner.batch_name,
        "base_config": batch_runner.base_config,
        "resources": {},
        "metadata": {},
        "runid_template": None,
    }

    run_directives_state = []
    directives_map = batch_runner.run_directives
    tasks = getattr(batch_runner, "DEFAULT_TASKS", BatchRunner.DEFAULT_TASKS)
    for task in tasks:
        label = task.label()
        run_directives_state.append(
            {
                "slug": task.value,
                "label": label,
                "enabled": directives_map.get(task, True),
            }
        )
    snapshot["run_directives"] = run_directives_state

    geojson_state = batch_runner.geojson_state
    if geojson_state:
        snapshot.setdefault("resources", {})["watershed_geojson"] = _serialize_geojson_state(geojson_state)

    sbs_state_getter = getattr(batch_runner, "sbs_resource_state", None)
    sbs_resource = sbs_state_getter() if callable(sbs_state_getter) else None
    if sbs_resource:
        snapshot.setdefault("resources", {})["sbs_map"] = sbs_resource

    template_state = batch_runner.runid_template_state
    if template_state:
        snapshot.setdefault("metadata", {})["template_validation"] = deepcopy(template_state)
        snapshot["runid_template"] = template_state.get("template")

    return snapshot


def _resolve_uploader(claims: dict[str, Any]) -> Optional[str]:
    for key in ("email", "username", "sub"):
        value = claims.get(key)
        if value:
            return str(value)
    return None


def _extract_upload(form, key: str) -> UploadFile | None:
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


def _safe_unlink(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


@router.post("/batch/_/{batch_name}/upload-geojson")
async def upload_geojson(batch_name: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_UPLOAD_SCOPES)
        require_roles(claims, ["Admin"])
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine upload-geojson auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    if not _batch_runner_feature_enabled():
        return error_response("Batch Runner is currently disabled.", status_code=403)

    try:
        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404)
    except Exception:
        logger.exception("rq-engine upload-geojson failed to load batch runner")
        return error_response_with_traceback("Failed to load batch runner", status_code=500)

    form = await request.form()
    upload = _extract_upload(form, "geojson_file") or _extract_upload(form, "file")
    if upload is None:
        return error_response("No file part named 'geojson_file'.", status_code=400)

    filename = upload.filename or ""
    if not filename:
        return error_response("Filename is required.", status_code=400)

    safe_name = secure_filename(filename)
    if not safe_name:
        return error_response("Filename contains no safe characters.", status_code=400)

    lower_name = safe_name.lower()
    if not lower_name.endswith((".geojson", ".json")):
        return error_response("Only .geojson or .json files are supported.", status_code=400)

    resources_dir = batch_runner.resources_dir
    os.makedirs(resources_dir, exist_ok=True)
    dest_path = os.path.join(resources_dir, safe_name)
    replaced = os.path.exists(dest_path)
    try:
        try:
            upload.file.seek(0)
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/microservices/rq_engine/upload_batch_runner_routes.py:171", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            pass
        with open(dest_path, "wb") as dest:
            shutil.copyfileobj(upload.file, dest)
    except OSError:
        _safe_unlink(dest_path)
        logger.exception("Failed to save GeoJSON upload")
        return error_response_with_traceback("Failed to save GeoJSON upload.", status_code=500)

    try:
        size_bytes = os.path.getsize(dest_path)
    except OSError:
        size_bytes = None

    if not size_bytes:
        _safe_unlink(dest_path)
        return error_response("GeoJSON file is empty.", status_code=400)

    max_bytes = _geojson_max_bytes()
    if size_bytes and size_bytes > max_bytes:
        _safe_unlink(dest_path)
        limit_mb = max(1, int(max_bytes // (1024 * 1024)))
        return error_response(f"GeoJSON file exceeds maximum size of {limit_mb} MB.", status_code=400)

    try:
        watershed_collection = WatershedCollection(dest_path)
        analysis_results = watershed_collection.analysis_results
    except ValueError as exc:
        _safe_unlink(dest_path)
        return error_response(f"GeoJSON must be a FeatureCollection: {exc}", status_code=400)
    except Exception:
        _safe_unlink(dest_path)
        logger.exception("Failed to ingest GeoJSON upload")
        return error_response_with_traceback("Failed to process GeoJSON upload.", status_code=500)

    if analysis_results.get("feature_count", 0) == 0:
        _safe_unlink(dest_path)
        return error_response("GeoJSON contains no features.", status_code=400)

    try:
        relative_path = os.path.relpath(dest_path, batch_runner.wd)
    except ValueError:
        relative_path = dest_path

    metadata = {
        "resource_type": "geojson",
        "filename": safe_name,
        "original_filename": filename,
        "relative_path": relative_path,
        "content_type": upload.content_type,
        "replaced": replaced,
    }

    metadata["uploaded_at"] = datetime.now(timezone.utc).isoformat()
    uploader = _resolve_uploader(claims)
    if uploader:
        metadata["uploaded_by"] = str(uploader)

    watershed_collection.update_analysis_results(metadata)

    try:
        batch_runner.register_geojson(watershed_collection, metadata=metadata)
    except NoDbAlreadyLockedError:
        clear_locks(batch_runner.runid)
        batch_runner.register_geojson(watershed_collection, metadata=metadata)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)

    snapshot = _build_batch_runner_snapshot(batch_runner)
    resource_payload = snapshot.get("resources", {}).get("watershed_geojson")
    template_state = snapshot.get("metadata", {}).get("template_validation")

    return JSONResponse(
        {
            "resource": resource_payload,
            "template_validation": template_state,
            "snapshot": snapshot,
            "message": "GeoJSON uploaded successfully.",
        },
        status_code=200,
    )


@router.post("/batch/_/{batch_name}/upload-sbs-map")
async def upload_sbs_map(batch_name: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_UPLOAD_SCOPES)
        require_roles(claims, ["Admin"])
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine upload-sbs-map auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    if not _batch_runner_feature_enabled():
        return error_response("Batch Runner is currently disabled.", status_code=403)

    try:
        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404)
    except Exception:
        logger.exception("rq-engine upload-sbs-map failed to load batch runner")
        return error_response_with_traceback("Failed to load batch runner", status_code=500)

    form = await request.form()
    upload = _extract_upload(form, "sbs_map") or _extract_upload(form, "file")
    if upload is None:
        return error_response("No file part named 'sbs_map'.", status_code=400)

    filename = upload.filename or ""
    if not filename:
        return error_response("Filename is required.", status_code=400)

    safe_name = secure_filename(filename)
    if not safe_name:
        return error_response("Filename contains no safe characters.", status_code=400)

    lower_name = safe_name.lower()
    if not lower_name.endswith((".tif", ".tiff", ".img", ".vrt")):
        return error_response("Only GeoTIFF/IMG/VRT rasters are supported.", status_code=400)

    resources_dir = batch_runner.resources_dir
    os.makedirs(resources_dir, exist_ok=True)
    dest_path = os.path.join(resources_dir, safe_name)
    replaced = os.path.exists(dest_path)
    with open(dest_path, "wb") as dest:
        shutil.copyfileobj(upload.file, dest)

    try:
        size_bytes = os.path.getsize(dest_path)
    except OSError:
        size_bytes = None

    sanity_status, sanity_message = sbs_map_sanity_check(dest_path)
    if sanity_status != 0:
        _safe_unlink(dest_path)
        return error_response(sanity_message or "Invalid SBS map.", status_code=400)

    burn_class_counts: Optional[Dict[str, int]] = None
    try:
        burn_class_counts = SoilBurnSeverityMap(dest_path).burn_class_counts
    except Exception as exc:
        logger.warning("rq-engine upload-sbs-map burn class summary failed: %s", exc)
    
    try:
        relative_path = os.path.relpath(dest_path, batch_runner.wd)
    except ValueError:
        relative_path = dest_path

    metadata: Dict[str, Any] = {
        "resource_type": "sbs_map",
        "filename": safe_name,
        "original_filename": filename,
        "relative_path": relative_path,
        "content_type": upload.content_type,
        "replaced": replaced,
        "sanity_status": sanity_status,
        "sanity_message": sanity_message,
        "size_bytes": size_bytes,
    }
    if burn_class_counts:
        metadata["burn_class_counts"] = burn_class_counts

    metadata["uploaded_at"] = datetime.now(timezone.utc).isoformat()
    uploader = _resolve_uploader(claims)
    if uploader:
        metadata["uploaded_by"] = str(uploader)

    try:
        batch_runner.sbs_map = relative_path
        batch_runner.sbs_map_metadata = metadata
    except NoDbAlreadyLockedError:
        clear_locks(batch_runner.runid)
        batch_runner.sbs_map = relative_path
        batch_runner.sbs_map_metadata = metadata

    snapshot = _build_batch_runner_snapshot(batch_runner)
    resource_payload = snapshot.get("resources", {}).get("sbs_map")

    return JSONResponse(
        {
            "resource": resource_payload,
            "snapshot": snapshot,
            "message": "SBS map uploaded successfully.",
        }
    )


__all__ = ["router"]
