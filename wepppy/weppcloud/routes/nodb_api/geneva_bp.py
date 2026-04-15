"""WP-07 Geneva CN-table routes and edit-csv integration."""

from __future__ import annotations

import logging
from typing import Any, Optional, Union
from urllib.parse import quote

from flask import Response

from .._common import (
    Blueprint,
    authorize,
    error_factory,
    load_run_context,
    parse_request_payload,
    render_template,
    request,
    success_factory,
)
from wepppy.nodb.mods.geneva import Geneva, GenevaNoDbError
from wepppy.nodb.mods.geneva.collaborators.cn_table_service import (
    CN_TABLE_CONTRACT_PATH,
    GENEVA_CN_TABLE_SCHEMA_VERSION,
)
from wepppy.weppcloud.utils.helpers import authorize_and_handle_with_exception_factory, url_for_run


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


def _geneva_error_response(exc: GenevaNoDbError) -> Response:
    return error_factory(
        exc.message,
        status_code=exc.status_code,
        code=exc.code,
        details=exc.details,
    )


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
        return error_factory('rows payload must be JSON list or {"rows": [...]}', status_code=400)

    if not isinstance(rows, list) or len(rows) == 0:
        return error_factory("rows payload must be a non-empty list", status_code=400)

    if any(not isinstance(row, (list, tuple, dict)) for row in rows):
        return error_factory("each row must be a list or mapping", status_code=400)

    pruned_rows, dropped_blank_rows = _prune_blank_rows(rows)
    if dropped_blank_rows:
        _logger.info(
            "geneva_cn_table_write_pruned_blank_rows runid=%s config=%s dropped_rows=%s",
            runid,
            config,
            dropped_blank_rows,
        )
    if len(pruned_rows) == 0:
        return error_factory("rows payload must include at least one non-blank row", status_code=400)

    geneva = _ensure_geneva_controller(wd, f"{config}.cfg")
    try:
        result = geneva.modify_cn_table(
            pruned_rows,
            if_match_sha256=if_match_sha256,
        )
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
