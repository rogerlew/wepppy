"""Admin-facing blueprint for the Batch Runner."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Dict, Optional, Sequence

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_security import current_user

from .._common import Blueprint, roles_required
from wepppy.nodb.base import get_configs, get_config_dir
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


def _existing_batches() -> Sequence[str]:
    root = _batch_root()
    if not root.exists():
        return ()
    return tuple(sorted(p.name for p in root.iterdir() if p.is_dir()))


def _load_manifest(batch_name: Optional[str]) -> Dict[str, object]:
    if not batch_name:
        return _serialize_manifest(BatchRunner.default_manifest())

    batch_dir = _batch_root() / batch_name
    try:
        runner = BatchRunner.getInstance(str(batch_dir))
    except FileNotFoundError:
        return _serialize_manifest(BatchRunner.default_manifest())
    except Exception as exc:  # pragma: no cover - defensive logging path
        current_app.logger.warning(
            "Unable to load batch runner manifest for %s: %s", batch_name, exc
        )
        return _serialize_manifest(BatchRunner.default_manifest())
    return runner.manifest_dict()


def _build_context(batch_name: Optional[str] = None) -> Dict[str, object]:
    enabled = _batch_runner_feature_enabled()
    manifest_payload = _load_manifest(batch_name)


    context = {
        "feature_enabled": enabled,
        "batch_name": batch_name,
        "manifest_payload": manifest_payload,
        "page_title": "WEPPcloud Batch Runner",
        "site_prefix": current_app.config.get("SITE_PREFIX", ""),
        "batch_root": str(_batch_root()),
        "available_configs": get_configs(),
        "existing_batches": _existing_batches(),
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
) -> Dict[str, object]:
    batch_root = _batch_root()
    base_config_cfg = f"{base_config}.cfg"
    config_file = Path(get_config_dir()) / base_config_cfg
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration '{config_file}' does not exist.")

    batch_root.mkdir(parents=True, exist_ok=True)

    batch_wd = batch_root / batch_name
    if batch_wd.exists():
        raise FileExistsError(f"Batch '{batch_name}' already exists.")

    subdirs = [batch_wd, batch_wd / "resources", batch_wd / "logs"]
    for directory in subdirs:
        directory.mkdir(parents=True, exist_ok=False)

    # create batch_dir
    batch_wd.mkdir(parents=True, exist_ok=False)
    runner = BatchRunner(
        str(batch_wd), 
        f"batch/{batch_config}.cfg", 
        base_config_cfg)

    subdirs = [batch_wd / "resources", batch_wd / "logs"]
    for directory in subdirs:
        directory.mkdir(parents=True, exist_ok=False)

    timestamp = datetime.now(timezone.utc).isoformat()
    history_entry = {
        "event": "created",
        "timestamp": timestamp,
    }
    if created_by:
        history_entry["user"] = created_by

    runner.update_manifest(
        batch_name=batch_name,
        batch_config=batch_config,
        base_config=base_config,
        created_at=timestamp,
        created_by=created_by,
        history=[history_entry],
    )

    return {
        "path": batch_wd,
        "manifest": runner.manifest_dict(),
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

        manifest = result["manifest"]
        created_name = manifest.get("batch_name") or batch_name_input.strip()
        flash(f"Batch '{created_name}' created successfully.", "success")
        return redirect(url_for("batch_runner.view_batch", batch_name=created_name))

    context.setdefault("form_state", {"batch_name": "", "config": context["available_configs"][0] if context["available_configs"] else ""})
    return render_template("create.htm", **context)


@batch_runner_bp.route("/batch/<string:batch_name>/", methods=["GET"])
@roles_required("Admin")
def view_batch(batch_name: str):
    """Render the placeholder batch detail page for Batch Runner (Phase 0)."""
    context = _build_context(batch_name=batch_name)
    return render_template("manage.htm", **context)
