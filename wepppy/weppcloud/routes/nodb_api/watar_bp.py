"""Routes for watar blueprint extracted from app.py."""

import wepppy

from ast import literal_eval

from wepppy.nodb.mods.ash_transport.ash_type import AshType

from .._common import *  # noqa: F401,F403

from wepppy.all_your_base.dateutils import YearlessDate
from wepppy.all_your_base import isint

from wepppy.nodb.core import *
from wepppy.nodb.base import *

from wepppy.nodb.unitizer import Unitizer
from wepppy.nodb.mods.ash_transport import Ash, AshPost
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.weppcloud.utils.helpers import get_run_owners_lazy, get_user_models, authorize, parse_rec_intervals
from wepppy.wepp.interchange.hill_wat_interchange import load_hill_wat_dataframe

from wepppy.wepp.reports import HillSummaryReport, ChannelSummaryReport, OutletSummaryReport


watar_bp = Blueprint('watar', __name__)

@watar_bp.route('/runs/<string:runid>/<config>/hillslope/<topaz_id>/ash')
@watar_bp.route('/runs/<string:runid>/<config>/hillslope/<topaz_id>/ash/')
def hillslope0_ash(runid, config, topaz_id):
    assert config is not None

    from wepppy.climates.cligen import ClimateFile

    wd = get_wd(runid)

    try:
        owners = get_run_owners_lazy(runid)
        ron = Ron.getInstance(wd)

        should_abort = True
        if current_user in owners:
            should_abort = False

        if not owners:
            should_abort = False

        if current_user.has_role('Admin'):
            should_abort = False

        if ron.public:
            should_abort = False

        #if should_abort:
        #    abort(404)

        fire_date = request.args.get('fire_date', None)
        if fire_date is None:
            fire_date = '8/4'
        _fire_date = YearlessDate.from_string(fire_date)

        ini_ash_depth = request.args.get('ini_ash_depth', None)
        if ini_ash_depth is None:
            ini_ash_depth = 5.0
        ini_ash_depth = float(ini_ash_depth)

        ash_type = request.args.get('ash_type', None)
        if ash_type is None:
            ash_type = 'black'

        _ash_type = None
        if 'black' in ash_type.lower():
            _ash_type = AshType.BLACK
        elif 'white' in ash_type.lower():
            _ash_type = AshType.WHITE

        ash_dir = _join(wd, '_ash')
        if not _exists(ash_dir):
            os.mkdir(ash_dir)

        unitizer = Unitizer.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        wepp_id = translator.wepp(top=topaz_id)
        sub = watershed.sub_summary(topaz_id)
        climate = Climate.getInstance(wd)
        wepp = Wepp.getInstance(wd)
        ash = Ash.getInstance(wd)
    
        cli_path = climate.cli_path
        cli_df = ClimateFile(cli_path).as_dataframe()

        hill_wat_df = load_hill_wat_dataframe(
            wepp.output_dir, wepp_id, collapse="daily"
        )

        prefix = 'H{wepp_id}'.format(wepp_id=wepp_id)
        recurrence = [100, 50, 20, 10, 2.5, 1]

        # model selection as alex or anu
        from wepppy.nodb.mods.ash_transport.ash_multi_year_model import WhiteAshModel, BlackAshModel

        if _ash_type == AshType.BLACK:
            _, results, annuals = BlackAshModel().run_model(_fire_date, cli_df, hill_wat_df,
                                                            ash_dir, prefix=prefix, recurrence=recurrence,
                                                            ini_ash_depth=ini_ash_depth)
        elif _ash_type == AshType.WHITE:
            _, results, annuals = WhiteAshModel().run_model(_fire_date, cli_df, hill_wat_df,
                                                            ash_dir, prefix=prefix, recurrence=recurrence,
                                                            ini_ash_depth=ini_ash_depth)
        else:
            raise ValueError

        results = json.loads(json.dumps(results))
        annuals = json.loads(json.dumps(annuals))

        #return jsonify(dict(results=results, recurrence_intervals=recurrence))

        return render_template('reports/ash/ash_hillslope.htm', runid=runid, config=config,
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               sub=sub,
                               ash_type=ash_type,
                               ini_ash_depth=5.0,
                               fire_date=fire_date,
                               recurrence_intervals=recurrence,
                               results=results,
                               annuals=annuals,
                               ron=ron,
                               user=current_user)

    except:
        return exception_factory('Error loading ash hillslope results', runid=runid)


@watar_bp.route('/runs/<string:runid>/<config>/tasks/set_ash_wind_transport', methods=['POST'])
@watar_bp.route('/runs/<string:runid>/<config>/tasks/set_ash_wind_transport/', methods=['POST'])
def task_set_ash_wind_transport(runid, config):

    try:
        state = request.json.get('run_wind_transport', None)
    except Exception:
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        ash = Ash.getInstance(wd)
        ash.run_wind_transport = state
    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()

@watar_bp.route('/runs/<string:runid>/<config>/report/run_ash')
@watar_bp.route('/runs/<string:runid>/<config>/report/run_ash/')
def report_run_ash(runid, config):
    try:
        wd = get_wd(runid)
        ash = Ash.getInstance(wd)

        return render_template('reports/ash/run_summary.htm', runid=runid, config=config,
                               ash=ash)

    except Exception:
        return exception_factory('Error', runid=runid)


@watar_bp.route('/runs/<string:runid>/<config>/report/ash')
@watar_bp.route('/runs/<string:runid>/<config>/report/ash/')
def report_ash(runid, config):
    try:
        wd = get_wd(runid)

        climate = Climate.getInstance(wd)
        rec_intervals = parse_rec_intervals(request, climate.years)

        ron = Ron.getInstance(wd)
        ash = Ash.getInstance(wd)
        ashpost = AshPost.getInstance(wd)

        fire_date = ash.fire_date
        ini_white_ash_depth_mm = ash.ini_white_ash_depth_mm
        ini_black_ash_depth_mm = ash.ini_black_ash_depth_mm
        unitizer = Unitizer.getInstance(wd)

        disturbed = None
        try:
            disturbed = Disturbed.getInstance(wd)
        except:
            pass


        burn_class_summary = ash.burn_class_summary()

        recurrence_intervals = ashpost.recurrence_intervals
        return_periods = ashpost.return_periods
        cum_return_periods = ashpost.cum_return_periods

        #return jsonify(dict(return_periods=return_periods, cum_return_period=cum_return_periods))

        return render_template('reports/ash/ash_watershed.htm', runid=runid, config=config,
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               fire_date=fire_date,
                               burn_class_summary=burn_class_summary,
                               ini_black_ash_depth_mm=ini_black_ash_depth_mm,
                               ini_white_ash_depth_mm=ini_white_ash_depth_mm,
                               recurrence_intervals=recurrence_intervals,
                               return_periods=return_periods,
                               cum_return_periods=cum_return_periods,
                               ash=ash,
                               ron=ron,
                               user=current_user)

    except Exception:
        return exception_factory('Error', runid=runid)


@watar_bp.route('/runs/<string:runid>/<config>/query/ash_out')
@watar_bp.route('/runs/<string:runid>/<config>/query/ash_out/')
def query_ash_out(runid, config):
    try:
        wd = get_wd(runid)
        ashpost = AshPost.getInstance(wd)
        ash_out = ashpost.ash_out

        return jsonify(ash_out)

    except Exception:
        return exception_factory(runid=runid)


@watar_bp.route('/runs/<string:runid>/<config>/report/ash_contaminant', methods=['GET', 'POST'])
@watar_bp.route('/runs/<string:runid>/<config>/report/ash_contaminant/', methods=['GET', 'POST'])
def report_contaminant(runid, config):

    try:
        wd = get_wd(runid)

        climate = Climate.getInstance(wd)
        ron = Ron.getInstance(wd)
        ash = Ash.getInstance(wd)
        ashpost = AshPost.getInstance(wd)

        rec_intervals = parse_rec_intervals(request, climate.years)
        contaminants = request.args.get('contaminants', None)
        contaminant_keys = sorted(ash.high_contaminant_concentrations.keys())

        if contaminants is not None:
            contaminants = contaminants.split(',')
        else:
            # defaults
            contaminants = []
            for c in ['Ca', 'Pb', 'P', 'Hg']:
                if c in contaminant_keys:
                    contaminants.append(c)
        
            # defaults not available
            if len(contaminants) == 0:
                contaminants = contaminant_keys

        if request.method == 'POST':
            ash.parse_cc_inputs(dict(request.form))
            ash = Ash.getInstance(wd)

        unitizer = Unitizer.getInstance(wd)

        # if not ash.has_watershed_summaries:
        #     ash.report()

        recurrence_intervals = ashpost.recurrence_intervals
        results = ashpost.burn_class_return_periods
        return_periods = ashpost.return_periods

        pw0_stats = ashpost.pw0_stats

        return render_template('reports/ash/ash_contaminant.htm', runid=runid, config=config,
                               rec_intervals=recurrence_intervals,
                               rec_results=results,
                               return_periods=return_periods,
                               contaminants=contaminants,
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               pw0_stats=pw0_stats,
                               ash=ash,
                               ron=ron,
                               user=current_user)

    except Exception:
        return exception_factory('Error', runid=runid)
