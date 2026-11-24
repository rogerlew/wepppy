"""Routes for Roads NoDb controls and reporting."""

from __future__ import annotations

from wepppy.wepp.interchange import _roads_lifecycle as roads_lifecycle

import os
from pathlib import Path
from typing import Any, Dict

import redis
from flask import Response, jsonify, render_template
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.microservices.vector_upload_normalization import (
    RetentionActor,
    VectorUploadError,
    prepare_vector_upload,
    validate_feature_collection_geometries,
)
from wepppy.nodb.core import Ron
from wepppy.nodb.mods.roads import Roads
from wepppy.nodb.mods.roads._constants import ROADS_UPLOAD_GEOJSON_MAX_BYTES
from wepppy.nodb.mods.roads.osm_download import download_osm_roads
from wepppy.topo.osm_roads.errors import OSMRoadsUpstreamError, OSMRoadsValidationError
from wepppy.weppcloud.utils.feature_access_flask import feature_decision
from wepppy.weppcloud.utils.feature_access_runtime import decision_status
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.job_id import new_rq_job_id
from wepppy.rq.roads_rq import (
    TIMEOUT,
    RoadsSingleFlightConflict,
    ensure_no_active_roads_job,
    reconcile_deferred_roads_jobs,
    run_roads_prepare_rq,
    run_roads_rq,
)
from wepppy.rq.submission_recovery import RqSubmissionConflict, rq_submission_lock
from wepppy.weppcloud.utils.cap_guard import requires_cap
from wepppy.weppcloud.utils.helpers import (
    authorize_and_handle_with_exception_factory,
    upload_error_factory,
    upload_exception_factory,
)

from .._common import *  # noqa: F401,F403

roads_bp = Blueprint("roads", __name__)


@roads_bp.after_request
def _roads_no_store(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


def _ensure_roads_controller(wd: str, cfg_fn: str) -> Roads:
    controller = Roads.tryGetInstance(wd)
    if controller is None:
        controller = Roads(wd, cfg_fn)
    return controller


def _sync_roads_enabled_state(wd: str, cfg_fn: str) -> Roads:
    ron = Ron.getInstance(wd)
    controller = Roads.tryGetInstance(wd)
    if controller is None:
        raise FileNotFoundError("Roads controller has not been initialized")
    should_enable = "roads" in (ron.mods or [])
    if controller.enabled != should_enable:
        raise RuntimeError(
            "Roads is unavailable because of a server configuration problem. "
            "This request could not be processed. "
            "Contact support and include this project's URL."
        )
    return controller


def _parameterization_view_state(wd: str) -> Dict[str, Any]:
    """Read optional Roads state without creating or enabling a controller."""
    ron = Ron.getInstance(wd)
    enabled = "roads" in (ron.mods or [])
    controller = Roads.tryGetInstance(wd)
    readonly = os.path.exists(os.path.join(wd, "READONLY")) or bool(getattr(ron, "readonly", False))
    if controller is None:
        return {"enabled": enabled, "readonly": readonly, "controller_present": False,
                "parameterization": Roads.initial_parameterization_preview() if enabled else None,
                "status": "absent"}
    try:
        summary = controller.query_summary()
    except (roads_lifecycle.RoadsResultsUnavailable, roads_lifecycle.RoadsOperationBusy):
        # A running writer owns scientific admission. Render an inspectable shell
        # without bypassing that guard or guessing at a partly updated snapshot.
        return {"enabled": enabled and bool(controller.enabled), "readonly": readonly,
                "controller_present": True, "parameterization": None,
                "status": "running", "busy": True}
    summary.update(enabled=enabled and bool(controller.enabled), readonly=readonly,
                   controller_present=True)
    return summary


@roads_bp.post("/runs/<string:runid>/<config>/api/roads/osm.geojson")
@authorize_and_handle_with_exception_factory
def roads_osm_download(runid: str, config: str) -> Response:
    wd = str(load_run_context(runid, config).active_root)
    decision = feature_decision("roads", wd=wd, operation="act")
    if not decision.allowed:
        return error_factory("Downloading roads is unavailable for this project or account.",
                             code=decision.reason, status_code=decision_status(decision))
    ron = Ron.getInstance(wd)
    if "roads" not in (ron.mods or []):
        return error_factory("Enable Roads before downloading.", status_code=403)
    try:
        payload = download_osm_roads(ron.extent)
    except OSMRoadsValidationError as exc:
        return error_factory(str(exc), status_code=422)
    except OSMRoadsUpstreamError as exc:
        details = dict(exc.context)
        reference = details.pop("reference", None)
        status = 504 if exc.code == "upstream_timeout" else 503
        if exc.code in {"upstream_invalid_response", "upstream_error"}:
            status = 502
        ron.logger.warning("Roads OSM download failed: %s; attempts=%s elapsed_s=%s upstream_status=%s reference=%s",
                           exc.code, details.get("attempts"), details.get("elapsed_seconds"),
                           details.get("upstream_status"), reference)
        return error_factory(str(exc), code=exc.code, status_code=status, details=details, error_id=reference)
    response = jsonify(payload)
    if response.calculate_content_length() > ROADS_UPLOAD_GEOJSON_MAX_BYTES:
        return error_factory("This road file exceeds the Roads upload size limit. Use a smaller local inventory.",
                             status_code=422)
    response.mimetype = "application/geo+json"
    response.headers["Content-Disposition"] = 'attachment; filename="osm-roads.geojson"'
    return response


@roads_bp.route("/runs/<string:runid>/<config>/roads/parameterization", methods=["GET"])
@authorize_and_handle_with_exception_factory
def roads_parameterization(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    state = _parameterization_view_state(str(ctx.active_root))
    return render_template(
        "roads/parameterization.htm", runid=runid, config=config,
        parameterization_state=state,
        parameterization_roles=(("road", "Road"), ("fill", "Fill"), ("buffer", "Forest / buffer")),
        parameterization_fields=(
            ("ksat_mm_h", "Baseline effective hydraulic conductivity", "mm/h"),
            ("ki_kg_s_m4", "Interrill erodibility (Ki)", "kg s/m⁴"),
            ("kr_s_m", "Rill erodibility (Kr)", "s/m"),
            ("critical_shear_pa", "Critical shear", "Pa"),
        ),
    )


def _require_enabled(controller: Roads) -> Response | None:
    if not controller.enabled:
        return error_factory("Roads module is not enabled for this run.")
    return None


def _invalidate_roads_timestamp(wd: str) -> None:
    prep = RedisPrep.getInstance(wd)
    prep.remove_timestamp(TaskEnum.run_roads)


def _run_vector_evidence_roots(wd: str) -> tuple[Path, ...]:
    root = Path(wd)
    return (
        root / "roads" / "vector_upload_attempts",
        root / "ag_fields" / "vector_upload_attempts",
        root / "_pups" / "omni" / "contrasts" / "vector_upload_attempts",
        root / "archives" / "private",
    )


def _roads_retention_actor() -> RetentionActor:
    try:
        user_id = int(getattr(current_user, "id", 0) or 0)
    except (TypeError, ValueError):
        user_id = 0
    if user_id > 0:
        return RetentionActor("human", user_id)
    return RetentionActor("unattributed", None)


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
                    roads="on",
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
    if not roads_lifecycle.available(controller.wd) or not isinstance(roads_report_resources, dict):
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
    controller = Roads.tryGetInstance(wd)
    if controller is None:
        decision = feature_decision("roads", wd=wd, operation="act")
        if not decision.allowed:
            return upload_error_factory("Uploading roads is unavailable for this project or account.",
                                        status_code=decision_status(decision), code=decision.reason)
        ron = Ron.getInstance(wd)
        enabled = "roads" in (ron.mods or [])
    else:
        enabled = _sync_roads_enabled_state(wd, f"{config}.cfg").enabled
    if not enabled:
        return upload_error_factory(
            "Roads module is not enabled for this run.",
            status_code=400,
            code="validation_error",
        )

    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return upload_error_factory(
            "Provide multipart `file` for Roads upload.",
            status_code=400,
            code="missing_upload_file",
        )

    filename = str(uploaded.filename)
    upload_dir = Path(controller.roads_upload_dir) if controller is not None else Path(wd) / "roads"
    attempt_root = upload_dir / "vector_upload_attempts"

    def _validate_candidate(_path: Path, payload: Dict[str, object]) -> Dict[str, object]:
        return validate_feature_collection_geometries(
            payload,
            ("LineString", "MultiLineString"),
        )

    try:
        if controller is None:
            upload_dir.mkdir(exist_ok=True)
        prepared = prepare_vector_upload(
            raw_filename=filename,
            stream=uploaded.stream,
            endpoint_max_bytes=ROADS_UPLOAD_GEOJSON_MAX_BYTES,
            attempt_root=attempt_root,
            evidence_roots=_run_vector_evidence_roots(wd),
            filesystem_root=Path(wd),
            project_key=f"run:{runid}",
            workflow="roads",
            project_identity=runid,
            actor=_roads_retention_actor(),
            validator=_validate_candidate,
        )

        def publish(candidate, commit):
            active = controller
            if active is None:
                active = _ensure_roads_controller(wd, f"{ron.config_stem}.cfg")
                active.set_enabled(True)
            return active.set_uploaded_geojson(str(candidate), publication_commit=commit)

        canonical_path = upload_dir / "roads.uploaded.geojson"
        summary = prepared.publish_transactional(
            mutation=publish,
            canonical_path=canonical_path,
            canonical_relative_path=os.fspath(canonical_path.relative_to(wd)),
        )
    except VectorUploadError as exc:
        return upload_error_factory(str(exc), status_code=exc.status_code, code=exc.code)
    except (FileNotFoundError, ValueError) as exc:
        return upload_error_factory(str(exc), status_code=400, code="validation_error")
    except OSError as exc:
        return upload_exception_factory(
            "Failed to persist Roads upload.",
            status_code=500,
            code="internal_error",
            details=str(exc),
        )

    _invalidate_roads_timestamp(wd)
    return success_factory(summary)


@roads_bp.route("/runs/<string:runid>/<config>/tasks/roads/set_params", methods=["POST"])
@roads_bp.route("/runs/<string:runid>/<config>/tasks/roads/set_params/", methods=["POST"])
@authorize_and_handle_with_exception_factory
def roads_set_params(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    payload = parse_request_payload(request)
    if "parameterization" in payload:
        ron = Ron.getInstance(wd)
        if os.path.exists(os.path.join(wd, "READONLY")) or bool(getattr(ron, "readonly", False)):
            return error_factory("This project is read-only.", status_code=403)
        if "roads" not in (ron.mods or []):
            return error_factory("Roads module is not enabled for this run.")
        controller = Roads.tryGetInstance(wd)
        if controller is None:
            try:
                Roads.validate_initial_params(payload)
            except ValueError as exc:
                return error_factory(str(exc))
            controller = _ensure_roads_controller(wd, f"{config}.cfg")
            controller.set_enabled(True)
        else:
            controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    else:
        controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    disabled_response = _require_enabled(controller)
    if disabled_response is not None:
        return disabled_response

    try:
        params = controller.set_params(payload)
    except ValueError as exc:
        return error_factory(str(exc))
    _invalidate_roads_timestamp(wd)
    summary = controller.query_summary()
    return success_factory(
        {
            "roads_params": params,
            "parameterization": summary.get("parameterization"),
            "attribute_field_map": summary.get("attribute_field_map") or {},
            "discovered_attribute_catalog": summary.get("discovered_attribute_catalog"),
        }
    )


def _enqueue_roads_job(runid: str, *, func, prep_key: str) -> Dict[str, Any]:
    wd = get_wd(runid)
    prep = RedisPrep.getInstance(wd)

    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
        try:
            lock_context = rq_submission_lock(redis_conn, f"{runid}:roads", lifecycle_key=runid)
            lease = lock_context.__enter__()
        except RqSubmissionConflict as exc:
            raise RoadsSingleFlightConflict(str(exc)) from exc
        try:
            reconcile_deferred_roads_jobs(
                runid, prep, redis_conn, lease_checkpoint=lease.checkpoint
            )
            lease.checkpoint()
            ensure_no_active_roads_job(runid, prep, redis_conn)
            queue = Queue(connection=redis_conn)
            replacement_job_id = new_rq_job_id()
            prep.set_rq_job_id(prep_key, replacement_job_id)
            lease.checkpoint()
            job = queue.enqueue_call(
                func=func,
                args=(runid,),
                timeout=TIMEOUT,
                job_id=replacement_job_id,
            )
            return {"job_id": job.id}
        finally:
            lock_context.__exit__(None, None, None)


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
            "attribute_field_map": summary.get("attribute_field_map") or {},
            "discovered_attribute_catalog": summary.get("discovered_attribute_catalog"),
            "uploaded_geojson_relpath": summary.get("uploaded_geojson_relpath"),
            "uploaded_geojson_sha256": summary.get("uploaded_geojson_sha256"),
        }
    )


@roads_bp.route("/runs/<string:runid>/<config>/api/roads/config", methods=["POST"])
@authorize_and_handle_with_exception_factory
def roads_set_config(runid: str, config: str) -> Response:
    if "parameterization" in parse_request_payload(request):
        # The new payload has one validation/initialization boundary across aliases.
        return roads_set_params.__wrapped__(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    payload = parse_request_payload(request)
    try:
        params = controller.set_params(payload)
    except ValueError as exc:
        return error_factory(str(exc))
    _invalidate_roads_timestamp(wd)
    summary = controller.query_summary()
    return success_factory(
        {
            "roads_params": params,
            "attribute_field_map": summary.get("attribute_field_map") or {},
            "discovered_attribute_catalog": summary.get("discovered_attribute_catalog"),
        }
    )


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
    return jsonify(_parameterization_view_state(str(ctx.active_root)))


@roads_bp.route("/runs/<string:runid>/<config>/resources/roads.json", methods=["GET"])
@roads_bp.route("/runs/<string:runid>/<config>/resources/roads.json/", methods=["GET"])
@authorize_and_handle_with_exception_factory
def resources_roads_geojson(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    view = request.args.get("view")
    if view is not None:
        if view != "detachment":
            return error_factory("Unsupported Roads map view.", status_code=400)
        from pyarrow import ArrowException
        from pyproj.exceptions import ProjError
        from wepppy.weppcloud.routes.nodb_api._roads_detachment import read_detachment_view
        try:
            return jsonify(read_detachment_view(wd))
        except (OSError, ValueError, TypeError, KeyError, OverflowError, ArrowException, ProjError):
            # Read boundary: preserve lifecycle exceptions for the shared 409 mapper;
            # malformed artifacts never expose paths or parser tracebacks to clients.
            current_app.logger.warning("Roads detachment view could not be materialized", exc_info=True)
            return error_factory("Roads detachment data is invalid or unreadable. Inspect Roads artifacts or contact support.",
                                 status_code=422, code="roads_detachment_invalid")
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    disabled_response = _require_enabled(controller)
    if disabled_response is not None:
        return disabled_response

    try:
        return jsonify(controller.query_map_segments_geojson())
    except FileNotFoundError as exc:
        response = error_factory(str(exc))
        response.status_code = 404
        return response
    except ValueError as exc:
        return error_factory(str(exc))


@roads_bp.route("/runs/<string:runid>/<config>/query/roads/segment/<segment_id>", methods=["GET"])
@roads_bp.route("/runs/<string:runid>/<config>/query/roads/segment/<segment_id>/", methods=["GET"])
@authorize_and_handle_with_exception_factory
def query_roads_segment_detail(runid: str, config: str, segment_id: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    disabled_response = _require_enabled(controller)
    if disabled_response is not None:
        return disabled_response

    try:
        return jsonify(controller.query_segment_detail(segment_id))
    except FileNotFoundError as exc:
        response = error_factory(str(exc))
        response.status_code = 404
        return response
    except KeyError as exc:
        response = error_factory(str(exc))
        response.status_code = 404
        return response
    except ValueError as exc:
        return error_factory(str(exc))


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


@roads_bp.route("/runs/<string:runid>/<config>/report/roads/segment_summary/<segment_id>")
@roads_bp.route("/runs/<string:runid>/<config>/report/roads/segment_summary/<segment_id>/")
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view WEPP reports.")
def report_roads_segment_summary(runid: str, config: str, segment_id: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    controller = _sync_roads_enabled_state(wd, f"{config}.cfg")
    disabled_response = _require_enabled(controller)
    if disabled_response is not None:
        return disabled_response

    try:
        segment_detail = controller.query_segment_detail(segment_id)
    except FileNotFoundError as exc:
        response = error_factory(str(exc))
        response.status_code = 404
        return response
    except KeyError as exc:
        response = error_factory(str(exc))
        response.status_code = 404
        return response
    except ValueError as exc:
        return error_factory(str(exc))

    return render_template(
        "reports/roads/segment_summary.htm",
        runid=runid,
        config=config,
        d=segment_detail,
        user=current_user,
    )
