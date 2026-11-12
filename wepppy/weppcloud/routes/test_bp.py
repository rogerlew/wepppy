from __future__ import annotations

from wepppy.weppcloud.routes._common import parse_json_payload, RequestPayloadError

import os
import math
import time
import shutil
from pathlib import Path
from typing import Dict, Any, Tuple

from flask import Blueprint, jsonify, request, current_app
from flask_security import current_user
from werkzeug.exceptions import BadRequest, Forbidden, NotFound, Unauthorized
from wepppy.weppcloud.utils import auth_tokens

from wepppy.weppcloud.routes.run_0.run_0_bp import create_run_dir
from wepppy.weppcloud.utils.helpers import url_for_run, get_wd
from wepppy.weppcloud.routes.readme_md import ensure_readme_on_create
from wepppy.weppcloud.utils.runid import generate_runid
from wepppy.nodb.core.ron import Ron


def _require_enabled() -> None:
    if (current_app.config.get("WEPPCLOUD_DEPLOYMENT_PROFILE") not in {"development", "test"}
            or not current_app.config.get("TEST_SUPPORT_ENABLED", False)):
        raise NotFound()

    parts = request.headers.get("Authorization", "").split()
    try:
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise auth_tokens.JWTDecodeError("Missing bearer")
        claims = auth_tokens.decode_token(parts[1], audience="weppcloud-test-support")
        issued, expires = claims.get("iat"), claims.get("exp")
        if (any(isinstance(value, bool) or not isinstance(value, (int, float))
                or (isinstance(value, float) and not math.isfinite(value)) for value in (issued, expires))
                or not issued < expires <= issued + 3600 or expires <= time.time()):
            raise auth_tokens.JWTDecodeError("Invalid support lifetime")
    except auth_tokens.JWTDecodeError:
        current_app.logger.info("test_support outcome=unauthorized route=%s", request.endpoint)
        raise Unauthorized() from None
    scopes = claims.get("scope", "")
    if isinstance(scopes, str):
        scopes = scopes.split(auth_tokens.get_jwt_config().scope_separator)
    if not isinstance(scopes, (list, tuple)) or "test:support" not in scopes:
        current_app.logger.info("test_support outcome=forbidden route=%s", request.endpoint)
        raise Forbidden()
    current_app.logger.info("test_support outcome=authorized route=%s", request.endpoint)


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
    shutil.rmtree(path, ignore_errors=True)


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
        ron = Ron(wd, cfg_with_params)
        try:
            from wepppy.weppcloud.utils.run_ttl import initialize_ttl

            initialize_ttl(wd)
        except (ImportError, OSError, RuntimeError, ValueError):
            current_app.logger.exception("Failed to initialize TTL for test run")
        ensure_readme_on_create(runid, config)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:  # clean up directory and re-raise
        current_app.logger.exception("Failed to create test run runid=%s config=%s wd=%s", runid, config, wd)
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
        runid = generate_runid()
        wd_path = root_path / runid
        if wd_path.exists():
            continue
        wd_path.mkdir(parents=True, exist_ok=False)
        return runid, str(wd_path)


test_bp = Blueprint("test_bp", __name__, url_prefix="/tests/api")


test_bp.register_error_handler(RequestPayloadError, lambda exc: (jsonify(exc.envelope()), 400))

@test_bp.get("/ping")
def ping():
    _require_enabled()
    return jsonify({"message": "test support online"}), 200


@test_bp.post("/create-run")
def create_run_endpoint():
    _require_enabled()

    payload = parse_json_payload(request)
    config = payload.get("config", "dev_unit_1")
    overrides = payload.get("overrides", {}) or {}

    result = _spawn_run(config, overrides)
    return jsonify({"run": result}), 201


@test_bp.delete("/run/<runid>")
def delete_run_endpoint(runid: str):
    _require_enabled()

    wd = get_wd(runid, prefer_active=False)
    path = Path(wd)
    if not path.exists():
        raise NotFound("Run directory not found")

    _cleanup_run_directory(path)
    return jsonify({"runid": runid}), 200


def register_csrf_exemptions(csrf) -> None:
    # Non-ambient scoped bearer is required before every operation.
    for view in (ping, create_run_endpoint, delete_run_endpoint):
        csrf.exempt(view)


@test_bp.errorhandler(Unauthorized)
def _unauthorized(exc):
    return jsonify({"error": "Unauthorized"}), 401


@test_bp.errorhandler(Forbidden)
def _forbidden(exc):
    return jsonify({"error": "Forbidden"}), 403
