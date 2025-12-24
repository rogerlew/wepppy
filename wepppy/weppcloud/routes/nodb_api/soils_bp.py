"""Routes for soils controller blueprint."""

from __future__ import annotations

from flask import Response

from .._common import (
    Blueprint,
    error_factory,
    exception_factory,
    jsonify,
    load_run_context,
    parse_request_payload,
    render_template,
    request,
    success_factory,
)

from wepppy.nodb.core import Soils, SoilsMode
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.weppcloud.utils.cap_guard import requires_cap


soils_bp = Blueprint('soils', __name__)


@soils_bp.route('/runs/<string:runid>/<config>/tasks/set_soil_mode/', methods=['POST'])
def set_soil_mode(runid: str, config: str) -> Response:
    """Persist soil mode selections for the active run."""
    payload = parse_request_payload(request)

    try:
        mode_raw = payload.get('mode')
        mode = int(mode_raw) if mode_raw is not None else None

        single_selection_raw = payload.get('soil_single_selection', None)
        single_selection = None
        if single_selection_raw not in (None, '', []):
            single_selection = int(single_selection_raw)

        single_dbselection_raw = payload.get('soil_single_dbselection', None)
        if isinstance(single_dbselection_raw, list):
            single_dbselection = single_dbselection_raw[0] if single_dbselection_raw else None
        else:
            single_dbselection = single_dbselection_raw
    except (TypeError, ValueError):
        return exception_factory('mode and soil_single_selection must be provided', runid=runid)

    if mode is None:
        return exception_factory('mode and soil_single_selection must be provided', runid=runid)

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    try:
        soils = Soils.getInstance(wd)
        soils.mode = SoilsMode(mode)
        if single_selection is not None:
            soils.single_selection = single_selection
        soils.single_dbselection = single_dbselection
    except Exception:
        return exception_factory('error setting soils mode', runid=runid)

    return success_factory()


@soils_bp.route('/runs/<string:runid>/<config>/query/soils')
@soils_bp.route('/runs/<string:runid>/<config>/query/soils/')
def query_soils(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Soils.getInstance(wd).domsoil_d)


@soils_bp.route('/runs/<string:runid>/<config>/query/soils/subcatchments')
@soils_bp.route('/runs/<string:runid>/<config>/query/soils/subcatchments/')
def query_soils_subcatchments(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Soils.getInstance(wd).subs_summary)


@soils_bp.route('/runs/<string:runid>/<config>/query/soils/channels')
@soils_bp.route('/runs/<string:runid>/<config>/query/soils/channels/')
def query_soils_channels(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Soils.getInstance(wd).chns_summary)


@soils_bp.route('/runs/<string:runid>/<config>/report/soils')
@soils_bp.route('/runs/<string:runid>/<config>/report/soils/')
@requires_cap(gate_reason="Complete verification to view soils reports.")
def report_soils(runid: str, config: str) -> Response:
    try:
        ctx = load_run_context(runid, config)
        wd = str(ctx.active_root)
        return render_template(
            'reports/soils.htm',
            runid=runid,
            config=config,
            report=Soils.getInstance(wd).report,
        )
    except Exception:
        return exception_factory('Building Soil Failed', runid=runid)


@soils_bp.route('/runs/<string:runid>/<config>/tasks/set_soils_ksflag', methods=['POST'])
@soils_bp.route('/runs/<string:runid>/<config>/tasks/set_soils_ksflag/', methods=['POST'])
def task_set_soils_ksflag(runid: str, config: str) -> Response:
    payload = parse_request_payload(request, boolean_fields={'ksflag'})
    state = payload.get('ksflag', None)

    if state is None:
        return exception_factory('Error parsing state', runid=runid)

    try:
        ctx = load_run_context(runid, config)
        wd = str(ctx.active_root)
        soils = Soils.getInstance(wd)
        soils.ksflag = bool(state)
    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()


@soils_bp.route('/runs/<string:runid>/<config>/tasks/set_disturbed_sol_ver', methods=['POST'])
@soils_bp.route('/runs/<string:runid>/<config>/tasks/set_disturbed_sol_ver/', methods=['POST'])
def task_set_disturbed_sol_ver(runid: str, config: str) -> Response:
    payload = parse_request_payload(request)
    state_raw = payload.get('sol_ver', None)

    if state_raw is None:
        return error_factory('state is None')

    try:
        state = float(state_raw)
    except (TypeError, ValueError):
        return exception_factory('Error parsing state', runid=runid)

    try:
        ctx = load_run_context(runid, config)
        wd = str(ctx.active_root)
        disturbed = Disturbed.getInstance(wd)
        disturbed.sol_ver = state
    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()
