"""Admin-facing blueprint for the Batch Runner."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
import json
import re
from pathlib import Path
import tempfile
from copy import deepcopy
from typing import Dict, Optional, Sequence

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_security import current_user

from .._common import Blueprint, roles_required, secure_filename
from wepppy.nodb.base import get_configs, get_config_dir
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.weppcloud.utils.helpers import get_batch_root_dir

batch_runner_bp = Blueprint(
    "batch_runner",
    __name__,
    template_folder="templates"
)


def _batch_runner_feature_enabled() -> bool:
    flag = current_app.config.get("BATCH_RUNNER_ENABLED", False)
    return bool(flag)


def _existing_batches() -> Sequence[str]:
    root = get_batch_root_dir()
    if not root.exists():
        return ()
    return tuple(sorted(p.name for p in root.iterdir() if p.is_dir()))


def _load_state(batch_name: Optional[str]) -> Dict[str, object]:
    if not batch_name:
        return BatchRunner.default_state()

    batch_dir = get_batch_root_dir() / batch_name
    try:
        runner = BatchRunner.getInstance(str(batch_dir))
    except FileNotFoundError:
        return BatchRunner.default_state()
    except Exception as exc:  # pragma: no cover - defensive logging path
        current_app.logger.warning(
            "Unable to load batch runner state for %s: %s", batch_name, exc
        )
        return BatchRunner.default_state()
    return runner.state_dict()


def _build_context(batch_name: Optional[str] = None) -> Dict[str, object]:
    enabled = _batch_runner_feature_enabled()
    state_payload = _load_state(batch_name)


    context = {
        "feature_enabled": enabled,
        "batch_name": batch_name,
        "state_payload": state_payload,
        "page_title": "WEPPcloud Batch Runner",
        "site_prefix": current_app.config.get("SITE_PREFIX", ""),
        "batch_root": str(get_batch_root_dir()),
        "available_configs": get_configs(),
        "existing_batches": _existing_batches(),
        "geojson_limit_mb": current_app.config.get("BATCH_GEOJSON_MAX_MB", 10),
    }
    return context


_BATCH_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,127}$")

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


def _create_batch_project(
    batch_name: str,
    base_config: str,    # config means no .cfg extension
    created_by: Optional[str],
    batch_config: str = "default_batch",  # config means no .cfg extension
    batch_root: Optional[Path] = None,
) -> Dict[str, object]:
    batch_root = batch_root or get_batch_root_dir()
    base_config_cfg = f"{base_config}.cfg"
    config_file = Path(get_config_dir()) / base_config_cfg
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration '{config_file}' does not exist.")

    batch_root.mkdir(parents=True, exist_ok=True)

    batch_wd = batch_root / batch_name
    if batch_wd.exists():
        raise FileExistsError(f"Batch '{batch_name}' already exists.")

    # create batch_dir
    batch_wd.mkdir(parents=True, exist_ok=False)

    runner = BatchRunner(
        str(batch_wd),
        f"batch/{batch_config}.cfg",
        base_config_cfg,
    )

    timestamp = datetime.now(timezone.utc).isoformat()
    history_entry = {
        "event": "created",
        "timestamp": timestamp,
    }
    if created_by:
        history_entry["user"] = created_by

    runner.update_state(
        batch_name=batch_name,
        batch_config=batch_config,
        config=base_config,
        base_config=base_config,
        created_at=timestamp,
        created_by=created_by,
    )
    runner.add_history(history_entry)

    return {
        "path": batch_wd,
        "state": runner.state_dict(),
    }


@batch_runner_bp.route("/batch/create/", methods=["GET", "POST"])
@roles_required("Admin")
def create_batch_project():
    """Render or submit the batch creation form."""
    context = _build_context()

    if request.method == "POST":
        if not context["feature_enabled"]:
            flash("Batch Runner is currently disabled.", "warning")
            return render_template("create.htm", **context)

        available_configs = context["available_configs"]
        batch_name_input = request.form.get("batch_name", "")
        base_config_input = request.form.get("base_config", "")
        
        context["form_state"] = {
            "batch_name": batch_name_input,
            "base_config": base_config_input,
        }

        errors = []
        try:
            base_config = _validate_config(base_config_input, available_configs)
            batch_name = _validate_batch_name(batch_name_input)
            result = _create_batch_project(
                batch_name=batch_name,
                base_config=base_config,
                created_by=(current_user.email if not current_user.is_anonymous else None)
            )
        except (ValueError, FileExistsError, FileNotFoundError) as err:
            errors.append(str(err))
        except Exception as err:  # pragma: no cover - defensive path
            current_app.logger.exception("Failed to create batch project")
            errors.append("An unexpected error occurred while creating the batch.")

        if errors:
            context["errors"] = errors
            return render_template("create.htm", **context)

        state = result["state"]
        created_name = state.get("batch_name") or batch_name_input.strip()
        flash(f"Batch '{created_name}' created successfully.", "success")
        return redirect(url_for("batch_runner.view_batch", batch_name=created_name))

    default_config = context["available_configs"][0] if context["available_configs"] else ""
    context.setdefault("form_state", {"batch_name": "", "base_config": default_config})
    return render_template("create.htm", **context)


@batch_runner_bp.route("/batch/_/<string:batch_name>/", methods=["GET"])
@roles_required("Admin")
def view_batch(batch_name: str):
    """Render the placeholder batch detail page for Batch Runner (Phase 0)."""
    context = _build_context(batch_name=batch_name)
    return render_template("manage.htm", **context)


def _batch_runner_disabled_response():
    return {
        "success": False,
        "error": "Batch Runner is currently disabled.",
    }


def _current_user_email() -> Optional[str]:
    try:
        if current_user and not current_user.is_anonymous:
            return getattr(current_user, "email", None)
    except Exception:  # pragma: no cover - defensive
        return None
    return None


def _load_runner(batch_name: str) -> BatchRunner:
    batch_dir = get_batch_root_dir() / batch_name
    if not batch_dir.exists():
        raise FileNotFoundError(f"Batch '{batch_name}' does not exist")
    return BatchRunner.getInstance(str(batch_dir))


def _load_geojson_features(resource_path: Path) -> Sequence[Dict[str, object]]:
    with open(resource_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise ValueError("GeoJSON resource must be a FeatureCollection")
    features = payload.get("features", [])
    if not isinstance(features, list) or not features:
        raise ValueError("GeoJSON resource contains no features")
    return features


def _max_geojson_size_bytes() -> Optional[int]:
    max_mb = current_app.config.get("BATCH_GEOJSON_MAX_MB", 10)
    try:
        max_mb = int(max_mb)
    except (TypeError, ValueError):
        return None
    if max_mb <= 0:
        return None
    return max_mb * 1024 * 1024


@batch_runner_bp.route("/batch/_/<string:batch_name>/upload-geojson", methods=["POST"])
@roles_required("Admin")
def upload_geojson(batch_name: str):
    if not _batch_runner_feature_enabled():
        return _json_response(_batch_runner_disabled_response(), 403)

    try:
        runner = _load_runner(batch_name)
    except FileNotFoundError as exc:
        return _json_response({"success": False, "error": str(exc)}, 404)

    storage = request.files.get("geojson_file") or request.files.get("file")
    if storage is None:
        return _json_response({"success": False, "error": "No file part named 'geojson_file'."}, 400)

    filename = storage.filename or ""
    if not filename:
        return _json_response({"success": False, "error": "Filename is required."}, 400)

    safe_name = secure_filename(filename)
    if not safe_name:
        return _json_response({"success": False, "error": "Filename contains no safe characters."}, 400)

    lower_name = safe_name.lower()
    if not lower_name.endswith((".geojson", ".json")):
        return _json_response({"success": False, "error": "Only .geojson or .json files are supported."}, 400)

    max_bytes = _max_geojson_size_bytes()
    resources_dir = Path(runner.resources_dir)
    resources_dir.mkdir(parents=True, exist_ok=True)
    dest_path = resources_dir / safe_name
    replacing = dest_path.exists()

    storage.stream.seek(0)
    temp_fd, temp_path_str = tempfile.mkstemp(dir=resources_dir, prefix="upload_", suffix=".tmp")
    temp_path = Path(temp_path_str)
    size = 0
    hasher = hashlib.sha256()

    try:
        with os.fdopen(temp_fd, "wb") as handle:  # type: ignore[arg-type]
            while True:
                chunk = storage.stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if max_bytes and size > max_bytes:
                    raise ValueError(
                        f"GeoJSON exceeds maximum size of {max_bytes // (1024 * 1024)} MB"
                    )
                handle.write(chunk)
                hasher.update(chunk)

        analysis = BatchRunner.analyse_geojson(temp_path)
    except ValueError as exc:
        temp_path.unlink(missing_ok=True)
        return _json_response({"success": False, "error": str(exc)}, 400)
    except Exception as exc:  # pragma: no cover - unexpected errors
        temp_path.unlink(missing_ok=True)
        current_app.logger.exception("Failed to ingest GeoJSON upload")
        return _json_response({"success": False, "error": "Failed to process GeoJSON upload."}, 500)

    os.replace(temp_path, dest_path)

    relative_path = os.path.relpath(dest_path, runner.wd)
    checksum = hasher.hexdigest()
    metadata = {
        "resource_type": "geojson",
        "filename": safe_name,
        "original_filename": filename,
        "relative_path": relative_path,
        "content_type": storage.mimetype,
        "size_bytes": size,
        "checksum": checksum,
    }
    metadata.update(analysis)

    stored = runner.register_resource(
        BatchRunner.RESOURCE_WATERSHED,
        metadata,
        user=_current_user_email(),
        replaced=replacing,
    )

    message = "GeoJSON uploaded successfully."
    if stored.get("replaced"):
        message = "GeoJSON replaced successfully."

    response_payload = {
        "success": True,
        "resource": stored,
        "message": message,
    }

    if runner.template_validation:
        response_payload["template_validation"] = deepcopy(runner.template_validation)

    return _json_response(response_payload, 200)


@batch_runner_bp.route("/batch/_/<string:batch_name>/validate-template", methods=["POST"])
@roles_required("Admin")
def validate_template(batch_name: str):
    if not _batch_runner_feature_enabled():
        return _json_response(_batch_runner_disabled_response(), 403)

    try:
        runner = _load_runner(batch_name)
    except FileNotFoundError as exc:
        return _json_response({"success": False, "error": str(exc)}, 404)
    payload = request.get_json(silent=True) or {}
    template = payload.get("template")
    if not template:
        return _json_response({"success": False, "error": "Template is required."}, 400)

    state = runner.state_dict()
    resource = state.get("resources", {}).get(BatchRunner.RESOURCE_WATERSHED)
    if not resource:
        return _json_response({"success": False, "error": "Upload a GeoJSON resource before validating."}, 400)

    relative_path = resource.get("relative_path")
    if not relative_path:
        return _json_response({"success": False, "error": "Resource metadata is incomplete."}, 400)

    resource_path = Path(runner.wd) / relative_path
    if not resource_path.exists():
        return _json_response({"success": False, "error": "Stored GeoJSON resource is missing."}, 400)

    try:
        features = _load_geojson_features(resource_path)
    except ValueError as exc:
        return _json_response({"success": False, "error": str(exc)}, 400)

    validation = BatchRunner.validate_template(
        template,
        list(features),
        resource_checksum=resource.get("checksum"),
    )

    status = "ok" if validation["summary"]["is_valid"] else "invalid"

    persisted = {
        "template": template,
        "template_hash": validation["template_hash"],
        "resource_id": BatchRunner.RESOURCE_WATERSHED,
        "resource_checksum": resource.get("checksum"),
        "summary": validation["summary"],
        "duplicates": validation["duplicates"][:50],
        "errors": validation["errors"][:50],
        "preview": validation["preview"],
        "validation_hash": validation["validation_hash"],
        "status": status,
    }

    stored_validation = runner.record_template_validation(
        persisted,
        user=_current_user_email(),
    )
    runner.update_state(runid_template=template)

    response_payload = {
        "success": status == "ok",
        "status": status,
        "validation": validation,
        "stored": stored_validation,
    }

    return _json_response(response_payload, 200)


def _json_response(payload: Dict[str, object], status_code: int) -> tuple:
    return jsonify(payload), status_code
