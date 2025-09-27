"""Routes for unitizer blueprint extracted from app.py."""

from .._common import *  # noqa: F401,F403

from wepppy.nodb import Unitizer


unitizer_bp = Blueprint('unitizer', __name__)

@unitizer_bp.route('/runs/<string:runid>/<config>/report/tasks/set_unit_preferences/', methods=['POST'])
@unitizer_bp.route('/runs/<string:runid>/<config>/tasks/set_unit_preferences/', methods=['POST'])
def task_set_unit_preferences(runid, config):
    try:
        ctx = load_run_context(runid, config)
        wd = str(ctx.active_root)
        unitizer = Unitizer.getInstance(wd)
        res = unitizer.set_preferences(request.form)
        return success_factory(res)
    except:
        return exception_factory('Error setting unit preferences', runid=runid)


@unitizer_bp.route('/runs/<string:runid>/<config>/unitizer')
@unitizer_bp.route('/runs/<string:runid>/<config>/unitizer/')
def unitizer_route(runid, config):

    try:
        ctx = load_run_context(runid, config)
        wd = str(ctx.active_root)
        unitizer = Unitizer.getInstance(wd)

        value = request.args.get('value')
        in_units = request.args.get('in_units')
        ctx_processer = unitizer.context_processor_package()

        contents = ctx_processer['unitizer'](float(value), in_units)
        return success_factory(contents)

    except Exception:
        return exception_factory(runid=runid)


@unitizer_bp.route('/runs/<string:runid>/<config>/unitizer_units')
@unitizer_bp.route('/runs/<string:runid>/<config>/unitizer_units/')
def unitizer_units_route(runid, config):

    try:
        ctx = load_run_context(runid, config)
        wd = str(ctx.active_root)
        unitizer = Unitizer.getInstance(wd)

        in_units = request.args.get('in_units')
        ctx_processer = unitizer.context_processor_package()

        contents = ctx_processer['unitizer_units'](in_units)
        return success_factory(contents)

    except Exception:
        return exception_factory(runid=runid)
