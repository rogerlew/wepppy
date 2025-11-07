from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Tuple

import awesome_codename

from flask import Blueprint, jsonify, request, current_app
from flask_security import current_user
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from wepppy.weppcloud.routes.run_0.run_0_bp import create_run_dir
from wepppy.weppcloud.utils.helpers import url_for_run, get_wd
from wepppy.weppcloud.routes.readme_md import ensure_readme_on_create
from wepppy.nodb.core.ron import Ron


def _require_enabled() -> None:
    if not current_app.config.get("TEST_SUPPORT_ENABLED", False):
        raise Forbidden("Test support endpoints are disabled")


def _build_cfg(config: str, overrides: Dict[str, Any]) -> str:
    cfg = config if config.endswith(".cfg") else f"{config}.cfg"
    if overrides:
        query = "&".join(
            [f"{key}={value}" for key, value in overrides.items() if value is not None]
        )
        if query:
            cfg = f"{cfg}?{query}"
    return cfg


def _cleanup_run_directory(path: Path) -> None:
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


def _spawn_run(config: str, overrides: Dict[str, Any]) -> Dict[str, Any]:
    cfg_with_params = _build_cfg(config, overrides)

    # create run directory using existing helper (generates unique run id)
    run_root_override = os.environ.get("SMOKE_RUN_ROOT")
    if run_root_override:
        runid, wd = _create_run_dir_override(run_root_override)
    else:
        runid, wd = create_run_dir(current_user)
    wd_path = Path(wd)

    try:
        Ron(wd, cfg_with_params)
        ensure_readme_on_create(runid, config)
    except Exception as exc:  # clean up directory and re-raise
        _cleanup_run_directory(wd_path)
        raise BadRequest(str(exc)) from exc

    run_url = url_for_run("run_0.runs0", runid=runid, config=config)
    url_params = []
    if overrides:
        url_params.extend([f"{key}={value}" for key, value in overrides.items() if value is not None])
    
    # Always add playwright_load_all for testing
    url_params.append("playwright_load_all=true")
    
    if url_params:
        run_url = f"{run_url}?{'&'.join(url_params)}"

    return {
        "runid": runid,
        "config": config,
        "url": run_url,
        "cfg": cfg_with_params,
    }


def _create_run_dir_override(run_root: str) -> Tuple[str, str]:
    root_path = Path(run_root).expanduser().resolve()
    root_path.mkdir(parents=True, exist_ok=True)

    while True:
        runid = awesome_codename.generate_codename().replace(' ', '-').replace("'", '')
        wd_path = root_path / runid
        if wd_path.exists():
            continue
        wd_path.mkdir(parents=True, exist_ok=False)
        return runid, str(wd_path)


test_bp = Blueprint("test_bp", __name__, url_prefix="/tests/api")


@test_bp.get("/ping")
def ping():
    _require_enabled()
    return jsonify({"success": True, "message": "test support online"}), 200


@test_bp.post("/create-run")
def create_run_endpoint():
    _require_enabled()

    payload = request.get_json(silent=True) or {}
    config = payload.get("config", "dev_unit_1")
    overrides = payload.get("overrides", {}) or {}

    result = _spawn_run(config, overrides)
    return jsonify({"success": True, "run": result}), 201


@test_bp.delete("/run/<runid>")
def delete_run_endpoint(runid: str):
    _require_enabled()

    wd = get_wd(runid, prefer_active=False)
    path = Path(wd)
    if not path.exists():
        raise NotFound("Run directory not found")

    _cleanup_run_directory(path)
    return jsonify({"success": True, "runid": runid}), 200
