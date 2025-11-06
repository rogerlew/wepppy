"""Flask blueprint for RHEM-specific report and query endpoints."""

from glob import glob

from os.path import join as _join

from .._common import *  # noqa: F401,F403

from wepppy.nodb.core import Ron
from wepppy.nodb.mods.rhem import RhemPost
from wepppy.nodb.unitizer import Unitizer
from wepppy.nodb.unitizer import precisions as UNITIZER_PRECISIONS
from wepppy.weppcloud.utils.helpers import (
    exception_factory,
    get_wd,
    render_template,
    authorize
)


rhem_bp = Blueprint('rhem', __name__)

@rhem_bp.route('/runs/<string:runid>/<config>/report/rhem/results')
@rhem_bp.route('/runs/<string:runid>/<config>/report/rhem/results/')
def report_rhem_results(runid, config):
    authorize(runid, config)

    try:
        return render_template('controls/rhem_reports.htm',
                               runid=runid,
                               config=config)
    except Exception:
        return exception_factory('Error building reports template', runid=runid)


@rhem_bp.route('/runs/<string:runid>/<config>/report/rhem/run_summary')
@rhem_bp.route('/runs/<string:runid>/<config>/report/rhem/run_summary/')
def report_rhem_run_summary(runid, config):
    authorize(runid, config)

    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        rhempost = RhemPost.getInstance(wd)
        subs_n = len(glob(_join(wd, 'rhem/output/*.sum')))

        return render_template(
            'reports/rhem_run_summary.htm',
            runid=runid,
            config=config,
            subs_n=subs_n,
            rhempost=rhempost,
            ron=ron,
        )
    except Exception:
        return exception_factory('Error building reports template', runid=runid)


@rhem_bp.route('/runs/<string:runid>/<config>/report/rhem/summary')
@rhem_bp.route('/runs/<string:runid>/<config>/report/rhem/summary/')
def report_rhem_avg_annuals(runid, config):
    authorize(runid, config)

    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        rhempost = RhemPost.getInstance(wd)
        unitizer = Unitizer.getInstance(wd)

        return render_template(
            'reports/rhem/avg_annual_summary.htm',
            runid=runid,
            config=config,
            rhempost=rhempost,
            ron=ron,
            unitizer_nodb=unitizer,
            precisions=UNITIZER_PRECISIONS,
            user=current_user,
        )
    except Exception:
        return exception_factory('Error running report_rhem_avg_annuals', runid=runid)

@rhem_bp.route('/runs/<string:runid>/<config>/report/rhem/return_periods')
@rhem_bp.route('/runs/<string:runid>/<config>/report/rhem/return_periods/')
def report_rhem_return_periods(runid, config):
    authorize(runid, config)

    try:
        _ = request.args.get('extraneous', None) == 'true'
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        rhempost = RhemPost.getInstance(wd)
        unitizer = Unitizer.getInstance(wd)

        return render_template(
            'reports/rhem/return_periods.htm',
            runid=runid,
            config=config,
            unitizer_nodb=unitizer,
            precisions=UNITIZER_PRECISIONS,
            rhempost=rhempost,
            ron=ron,
            user=current_user,
        )
    except Exception:
        return exception_factory('Error running report_rhem_return_periods', runid=runid)


@rhem_bp.route('/runs/<string:runid>/<config>/query/rhem/runoff/subcatchments')
@rhem_bp.route('/runs/<string:runid>/<config>/query/rhem/runoff/subcatchments/')
def query_rhem_sub_runoff(runid, config):
    authorize(runid, config)
    try:
        wd = get_wd(runid)
        rhempost = RhemPost.getInstance(wd)
        return jsonify(rhempost.query_sub_val('runoff'))

    except Exception:
        return exception_factory('Error querying RHEM subcatchments runoff', runid=runid)

@rhem_bp.route('/runs/<string:runid>/<config>/query/rhem/sed_yield/subcatchments')
@rhem_bp.route('/runs/<string:runid>/<config>/query/rhem/sed_yield/subcatchments/')
def query_rhem_sub_sed_yield(runid, config):
    wd = get_wd(runid)
    rhempost = RhemPost.getInstance(wd)
    return jsonify(rhempost.query_sub_val('sed_yield'))


@rhem_bp.route('/runs/<string:runid>/<config>/query/rhem/soil_loss/subcatchments')
@rhem_bp.route('/runs/<string:runid>/<config>/query/rhem/soil_loss/subcatchments/')
def query_rhem_sub_soil_loss(runid, config):
    wd = get_wd(runid)
    rhempost = RhemPost.getInstance(wd)
    return jsonify(rhempost.query_sub_val('soil_loss'))
