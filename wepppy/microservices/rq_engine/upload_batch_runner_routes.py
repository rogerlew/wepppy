from __future__ import annotations

import logging
import os
import shutil
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from wepppy.request_payload import RequestPayloadError
from .payloads import request_form, PayloadRoute

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from werkzeug.utils import secure_filename

from wepppy.nodb.base import NoDbAlreadyLockedError, clear_locks
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap, sbs_map_sanity_check
from wepppy.topo.watershed_collection.watershed_collection import (
    WatershedCollection,
    validate_new_upload_polygon_geojson,
)
from wepppy.microservices.vector_upload_normalization import (
    RetentionActor,
    VectorUploadError,
    prepare_vector_upload,
)

from .feature_access import require_feature_access
from .auth import AuthError, require_jwt
from .responses import error_response
from .upload_helpers import UploadError, save_upload_file, validate_raster_upload

logger = logging.getLogger(__name__)

router = APIRouter(route_class=PayloadRoute)

RQ_UPLOAD_SCOPES = ["rq:enqueue"]
GEOJSON_MAX_BYTES = 30 * 1024 * 1024
SBS_MAP_MAX_BYTES = 100 * 1024 * 1024
SBS_MAP_ALLOWED_EXTENSIONS = ("tif", "tiff", "img")


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


def _retention_actor(claims: dict[str, Any]) -> RetentionActor:
    token_class = str(claims.get("token_class") or "").strip().lower()
    if token_class in {"user", "session"}:
        try:
            principal = claims.get("feature_access_principal")
            principal_id = principal.get("id") if isinstance(principal, dict) and principal.get("kind") == "human" else None
            user_id = int(claims.get("user_id") or principal_id or (claims.get("sub") if token_class == "user" else 0))
        except (TypeError, ValueError):
            user_id = 0
        if user_id > 0:
            return RetentionActor("human", user_id)
    if token_class in {"service", "mcp"}:
        subject = str(claims.get("sub") or "").strip()
        if subject:
            return RetentionActor(token_class, subject)
    return RetentionActor("unattributed", None)


def _extract_upload(form, key: str) -> UploadFile | None:
    if len(form.getlist(key)) > 1:
        raise RequestPayloadError()
    upload = form.get(key)
    if isinstance(upload, UploadFile):
        return upload
    return None


def _upload_error_status(exc: UploadError) -> int:
    if "maximum allowed size" in str(exc).lower():
        return 413
    return 400


def _safe_unlink(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


@router.post("/batch/_/{batch_name}/upload-geojson")
async def upload_geojson(batch_name: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_UPLOAD_SCOPES)
        require_feature_access(claims, "batch_runner")
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine upload-geojson auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    if not _batch_runner_feature_enabled():
        return error_response("Batch Runner is currently disabled.", status_code=403)

    form = await request_form(request)
    try:
        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404)
    except Exception:
        logger.exception("rq-engine upload-geojson failed to load batch runner")
        return error_response("Failed to load batch runner", status_code=500)

    upload = _extract_upload(form, "geojson_file") or _extract_upload(form, "file")
    if upload is None:
        return error_response("No file part named 'geojson_file'.", status_code=400)

    filename = upload.filename or ""
    if not filename:
        return error_response("Filename is required.", status_code=400)

    safe_name = secure_filename(filename)
    if not safe_name:
        return error_response("Filename contains no safe characters.", status_code=400)

    resources_dir = Path(batch_runner.resources_dir)
    resources_dir.mkdir(parents=True, exist_ok=True)
    canonical_name = f"{Path(safe_name).stem}.geojson"
    dest_path = resources_dir / canonical_name
    replaced = dest_path.exists()
    attempt_root = resources_dir / "vector_upload_attempts"
    analysis_results: dict[str, Any] = {}

    def validate_geojson(path: Path, payload: dict[str, object]) -> dict[str, object]:
        nonlocal analysis_results
        validate_new_upload_polygon_geojson(payload)
        collection = WatershedCollection(str(path))
        analysis_results = collection.analysis_results
        if analysis_results.get("feature_count", 0) == 0:
            raise ValueError("GeoJSON contains no features.")
        return {
            "feature_count": int(analysis_results["feature_count"]),
            "geometry_types": ["Polygon", "MultiPolygon"],
        }

    try:
        prepared = await run_in_threadpool(
            lambda: prepare_vector_upload(
                raw_filename=filename,
                stream=upload.file,
                endpoint_max_bytes=_geojson_max_bytes(),
                attempt_root=attempt_root,
                evidence_roots=(attempt_root, Path(batch_runner.wd) / "archives" / "private"),
                filesystem_root=Path(batch_runner.wd),
                project_key=f"batch:{batch_name}",
                workflow="batch_runner",
                project_identity=batch_name,
                actor=_retention_actor(dict(claims)),
                validator=validate_geojson,
            )
        )
    except VectorUploadError as exc:
        return error_response(str(exc), status_code=exc.status_code, code=exc.code)

    try:
        relative_path = os.path.relpath(dest_path, batch_runner.wd)
    except ValueError:
        relative_path = dest_path

    metadata = {
        "resource_type": "geojson",
        "filename": canonical_name,
        "original_filename": filename,
        "relative_path": relative_path,
        "content_type": "application/geo+json",
        "replaced": replaced,
    }

    metadata["uploaded_at"] = datetime.now(timezone.utc).isoformat()
    uploader = _resolve_uploader(claims)
    if uploader:
        metadata["uploaded_by"] = str(uploader)

    def publish_candidate(candidate_path: Path, publication_commit) -> None:
        resources_dir.mkdir(parents=True, exist_ok=True)
        prior_state = {
            "_geojson_state": deepcopy(getattr(batch_runner, "_geojson_state", None)),
            "_runid_template_state": deepcopy(getattr(batch_runner, "_runid_template_state", None)),
        }
        backup_path: Path | None = None
        if dest_path.exists():
            descriptor, backup_name = tempfile.mkstemp(
                prefix=f".{dest_path.name}.", suffix=".backup", dir=resources_dir
            )
            os.close(descriptor)
            backup_path = Path(backup_name)
            shutil.copy2(dest_path, backup_path)
        staged_path = resources_dir / f".{dest_path.name}.{prepared.attempt_id}.tmp"
        published = False
        try:
            shutil.copy2(candidate_path, staged_path)
            os.replace(staged_path, dest_path)
            watershed_collection = WatershedCollection(str(dest_path))
            watershed_collection.update_analysis_results(metadata)
            try:
                batch_runner.register_geojson(watershed_collection, metadata=metadata)
            except NoDbAlreadyLockedError:
                clear_locks(batch_runner.runid)
                batch_runner.register_geojson(watershed_collection, metadata=metadata)
            publication_commit()
            published = True
        finally:
            if not published and not prepared.is_terminal:
                staged_path.unlink(missing_ok=True)
                if backup_path is not None:
                    os.replace(backup_path, dest_path)
                else:
                    dest_path.unlink(missing_ok=True)
                locked = getattr(batch_runner, "locked", None)
                if callable(locked):
                    with locked():
                        for name, value in prior_state.items():
                            setattr(batch_runner, name, value)
            if backup_path is not None:
                backup_path.unlink(missing_ok=True)

    try:
        await run_in_threadpool(
            lambda: prepared.publish_transactional(
                mutation=publish_candidate,
                canonical_path=dest_path,
                canonical_relative_path=relative_path,
            )
        )
    except VectorUploadError as exc:
        return error_response(str(exc), status_code=exc.status_code, code=exc.code)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except (KeyError, OSError, RuntimeError, TypeError):
        logger.exception("Failed to publish Batch vector upload")
        return error_response("Failed to process GeoJSON upload.", status_code=500)

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
        require_feature_access(claims, "batch_runner")
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine upload-sbs-map auth failed")
        return error_response("Failed to authorize request", status_code=401, code="unauthorized")

    if not _batch_runner_feature_enabled():
        return error_response("Batch Runner is currently disabled.", status_code=403)

    form = await request_form(request)
    try:
        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404)
    except Exception:
        logger.exception("rq-engine upload-sbs-map failed to load batch runner")
        return error_response("Failed to load batch runner", status_code=500)

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
    if not lower_name.endswith((".tif", ".tiff", ".img")):
        return error_response("Only GeoTIFF or self-contained IMG rasters are supported.", status_code=400)

    resources_dir = batch_runner.resources_dir
    dest_path = os.path.join(resources_dir, safe_name)
    replaced = os.path.exists(dest_path)
    sanity_status, sanity_message, burn_class_counts = 0, "", {}
    def validate_sbs(path):
        nonlocal sanity_status, sanity_message, burn_class_counts
        sanity_status, sanity_message = sbs_map_sanity_check(str(path))
        if sanity_status != 0:
            raise UploadError(sanity_message or "Invalid SBS map.")
        burn_class_counts = SoilBurnSeverityMap(str(path)).burn_class_counts
    try:
        save_upload_file(upload, allowed_extensions=SBS_MAP_ALLOWED_EXTENSIONS,
            dest_dir=Path(resources_dir), filename_transform=lambda _value: safe_name,
            overwrite=True, max_bytes=SBS_MAP_MAX_BYTES,
            post_save=lambda path: validate_raster_upload(
                path, semantic_validator=validate_sbs
            ),
            isolated_post_save=True)
        size_bytes = os.path.getsize(dest_path)
    except UploadError as exc:
        return error_response(str(exc), status_code=_upload_error_status(exc))
    except Exception:  # Native/GDAL boundary; never publish a failed SBS computation.
        logger.exception("rq-engine upload-sbs-map native validation failed")
        return error_response("SBS raster processing failed.", status_code=500)

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
        batch_runner.apply_sbs_resource_update(sbs_map=relative_path, metadata=metadata)
    except NoDbAlreadyLockedError:
        clear_locks(batch_runner.runid)
        batch_runner.apply_sbs_resource_update(sbs_map=relative_path, metadata=metadata)

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
