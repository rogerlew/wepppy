"""Routes for soils blueprint extracted from app.py."""

from .._common import *  # noqa: F401,F403

from wepppy.nodb.core import Soils, SoilsMode
from wepppy.nodb.mods.disturbed import Disturbed


soils_bp = Blueprint('soils', __name__)

@soils_bp.route('/runs/<string:runid>/<config>/tasks/set_soil_mode/', methods=['POST'])
def set_soil_mode(runid, config):

    mode = None
    single_selection = None

    try:
        mode = int(request.form.get('mode', None))
        single_selection = \
            int(request.form.get('soil_single_selection', None))

        single_dbselection = \
            request.form.get('soil_single_dbselection', None)

    except Exception:
        exception_factory('mode and soil_single_selection must be provided', runid=runid)

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    try:
        soils = Soils.getInstance(wd)
        soils.mode = SoilsMode(mode)
        soils.single_selection = single_selection
        soils.single_dbselection = single_dbselection

    except Exception:
        exception_factory('error setting soils mode', runid=runid)

    return success_factory()


@soils_bp.route('/runs/<string:runid>/<config>/query/soils')
@soils_bp.route('/runs/<string:runid>/<config>/query/soils/')
def query_soils(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Soils.getInstance(wd).domsoil_d)


@soils_bp.route('/runs/<string:runid>/<config>/query/soils/subcatchments')
@soils_bp.route('/runs/<string:runid>/<config>/query/soils/subcatchments/')
def query_soils_subcatchments(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Soils.getInstance(wd).subs_summary)


@soils_bp.route('/runs/<string:runid>/<config>/query/soils/channels')
@soils_bp.route('/runs/<string:runid>/<config>/query/soils/channels/')
def query_soils_channels(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Soils.getInstance(wd).chns_summary)


@soils_bp.route('/runs/<string:runid>/<config>/report/soils')
@soils_bp.route('/runs/<string:runid>/<config>/report/soils/')
def report_soils(runid, config):
    try:
        ctx = load_run_context(runid, config)
        wd = str(ctx.active_root)
        return render_template('reports/soils.htm', runid=runid, config=config,
                               report=Soils.getInstance(wd).report)
    except Exception as e:
        return exception_factory('Building Soil Failed', runid=runid)


@soils_bp.route('/runs/<string:runid>/<config>/tasks/set_soils_ksflag', methods=['POST'])
@soils_bp.route('/runs/<string:runid>/<config>/tasks/set_soils_ksflag/', methods=['POST'])
def task_set_soils_ksflag(runid, config):

    try:
        state = request.json.get('ksflag', None)
    except Exception:
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        ctx = load_run_context(runid, config)
        wd = str(ctx.active_root)
        soils = Soils.getInstance(wd)
        soils.ksflag = state
    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()


@soils_bp.route('/runs/<string:runid>/<config>/tasks/set_disturbed_sol_ver', methods=['POST'])
@soils_bp.route('/runs/<string:runid>/<config>/tasks/set_disturbed_sol_ver/', methods=['POST'])
def task_set_disturbed_sol_ver(runid, config):

    try:
        state = request.json.get('sol_ver', None)
    except Exception:
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        ctx = load_run_context(runid, config)
        wd = str(ctx.active_root)
        disturbed = Disturbed.getInstance(wd)
        disturbed.sol_ver = state
    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()
