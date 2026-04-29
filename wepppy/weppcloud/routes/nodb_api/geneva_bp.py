"""Geneva routes for config/tasks/status/results/frequency/query/report APIs."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any, Mapping, Optional, Union
from urllib.parse import quote

import redis
from flask import Response, jsonify
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Ron
from wepppy.nodb.core.ron import RonViewModel
from wepppy.nodb.mods.geneva import Geneva, GenevaNoDbError, GenevaValidationError
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.unitizer import Unitizer
from wepppy.nodb.unitizer import precisions as UNITIZER_PRECISIONS
from wepppy.nodb.mods.geneva.collaborators.cn_table_service import (
    CN_TABLE_CONTRACT_PATH,
    GENEVA_CN_TABLE_SCHEMA_VERSION,
)
from wepppy.rq.geneva_rq import (
    GENEVA_RQ_TIMEOUT,
    run_geneva_build_frequency_panel_rq,
    run_geneva_prepare_hrus_rq,
    run_geneva_run_batch_rq,
)
from wepppy.weppcloud.utils.helpers import authorize_and_handle_with_exception_factory, url_for_run

from .._common import (
    Blueprint,
    authorize,
    current_user,
    error_factory,
    load_run_context,
    parse_request_payload,
    render_template,
    request,
    success_factory,
)


_logger = logging.getLogger(__name__)
geneva_bp = Blueprint("geneva", __name__)


def _ensure_geneva_controller(wd: str, cfg_fn: str) -> Geneva:
    controller = Geneva.tryGetInstance(wd)
    if controller is None:
        controller = Geneva(wd, cfg_fn)
    return controller


def _set_no_store_headers(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _invalidate_geneva_preflight_timestamp(wd: str) -> None:
    RedisPrep.getInstance(wd).remove_timestamp(TaskEnum.run_geneva)


def _geneva_error_response(exc: GenevaNoDbError) -> Response:
    details = exc.details if exc.details is not None else exc.message
    return error_factory(
        exc.message,
        status_code=exc.status_code,
        code=exc.code,
        details=details,
    )


def _resolve_report_shell_context(wd: str, runid: str, config: str) -> tuple[Any, Any]:
    try:
        ron = Ron.getInstance(wd)
        return ron, RonViewModel(ron)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        # Boundary fallback: keep report shell renderable even if Ron metadata is unavailable.
        fallback = SimpleNamespace(
            runid=runid,
            config_stem=config,
            name="",
            scenario="",
            nodb_version=None,
            mods=[],
            readonly=False,
            public=False,
        )
        return fallback, fallback


def _resolve_report_unitizer_context(wd: str) -> Any:
    try:
        return Unitizer.getInstance(wd)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        # Boundary fallback for report shell rendering when unitizer state cannot load.
        preference_map = {
            unit_class: next(iter(unit_options.keys()))
            for unit_class, unit_options in UNITIZER_PRECISIONS.items()
            if unit_options
        }
        return SimpleNamespace(is_english=False, preferences=preference_map)


def _json_object_payload() -> dict[str, Any]:
    raw_json = request.get_json(silent=True)
    if raw_json is None:
        return {}
    if not isinstance(raw_json, dict):
        raise GenevaValidationError(
            "request payload must be a JSON object",
            code="invalid_input",
            details="request payload must be a JSON object",
            status_code=400,
        )
    return dict(raw_json)


def _require_schema_version(payload: Mapping[str, Any], *, expected: int = 1) -> None:
    if "schema_version" not in payload:
        return
    try:
        schema_version = int(payload.get("schema_version", expected))
    except (TypeError, ValueError) as exc:
        raise GenevaValidationError(
            f"schema_version must equal {expected}",
            code="invalid_input",
            details=f"schema_version must equal {expected}",
            status_code=400,
        ) from exc
    if schema_version != expected:
        raise GenevaValidationError(
            f"schema_version must equal {expected}",
            code="invalid_input",
            details=f"schema_version must equal {expected}",
            status_code=400,
        )


def _parse_optional_ari_years_filter() -> list[int] | None:
    raw_values = request.args.getlist("ari_years")
    if not raw_values:
        return None

    parsed: list[int] = []
    for raw in raw_values:
        for token in str(raw).split(","):
            text = token.strip()
            if not text:
                continue
            try:
                value = int(text)
            except (TypeError, ValueError) as exc:
                raise GenevaValidationError(
                    "ari_years filter values must be integers",
                    code="invalid_input",
                    details="ari_years filter values must be integers",
                    status_code=400,
                ) from exc
            if value <= 0:
                raise GenevaValidationError(
                    "ari_years filter values must be positive",
                    code="invalid_input",
                    details="ari_years filter values must be positive",
                    status_code=400,
                )
            parsed.append(value)

    if not parsed:
        return None
    return sorted(set(parsed))


def _parse_include_schema_flag(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    raise GenevaValidationError(
        "include_schema must be boolean when provided",
        code="invalid_input",
        details="include_schema must be boolean when provided",
        status_code=400,
    )


def _parse_optional_positive_limit(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise GenevaValidationError(
            "limit must be a positive integer when provided",
            code="invalid_input",
            details="limit must be a positive integer when provided",
            status_code=400,
        ) from exc
    if parsed <= 0:
        raise GenevaValidationError(
            "limit must be a positive integer when provided",
            code="invalid_input",
            details="limit must be a positive integer when provided",
            status_code=400,
        )
    return parsed


def _enqueue_geneva_job(
    *,
    runid: str,
    config: str,
    payload: Mapping[str, Any],
    func: Any,
    geneva: Geneva,
    queued_status_message: str,
) -> dict[str, str]:
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
        queue = Queue(connection=redis_conn)
        job = queue.enqueue_call(
            func=func,
            args=(runid, config, dict(payload)),
            timeout=GENEVA_RQ_TIMEOUT,
        )

    job_id = str(job.id)
    geneva.mark_job_queued(job_id, status_message=queued_status_message)
    return {
        "job_id": job_id,
        "status_url": f"/rq-engine/api/jobstatus/{job_id}",
        "message": "Job enqueued.",
    }


def _is_blank_cell(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _is_blank_row(row: Union[list[Any], tuple[Any, ...], dict[str, Any]]) -> bool:
    values: Any
    if isinstance(row, dict):
        values = row.values()
    else:
        values = row
    return all(_is_blank_cell(value) for value in values)


def _prune_blank_rows(
    rows: list[Union[list[Any], tuple[Any, ...], dict[str, Any]]],
) -> tuple[list[Union[list[Any], tuple[Any, ...], dict[str, Any]]], int]:
    pruned_rows: list[Union[list[Any], tuple[Any, ...], dict[str, Any]]] = []
    dropped = 0
    for row in rows:
        if _is_blank_row(row):
            dropped += 1
            continue
        pruned_rows.append(row)
    return pruned_rows, dropped


@geneva_bp.route("/runs/<string:runid>/<config>/api/geneva/config", methods=["GET"])
@authorize_and_handle_with_exception_factory
def geneva_get_config(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    return jsonify(geneva.get_config())


@geneva_bp.route("/runs/<string:runid>/<config>/api/geneva/config", methods=["POST"])
@authorize_and_handle_with_exception_factory
def geneva_set_config(runid: str, config: str) -> Response:
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    payload = _json_object_payload()
    _require_schema_version(payload)

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")

    try:
        config_before = geneva.get_config()
        enabled = payload.pop("enabled", None)
        if enabled is not None:
            if not isinstance(enabled, bool):
                raise GenevaValidationError(
                    "enabled must be boolean",
                    code="invalid_input",
                    details="enabled must be boolean",
                    status_code=400,
                )
            geneva.set_enabled(enabled)

        if payload:
            geneva.update_config(payload)

        config_after = geneva.get_config()
        if config_after != config_before:
            _invalidate_geneva_preflight_timestamp(wd)
        return jsonify(config_after)
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)


@geneva_bp.route("/runs/<string:runid>/<config>/tasks/geneva/prepare_hrus", methods=["POST"])
@authorize_and_handle_with_exception_factory
def task_geneva_prepare_hrus(runid: str, config: str) -> Response:
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    payload = _json_object_payload()
    _require_schema_version(payload)

    force_rebuild = payload.get("force_rebuild", False)
    if not isinstance(force_rebuild, bool):
        return _geneva_error_response(
            GenevaValidationError(
                "force_rebuild must be boolean",
                code="invalid_input",
                details="force_rebuild must be boolean",
                status_code=400,
            )
        )

    input_refs = payload.get("input_refs")
    if input_refs is not None and not isinstance(input_refs, dict):
        return _geneva_error_response(
            GenevaValidationError(
                "input_refs must be an object when provided",
                code="invalid_input",
                details="input_refs must be an object when provided",
                status_code=400,
            )
        )

    normalized_payload: dict[str, Any] = {
        "schema_version": 1,
        "force_rebuild": force_rebuild,
    }
    if input_refs is not None:
        normalized_payload["input_refs"] = dict(input_refs)

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    try:
        geneva.assert_task_guardrails()
        _invalidate_geneva_preflight_timestamp(wd)
        submission = _enqueue_geneva_job(
            runid=runid,
            config=config,
            payload=normalized_payload,
            func=run_geneva_prepare_hrus_rq,
            geneva=geneva,
            queued_status_message="Geneva HRU preparation queued.",
        )
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)

    response = jsonify(submission)
    response.status_code = 202
    return response


@geneva_bp.route("/runs/<string:runid>/<config>/tasks/geneva/build_frequency_panel", methods=["POST"])
@authorize_and_handle_with_exception_factory
def task_geneva_build_frequency_panel(runid: str, config: str) -> Response:
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    payload = _json_object_payload()
    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    try:
        normalized_payload = geneva.frequency_panel_service.normalize_request(payload)
        geneva.assert_task_guardrails()
        _invalidate_geneva_preflight_timestamp(wd)
        submission = _enqueue_geneva_job(
            runid=runid,
            config=config,
            payload=normalized_payload,
            func=run_geneva_build_frequency_panel_rq,
            geneva=geneva,
            queued_status_message="Geneva frequency panel build queued.",
        )
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)

    response = jsonify(submission)
    response.status_code = 202
    return response


@geneva_bp.route("/runs/<string:runid>/<config>/tasks/geneva/run_batch", methods=["POST"])
@authorize_and_handle_with_exception_factory
def task_geneva_run_batch(runid: str, config: str) -> Response:
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    payload = _json_object_payload()
    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    try:
        geneva.batch_run_service.validate_request(geneva, payload)
        geneva.assert_task_guardrails()
        submission = _enqueue_geneva_job(
            runid=runid,
            config=config,
            payload=payload,
            func=run_geneva_run_batch_rq,
            geneva=geneva,
            queued_status_message="Geneva batch run queued.",
        )
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)

    response = jsonify(submission)
    response.status_code = 202
    return response


@geneva_bp.route("/runs/<string:runid>/<config>/api/geneva/status")
@authorize_and_handle_with_exception_factory
def geneva_status(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    return jsonify(geneva.status_payload())


@geneva_bp.route("/runs/<string:runid>/<config>/api/geneva/results")
@authorize_and_handle_with_exception_factory
def geneva_results(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    return jsonify(geneva.results_payload())


@geneva_bp.route("/runs/<string:runid>/<config>/api/geneva/frequency_panel")
@authorize_and_handle_with_exception_factory
def geneva_frequency_panel(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    try:
        payload = geneva.frequency_panel_payload()
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)
    return jsonify(payload)


@geneva_bp.route("/runs/<string:runid>/<config>/query/geneva/summary")
@authorize_and_handle_with_exception_factory
def query_geneva_summary(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    datasource_id = str(request.args.get("datasource_id", "all") or "all").strip() or "all"
    measure = str(request.args.get("measure", "peak_discharge") or "peak_discharge").strip()
    try:
        ari_years = _parse_optional_ari_years_filter()
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)
    selected_storm_id = str(request.args.get("selected_storm_id", "") or "").strip() or None

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    try:
        payload = geneva.query_summary_payload(
            datasource_id=datasource_id,
            ari_years=ari_years,
            measure=measure,
            selected_storm_id=selected_storm_id,
        )
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)
    return _set_no_store_headers(jsonify(payload))


@geneva_bp.route("/runs/<string:runid>/<config>/query/geneva/hru_map_rows", methods=["POST"])
@authorize_and_handle_with_exception_factory
def query_geneva_hru_map_rows(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    payload = _json_object_payload()
    _require_schema_version(payload)
    storm_id = str(payload.get("storm_id", "") or "").strip()
    measure_id = str(payload.get("measure_id") or payload.get("measure") or "").strip()
    try:
        include_schema = _parse_include_schema_flag(payload.get("include_schema"))
        limit = _parse_optional_positive_limit(payload.get("limit"))
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    try:
        response_payload = geneva.query_hru_map_rows_payload(
            storm_id=storm_id,
            measure_id=measure_id,
            include_schema=include_schema,
            limit=limit,
        )
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)

    return _set_no_store_headers(jsonify(response_payload))


@geneva_bp.route("/runs/<string:runid>/<config>/report/geneva/summary")
@authorize_and_handle_with_exception_factory
def report_geneva_summary(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    datasource_id = str(request.args.get("datasource_id", "all") or "all").strip() or "all"
    measure = str(request.args.get("measure", "peak_discharge") or "peak_discharge").strip()
    try:
        ari_years = _parse_optional_ari_years_filter()
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)
    selected_storm_id = str(request.args.get("selected_storm_id", "") or "").strip() or None

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    try:
        summary_payload = geneva.query_summary_payload(
            datasource_id=datasource_id,
            ari_years=ari_years,
            measure=measure,
            selected_storm_id=selected_storm_id,
        )
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)

    ron, current_ron = _resolve_report_shell_context(wd, runid, config)
    unitizer = _resolve_report_unitizer_context(wd)

    return _set_no_store_headers(
        Response(
            render_template(
                "reports/geneva/summary.htm",
                runid=runid,
                config=config,
                summary_payload=summary_payload,
                ron=ron,
                current_ron=current_ron,
                unitizer_nodb=unitizer,
                precisions=UNITIZER_PRECISIONS,
                user=current_user,
            )
        )
    )


@geneva_bp.route("/runs/<string:runid>/<config>/modify_geneva_cn_table")
@authorize_and_handle_with_exception_factory
def modify_geneva_cn_table(runid: str, config: str) -> Response:
    """Render the shared CSV editor for the run-scoped Geneva CN table."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    try:
        geneva.cn_table_meta()
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)

    quoted_runid = quote(runid, safe="")
    quoted_config = quote(config, safe="")
    return render_template(
        "controls/edit_csv.htm",
        runid=runid,
        config=config,
        page_title="Edit Geneva CN Table",
        editor_title="Geneva CN Table",
        editor_description="Run-scoped Geneva CN lookup table with optimistic concurrency.",
        save_success_message="Geneva CN table saved successfully.",
        csv_url=url_for_run(
            "download.download_with_subpath",
            runid=runid,
            config=config,
            subpath=CN_TABLE_CONTRACT_PATH,
        ),
        save_url=url_for_run(
            "geneva.task_modify_geneva_cn_table",
            runid=runid,
            config=config,
        ),
        lookup_meta_url=url_for_run(
            "geneva.lookup_geneva_cn_table_meta",
            runid=runid,
            config=config,
        ),
        lookup_snapshot_url=url_for_run(
            "geneva.lookup_geneva_cn_table_snapshot",
            runid=runid,
            config=config,
        ),
        lookup_variant="cn_table",
        freeze_columns=5,
        session_token_url=f"/rq-engine/api/runs/{quoted_runid}/{quoted_config}/session-token",
    )


@geneva_bp.route("/runs/<string:runid>/<config>/api/geneva/cn_table_meta")
@authorize_and_handle_with_exception_factory
def lookup_geneva_cn_table_meta(runid: str, config: str) -> Response:
    """Return Geneva CN-table fingerprint metadata for optimistic concurrency."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    try:
        payload = geneva.cn_table_meta()
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)

    response = success_factory(payload)
    return _set_no_store_headers(response)


@geneva_bp.route("/runs/<string:runid>/<config>/api/geneva/cn_table_snapshot")
@authorize_and_handle_with_exception_factory
def lookup_geneva_cn_table_snapshot(runid: str, config: str) -> Response:
    """Return Geneva CN-table snapshot and CSV text from one locked read."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    try:
        payload = geneva.cn_table_snapshot()
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)

    response = success_factory(payload)
    return _set_no_store_headers(response)


@geneva_bp.route("/runs/<string:runid>/<config>/tasks/modify_geneva_cn_table", methods=["POST"])
@authorize_and_handle_with_exception_factory
def task_modify_geneva_cn_table(runid: str, config: str) -> Response:
    """Persist Geneva CN-table edits with an optimistic concurrency token."""
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    raw_json = request.get_json(silent=True, force=True)
    if_match_sha256: Optional[str] = request.headers.get("X-If-Match-Sha256")

    if isinstance(raw_json, list):
        rows: Any = raw_json
    elif isinstance(raw_json, dict):
        rows = raw_json.get("rows", [])
        requested_sha = raw_json.get("if_match_sha256")
        if requested_sha is not None:
            if_match_sha256 = str(requested_sha).strip()
        if isinstance(rows, dict):
            rows = [rows]
    else:
        return error_factory(
            'rows payload must be JSON list or {"rows": [...]}',
            status_code=400,
            code="invalid_rows_payload",
            details='rows payload must be JSON list or {"rows": [...]}',
        )

    if not isinstance(rows, list) or len(rows) == 0:
        return error_factory(
            "rows payload must be a non-empty list",
            status_code=400,
            code="invalid_rows_payload",
            details="rows payload must be a non-empty list",
        )

    if any(not isinstance(row, (list, tuple, dict)) for row in rows):
        return error_factory(
            "each row must be a list or mapping",
            status_code=400,
            code="invalid_rows_payload",
            details="each row must be a list or mapping",
        )

    pruned_rows, dropped_blank_rows = _prune_blank_rows(rows)
    if dropped_blank_rows:
        _logger.info(
            "geneva_cn_table_write_pruned_blank_rows runid=%s config=%s dropped_rows=%s",
            runid,
            config,
            dropped_blank_rows,
        )
    if len(pruned_rows) == 0:
        return error_factory(
            "rows payload must include at least one non-blank row",
            status_code=400,
            code="invalid_rows_payload",
            details="rows payload must include at least one non-blank row",
        )

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    try:
        result = geneva.modify_cn_table(
            pruned_rows,
            if_match_sha256=if_match_sha256,
        )
        _invalidate_geneva_preflight_timestamp(wd)
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)

    response = success_factory()
    response.headers["X-Lookup-Sha256"] = str(result.get("sha256") or "")
    response.headers["X-Lookup-Variant"] = "cn_table"
    return response


@geneva_bp.route("/runs/<string:runid>/<config>/tasks/reset_geneva_cn_table", methods=["POST"])
@authorize_and_handle_with_exception_factory
def task_reset_geneva_cn_table(runid: str, config: str) -> Response:
    """Reset run-scoped Geneva CN table to the canonical module seed."""
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    payload = parse_request_payload(request, boolean_fields={"confirm"})
    confirm = payload.get("confirm")
    if confirm is not True:
        return error_factory(
            "confirm must be true to reset the Geneva CN table",
            status_code=400,
            code="invalid_reset_request",
            details={"schema_version": GENEVA_CN_TABLE_SCHEMA_VERSION},
        )

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    try:
        reset_meta = geneva.reset_cn_table(reason="manual")
        _invalidate_geneva_preflight_timestamp(wd)
    except GenevaNoDbError as exc:
        return _geneva_error_response(exc)

    return success_factory(
        {
            "path": CN_TABLE_CONTRACT_PATH,
            "schema_version": GENEVA_CN_TABLE_SCHEMA_VERSION,
            "lookup_sha256": reset_meta.get("sha256"),
            "rows": reset_meta.get("rows"),
            "columns": reset_meta.get("columns"),
        }
    )


__all__ = ["geneva_bp"]
