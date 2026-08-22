"""Routes for PATH cost-effective blueprint extracted from app.py."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import redis
from flask import Response
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from .._common import *  # noqa: F401,F403
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Ron
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.path_ce import PathCostEffective
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.rq.job_id import new_rq_job_id
from wepppy.rq.submission_recovery import (
    RqSubmissionConflict,
    prepare_redisprep_job_id,
    rq_submission_lock,
)
from wepppy.rq.path_ce_rq import TIMEOUT, run_path_cost_effective_rq
from wepppy.weppcloud.utils.helpers import authorize_and_handle_with_exception_factory, run_lifecycle_mutation
from .project_bp import set_project_mod_state

path_ce_bp = Blueprint("path_ce", __name__)


def _blank_to_none(value: Any) -> Any:
    """Map form-style 'unset' markers to None; invalid values pass through
    unchanged so the controller's strict normalization rejects them."""
    if value in (None, "", [], ()):
        return None
    if isinstance(value, (list, tuple)):
        return _blank_to_none(value[0]) if value else None
    return value


def _parse_treatments(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
        raise ValueError("treatments must be a list of treatment objects")
    return [dict(item) for item in raw]


def _build_config_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt request structure only; value validation stays in the controller,
    so present-but-invalid fields raise instead of coercing silently."""
    payload: Dict[str, Any] = {}
    if "sddc_threshold" in raw:
        payload["sddc_threshold"] = _blank_to_none(raw.get("sddc_threshold"))
    if "sdyd_threshold" in raw:
        payload["sdyd_threshold"] = _blank_to_none(raw.get("sdyd_threshold"))

    if "slope_range" in raw:
        payload["slope_range"] = raw.get("slope_range")
    else:
        slope_min = _blank_to_none(raw.get("slope_min", raw.get("slope_range_min")))
        slope_max = _blank_to_none(raw.get("slope_max", raw.get("slope_range_max")))
        if slope_min is not None or slope_max is not None:
            payload["slope_range"] = [slope_min, slope_max]

    if "severity_filter" in raw:
        payload["severity_filter"] = raw.get("severity_filter")

    if "treatments" in raw:
        payload["treatments"] = _parse_treatments(raw.get("treatments"))

    return payload


@path_ce_bp.route(
    "/runs/<string:runid>/<config>/tasks/path_cost_effective_enable",
    methods=["GET"],
)
@authorize_and_handle_with_exception_factory
@run_lifecycle_mutation
def enable_path_cost_effective(runid: str, config: str):
    authorize(runid, config)
    try:
        state = set_project_mod_state(runid, config, "path_ce", True)
        if not state.get("changed", False):
            return error_factory("PATH cost-effective module already enabled")
        return success_factory("Reload project to access PATH cost-effective controls")
    except ValueError as exc:
        return error_factory(str(exc))
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/path_ce_bp.py:111", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory(
            "Error enabling PATH cost-effective module", runid=runid
        )


def _ensure_controller(wd: str, cfg: str) -> PathCostEffective:
    try:
        return PathCostEffective.getInstance(wd)
    except FileNotFoundError:
        return PathCostEffective(wd, cfg)


def _active_path_ce_job_id(wd: str, redis_conn: "redis.Redis") -> Optional[str]:
    """Return the job id of an in-flight PATH-CE run for this project, if any."""
    prep = RedisPrep.tryGetInstance(wd)
    if prep is None:
        return None
    job_id = prep.get_rq_job_id("run_path_ce")
    if not job_id:
        return None
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except NoSuchJobError:
        return None
    if job.get_status(refresh=False) in ("queued", "started", "scheduled"):
        return job_id
    return None


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
    try:
        payload = _build_config_payload(raw_payload)
        controller.config = {**controller.config, **payload}
    except ValueError as exc:
        return error_factory(str(exc))
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
            {
                "status": "uninitialized",
                "status_message": "Module not configured.",
                "progress": 0.0,
                "precondition_errors": [],
            }
        )
    return jsonify(
        {
            "status": controller.status,
            "status_message": controller.status_message,
            "progress": controller.progress,
            "precondition_errors": getattr(controller, "precondition_errors", []),
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

    controller = _ensure_controller(wd, f"{config}.cfg")
    raw_payload = parse_request_payload(request)
    if raw_payload:
        try:
            payload = _build_config_payload(raw_payload)
            controller.config = {**controller.config, **payload}
        except ValueError as exc:
            return error_factory(str(exc))

    if not Disturbed.getInstance(wd).has_sbs:
        return error_factory("PATH Cost-Effective requires an SBS map. Upload or configure one in Disturbed before running.")

    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
        try:
            lock_context = rq_submission_lock(redis_conn, f"{runid}:path_ce", lifecycle_key=runid)
            lease = lock_context.__enter__()
        except RqSubmissionConflict as exc:
            return error_factory(str(exc))
        try:
            active_job_id = _active_path_ce_job_id(wd, redis_conn)
            if active_job_id is not None:
                return error_factory(
                    f"A PATH Cost-Effective run is already in progress (job {active_job_id}). "
                    f"Wait for it to finish before starting another."
                )
            prep = RedisPrep.getInstance(wd)
            replacement_job_id = new_rq_job_id()
            try:
                prepare_redisprep_job_id(
                    prep,
                    job_key="run_path_ce",
                    replacement_job_id=replacement_job_id,
                    connection=redis_conn,
                    runid=runid,
                    expected_root_module=run_path_cost_effective_rq.__module__,
                    expected_root_func_name=(
                        f"{run_path_cost_effective_rq.__module__}."
                        f"{run_path_cost_effective_rq.__qualname__}"
                    ),
                    allowed_origins=("default",),
                    lease_checkpoint=lease.checkpoint,
                )
            except RqSubmissionConflict as exc:
                return error_factory(str(exc))
            queue = Queue(connection=redis_conn)
            lease.checkpoint()
            job = queue.enqueue_call(
                func=run_path_cost_effective_rq,
                args=(runid,),
                timeout=TIMEOUT,
                job_id=replacement_job_id,
            )
        finally:
            lock_context.__exit__(None, None, None)

    return jsonify({"job_id": job.id})
