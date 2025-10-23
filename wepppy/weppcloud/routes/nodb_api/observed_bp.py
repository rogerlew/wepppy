"""Routes for observed blueprint extracted from app.py."""

from .._common import *  # noqa: F401,F403

from wepppy.nodb.core import Ron, Wepp
from wepppy.nodb.unitizer import Unitizer
from wepppy.nodb.mods.observed import Observed


observed_bp = Blueprint('observed', __name__)


@observed_bp.route('/runs/<string:runid>/<config>/tasks/run_model_fit', methods=['POST'])
@observed_bp.route('/runs/<string:runid>/<config>/tasks/run_model_fit/', methods=['POST'])
def submit_task_run_model_fit(runid, config):
    wd = get_wd(runid)
    observed = Observed.getInstance(wd)

    payload = parse_request_payload(request, trim_strings=False)
    textdata = payload.get('data')
    if textdata is None:
        textdata = payload.get('observed_text')

    if textdata is None:
        response = error_factory('No observed dataset supplied.')
        response.status_code = 400
        return response

    if not isinstance(textdata, str):
        response = error_factory('Observed dataset must be provided as CSV text.')
        response.status_code = 400
        return response

    try:
        observed.parse_textdata(textdata)
    except Exception:
        return exception_factory('Error parsing text', runid=runid)
    # TODO refactor as RQ task?
    try:
        observed.calc_model_fit()
    except Exception:
        return exception_factory('Error running model fit', runid=runid)

    return success_factory()


@observed_bp.route('/runs/<string:runid>/<config>/report/observed')
@observed_bp.route('/runs/<string:runid>/<config>/report/observed/')
def report_observed(runid, config):
    wd = get_wd(runid)
    observed = Observed.getInstance(wd)
    ron = Ron.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/observed.htm', runid=runid, config=config,
                           results=observed.results,
                           stat_names=observed.stat_names,
                           ron=ron,
                           unitizer_nodb=unitizer,
                           user=current_user)


@observed_bp.route('/runs/<string:runid>/<config>/plot/observed/<selected>/')
@observed_bp.route('/runs/<string:runid>/<config>/plot/observed/<selected>/')
def plot_observed(runid, config, selected):

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)

    graph_series = glob(_join(wepp.observed_dir, '*.csv'))
    graph_series = [_split(fn)[-1].replace('.csv', '') for fn in graph_series]
    graph_series.remove('observed')

    assert selected in graph_series

    if 'Daily' in selected:
        parseDate_fmt = "%m/%d/%Y"
    else:
        parseDate_fmt = "%Y"

    return render_template('reports/wepp/observed_comparison_graph.htm', runid=runid, config=config,
                           graph_series=sorted(graph_series),
                           selected=selected,
                           parseDate_fmt=parseDate_fmt,
                           ron=ron,
                           unitizer_nodb=unitizer,
                           user=current_user)


@observed_bp.route('/runs/<string:runid>/<config>/resources/observed/<file>')
def resources_observed_data(runid, config, file):

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    fn = _join(ron.observed_dir, file)

    assert _exists(fn)
    return send_file(fn, mimetype='text/csv', download_name=file)
