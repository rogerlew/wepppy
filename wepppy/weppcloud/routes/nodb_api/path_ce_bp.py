"""Routes for PATH cost-effective blueprint extracted from app.py."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import redis
from flask import Response
from rq import Queue

from .._common import *  # noqa: F401,F403
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Ron
from wepppy.nodb.mods.path_ce import PathCostEffective
from wepppy.rq.path_ce_rq import TIMEOUT, run_path_cost_effective_rq
from wepppy.weppcloud.utils.helpers import authorize_and_handle_with_exception_factory

path_ce_bp = Blueprint("path_ce", __name__)


def _coerce_optional_float(value: Any) -> Optional[float]:
    if value in (None, "", [], ()):
        return None
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        value = value[0]
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any, default: float = 0.0) -> float:
    coerced = _coerce_optional_float(value)
    return default if coerced is None else coerced


def _normalize_severity(value: Any) -> Optional[List[str]]:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = [value]
    try:
        normalized = [str(item).strip() for item in value if item not in (None, "")]
    except TypeError:
        return None
    return normalized or None


def _normalize_treatment_options(options: Any) -> List[Dict[str, Any]]:
    if isinstance(options, dict):
        options = [options]
    if not isinstance(options, list):
        return []
    normalized: List[Dict[str, Any]] = []
    for item in options:
        if isinstance(item, dict):
            normalized.append(dict(item))
    return normalized


def _build_config_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(raw)
    payload["sddc_threshold"] = _coerce_float(raw.get("sddc_threshold"))
    payload["sdyd_threshold"] = _coerce_float(raw.get("sdyd_threshold"))

    slope_min = _coerce_optional_float(raw.get("slope_min") or raw.get("slope_range_min"))
    slope_max = _coerce_optional_float(raw.get("slope_max") or raw.get("slope_range_max"))
    payload["slope_range"] = [slope_min, slope_max]
    payload.pop("slope_min", None)
    payload.pop("slope_max", None)
    payload.pop("slope_range_min", None)
    payload.pop("slope_range_max", None)

    payload["severity_filter"] = _normalize_severity(raw.get("severity_filter"))
    payload["treatment_options"] = _normalize_treatment_options(raw.get("treatment_options"))

    return payload


@path_ce_bp.route(
    "/runs/<string:runid>/<config>/tasks/path_cost_effective_enable",
    methods=["GET"],
)
def enable_path_cost_effective(runid: str, config: str):
    authorize(runid, config)
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)

        existing_mods = ron.mods or []
        if "path_ce" in existing_mods:
            return error_factory("PATH cost-effective module already enabled")

        with ron.locked():
            mods = ron.mods
            if mods is None:
                ron._mods = ["path_ce"]
            elif "path_ce" not in mods:
                ron._mods.append("path_ce")

        cfg_fn = f"{config}.cfg"
        PathCostEffective(wd, cfg_fn)

        return success_factory("Reload project to access PATH cost-effective controls")
    except Exception:
        return exception_factory(
            "Error enabling PATH cost-effective module", runid=runid
        )


def _ensure_controller(wd: str, cfg: str) -> PathCostEffective:
    try:
        return PathCostEffective.getInstance(wd)
    except FileNotFoundError:
        return PathCostEffective(wd, cfg)


@path_ce_bp.route(
    "/runs/<string:runid>/<config>/api/path_ce/config",
    methods=["GET"],
)
@authorize_and_handle_with_exception_factory
def get_path_cost_effective_config(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _ensure_controller(wd, f"{config}.cfg")
    return jsonify({"config": controller.config})


@path_ce_bp.route(
    "/runs/<string:runid>/<config>/api/path_ce/config",
    methods=["POST"],
)
@authorize_and_handle_with_exception_factory
def update_path_cost_effective_config(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _ensure_controller(wd, f"{config}.cfg")
    raw_payload = parse_request_payload(request)
    payload = _build_config_payload(raw_payload)
    controller.config = payload
    return success_factory({"config": controller.config})


@path_ce_bp.route(
    "/runs/<string:runid>/<config>/api/path_ce/status",
    methods=["GET"],
)
@authorize_and_handle_with_exception_factory
def get_path_cost_effective_status(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = PathCostEffective.tryGetInstance(wd)
    if controller is None:
        return jsonify(
            {"status": "uninitialized", "status_message": "Module not configured.", "progress": 0.0}
        )
    return jsonify(
        {
            "status": controller.status,
            "status_message": controller.status_message,
            "progress": controller.progress,
        }
    )


@path_ce_bp.route(
    "/runs/<string:runid>/<config>/api/path_ce/results",
    methods=["GET"],
)
@authorize_and_handle_with_exception_factory
def get_path_cost_effective_results(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = PathCostEffective.tryGetInstance(wd)
    if controller is None:
        return jsonify({"results": {}})
    return jsonify({"results": controller.results})


@path_ce_bp.route(
    "/runs/<string:runid>/<config>/tasks/path_cost_effective_run",
    methods=["POST"],
)
@authorize_and_handle_with_exception_factory
def run_path_cost_effective(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)
    if "path_ce" not in (ron.mods or []):
        return error_factory("PATH Cost-Effective module is not enabled for this run.")

    _ensure_controller(wd, f"{config}.cfg")

    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
        queue = Queue(connection=redis_conn)
        job = queue.enqueue_call(
            func=run_path_cost_effective_rq,
            args=(runid,),
            timeout=TIMEOUT,
        )

    return jsonify({"Success": True, "job_id": job.id})
