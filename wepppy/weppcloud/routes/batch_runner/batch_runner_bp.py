"""Admin-facing blueprint scaffolding for the Batch Runner (Phase 0)."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict, Optional

from flask import current_app, render_template

from .._common import Blueprint, roles_required
from wepppy.nodb.batch_runner import BatchRunner

batch_runner_bp = Blueprint(
    "batch_runner",
    __name__,
    template_folder="templates"
)


def _batch_runner_feature_enabled() -> bool:
    flag = current_app.config.get("BATCH_RUNNER_ENABLED", False)
    return bool(flag)


def _batch_root() -> Path:
    root = current_app.config.get("BATCH_RUNNER_ROOT")
    if root:
        return Path(root)
    # Default placeholder mirrors production layout but remains configurable.
    return Path("/wc1/batch")


def _serialize_manifest(manifest) -> Dict[str, object]:
    return asdict(manifest)


def _build_context(batch_name: Optional[str] = None) -> Dict[str, object]:
    enabled = _batch_runner_feature_enabled()
    manifest = BatchRunner.default_manifest()
    if batch_name:
        manifest.batch_name = batch_name

    context = {
        "feature_enabled": enabled,
        "batch_name": batch_name,
        "manifest_payload": _serialize_manifest(manifest),
        "page_title": "WEPPcloud Batch Runner",
        "site_prefix": current_app.config.get("SITE_PREFIX", ""),
        "batch_root": str(_batch_root()),
    }
    return context


@batch_runner_bp.route("/batch/create/", methods=["GET"])
@roles_required("Admin")
def create_batch_project():
    """Render the placeholder create page for Batch Runner (Phase 0)."""
    context = _build_context()
    return render_template("create.htm", **context)


@batch_runner_bp.route("/batch/<string:batch_name>/", methods=["GET"])
@roles_required("Admin")
def view_batch(batch_name: str):
    """Render the placeholder batch detail page for Batch Runner (Phase 0)."""
    context = _build_context(batch_name=batch_name)
    return render_template("manage.htm", **context)
