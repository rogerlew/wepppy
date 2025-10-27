"""Routes for watershed blueprint extracted from app.py."""

import math

from .._common import *  # noqa: F401,F403

from wepppy.nodb.core import Ron, Watershed
from wepppy.topo.watershed_abstraction import ChannelRoutingError
from wepppy.weppcloud.utils.helpers import authorize, authorize_and_handle_with_exception_factory

watershed_bp = Blueprint('watershed', __name__)

@watershed_bp.route('/runs/<string:runid>/<config>/query/delineation_pass')
@watershed_bp.route('/runs/<string:runid>/<config>/query/delineation_pass/')
@authorize_and_handle_with_exception_factory
def query_topaz_pass(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    watershed = Watershed.getInstance(wd)
    has_channels = watershed.has_channels
    has_subcatchments = watershed.has_subcatchments

    if not has_channels:
        return jsonify(0)

    if has_channels and not has_subcatchments:
        return jsonify(1)

    if has_channels and has_subcatchments:
        return jsonify(2)

    return None


@watershed_bp.route('/runs/<string:runid>/<config>/resources/channels.json')
@authorize_and_handle_with_exception_factory
def resources_channels_geojson(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    watershed = Watershed.getInstance(wd)
    fn = watershed.channels_shp

    js = json.load(open(fn))
    ron = Ron.getInstance(wd)
    name = ron.name

    if name.strip() == '':
        js['name'] = runid
    else:
        js['name'] = name

    return jsonify(js)

@watershed_bp.route('/runs/<string:runid>/<config>/query/extent')
@watershed_bp.route('/runs/<string:runid>/<config>/query/extent/')
@authorize_and_handle_with_exception_factory
def query_extent(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Ron.getInstance(wd).extent)


@watershed_bp.route('/runs/<string:runid>/<config>/report/channel')
@authorize_and_handle_with_exception_factory
def report_channel(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return render_template('reports/channel.htm', 
                           runid=runid, config=config,
                           map=Ron.getInstance(wd).map)


@watershed_bp.route('/runs/<string:runid>/<config>/query/outlet')
@watershed_bp.route('/runs/<string:runid>/<config>/query/outlet/')
@authorize_and_handle_with_exception_factory
def query_outlet(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Watershed.getInstance(wd)
                        .outlet
                        .as_dict())


@watershed_bp.route('/runs/<string:runid>/<config>/report/outlet')
@watershed_bp.route('/runs/<string:runid>/<config>/report/outlet/')
@authorize_and_handle_with_exception_factory
def report_outlet(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return render_template('reports/outlet.htm', runid=runid, config=config,
                           outlet=Watershed.getInstance(wd).outlet,
                           ron=Ron.getInstance(wd))


@watershed_bp.route('/runs/<string:runid>/<config>/query/has_dem')
@watershed_bp.route('/runs/<string:runid>/<config>/query/has_dem/')
@authorize_and_handle_with_exception_factory
def query_has_dem(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Ron.getInstance(wd).has_dem)


@watershed_bp.route('/runs/<string:runid>/<config>/query/watershed/subcatchments')
@watershed_bp.route('/runs/<string:runid>/<config>/query/watershed/subcatchments/')
@authorize_and_handle_with_exception_factory
def query_watershed_summary_subcatchments(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Watershed.getInstance(wd).subs_summary)


@watershed_bp.route('/runs/<string:runid>/<config>/query/watershed/channels')
@watershed_bp.route('/runs/<string:runid>/<config>/query/watershed/channels/')
@authorize_and_handle_with_exception_factory
def query_watershed_summary_channels(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Watershed.getInstance(wd).chns_summary)


@watershed_bp.route('/runs/<string:runid>/<config>/report/subcatchments')
@watershed_bp.route('/runs/<string:runid>/<config>/report/subcatchments/')
@authorize_and_handle_with_exception_factory
def query_watershed_summary(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return render_template('reports/subcatchments.htm', runid=runid, config=config,
                            user=current_user,
                            watershed=Watershed.getInstance(wd))

@watershed_bp.route('/runs/<string:runid>/<config>/tasks/abstract_watershed/', methods=['GET', 'POST'])
@authorize_and_handle_with_exception_factory
def task_abstract_watershed(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    watershed = Watershed.getInstance(wd)
    watershed.abstract_watershed()
    return success_factory()


@watershed_bp.route('/runs/<string:runid>/<config>/tasks/sub_intersection/', methods=['POST'])
@authorize_and_handle_with_exception_factory
def sub_intersection(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    extent = request.json.get('extent', None)
    ron = Ron.getInstance(wd)
    _map = ron.map
    subwta_fn = Watershed.getInstance(wd).subwta
    raw_ids = _map.raster_intersection(extent, raster_fn=subwta_fn, discard=(0,))

    cleaned_ids = []
    seen = set()
    for value in raw_ids:
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(numeric) or numeric < 1:
            continue
        integer_id = int(numeric)
        if integer_id < 1 or integer_id in seen:
            continue
        seen.add(integer_id)
        cleaned_ids.append(integer_id)

    return jsonify(cleaned_ids)
