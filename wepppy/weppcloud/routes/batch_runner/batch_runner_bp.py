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
from wepppy.nodb.base import get_configs, get_config_dir
from wepppy.nodb.batch_runner import BatchRunner, RunDirectiveEnum
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
    for directive in RunDirectiveEnum:
        label = directive.name.replace('_', ' ').title()
        label = label.replace('Wepp', 'WEPP').replace('Omni', 'OMNI').replace('Rap', 'RAP')
        run_directives_state.append({
            "slug": directive.value,
            "label": label,
            "enabled": bool(batch_runner.run_directives.get(directive.value, False)),
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
def view_batch(batch_name: str):
    """Render the placeholder batch detail page for Batch Runner (Phase 0)."""
    global _GEOJSON_MAX_MB

    feature_enabled = _batch_runner_feature_enabled()
    if not feature_enabled:
        return jsonify(_batch_runner_disabled_response()), 403
    
    batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
    wd = batch_runner.base_wd
    
    # for now get nodb singletons like in run_0_bp.runs0 from base_wd
    # we will setup a proper common context loader in the future

    from wepppy.nodb import Ron, Landuse, Soils, Climate, Wepp, Watershed, Unitizer
    from wepppy.nodb.topaz import Topaz
    from wepppy.nodb.observed import Observed
    from wepppy.nodb.mods.rangeland_cover import RangelandCover
    from wepppy.nodb.mods.rhem import Rhem
    from wepppy.nodb.mods.disturbed import Disturbed
    from wepppy.nodb.mods.ash_transport import Ash
    import wepppy.nodb.mods
    from wepppy.nodb.mods.revegetation import Revegetation
    from wepppy.nodb.mods.omni import Omni, OmniScenario
    from wepppy.nodb.mods.treatments import Treatments
    from wepppy.nodb.redis_prep import RedisPrep
    from wepppy.wepp.soils import soilsdb
    from wepppy.wepp import management
    from wepp_runner.wepp_runner import linux_wepp_bin_opts
    from wepppy.wepp.management.managements import landuse_management_mapping_options
    
    ron = Ron.getInstance(wd)

    runid = '_base'
    config = ron.config_stem
    landuse = Landuse.getInstance(wd)
    soils = Soils.getInstance(wd)
    climate = Climate.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    watershed = Watershed.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)
    site_prefix = current_app.config['SITE_PREFIX']

    if watershed.delineation_backend_is_topaz:
        topaz = Topaz.getInstance(wd)
    else:
        topaz = None

    observed = Observed.tryGetInstance(wd)
    rangeland_cover = RangelandCover.tryGetInstance(wd)
    rhem = Rhem.tryGetInstance(wd)
    disturbed = Disturbed.tryGetInstance(wd)
    ash = Ash.tryGetInstance(wd)
    skid_trails = wepppy.nodb.mods.SkidTrails.tryGetInstance(wd)
    reveg = Revegetation.tryGetInstance(wd)
    omni = Omni.tryGetInstance(wd)
    treatments = Treatments.tryGetInstance(wd)
    redis_prep = RedisPrep.tryGetInstance(wd)
    
    if redis_prep is not None:
        rq_job_ids = redis_prep.get_rq_job_ids()
    else:
        rq_job_ids = {}

    landuseoptions = landuse.landuseoptions
    soildboptions = soilsdb.load_db()

    critical_shear_options = management.load_channel_d50_cs()
    batch_runner_state = _build_batch_runner_snapshot(batch_runner)


    return render_template("manage.htm", 
                            feature_enabled=feature_enabled,
                            batch_name=batch_name,
                            batch_runner_state=batch_runner_state,
                            user=current_user,
                            site_prefix=site_prefix,
                            topaz=topaz,
                            soils=soils,
                            ron=ron,
                            landuse=landuse,
                            climate=climate,
                            wepp=wepp,
                            wepp_bin_opts=linux_wepp_bin_opts,
                            rhem=rhem,
                            disturbed=disturbed,
                            ash=ash,
                            skid_trails=skid_trails,
                            reveg=reveg,
                            watershed=watershed,
                            unitizer_nodb=unitizer,
                            observed=observed,
                            rangeland_cover=rangeland_cover,
                            omni=omni,
                            OmniScenario=OmniScenario,
                            treatments=treatments,
                            rq_job_ids=rq_job_ids,
                            landuseoptions=landuseoptions,
                            landuse_management_mapping_options=landuse_management_mapping_options,
                            soildboptions=soildboptions,
                            critical_shear_options=critical_shear_options,
                            precisions=wepppy.nodb.unitizer.precisions,
                            geojson_limit_mb=_GEOJSON_MAX_MB,
                            run_id=runid,
                            runid=runid,
                            config=config,
                            pup_relpath=None)


@batch_runner_bp.route('/batch/_/<string:batch_name>/run-directives', methods=['POST'])
@roles_required('Admin')
@handle_with_exception_factory
def update_run_directives(batch_name: str):
    if not _batch_runner_feature_enabled():
        return jsonify(_batch_runner_disabled_response()), 403

    try:
        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
    except FileNotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404

    payload = request.get_json(silent=True) or {}
    raw_directives = payload.get('run_directives')
    if raw_directives is None:
        return jsonify({'success': False, 'error': 'run_directives payload is required.'}), 400

    if isinstance(raw_directives, dict):
        parsed = raw_directives
    elif isinstance(raw_directives, list):
        parsed = {}
        for item in raw_directives:
            if not isinstance(item, dict):
                continue
            slug = item.get('slug') or item.get('key')
            if not slug:
                continue
            parsed[slug] = item.get('enabled', item.get('value'))
    else:
        return jsonify({'success': False, 'error': 'run_directives must be a list or object.'}), 400

    batch_runner.update_run_directives(parsed)
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
