"""Routes for disturbed blueprint extracted from app.py."""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
import logging
import os
from urllib.parse import quote
from typing import Any, Dict, Optional, Tuple, Union

from flask import Response

from .._common import (
    Blueprint,
    authorize,
    error_factory,
    exception_factory,
    jsonify,
    load_run_context,
    parse_request_payload,
    render_template,
    request,
    send_file,
    success_factory,
)
from wepppy.nodb.core import Ron
from wepppy.nodb.base import NoDbAlreadyLockedError
from wepppy.nodb.mods.baer import Baer
from wepppy.nodb.mods.disturbed import (
    Disturbed,
    get_disturbed_land_soil_lookup_sha256,
    get_disturbed_land_soil_lookup_snapshot,
    write_disturbed_land_soil_lookup,
)
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.weppcloud.utils.helpers import authorize_and_handle_with_exception_factory, url_for_run

disturbed_bp = Blueprint('disturbed', __name__)
_logger = logging.getLogger(__name__)
LOOKUP_VARIANT_BASE = 'base'
LOOKUP_VARIANT_EXTENDED = 'extended'
LOOKUP_VARIANT_UNAVAILABLE_CODE = 'LOOKUP_VARIANT_UNAVAILABLE'


class LookupVariantUnavailableError(RuntimeError):
    """Raised when an explicitly requested lookup variant is unavailable."""

    def __init__(self, requested_variant: str):
        super().__init__(requested_variant)
        self.requested_variant = requested_variant


def _set_no_store_headers(response: Response) -> Response:
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@contextmanager
def _controller_lock(controller: Any):
    if not hasattr(controller, 'lock') or not hasattr(controller, 'unlock'):
        # Test stubs may only expose locked(); production NoDb controllers provide lock/unlock.
        with controller.locked():
            yield
        return

    acquired = False
    controller.lock()
    acquired = True
    try:
        yield
    finally:
        if acquired:
            controller.unlock()


@contextmanager
def _best_effort_read_lock(controller: Any):
    if not hasattr(controller, 'lock') or not hasattr(controller, 'unlock'):
        # Test stubs may only expose locked(); production NoDb controllers provide lock/unlock.
        with controller.locked():
            yield
        return

    acquired = False
    try:
        controller.lock()
        acquired = True
    except NoDbAlreadyLockedError:
        # Read-only lookup refresh should not fail when a writer holds the lock.
        _logger.debug(
            'disturbed_lookup_read_lock_busy controller=%s',
            getattr(controller, '__class__', type(controller)).__name__,
            exc_info=True,
        )

    try:
        yield
    finally:
        if acquired:
            controller.unlock()


def _read_lock_context(controller: Any):
    if getattr(controller, 'readonly', False):
        return nullcontext()
    return _best_effort_read_lock(controller)


def _is_blank_lookup_cell(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ''
    return False


def _is_blank_lookup_row(row: Union[list, tuple, dict]) -> bool:
    if isinstance(row, dict):
        values = row.values()
    else:
        values = row
    return all(_is_blank_lookup_cell(value) for value in values)


def _prune_blank_lookup_rows(rows: list[Union[list, tuple, dict]]) -> tuple[list[Union[list, tuple, dict]], int]:
    pruned_rows = []
    dropped_count = 0
    for row in rows:
        if _is_blank_lookup_row(row):
            dropped_count += 1
            continue
        pruned_rows.append(row)
    return pruned_rows, dropped_count


def _build_lookup_snapshot_payload(lookup_fn: str) -> Dict[str, Any]:
    snapshot = get_disturbed_land_soil_lookup_snapshot(lookup_fn)
    csv_text = ''
    if lookup_fn and os.path.exists(lookup_fn):
        with open(lookup_fn) as fp:
            csv_text = fp.read()
    return dict(
        csv_text=csv_text,
        lookup_sha256=snapshot.get('sha256'),
        size_bytes=snapshot.get('size_bytes'),
        mtime_epoch=snapshot.get('mtime_epoch'),
        rows=snapshot.get('rows'),
        columns=snapshot.get('columns'),
    )


def _normalize_lookup_variant(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    normalized = str(value).strip().lower()
    if normalized in {'base', 'default', 'disturbed_land_soil_lookup', 'disturbed_land_soil_lookup.csv'}:
        return LOOKUP_VARIANT_BASE
    if normalized in {'extended', 'disturbed_land_soil_lookup_extended', 'disturbed_land_soil_lookup_extended.csv'}:
        return LOOKUP_VARIANT_EXTENDED
    return None


def _has_extended_lookup(disturbed: Any) -> bool:
    extended_lookup_fn = getattr(disturbed, 'extended_lookup_fn', None)
    return (
        isinstance(extended_lookup_fn, str)
        and extended_lookup_fn != ''
        and os.path.exists(extended_lookup_fn)
    )


def _resolve_lookup_target(
    disturbed: Any,
    requested_variant: Optional[str] = None,
    *,
    strict_requested: bool = False,
) -> Tuple[str, str]:
    base_lookup_fn = disturbed.lookup_fn
    extended_lookup_fn = getattr(disturbed, 'extended_lookup_fn', None)
    has_extended_lookup = _has_extended_lookup(disturbed)

    variant = _normalize_lookup_variant(requested_variant)
    if variant is None:
        persisted_variant = _normalize_lookup_variant(getattr(disturbed, 'active_lookup_variant', None))
        if persisted_variant is not None:
            variant = persisted_variant

    if variant == LOOKUP_VARIANT_BASE:
        return LOOKUP_VARIANT_BASE, base_lookup_fn
    if variant == LOOKUP_VARIANT_EXTENDED:
        if has_extended_lookup:
            return LOOKUP_VARIANT_EXTENDED, extended_lookup_fn
        if strict_requested:
            raise LookupVariantUnavailableError(LOOKUP_VARIANT_EXTENDED)
        _logger.info(
            'disturbed_lookup_variant_missing_extended_fallback_base requested_variant=%s base_lookup_fn=%s extended_lookup_fn=%s',
            requested_variant,
            base_lookup_fn,
            extended_lookup_fn,
        )
        return LOOKUP_VARIANT_BASE, base_lookup_fn

    if has_extended_lookup:
        return LOOKUP_VARIANT_EXTENDED, extended_lookup_fn
    return LOOKUP_VARIANT_BASE, base_lookup_fn


def _resolve_lookup_target_from_request(disturbed: Any) -> Tuple[str, str]:
    requested_variant = request.args.get('lookup') or request.args.get('table')
    normalized_requested_variant = _normalize_lookup_variant(requested_variant)
    strict_requested = normalized_requested_variant == LOOKUP_VARIANT_EXTENDED
    return _resolve_lookup_target(
        disturbed,
        requested_variant=requested_variant,
        strict_requested=strict_requested,
    )


def _lookup_variant_unavailable_error_response() -> Response:
    return error_factory(
        'Extended lookup table is unavailable. Load extended lookup first.',
        status_code=409,
        code=LOOKUP_VARIANT_UNAVAILABLE_CODE,
    )


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/set_lookup_variant', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_set_lookup_variant(runid: str, config: str) -> Response:
    """Persist the run-scoped active disturbed lookup variant in Disturbed NoDb."""
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    disturbed = Disturbed.getInstance(wd)

    payload = parse_request_payload(request)
    requested_variant = payload.get('lookup_variant')
    if requested_variant is None:
        requested_variant = payload.get('lookup')

    normalized_variant = _normalize_lookup_variant(requested_variant)
    if normalized_variant is None:
        return error_factory("lookup_variant must be one of {'base', 'extended'}", status_code=400)
    if normalized_variant == LOOKUP_VARIANT_EXTENDED and not _has_extended_lookup(disturbed):
        return _lookup_variant_unavailable_error_response()

    disturbed.active_lookup_variant = normalized_variant
    effective_variant, _ = _resolve_lookup_target(disturbed, requested_variant=normalized_variant)

    return success_factory(
        dict(
            requested_lookup_variant=normalized_variant,
            lookup_variant=effective_variant,
            has_extended_lookup=_has_extended_lookup(disturbed),
        )
    )


@disturbed_bp.route('/runs/<string:runid>/<config>/modify_disturbed')
@authorize_and_handle_with_exception_factory
def modify_disturbed(runid: str, config: str) -> Response:
    """Render the CSV editor for disturbed land/soil lookup."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    disturbed = Disturbed.getInstance(wd)
    try:
        lookup_variant, lookup_fn = _resolve_lookup_target_from_request(disturbed)
    except LookupVariantUnavailableError:
        return _lookup_variant_unavailable_error_response()
    lookup_filename = os.path.basename(lookup_fn)

    quoted_runid = quote(runid, safe="")
    quoted_config = quote(config, safe="")
    return render_template(
        'controls/edit_csv.htm',
        runid=runid,
        config=config,
        csv_url=url_for_run(
            'download.download_with_subpath',
            runid=runid,
            config=config,
            subpath=f'disturbed/{lookup_filename}',
        ),
        save_url=url_for_run(
            'disturbed.task_modify_disturbed',
            runid=runid,
            config=config,
            lookup=lookup_variant,
        ),
        lookup_meta_url=url_for_run(
            'disturbed.lookup_disturbed_lookup_meta',
            runid=runid,
            config=config,
            lookup=lookup_variant,
        ),
        lookup_snapshot_url=url_for_run(
            'disturbed.lookup_disturbed_lookup_snapshot',
            runid=runid,
            config=config,
            lookup=lookup_variant,
        ),
        lookup_variant=lookup_variant,
        session_token_url=f"/rq-engine/api/runs/{quoted_runid}/{quoted_config}/session-token",
    )

@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/reset_disturbed', methods=['POST'])
@authorize_and_handle_with_exception_factory
def reset_disturbed(runid: str, config: str) -> Response:
    """Reset the disturbed land/soil lookup to defaults."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    disturbed = Disturbed.getInstance(wd)
    disturbed.reset_land_soil_lookup()
    return success_factory()

@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/load_extended_land_soil_lookup', methods=['POST'])
@authorize_and_handle_with_exception_factory
def load_extended_land_soil_lookup(runid: str, config: str) -> Response:
    """Populate the extended disturbed land/soil lookup."""
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    disturbed = Disturbed.getInstance(wd)
    disturbed.build_extended_land_soil_lookup()
    return success_factory()


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/delete_extended_land_soil_lookup', methods=['POST'])
@authorize_and_handle_with_exception_factory
def delete_extended_land_soil_lookup(runid: str, config: str) -> Response:
    """Delete the extended disturbed lookup table when present."""
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    disturbed = Disturbed.getInstance(wd)

    extended_lookup_fn = getattr(disturbed, 'extended_lookup_fn', None)
    deleted = False
    if isinstance(extended_lookup_fn, str) and extended_lookup_fn:
        with _controller_lock(disturbed):
            if os.path.exists(extended_lookup_fn):
                os.remove(extended_lookup_fn)
                deleted = True

    disturbed.active_lookup_variant = LOOKUP_VARIANT_BASE

    _logger.info(
        'disturbed_lookup_delete_extended runid=%s config=%s deleted=%s extended_lookup_fn=%s',
        runid,
        config,
        deleted,
        extended_lookup_fn,
    )
    return success_factory()


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/sync_base_to_extended_land_soil_lookup', methods=['POST'])
@authorize_and_handle_with_exception_factory
def sync_base_to_extended_land_soil_lookup(runid: str, config: str) -> Response:
    """Rebuild the extended disturbed lookup from the current base lookup."""
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    disturbed = Disturbed.getInstance(wd)
    disturbed.build_extended_land_soil_lookup()
    return success_factory()


@disturbed_bp.route('/runs/<string:runid>/<config>/api/disturbed/has_sbs')
@disturbed_bp.route('/runs/<string:runid>/<config>/api/disturbed/has_sbs/')
@authorize_and_handle_with_exception_factory
def has_sbs(runid: str, config: str) -> Response:
    """Return whether an SBS raster is registered with the disturbed controller."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    disturbed = Disturbed.getInstance(wd)
    return jsonify(dict(has_sbs=disturbed.has_sbs))


@disturbed_bp.route('/runs/<string:runid>/<config>/api/disturbed/lookup_meta')
@authorize_and_handle_with_exception_factory
def lookup_disturbed_lookup_meta(runid: str, config: str) -> Response:
    """Return run-scoped disturbed lookup fingerprint metadata."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    disturbed = Disturbed.getInstance(wd)

    try:
        with _read_lock_context(disturbed):
            lookup_variant, lookup_fn = _resolve_lookup_target_from_request(disturbed)
            snapshot = get_disturbed_land_soil_lookup_snapshot(lookup_fn)
    except LookupVariantUnavailableError:
        return _lookup_variant_unavailable_error_response()

    response = success_factory(
        dict(
            lookup_variant=lookup_variant,
            has_extended_lookup=_has_extended_lookup(disturbed),
            lookup_sha256=snapshot.get('sha256'),
            size_bytes=snapshot.get('size_bytes'),
            mtime_epoch=snapshot.get('mtime_epoch'),
            rows=snapshot.get('rows'),
            columns=snapshot.get('columns'),
        )
    )
    return _set_no_store_headers(response)


@disturbed_bp.route('/runs/<string:runid>/<config>/api/disturbed/lookup_snapshot')
@authorize_and_handle_with_exception_factory
def lookup_disturbed_lookup_snapshot(runid: str, config: str) -> Response:
    """Return run-scoped disturbed lookup CSV + fingerprint from one locked read."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    disturbed = Disturbed.getInstance(wd)

    try:
        with _read_lock_context(disturbed):
            lookup_variant, lookup_fn = _resolve_lookup_target_from_request(disturbed)
            payload = _build_lookup_snapshot_payload(lookup_fn)
            payload['lookup_variant'] = lookup_variant
            payload['has_extended_lookup'] = _has_extended_lookup(disturbed)
    except LookupVariantUnavailableError:
        return _lookup_variant_unavailable_error_response()

    response = success_factory(payload)
    return _set_no_store_headers(response)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/modify_disturbed', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_modify_disturbed(runid: str, config: str) -> Response:
    """Persist edited disturbed lookup entries received from the UI."""
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    # The frontend sends a raw JSON array of rows (list of lists).
    # Try to parse it directly first, falling back to dict payload format.
    raw_json = request.get_json(silent=True, force=True)
    if_match_sha256: Optional[str] = request.headers.get('X-If-Match-Sha256')
    if isinstance(raw_json, list):
        # Direct array payload from jspreadsheet getData()
        rows = raw_json
    elif isinstance(raw_json, dict):
        # Dict payload with 'rows' key
        rows = raw_json.get('rows', [])
        requested_sha = raw_json.get('if_match_sha256')
        if requested_sha is not None:
            if_match_sha256 = str(requested_sha).strip()
        if isinstance(rows, dict):
            rows = [rows]
    else:
        return error_factory('rows payload must be JSON list or {"rows": [...]}', status_code=400)

    if not isinstance(rows, list) or len(rows) == 0:
        return error_factory('rows payload must be a non-empty list', status_code=400)

    if any(not isinstance(row, (list, tuple, dict)) for row in rows):
        return error_factory('each row must be a list or mapping', status_code=400)

    rows, dropped_blank_rows = _prune_blank_lookup_rows(rows)
    if dropped_blank_rows:
        _logger.info(
            'disturbed_lookup_write_pruned_blank_rows runid=%s config=%s dropped_rows=%s',
            runid,
            config,
            dropped_blank_rows,
        )
    if len(rows) == 0:
        return error_factory('rows payload must include at least one non-blank row', status_code=400)

    if if_match_sha256 is not None:
        if_match_sha256 = if_match_sha256.strip()
    if not if_match_sha256:
        _logger.warning(
            'disturbed_lookup_write_blocked_missing_if_match runid=%s config=%s',
            runid,
            config,
        )
        return error_factory('if_match_sha256 is required', status_code=428)

    disturbed = Disturbed.getInstance(wd)

    try:
        with _controller_lock(disturbed):
            lookup_variant, lookup_fn = _resolve_lookup_target_from_request(disturbed)
            current_sha256 = get_disturbed_land_soil_lookup_sha256(lookup_fn)
            if not current_sha256:
                _logger.warning(
                    'disturbed_lookup_write_blocked_sha_unavailable runid=%s config=%s lookup_variant=%s lookup_fn=%s',
                    runid,
                    config,
                    lookup_variant,
                    lookup_fn,
                )
                return error_factory(
                    'Unable to verify current disturbed lookup version. Reload and retry.',
                    status_code=409,
                    code='LOOKUP_VERSION_UNAVAILABLE',
                )
            if current_sha256 != if_match_sha256:
                _logger.warning(
                    'disturbed_lookup_write_blocked_stale runid=%s config=%s lookup_variant=%s expected_sha=%s current_sha=%s',
                    runid,
                    config,
                    lookup_variant,
                    if_match_sha256,
                    current_sha256,
                )
                return error_factory(
                    'Stale disturbed lookup. Reload current data before saving.',
                    status_code=409,
                    code='STALE_LOOKUP',
                    details=dict(
                        expected_sha256=if_match_sha256,
                        current_sha256=current_sha256,
                    ),
                )
            write_disturbed_land_soil_lookup(lookup_fn, rows)
            updated_sha256 = get_disturbed_land_soil_lookup_sha256(lookup_fn)
            if not updated_sha256:
                _logger.warning(
                    'disturbed_lookup_write_postsave_sha_unavailable runid=%s config=%s lookup_variant=%s lookup_fn=%s',
                    runid,
                    config,
                    lookup_variant,
                    lookup_fn,
                )
                return error_factory(
                    'Disturbed lookup saved but new version fingerprint is unavailable.',
                    status_code=409,
                    code='LOOKUP_VERSION_UNAVAILABLE',
                )
            _logger.info(
                'disturbed_lookup_write_committed runid=%s config=%s lookup_variant=%s expected_sha=%s prior_sha=%s updated_sha=%s row_count=%s',
                runid,
                config,
                lookup_variant,
                if_match_sha256,
                current_sha256,
                updated_sha256,
                len(rows),
            )
    except LookupVariantUnavailableError:
        return _lookup_variant_unavailable_error_response()
    except ValueError as exc:
        _logger.warning(
            'disturbed_lookup_write_rejected runid=%s config=%s err=%s',
            runid,
            config,
            exc,
        )
        return error_factory(str(exc), status_code=400)
    response = success_factory()
    response.headers['X-Lookup-Sha256'] = updated_sha256
    response.headers['X-Lookup-Variant'] = lookup_variant
    return response


@disturbed_bp.route('/runs/<string:runid>/<config>/query/baer_wgs_map')
@disturbed_bp.route('/runs/<string:runid>/<config>/query/baer_wgs_map/')
@authorize_and_handle_with_exception_factory
def query_baer_wgs_bounds(runid: str, config: str) -> Response:
    """Return BAER map metadata (bounds/classes) or error if no raster is registered."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)
    if 'baer' in ron.mods:
        baer = Baer.getInstance(wd)
    else:
        baer = Disturbed.getInstance(wd)

    if not baer.has_map:
        return error_factory('No SBS map has been specified')

    return success_factory(dict(bounds=baer.bounds, classes=baer.classes, imgurl='resources/baer.png'))


@disturbed_bp.route('/runs/<string:runid>/<config>/view/modify_burn_class')
@authorize_and_handle_with_exception_factory
def query_baer_class_map(runid: str, config: str) -> Response:
    """Render the burn-class modification template for BAER maps."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    
    ron = Ron.getInstance(wd)
    if 'baer' in ron.mods:
        baer = Baer.getInstance(wd)
    else:
        baer = Disturbed.getInstance(wd)

    if not baer.has_map:
        return error_factory('No SBS map has been specified')

    return render_template('mods/baer/classify.htm', baer=baer)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/modify_burn_class', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_baer_class_map(runid: str, config: str) -> Response:
    """Apply burn-class edits to the active BAER or disturbed map."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    ron = Ron.getInstance(wd)
    if 'baer' in ron.mods:
        baer = Baer.getInstance(wd)
    else:
        baer = Disturbed.getInstance(wd)

    if not baer.has_map:
        return error_factory('No SBS map has been specified')

    payload = parse_request_payload(request)
    raw_classes = payload.get('classes')
    if raw_classes is None:
        return error_factory('classes must be provided')
    if not isinstance(raw_classes, list):
        raw_classes = [raw_classes]
    if len(raw_classes) != 4:
        return error_factory('classes must include four break values')

    try:
        classes = [int(value) for value in raw_classes]
    except (TypeError, ValueError):
        return error_factory('classes must contain integers')

    nodata_vals = payload.get('nodata_vals')

    baer.modify_burn_class(classes, nodata_vals)
    prep = RedisPrep.getInstance(wd)
    prep.remove_timestamp(TaskEnum.build_rusle)
    prep.remove_timestamp(TaskEnum.run_geneva)
    return success_factory()


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/modify_color_map', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_baer_modify_color_map(runid: str, config: str) -> Response:
    """Update the color map used to render BAER severity classes."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)
    if 'baer' in ron.mods:
        baer = Baer.getInstance(wd)
    else:
        baer = Disturbed.getInstance(wd)

    if not baer.has_map:
        return error_factory('No SBS map has been specified')

    payload = parse_request_payload(request)
    raw_map = payload.get('color_map')
    if raw_map is None:
        return error_factory('color_map must be provided')
    if not isinstance(raw_map, dict):
        return error_factory('color_map must be a mapping of RGB strings to severities')

    color_map: Dict[Tuple[int, int, int], Any] = {}
    for color, severity in raw_map.items():
        try:
            rgb = tuple(int(component) for component in color.split('_'))
        except (TypeError, ValueError):
            return error_factory('color_map keys must be formatted as R_G_B integers')
        color_map[rgb] = severity

    baer.modify_color_map(color_map)
    return success_factory()


@disturbed_bp.route('/runs/<string:runid>/<config>/resources/baer.png')
def resources_baer_sbs(runid: str, config: str) -> Response:
    """Stream the BAER RGB overlay for the active run."""
    try:
        ctx = load_run_context(runid, config)
        wd = str(ctx.active_root)
        ron = Ron.getInstance(wd)
        if 'baer' in ron.mods:
            baer = Baer.getInstance(wd)
        else:
            baer = Disturbed.getInstance(wd)

        if not baer.has_map:
            return error_factory('No SBS map has been specified')

        return send_file(baer.baer_rgb_png, mimetype='image/png')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/disturbed_bp.py:224", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory(runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/set_firedate/', methods=['POST'])
@authorize_and_handle_with_exception_factory
def set_firedate(runid: str, config: str) -> Response:
    """Persist the fire date for the disturbed controller."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    disturbed = Disturbed.getInstance(wd)
    try:
        payload = parse_request_payload(request)
        fire_date = payload.get('fire_date')
        disturbed.fire_date = fire_date
        return success_factory()
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/disturbed_bp.py:240", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory("failed to set firedate", runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/remove_sbs', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_remove_sbs(runid: str, config: str) -> Response:
    """Remove the SBS raster from BAER/disturbed controllers."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)
    if 'baer' in ron.mods:
        baer = Baer.getInstance(wd)
        baer.remove_sbs()
    else:
        baer = Disturbed.getInstance(wd)
        baer.remove_sbs()
    prep = RedisPrep.getInstance(wd)
    prep.remove_timestamp(TaskEnum.build_rusle)
    prep.remove_timestamp(TaskEnum.run_geneva)
    return success_factory()


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/build_uniform_sbs', methods=['POST'])
@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/build_uniform_sbs/<value>', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_build_uniform_sbs(runid: str, config: str, value: Optional[str] = None) -> Response:
    """Generate a uniform SBS raster with the requested severity value."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)
    disturbed = Disturbed.getInstance(wd)
    payload = parse_request_payload(request)

    raw_value: Union[str, int, None]
    if 'value' in payload:
        raw_value = payload['value']
    elif 'severity' in payload:
        raw_value = payload['severity']
    else:
        raw_value = value

    if isinstance(raw_value, list):
        raw_value = raw_value[0] if raw_value else None

    if raw_value is None:
        return error_factory('value must be provided')

    try:
        severity = int(raw_value)
    except (TypeError, ValueError):
        return error_factory('value must be an integer')

    sbs_fn = disturbed.build_uniform_sbs(severity)
    disturbed.validate(sbs_fn, mode=1, uniform_severity=severity)

    if 'baer' in ron.mods:
        baer = Baer.getInstance(wd)
        try:
            baer.validate(disturbed.disturbed_fn, mode=1, uniform_severity=severity)
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/disturbed_bp.py:297", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            # Fall back to direct assignments if validation fails on legacy runs
            baer.sbs_mode = 1
            baer.uniform_severity = severity
            try:
                baer._baer_fn = disturbed.disturbed_fn  # type: ignore[attr-defined]
            except Exception:
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/disturbed_bp.py:303", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                pass

    prep = RedisPrep.getInstance(wd)
    prep.remove_timestamp(TaskEnum.build_rusle)
    prep.remove_timestamp(TaskEnum.run_geneva)
    return success_factory({'disturbed_fn': disturbed.disturbed_fn})
