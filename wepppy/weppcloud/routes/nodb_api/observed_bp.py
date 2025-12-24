"""Routes for observed blueprint extracted from app.py."""

from .._common import *  # noqa: F401,F403

from wepppy.nodb.core import Ron
from wepppy.nodb.unitizer import Unitizer
from wepppy.nodb.unitizer import precisions as UNITIZER_PRECISIONS
from wepppy.nodb.mods.observed import Observed
from wepppy.weppcloud.utils.helpers import authorize_and_handle_with_exception_factory
from wepppy.weppcloud.utils.cap_guard import requires_cap


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
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view observed reports.")
def report_observed(runid, config):
    wd = get_wd(runid)
    observed = Observed.getInstance(wd)
    ron = Ron.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)

    results = observed.results
    stat_names = observed.stat_names if results else []

    graph_series = glob(_join(ron.observed_dir, '*.csv'))
    graph_series = [_split(fn)[-1].replace('.csv', '') for fn in graph_series]
    if 'observed' in graph_series:
        graph_series.remove('observed')
    graph_series = sorted(graph_series)

    selected = request.args.get('selected')
    if selected not in graph_series:
        default_graph = 'Hillslopes-Streamflow_(mm)-Daily'
        if default_graph in graph_series:
            selected = default_graph
        else:
            selected = graph_series[0] if graph_series else None

    parseDate_fmt = "%Y-%m-%d"
    if selected:
        if 'Daily' in selected:
            parseDate_fmt = "%Y-%m-%d"
        elif 'Yearly' in selected:
            parseDate_fmt = "%Y"

    selected_scope = ""
    selected_period = ""
    selected_label = ""
    if selected:
        parts = selected.split('-')
        if parts:
            selected_scope = parts[0]
        if len(parts) > 1:
            selected_period = parts[-1]
        if len(parts) > 2:
            measure_part = "-".join(parts[1:-1])
        elif len(parts) > 1:
            measure_part = parts[1]
        else:
            measure_part = selected
        selected_label = measure_part.replace('_', ' ')

    data_url = None
    if selected:
        data_url = url_for_run(
            'observed.resources_observed_data',
            runid=runid,
            config=config,
            file=f"{selected}.csv",
        )

    return render_template('reports/wepp/observed.htm', runid=runid, config=config,
                           results=results,
                           stat_names=stat_names,
                           graph_series=graph_series,
                           selected=selected,
                           parseDate_fmt=parseDate_fmt,
                           selected_scope=selected_scope,
                           selected_period=selected_period,
                           selected_label=selected_label,
                           data_url=data_url,
                           ron=ron,
                           unitizer_nodb=unitizer,
                           precisions=UNITIZER_PRECISIONS,
                           user=current_user)


@observed_bp.route('/runs/<string:runid>/<config>/resources/observed/<file>')
def resources_observed_data(runid, config, file):

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    fn = _join(ron.observed_dir, file)

    assert _exists(fn)
    return send_file(fn, mimetype='text/csv', download_name=file)
