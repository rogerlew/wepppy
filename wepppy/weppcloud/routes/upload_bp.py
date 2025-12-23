"""Upload-prefixed aliases for upload-capable endpoints."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from .batch_runner.batch_runner_bp import upload_geojson, upload_sbs_map
from .huc_fire import upload_sbs as huc_upload_sbs
from .nodb_api.climate_bp import task_upload_cli
from .nodb_api.disturbed_bp import task_upload_cover_transform, task_upload_sbs
from .rq.api.api import (
    api_build_landuse,
    api_build_treatments,
    api_run_ash,
    api_run_omni,
    run_omni_contrasts,
)

upload_bp = Blueprint("upload", __name__, url_prefix="/upload")


@upload_bp.route("/health")
def upload_health():
    return jsonify({
        "status": "ok",
        "scope": "upload",
        "message": "upload health endpoint",
        "prefix": request.script_root or "/upload",
    })


upload_bp.add_url_rule(
    "/runs/<string:runid>/<config>/tasks/upload_cli/",
    view_func=task_upload_cli,
    methods=["POST"],
)
upload_bp.add_url_rule(
    "/runs/<string:runid>/<config>/tasks/upload_sbs/",
    view_func=task_upload_sbs,
    methods=["POST"],
)
upload_bp.add_url_rule(
    "/runs/<string:runid>/<config>/tasks/upload_cover_transform",
    view_func=task_upload_cover_transform,
    methods=["POST"],
)
upload_bp.add_url_rule(
    "/huc-fire/tasks/upload_sbs/",
    view_func=huc_upload_sbs,
    methods=["POST"],
)
upload_bp.add_url_rule(
    "/batch/_/<string:batch_name>/upload-geojson",
    view_func=upload_geojson,
    methods=["POST"],
)
upload_bp.add_url_rule(
    "/batch/_/<string:batch_name>/upload-sbs-map",
    view_func=upload_sbs_map,
    methods=["POST"],
)
upload_bp.add_url_rule(
    "/runs/<string:runid>/<config>/rq/api/build_landuse",
    view_func=api_build_landuse,
    methods=["POST"],
)
upload_bp.add_url_rule(
    "/runs/<string:runid>/<config>/rq/api/build_treatments",
    view_func=api_build_treatments,
    methods=["POST"],
)
upload_bp.add_url_rule(
    "/runs/<string:runid>/<config>/rq/api/run_ash",
    view_func=api_run_ash,
    methods=["POST"],
)
upload_bp.add_url_rule(
    "/runs/<string:runid>/<config>/rq/api/run_omni",
    view_func=api_run_omni,
    methods=["POST"],
)
upload_bp.add_url_rule(
    "/runs/<string:runid>/<config>/rq/api/run_omni_contrasts",
    view_func=run_omni_contrasts,
    methods=["POST"],
)


__all__ = ["upload_bp"]
