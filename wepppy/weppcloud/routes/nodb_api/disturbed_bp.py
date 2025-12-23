"""Routes for disturbed blueprint extracted from app.py."""

from __future__ import annotations

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
    secure_filename,
    send_file,
    success_factory,
    _join,
)
from wepppy.nodb.core import Ron
from wepppy.nodb.mods.baer import Baer
from wepppy.nodb.mods.disturbed import Disturbed, write_disturbed_land_soil_lookup
from wepppy.weppcloud.utils.helpers import authorize_and_handle_with_exception_factory
from wepppy.weppcloud.utils.uploads import (
    UploadError,
    save_run_file,
    upload_failure,
    upload_success,
)

disturbed_bp = Blueprint('disturbed', __name__)


@disturbed_bp.route('/runs/<string:runid>/<config>/modify_disturbed')
@authorize_and_handle_with_exception_factory
def modify_disturbed(runid: str, config: str) -> Response:
    """Render the CSV editor for disturbed land/soil lookup."""
    return render_template(
        'controls/edit_csv.htm',
        csv_url='download/disturbed/disturbed_land_soil_lookup.csv',
    )

@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/reset_disturbed', methods=['GET', 'POST'])
@authorize_and_handle_with_exception_factory
def reset_disturbed(runid: str, config: str) -> Response:
    """Reset the disturbed land/soil lookup to defaults."""
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    disturbed = Disturbed.getInstance(wd)
    disturbed.reset_land_soil_lookup()
    return success_factory()

@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/load_extended_land_soil_lookup', methods=['GET', 'POST'])
@authorize_and_handle_with_exception_factory
def load_extended_land_soil_lookup(runid: str, config: str) -> Response:
    """Populate the extended disturbed land/soil lookup."""
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
    if isinstance(raw_json, list):
        # Direct array payload from jspreadsheet getData()
        rows = raw_json
    elif isinstance(raw_json, dict):
        # Dict payload with 'rows' key
        rows = raw_json.get('rows', [])
        if isinstance(rows, dict):
            rows = [rows]
    else:
        rows = []

    lookup_fn = Disturbed.getInstance(wd).lookup_fn
    write_disturbed_land_soil_lookup(lookup_fn, rows)
    return success_factory()


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
        return exception_factory("failed to set firedate", runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/upload_sbs/', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_upload_sbs(runid: str, config: str) -> Response:
    """Upload and validate an SBS raster."""
    from wepppy.nodb.mods.baer.sbs_map import sbs_map_sanity_check
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    ron = Ron.getInstance(wd)
    if 'baer' in ron.mods:
        baer = Baer.getInstance(wd)
    else:
        baer = Disturbed.getInstance(wd)

    file_storage = request.files.get('input_upload_sbs')
    if file_storage is None or not file_storage.filename:
        return error_factory('input_upload_sbs must be provided')

    filename = secure_filename(file_storage.filename)
    if not filename:
        return error_factory('input_upload_sbs must have a valid filename')
    if filename.lower() == 'baer.cropped.tif':
        # Prevent collisions with derived baer.cropped.tif artifacts generated later.
        filename = '_baer.cropped.tif'

    file_storage.save(_join(baer.baer_dir, filename))

    ret, description = sbs_map_sanity_check(_join(baer.baer_dir, filename))
    if ret != 0:
        return exception_factory(description, runid=runid)
    baer.validate(filename, mode=0)
    return success_factory({'disturbed_fn': baer.disturbed_fn})


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/upload_cover_transform', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_upload_cover_transform(runid: str, config: str) -> Response:
    """Upload a user-defined cover transform for revegetation workflows."""
    from wepppy.nodb.mods.revegetation import Revegetation
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    reveg = Revegetation.getInstance(wd)
    try:
        saved_path = save_run_file(
            runid=runid,
            config=config,
            form_field='input_upload_cover_transform',
            allowed_extensions=('csv',),
            dest_subdir='revegetation',
            run_root=wd,
            filename_transform=lambda value: value,
            overwrite=True,
        )
    except UploadError as exc:
        return upload_failure(str(exc))

    try:
        res = reveg.validate_user_defined_cover_transform(saved_path.name)
    except UploadError as exc:
        return upload_failure(str(exc))

    return upload_success(content=res)


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
            # Fall back to direct assignments if validation fails on legacy runs
            baer.sbs_mode = 1
            baer.uniform_severity = severity
            try:
                baer._baer_fn = disturbed.disturbed_fn  # type: ignore[attr-defined]
            except Exception:
                pass

    return success_factory({'disturbed_fn': disturbed.disturbed_fn})
