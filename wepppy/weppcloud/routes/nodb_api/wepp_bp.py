"""Routes for wepp blueprint extracted from app.py."""

import wepppy

from .._common import *  # noqa: F401,F403

from wepppy.all_your_base import isint
from wepppy.nodb import Landuse, Ron, Unitizer, Watershed, Wepp, WeppPost
from wepppy.nodb.climate import Climate
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.wepp import management
from wepppy.wepp.out import DisturbedTotalWatSed2, Element, HillWat, TotalWatSed2
from wepppy.wepp.stats import ChannelSummary, HillSummary, OutletSummary, TotalWatbal
from wepppy.weppcloud.utils.helpers import (error_factory, exception_factory, parse_rec_intervals, authorize_and_handle_with_exception_factory)

wepp_bp = Blueprint('wepp', __name__)

@wepp_bp.route('/runs/<string:runid>/<config>/view/channel_def/<chn_key>')
@wepp_bp.route('/runs/<string:runid>/<config>/view/channel_def/<chn_key>/')
@authorize_and_handle_with_exception_factory
def view_channel_def(runid, config, chn_key):
    wd = get_wd(runid)
    assert wd is not None

    try:
        chn_d = management.get_channel(chn_key)
    except KeyError:
        return error_factory('Could not find channel def with key "%s"' % chn_key)

    return jsonify(chn_d)


@wepp_bp.route('/runs/<string:runid>/<config>/view/management/<key>')
@wepp_bp.route('/runs/<string:runid>/<config>/view/management/<key>/')
@authorize_and_handle_with_exception_factory
def view_management(runid, config, key):
    wd = get_wd(runid)
    assert wd is not None

    landuse = Landuse.getInstance(wd)
    man = landuse.managements[str(key)].get_management()
    contents = repr(man)

    r = Response(response=contents, status=200, mimetype="text/plain")
    r.headers["Content-Type"] = "text/plain; charset=utf-8"
    return r


@wepp_bp.route('/runs/<string:runid>/<config>/tasks/set_run_wepp_routine', methods=['POST'])
@wepp_bp.route('/runs/<string:runid>/<config>/tasks/set_run_wepp_routine/', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_set_hourly_seepage(runid, config):

    try:
        routine = request.json.get('routine', None)
    except Exception:
        return exception_factory('Error parsing routine', runid=runid)

    if routine is None:
        return error_factory('routine is None')

    if routine not in ['wepp_ui', 'pmet', 'frost', 'tcr', 'snow', 'run_flowpaths']:
        return error_factory("routine not in ['wepp_ui', 'pmet', 'frost', 'tcr', 'snow', 'run_flowpaths']")

    try:
        state = request.json.get('state', None)
    except Exception:
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)

        if routine == 'wepp_ui':
            wepp.set_run_wepp_ui(state)
        elif routine == 'pmet':
            wepp.set_run_pmet(state)
        elif routine == 'frost':
            wepp.set_run_frost(state)
        elif routine == 'tcr':
            wepp.set_run_tcr(state)
        elif routine == 'snow':
            wepp.set_run_snow(state)
        elif routine == 'run_flowpaths':
            wepp.set_run_flowpaths(state)

    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/results')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/results/')
@authorize_and_handle_with_exception_factory
def report_wepp_results(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)
    
    try:
        prep = RedisPrep.getInstance(wd)
    except FileNotFoundError:
        prep = None

    try:
        return render_template('controls/wepp_reports.htm',
                               climate=climate,
                               prep=prep,
                               user=current_user)
    except:
        return exception_factory('Error building reports template', runid=runid)



@wepp_bp.route('/runs/<string:runid>/<config>/query/subcatchments_summary')
@wepp_bp.route('/runs/<string:runid>/<config>/query/subcatchments_summary/')
@authorize_and_handle_with_exception_factory
def query_subcatchments_summary(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:
        subcatchments_summary = ron.subs_summary()

        return jsonify(subcatchments_summary)
    except:
        return exception_factory('Error building summary', runid=runid)



@wepp_bp.route('/runs/<string:runid>/<config>/query/channels_summary')
@wepp_bp.route('/runs/<string:runid>/<config>/query/channels_summary/')
@authorize_and_handle_with_exception_factory
def query_channels_summary(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:
        channels_summary = ron.chns_summary()

        return jsonify(channels_summary)
    except:
        return exception_factory('Error building summary', runid=runid)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/prep_details')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/prep_details/')
@authorize_and_handle_with_exception_factory
def get_wepp_prep_details(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    subcatchments_summary = ron.subs_summary(abbreviated=True)
    channels_summary = ron.chns_summary(abbreviated=True)

    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/prep_details.htm', runid=runid, config=config,
                            unitizer_nodb=unitizer,
                            precisions=wepppy.nodb.unitizer.precisions,
                            subcatchments_summary=subcatchments_summary,
                            channels_summary=channels_summary,
                            user=current_user,
                            ron=ron)


@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/phosphorus_opts')
@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/phosphorus_opts/')
@authorize_and_handle_with_exception_factory
def query_wepp_phos_opts(runid, config):
    wd = get_wd(runid)
    phos_opts = Wepp.getInstance(wd).phosphorus_opts.asdict()
    return jsonify(phos_opts)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/run_summary')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/run_summary/')
@authorize_and_handle_with_exception_factory
def report_wepp_run_summary(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    flowpaths_n = len(glob(_join(wd, 'wepp/flowpaths/output/*.plot.dat')))
    subs_n = len(glob(_join(wd, 'wepp/output/*.pass.dat')))
    subs_n += len(glob(_join(wd, 'wepp/output/*/*.pass.dat')))

    return render_template('reports/wepp_run_summary.htm', runid=runid, config=config,
                           flowpaths_n=flowpaths_n,
                           subs_n=subs_n,
                           ron=ron)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/summary')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/summary/')
@authorize_and_handle_with_exception_factory
def report_wepp_loss(runid, config):
    extraneous = request.args.get('extraneous', None) == 'true'

    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))

    except:
        exclude_yr_indxs = None

    class_fractions = request.args.get('class_fractions', False)
    class_fractions = str(class_fractions).lower() == 'true'

    fraction_under = request.args.get('fraction_under', None)
    if fraction_under is not None:
        try:
            fraction_under = float(fraction_under)
        except:
            fraction_under = None

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    loss = Wepp.getInstance(wd).report_loss(exclude_yr_indxs=exclude_yr_indxs)
    is_singlestorm = loss.is_singlestorm
    out_rpt = OutletSummary(loss)
    hill_rpt = HillSummary(loss, class_fractions=class_fractions, fraction_under=fraction_under)
    chn_rpt = ChannelSummary(loss)
    avg_annual_years = loss.avg_annual_years
    excluded_years = loss.excluded_years
    translator = Watershed.getInstance(wd).translator_factory()
    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/summary.htm', runid=runid, config=config,
                        extraneous=extraneous,
                        out_rpt=out_rpt,
                        hill_rpt=hill_rpt,
                        chn_rpt=chn_rpt,
                        avg_annual_years=avg_annual_years,
                        excluded_years=excluded_years,
                        translator=translator,
                        unitizer_nodb=unitizer,
                        precisions=wepppy.nodb.unitizer.precisions,
                        ron=ron,
                        is_singlestorm=is_singlestorm,
                        user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/yearly_watbal')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/yearly_watbal/')
@authorize_and_handle_with_exception_factory
def report_wepp_yearly_watbal(runid, config):
    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))

    except:
        exclude_yr_indxs = [0, 1]

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    totwatsed = TotalWatSed2(wd)
    totwatbal = TotalWatbal(totwatsed,
                            exclude_yr_indxs=exclude_yr_indxs)

    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/yearly_watbal.htm', runid=runid, config=config,
                            unitizer_nodb=unitizer,
                            precisions=wepppy.nodb.unitizer.precisions,
                            rpt=totwatbal,
                            ron=ron,
                            user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/avg_annual_by_landuse')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/avg_annual_by_landuse/')
@authorize_and_handle_with_exception_factory
def report_wepp_avg_annual_by_landuse(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    wepp = Wepp.getInstance(wd)
    dwat = DisturbedTotalWatSed2(wd, wepp.baseflow_opts, wepp.phosphorus_opts)
    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/avg_annuals_by_landuse.htm', runid=runid, config=config,
                        unitizer_nodb=unitizer,
                        precisions=wepppy.nodb.unitizer.precisions,
                        report=dwat.annual_averages_report,
                        ron=ron,
                        user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/avg_annual_watbal')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/avg_annual_watbal/')
@authorize_and_handle_with_exception_factory
def report_wepp_avg_annual_watbal(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    hill_rpt = wepp.report_hill_watbal()
    # chn_rpt = wepp.report_chn_watbal()

    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/avg_annual_watbal.htm', runid=runid, config=config,
                            unitizer_nodb=unitizer,
                            precisions=wepppy.nodb.unitizer.precisions,
                            hill_rpt=hill_rpt,
                            # chn_rpt=chn_rpt,
                            ron=ron,
                            user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/resources/wepp/daily_streamflow.csv')
@authorize_and_handle_with_exception_factory
def resources_wepp_streamflow(runid, config):
    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))

    except:
        exclude_yr_indxs = [0, 1]

    stacked = request.args.get('stacked', None)
    if stacked is None:
        stacked = False
    else:
        stacked = stacked.lower() == 'true'

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    wepppost = WeppPost.getInstance(wd)
    fn = _join(ron.export_dir, 'daily_streamflow.csv')
    wepppost.export_streamflow(fn, exclude_yr_indxs=exclude_yr_indxs, stacked=stacked)

    assert _exists(fn)

    return send_file(fn, mimetype='text/csv', download_name='daily_streamflow.csv')


@wepp_bp.route('/runs/<string:runid>/<config>/resources/wepp/totalwatsed.csv')
@authorize_and_handle_with_exception_factory
def resources_wepp_totalwatsed(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    fn = _join(ron.export_dir, 'totalwatsed.csv')
    if not _exists(fn):
        totwatsed_txt = _join(ron.output_dir, 'totalwatsed.txt')
        if not _exists(totwatsed_txt):
           return error_factory('totalwatsed.csv is not available for this project. Please use totalwatsed2.csv')
        wepp = Wepp.getInstance(wd)
        totwatsed = TotalWatSed2(totwatsed_txt,
                                wepp.baseflow_opts, wepp.phosphorus_opts)
        totwatsed.export(fn)

    assert _exists(fn)

    return send_file(fn, mimetype='text/csv', download_name='totalwatsed.csv')


@wepp_bp.route('/runs/<string:runid>/<config>/resources/wepp/totalwatsed2.csv')
@authorize_and_handle_with_exception_factory
def resources_wepp_totalwatsed2(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    fn = _join(ron.export_dir, 'totalwatsed2.csv')

    if not _exists(fn):
        totwatsed = TotalWatSed2(wd)
        totwatsed.export(fn)
    assert _exists(fn)

    return send_file(fn, mimetype='text/csv', download_name='totalwatsed2.csv', as_attachment=True)


@wepp_bp.route('/runs/<string:runid>/<config>/plot/wepp/streamflow')
@wepp_bp.route('/runs/<string:runid>/<config>/plot/wepp/streamflow/')
@authorize_and_handle_with_exception_factory
def plot_wepp_streamflow(runid, config):
    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))
    except:
        exclude_yr_indxs = [0, 1]

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)
    return render_template('reports/wepp/daily_streamflow_graph.htm', runid=runid, config=config,
                            unitizer_nodb=unitizer,
                            precisions=wepppy.nodb.unitizer.precisions,
                            exclude_yr_indxs=','.join(str(yr) for yr in exclude_yr_indxs),
                            ron=ron,
                            user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/return_periods')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/return_periods/')
@authorize_and_handle_with_exception_factory
def report_wepp_return_periods(runid, config):
    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))
    except:
        exclude_yr_indxs = None

    try:
        res = request.args.get('exclude_months')
        exclude_months = []
        for month in res.split(','):
            if isint(month):
                exclude_months.append(int(month))
    except:
        exclude_months = None

    # get method and gringorten_correction
    # method default is cta gringorten_correction default is False
    method = request.args.get('method', 'cta')
    if method not in ['cta', 'am']:
        return error_factory('method must be either cta or am')
    
    gringorten_correction = request.args.get('gringorten_correction', 'false').lower() == 'true'

    extraneous = request.args.get('extraneous', None) == 'true'

    chn_topaz_id_of_interest = request.args.get('chn_topaz_id_of_interest', None)
    if chn_topaz_id_of_interest is not None:
        chn_topaz_id_of_interest = int(chn_topaz_id_of_interest)

    wd = get_wd(runid)

    climate = Climate.getInstance(wd)
    rec_intervals = parse_rec_intervals(request, climate.years)

    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    report = wepp.report_return_periods(
        rec_intervals=rec_intervals, 
        exclude_yr_indxs=exclude_yr_indxs,
        method=method, 
        gringorten_correction=gringorten_correction, 
        exclude_months=exclude_months,
        chn_topaz_id_of_interest=chn_topaz_id_of_interest
    )

    translator = Watershed.getInstance(wd).translator_factory()
    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/return_periods.htm', runid=runid, config=config,
                            extraneous=extraneous,
                            chn_topaz_id_of_interest=chn_topaz_id_of_interest,
                            chn_topaz_id_options=wepp.chn_topaz_ids_of_interest,
                            gringorten_correction=gringorten_correction,
                            unitizer_nodb=unitizer,
                            precisions=wepppy.nodb.unitizer.precisions,
                            report=report,
                            translator=translator,
                            ron=ron,
                            user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/frq_flood')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/frq_flood/')
@authorize_and_handle_with_exception_factory
def report_wepp_frq_flood(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    report = Wepp.getInstance(wd).report_frq_flood()
    translator = Watershed.getInstance(wd).translator_factory()

    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/frq_flood.htm', runid=runid, config=config,
                            unitizer_nodb=unitizer,
                            precisions=wepppy.nodb.unitizer.precisions,
                            report=report,
                            translator=translator,
                            ron=ron,
                            user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/sediment_characteristics')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/sediment_characteristics/')
@authorize_and_handle_with_exception_factory
def report_wepp_sediment_delivery(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    sed_del = Wepp.getInstance(wd).report_sediment_delivery()
    translator = Watershed.getInstance(wd).translator_factory()

    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/sediment_characteristics.htm', runid=runid, config=config,
                            unitizer_nodb=unitizer,
                            precisions=wepppy.nodb.unitizer.precisions,
                            sed_del=sed_del,
                            translator=translator,
                            ron=ron,
                            user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/runoff/subcatchments')
@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/runoff/subcatchments/')
@authorize_and_handle_with_exception_factory
def query_wepp_sub_runoff(runid, config):
    # blackwood http://wepp.cloud/weppcloud/runs/7f6d9b28-9967-4547-b121-e160066ed687/0/
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('Runoff'))


@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/subrunoff/subcatchments')
@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/subrunoff/subcatchments/')
@authorize_and_handle_with_exception_factory
def query_wepp_sub_subrunoff(runid, config):
    # blackwood http://wepp.cloud/weppcloud/runs/7f6d9b28-9967-4547-b121-e160066ed687/0/
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('Subrunoff'))


@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/baseflow/subcatchments')
@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/baseflow/subcatchments/')
@authorize_and_handle_with_exception_factory
def query_wepp_sub_baseflow(runid, config):
    # blackwood http://wepp.cloud/weppcloud/runs/7f6d9b28-9967-4547-b121-e160066ed687/0/
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('Baseflow'))


@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/loss/subcatchments')
@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/loss/subcatchments/')
@authorize_and_handle_with_exception_factory
def query_wepp_sub_loss(runid, config):
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('Soil Loss Density'))


@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/phosphorus/subcatchments')
@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/phosphorus/subcatchments/')
@authorize_and_handle_with_exception_factory
def query_wepp_sub_phosphorus(runid, config):
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('Total P Density'))


@wepp_bp.route('/runs/<string:runid>/<config>/query/chn_summary/<topaz_id>')
@wepp_bp.route('/runs/<string:runid>/<config>/query/chn_summary/<topaz_id>/')
@authorize_and_handle_with_exception_factory
def query_ron_chn_summary(runid, config, topaz_id):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    return jsonify(ron.chn_summary(topaz_id))


@wepp_bp.route('/runs/<string:runid>/<config>/query/sub_summary/<topaz_id>')
@wepp_bp.route('/runs/<string:runid>/<config>/query/sub_summary/<topaz_id>/')
@authorize_and_handle_with_exception_factory
def query_ron_sub_summary(runid, config, topaz_id):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        return jsonify(ron.sub_summary(topaz_id))
    except Exception:
        return exception_factory(runid=runid)


@wepp_bp.route('/runs/<string:runid>/<config>/report/chn_summary/<topaz_id>')
@wepp_bp.route('/runs/<string:runid>/<config>/report/chn_summary/<topaz_id>/')
@authorize_and_handle_with_exception_factory
def report_ron_chn_summary(runid, config, topaz_id):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        return render_template('reports/hill.htm', runid=runid, config=config,
                            ron=ron,
                            d=ron.chn_summary(topaz_id))
    except Exception:
        return exception_factory(runid=runid)


@wepp_bp.route('/runs/<string:runid>/<config>/query/topaz_wepp_map')
@wepp_bp.route('/runs/<string:runid>/<config>/query/topaz_wepp_map/')
@authorize_and_handle_with_exception_factory
def query_topaz_wepp_map(runid, config):
    wd = get_wd(runid)
    translator = Watershed.getInstance(wd).translator_factory()

    d = dict([(wepp, translator.top(wepp=wepp)) for wepp in translator.iter_wepp_sub_ids()])

    return jsonify(d)


@wepp_bp.route('/runs/<string:runid>/<config>/report/sub_summary/<topaz_id>')
@wepp_bp.route('/runs/<string:runid>/<config>/report/sub_summary/<topaz_id>/')
@authorize_and_handle_with_exception_factory
def report_ron_sub_summary(runid, config, topaz_id):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    return render_template('reports/hill.htm', runid=runid, config=config,
                           ron=ron,
                           d=ron.sub_summary(topaz_id))


@wepp_bp.route('/runs/<string:runid>/<config>/resources/wepp_loss.tif')
@authorize_and_handle_with_exception_factory
def resources_wepp_loss(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        loss_grid_wgs = _join(ron.plot_dir, 'loss.WGS.tif')

        if _exists(loss_grid_wgs):
            return send_file(loss_grid_wgs, mimetype='image/tiff')

        return error_factory('loss_grid_wgs does not exist')

    except Exception:
        return exception_factory(runid=runid)


@wepp_bp.route('/runs/<string:runid>/<config>/resources/flowpaths_loss.tif')
@authorize_and_handle_with_exception_factory
def resources_flowpaths_loss(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        loss_grid_wgs = _join(ron.plot_dir, 'flowpaths_loss.WGS.tif')

        if _exists(loss_grid_wgs):
            return send_file(loss_grid_wgs, mimetype='image/tiff')

        return error_factory('loss_grid_wgs does not exist')

    except Exception:
        return exception_factory(runid=runid)


@wepp_bp.route('/runs/<string:runid>/<config>/query/bound_coords')
@wepp_bp.route('/runs/<string:runid>/<config>/query/bound_coords/')
@authorize_and_handle_with_exception_factory
def query_bound_coords(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        bound_wgs_json = _join(ron.topaz_wd, 'BOUND.WGS.JSON')

        if _exists(bound_wgs_json):
            with open(bound_wgs_json) as fp:
                js = json.load(fp)
                coords = js['features'][0]['geometry']['coordinates'][0]
                coords = [ll[::-1] for ll in coords]

                return success_factory(coords)

        return error_factory('Could not determine coords')

    except Exception:
        return exception_factory(runid=runid)
