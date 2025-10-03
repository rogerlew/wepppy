"""Admin-facing blueprint for the Batch Runner."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
import json
import re
from copy import deepcopy
from typing import Any, Dict, Optional, Sequence, Union

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_security import current_user

from wepppy.topo.watershed_collection.watershed_collection import WatershedCollection

from .._common import Blueprint, roles_required, secure_filename
from wepppy.nodb import unitizer as unitizer_module
from wepppy.nodb.base import get_configs, get_config_dir
from wepppy.nodb.ron import RonViewModel
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.weppcloud.utils.helpers import exception_factory, get_batch_root_dir, handle_with_exception_factory

batch_runner_bp = Blueprint(
    "batch_runner",
    __name__,
    template_folder="templates"
)

def _batch_runner_feature_enabled() -> bool:
    flag = current_app.config.get("BATCH_RUNNER_ENABLED", False)
    return bool(flag)


_BATCH_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,127}$")
_GEOJSON_MAX_BYTES = 10 * 1024 * 1024
_GEOJSON_MAX_MB = int(_GEOJSON_MAX_BYTES // (1024 * 1024))

def _validate_batch_name(raw_name: str) -> str:
    name = (raw_name or "").strip()
    if not name:
        raise ValueError("Batch name is required.")
    if not _BATCH_NAME_RE.fullmatch(name):
        raise ValueError(
            "Batch name must start with an alphanumeric character and contain only "
            "letters, numbers, underscores, or hyphens (minimum 3 characters)."
        )
    if name in {"_base", "resources", "logs"}:
        raise ValueError("Batch name cannot be a reserved directory name.")
    return name


def _validate_config(config_name: str, available: Sequence[str]) -> str:
    if not config_name:
        raise ValueError("Configuration selection is required.")
    if config_name not in available:
        raise ValueError("Unknown configuration selected.")
    return config_name


BatchRoot = Union[str, os.PathLike[str]]


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
    for task in BatchRunner.DEFAULT_TASKS:
        label = task.label()
        run_directives_state.append({
            "slug": task.value,
            "label": label,
            "enabled": directives_map[task]
        })
    snapshot["run_directives"] = run_directives_state

    geojson_state = batch_runner.geojson_state
    if geojson_state:
        snapshot.setdefault("resources", {})["watershed_geojson"] = _serialize_geojson_state(geojson_state)

    template_state = batch_runner.runid_template_state
    if template_state:
        snapshot.setdefault("metadata", {})["template_validation"] = deepcopy(template_state)
        snapshot["runid_template"] = template_state.get("template")

    return snapshot


def _create_batch_project(
    batch_name: str,
    base_config: str,    # config means no .cfg extension
    batch_config: str = "default_batch",  # config means no .cfg extension
    batch_root: Optional[BatchRoot] = None,
) -> BatchRunner:
    batch_root = batch_root or get_batch_root_dir()
    batch_root_path = os.fspath(batch_root)
    base_config_cfg = f"{base_config}.cfg"
    config_file = os.path.join(get_config_dir(), base_config_cfg)
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration '{config_file}' does not exist.")

    os.makedirs(batch_root_path, exist_ok=True)

    batch_wd = os.path.join(batch_root_path, batch_name)
    if os.path.exists(batch_wd):
        raise FileExistsError(f"Batch '{batch_name}' already exists.")

    # create batch_wd
    os.makedirs(batch_wd)

    runner = BatchRunner(
        batch_wd,
        f"batch/{batch_config}.cfg",
        base_config_cfg,
    )

    return runner


@batch_runner_bp.route("/batch/create/", methods=["GET", "POST"])
@roles_required("Admin")
@handle_with_exception_factory
def create_batch_project():
    """Render or submit the batch creation form."""
    feature_enabled = _batch_runner_feature_enabled()
    if not feature_enabled:
        flash("Batch Runner is currently disabled.", "warning")
        return render_template("create.htm", feature_enabled=False, geojson_limit_mb=_GEOJSON_MAX_MB)
   
    context = {'feature_enabled': True, 'geojson_limit_mb': _GEOJSON_MAX_MB}

    available_configs = get_configs()
    context['available_configs'] = available_configs

    errors = []
    if request.method == "POST":

        batch_name_input = request.form.get("batch_name", "")
        base_config_input = request.form.get("base_config", "")
        
        context["form_state"] = {
            "batch_name": batch_name_input,
            "base_config": base_config_input,
        }

        try:
            base_config = _validate_config(base_config_input, available_configs)
            batch_name = _validate_batch_name(batch_name_input)
            batch_runner = _create_batch_project(
                batch_name=batch_name,
                base_config=base_config
            )
            return redirect(url_for("batch_runner.view_batch", batch_name=batch_runner.batch_name))   
        except (ValueError, FileExistsError, FileNotFoundError) as err:
            errors.append(str(err))
        except Exception as err:  # pragma: no cover - defensive path
            current_app.logger.exception("Failed to create batch project")
            errors.append(f"An unexpected error occurred while creating the batch: {err}")
            raise

    if errors:
        context["errors"] = errors

    default_config = "disturbed9002_wbt" if "disturbed9002_wbt" in available_configs else available_configs[0]
    context.setdefault("form_state", {"batch_name": "", "base_config": default_config})
    return render_template("create.htm", **context)


@batch_runner_bp.route("/batch/_/<string:batch_name>/", methods=["GET"])
@roles_required("Admin")
@handle_with_exception_factory
def view_batch(batch_name: str):
    """Render the placeholder batch detail page for Batch Runner (Phase 0)."""
    global _GEOJSON_MAX_MB

    feature_enabled = _batch_runner_feature_enabled()
    if not feature_enabled:
        return jsonify(_batch_runner_disabled_response()), 403
    
    batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
    base_runid = f"batch;;{batch_name};;_base"
    base_config = batch_runner.base_config
    batch_runner_state = _build_batch_runner_snapshot(batch_runner)
    ron = RonViewModel.getInstanceFromRunID(base_runid)

    context: Dict[str, Any] = {
        "feature_enabled": feature_enabled,
        "batch_name": batch_name,
        "base_config": base_config,
        "ron": ron,
        "batch_runner_state": batch_runner_state,
        "user": current_user,
        "precisions": unitizer_module.precisions,
        "geojson_limit_mb": _GEOJSON_MAX_MB,
        "run_id": base_runid,
        "runid": base_runid,
        "batch_base_runid": base_runid,
        "pup_relpath": None,
    }

    context.setdefault("site_prefix", current_app.config.get("SITE_PREFIX", ""))

    return render_template("manage.htm", **context)


@batch_runner_bp.route('/batch/_/<string:batch_name>/run-directives', methods=['POST'])
@roles_required('Admin')
@handle_with_exception_factory
def update_run_directives(batch_name: str):
    if not _batch_runner_feature_enabled():
        return jsonify(_batch_runner_disabled_response()), 403
    
    batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)

    payload = request.get_json(silent=True) or {}
    raw_directives = payload.get('run_directives')
    if raw_directives is None:
        return jsonify({'success': False, 'error': 'run_directives payload is required.'}), 400

    batch_runner.update_run_directives(raw_directives)

    snapshot = _build_batch_runner_snapshot(batch_runner)

    return jsonify({
        'success': True,
        'run_directives': snapshot.get('run_directives', []),
        'snapshot': snapshot,
    })


def _batch_runner_disabled_response():
    return {
        "success": False,
        "error": "Batch Runner is currently disabled.",
    }

@batch_runner_bp.route("/batch/_/<string:batch_name>/upload-geojson", methods=["POST"])
@roles_required("Admin")
@handle_with_exception_factory
def upload_geojson(batch_name: str):
    if not _batch_runner_feature_enabled():
        return jsonify(_batch_runner_disabled_response()), 403

    batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
    
    storage = request.files.get("geojson_file") or request.files.get("file")
    if storage is None:
        return jsonify({"success": False, "error": "No file part named 'geojson_file'."}), 400

    filename = storage.filename or ""
    if not filename:
        return jsonify({"success": False, "error": "Filename is required."}), 400

    safe_name = secure_filename(filename)
    if not safe_name:
        return jsonify({"success": False, "error": "Filename contains no safe characters."}), 400

    lower_name = safe_name.lower()
    if not lower_name.endswith((".geojson", ".json")):
        return jsonify({"success": False, "error": "Only .geojson or .json files are supported."}), 400

    resources_dir = batch_runner.resources_dir
    os.makedirs(resources_dir, exist_ok=True)
    dest_path = os.path.join(resources_dir, safe_name)
    replaced = os.path.exists(dest_path)
    storage.save(dest_path)

    # initial validation for security
    try:
        watershed_collection = WatershedCollection(dest_path)
        analysis_results = watershed_collection.analysis_results  # lazy runs analysis
    except ValueError as exc:
        _safe_unlink(dest_path)
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - unexpected errors
        _safe_unlink(dest_path)
        current_app.logger.exception("Failed to ingest GeoJSON upload")
        return jsonify({"success": False, "error": "Failed to process GeoJSON upload."}), 500

    if analysis_results.get("feature_count", 0) == 0:
        _safe_unlink(dest_path)
        return jsonify({"success": False, "error": "GeoJSON contains no features."}), 400

    if os.path.getsize(dest_path) > _GEOJSON_MAX_BYTES:
        _safe_unlink(dest_path)
        return jsonify({"success": False, "error": f"GeoJSON file exceeds maximum size of {_GEOJSON_MAX_MB} MB."}), 400

    relative_path = os.path.relpath(dest_path, batch_runner.wd)
    metadata = {
        "resource_type": "geojson",
        "filename": safe_name,
        "original_filename": filename,
        "relative_path": relative_path,
        "content_type": storage.mimetype,
        "replaced": replaced
    }

    metadata["uploaded_at"] = datetime.now(timezone.utc).isoformat()
    uploader = getattr(current_user, "email", None) or getattr(current_user, "username", None) or getattr(current_user, "id", None)
    if uploader:
        metadata["uploaded_by"] = str(uploader)

    watershed_collection.update_analysis_results(metadata)

    # let BatchRunner verify it meets the requirements
    try:
        batch_runner.register_geojson(watershed_collection)
    except ValueError as exc:
        response_payload = {"success": False, "error": str(exc)}
        return jsonify(response_payload), 400

    snapshot = _build_batch_runner_snapshot(batch_runner)
    resource_payload = snapshot.get("resources", {}).get("watershed_geojson")
    template_state = snapshot.get("metadata", {}).get("template_validation")

    response_payload = {
        "success": True,
        "resource": resource_payload,
        "template_validation": template_state,
        "snapshot": snapshot,
        "message": "GeoJSON uploaded successfully."
    }

    return jsonify(response_payload), 200


def _safe_unlink(path: Union[str, os.PathLike[str]]) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


@batch_runner_bp.route("/batch/_/<string:batch_name>/validate-template", methods=["POST"])
@roles_required("Admin")
def validate_template(batch_name: str):
    if not _batch_runner_feature_enabled():
        return jsonify(_batch_runner_disabled_response()), 403

    try:
        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
    except FileNotFoundError as exc:
        return jsonify({"success": False, "error": str(exc)}), 404
    payload = request.get_json(silent=True) or {}
    template = payload.get("template")
    if not template:
        return jsonify({"success": False, "error": "Template is required."}), 400

    try:
        watershed_collection = batch_runner.get_watershed_collection()
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    validation = watershed_collection.validate_template(template)
    status = "ok" if validation["summary"]["is_valid"] else "invalid"

    runid_template_state = {
        "template": template,
        "template_hash": validation["template_hash"],
        "resource_checksum": watershed_collection.checksum,
        "summary": validation["summary"],
        "duplicates": validation["duplicates"][:50],
        "errors": validation["errors"][:50],
        "preview": validation["preview"],
        "validation_hash": validation["validation_hash"],
        "status": status,
    }

    batch_runner.runid_template_state = runid_template_state
    snapshot = _build_batch_runner_snapshot(batch_runner)
    stored_state = snapshot.get("metadata", {}).get("template_validation")
    response_payload = {
        "success": status == "ok",
        "status": status,
        "validation": validation,
        "stored": stored_state,
        "snapshot": snapshot,
    }

    return jsonify(response_payload), 200
