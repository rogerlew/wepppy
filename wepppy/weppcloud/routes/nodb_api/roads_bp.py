"""Routes for Roads NoDb controls and reporting."""

from __future__ import annotations

import os
import time
from typing import Any, Dict

import redis
from flask import Response, jsonify, render_template
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Ron
from wepppy.nodb.mods.roads import Roads
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.roads_rq import (
    TIMEOUT,
    RoadsSingleFlightConflict,
    acquire_roads_submit_lock,
    ensure_no_active_roads_job,
    release_roads_submit_lock,
    run_roads_prepare_rq,
    run_roads_rq,
)
from wepppy.weppcloud.utils.helpers import authorize_and_handle_with_exception_factory

from .._common import *  # noqa: F401,F403

roads_bp = Blueprint("roads", __name__)


def _ensure_roads_controller(wd: str, cfg_fn: str) -> Roads:
    controller = Roads.tryGetInstance(wd)
    if controller is None:
        controller = Roads(wd, cfg_fn)
    return controller


def _sync_roads_enabled_state(wd: str, cfg_fn: str) -> Roads:
    ron = Ron.getInstance(wd)
    controller = _ensure_roads_controller(wd, cfg_fn)
    should_enable = "roads" in (ron.mods or [])
    if controller.enabled != should_enable:
        controller.set_enabled(should_enable)
    return controller


def _require_enabled(controller: Roads) -> Response | None:
    if not controller.enabled:
        return error_factory("Roads module is not enabled for this run.")
    return None


def _invalidate_roads_timestamp(wd: str) -> None:
    prep = RedisPrep.getInstance(wd)
    prep.remove_timestamp(TaskEnum.run_roads)


def _roads_run_results_report_links(
    runid: str,
    config: str,
    roads_report_resources: Dict[str, Any],
) -> list[Dict[str, str]]:
    required_relpaths_raw = roads_report_resources.get("required_relpaths", [])
    required_relpaths = {
        relpath.strip()
        for relpath in required_relpaths_raw
        if isinstance(relpath, str) and relpath.strip()
    }
    interchange_base = os.path.join("wepp", "roads", "output", "interchange")

    def _has_resources(*resource_names: str) -> bool:
        return all(os.path.join(interchange_base, name) in required_relpaths for name in resource_names)

    links: list[Dict[str, str]] = []

    if _has_resources("loss_pw0.out.parquet", "loss_pw0.hill.parquet", "loss_pw0.chn.parquet"):
        links.append(
            {
                "label": "Watershed Loss Summary",
                "href": url_for_run(
                    "wepp.report_wepp_loss",
                    runid=runid,
                    config=config,
                    output_scope="roads",
                ),
                "description": "Outlet, hillslope, and channel loss summary table.",
            }
        )
    if _has_resources("ebe_pw0.parquet", "totalwatsed3.parquet"):
        links.append(
            {
                "label": "Return Periods",
                "href": url_for_run(
                    "wepp.report_wepp_return_periods",
                    runid=runid,
                    config=config,
                    output_scope="roads",
                ),
                "description": "Roads-scoped recurrence and exceedance analysis.",
            }
        )
    if _has_resources("totalwatsed3.parquet"):
        links.extend(
            [
                {
                    "label": "Yearly Water Balance",
                    "href": url_for_run(
                        "wepp.report_wepp_yearly_watbal",
                        runid=runid,
                        config=config,
                        output_scope="roads",
                    ),
                    "description": "Roads-scoped annual watershed water-balance table.",
                },
                {
                    "label": "Daily Streamflow",
                    "href": url_for_run(
                        "wepp.plot_wepp_streamflow",
                        runid=runid,
                        config=config,
                        output_scope="roads",
                    ),
                    "description": "Roads-scoped daily streamflow graph and query payload.",
                },
            ]
        )
    if _has_resources("H.wat.parquet"):
        links.append(
            {
                "label": "Average Annual Water Balance",
                "href": url_for_run(
                    "wepp.report_wepp_avg_annual_watbal",
                    runid=runid,
                    config=config,
                    output_scope="roads",
                ),
                "description": "Roads-scoped average annual water-balance summary.",
            }
        )

    links.extend(
        [
            {
                "label": "GL Dashboard",
                "href": url_for_run(
                    "gl_dashboard.gl_dashboard",
                    runid=runid,
                    config=config,
                    output_scope="roads",
                ),
                "description": "Roads-scoped interchange datasets in map analytics.",
            },
            {
                "label": "Storm Event Analyzer",
                "href": url_for_run(
                    "storm_event_analyzer.storm_event_analyzer",
                    runid=runid,
                    config=config,
                    output_scope="roads",
                ),
                "description": "Roads-scoped event-level frequency and hydrology analysis.",
            },
        ]
    )
    segment_loss_relpath = roads_report_resources.get("roads_segment_loss_summary_relpath")
    if isinstance(segment_loss_relpath, str) and segment_loss_relpath.strip():
        links.extend(
            [
                {
                    "label": "Road Segment Loss Summary (Parquet)",
                    "href": url_for_run(
                        "browse.browse_tree",
                        runid=runid,
                        config=config,
                        subpath=segment_loss_relpath,
                    ),
                    "description": "Segment-level roads loss metrics derived from roads-scoped hillslope loss outputs.",
                },
                {
                    "label": "Road Segment Loss Summary (CSV)",
                    "href": (
                        url_for_run(
                            "download.download_with_subpath",
                            runid=runid,
                            config=config,
                            subpath=segment_loss_relpath,
                        )
                        + "?as_csv=1"
                    ),
                    "description": "On-demand CSV conversion from the segment-loss parquet (no CSV stored on disk).",
                },
            ]
        )
    return links


def _roads_run_results_report_resources_links(
    runid: str,
    config: str,
    roads_report_resources: Dict[str, Any],
) -> list[Dict[str, str]]:
    required_relpaths = roads_report_resources.get("required_relpaths", [])
    return [
        {
            "relpath": relpath,
            "href": url_for_run(
                "browse.browse_tree",
                runid=runid,
                config=config,
                subpath=relpath,
            ),
        }
        for relpath in required_relpaths
        if isinstance(relpath, str) and relpath.strip()
    ]


def _roads_results_context(runid: str, config: str, controller: Roads) -> Dict[str, Any]:
    roads_status = controller.query_status()
    roads_summary = controller.query_summary()
    roads_run_summary = roads_summary.get("last_run_summary")
    if not isinstance(roads_run_summary, dict):
        roads_run_summary = {}
    roads_report_resources = roads_run_summary.get("roads_report_resources")
    if not isinstance(roads_report_resources, dict):
        roads_report_resources = {}
    return {
        "roads_status": roads_status,
        "roads_summary": roads_summary,
        "roads_run_summary": roads_run_summary,
        "roads_report_resources": roads_report_resources,
        "roads_report_links": _roads_run_results_report_links(
            runid,
            config,
            roads_report_resources,
        ),
        "roads_resource_links": _roads_run_results_report_resources_links(
            runid,
            config,
            roads_report_resources,
        ),
    }


@roads_bp.route("/runs/<string:runid>/<config>/tasks/roads/upload_geojson", methods=["POST"])
@roads_bp.route("/runs/<string:runid>/<config>/tasks/roads/upload_geojson/", methods=["POST"])
@authorize_and_handle_with_exception_factory
def roads_upload_geojson(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    disabled_response = _require_enabled(controller)
    if disabled_response is not None:
        return disabled_response

    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return error_factory("Provide multipart `file` for Roads upload.")

    filename = str(uploaded.filename)
    if not filename.lower().endswith(".geojson"):
        return error_factory("Roads upload must be a .geojson file.")
    os.makedirs(controller.roads_upload_dir, exist_ok=True)
    source_path = os.path.join(controller.roads_upload_dir, "roads.upload.source.geojson")
    uploaded.save(source_path)

    try:
        summary = controller.set_uploaded_geojson(str(source_path))
    except FileNotFoundError as exc:
        response = error_factory(str(exc))
        response.status_code = 404
        return response
    except ValueError as exc:
        return error_factory(str(exc))

    _invalidate_roads_timestamp(wd)
    return success_factory(summary)


@roads_bp.route("/runs/<string:runid>/<config>/tasks/roads/set_params", methods=["POST"])
@roads_bp.route("/runs/<string:runid>/<config>/tasks/roads/set_params/", methods=["POST"])
@authorize_and_handle_with_exception_factory
def roads_set_params(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    disabled_response = _require_enabled(controller)
    if disabled_response is not None:
        return disabled_response

    payload = parse_request_payload(request)
    try:
        params = controller.set_params(payload)
    except ValueError as exc:
        return error_factory(str(exc))
    _invalidate_roads_timestamp(wd)
    return success_factory({"roads_params": params})


def _enqueue_roads_job(runid: str, *, func, prep_key: str) -> Dict[str, Any]:
    wd = get_wd(runid)
    prep = RedisPrep.getInstance(wd)

    submit_owner = f"{prep_key}:{int(time.time() * 1000)}"
    if not acquire_roads_submit_lock(runid, submit_owner):
        raise RoadsSingleFlightConflict("Roads enqueue already in progress for this run.")
    try:
        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
            ensure_no_active_roads_job(runid, prep, redis_conn)
            queue = Queue(connection=redis_conn)
            job = queue.enqueue_call(func=func, args=(runid,), timeout=TIMEOUT)
            prep.set_rq_job_id(prep_key, job.id)
        return {"job_id": job.id}
    finally:
        release_roads_submit_lock(runid, submit_owner)


@roads_bp.route("/runs/<string:runid>/<config>/tasks/roads/prepare_segments", methods=["POST"])
@roads_bp.route("/runs/<string:runid>/<config>/tasks/roads/prepare_segments/", methods=["POST"])
@authorize_and_handle_with_exception_factory
def roads_prepare_segments(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    disabled_response = _require_enabled(controller)
    if disabled_response is not None:
        return disabled_response

    try:
        return jsonify(_enqueue_roads_job(runid, func=run_roads_prepare_rq, prep_key="run_roads_prepare_rq"))
    except RoadsSingleFlightConflict as exc:
        response = error_factory(str(exc))
        response.status_code = 409
        return response


@roads_bp.route("/runs/<string:runid>/<config>/tasks/roads/run", methods=["POST"])
@roads_bp.route("/runs/<string:runid>/<config>/tasks/roads/run/", methods=["POST"])
@authorize_and_handle_with_exception_factory
def roads_run(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    disabled_response = _require_enabled(controller)
    if disabled_response is not None:
        return disabled_response

    try:
        return jsonify(_enqueue_roads_job(runid, func=run_roads_rq, prep_key="run_roads_rq"))
    except RoadsSingleFlightConflict as exc:
        response = error_factory(str(exc))
        response.status_code = 409
        return response


@roads_bp.route("/runs/<string:runid>/<config>/api/roads/config", methods=["GET"])
@authorize_and_handle_with_exception_factory
def roads_get_config(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    summary = controller.query_summary()
    return jsonify(
        {
            "enabled": summary.get("enabled", False),
            "roads_params": summary.get("roads_params", {}),
            "uploaded_geojson_relpath": summary.get("uploaded_geojson_relpath"),
            "uploaded_geojson_sha256": summary.get("uploaded_geojson_sha256"),
        }
    )


@roads_bp.route("/runs/<string:runid>/<config>/api/roads/config", methods=["POST"])
@authorize_and_handle_with_exception_factory
def roads_set_config(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    payload = parse_request_payload(request)
    try:
        params = controller.set_params(payload)
    except ValueError as exc:
        return error_factory(str(exc))
    _invalidate_roads_timestamp(wd)
    return success_factory({"roads_params": params})


@roads_bp.route("/runs/<string:runid>/<config>/api/roads/status", methods=["GET"])
@authorize_and_handle_with_exception_factory
def roads_status(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    return jsonify(controller.query_status())


@roads_bp.route("/runs/<string:runid>/<config>/api/roads/results", methods=["GET"])
@authorize_and_handle_with_exception_factory
def roads_results(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    summary = controller.query_summary()
    return jsonify(
        {
            "last_prepare_summary": summary.get("last_prepare_summary"),
            "last_run_summary": summary.get("last_run_summary"),
            "status": summary.get("status"),
            "errors": summary.get("errors", []),
        }
    )


@roads_bp.route("/runs/<string:runid>/<config>/query/roads", methods=["GET"])
@roads_bp.route("/runs/<string:runid>/<config>/query/roads/", methods=["GET"])
@authorize_and_handle_with_exception_factory
def query_roads(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    return jsonify(controller.query_status())


@roads_bp.route("/runs/<string:runid>/<config>/query/roads/summary", methods=["GET"])
@roads_bp.route("/runs/<string:runid>/<config>/query/roads/summary/", methods=["GET"])
@authorize_and_handle_with_exception_factory
def query_roads_summary(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    return jsonify(controller.query_summary())


@roads_bp.route("/runs/<string:runid>/<config>/report/roads/summary")
@roads_bp.route("/runs/<string:runid>/<config>/report/roads/summary/")
@authorize_and_handle_with_exception_factory
def report_roads_summary(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    context = _roads_results_context(runid, config, controller)
    return render_template(
        "reports/roads/summary.htm",
        runid=runid,
        config=config,
        **context,
        user=current_user,
    )


@roads_bp.route("/runs/<string:runid>/<config>/report/roads/results")
@roads_bp.route("/runs/<string:runid>/<config>/report/roads/results/")
@authorize_and_handle_with_exception_factory
def report_roads_results(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    context = _roads_results_context(runid, config, controller)
    return render_template(
        "controls/roads_reports.htm",
        runid=runid,
        config=config,
        run_results_title="Run Results",
        **context,
        user=current_user,
    )
