"""Routes for climate blueprint extracted from app.py."""

from ._common import *  # noqa: F401,F403

from wepppy.climates.cligen import StationMeta
from wepppy.nodb import Ron
from wepppy.nodb.climate import Climate, ClimateStationMode


climate_bp = Blueprint('climate', __name__)


@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_climatestation_mode/', methods=['POST'])
def set_climatestation_mode(runid, config):

    try:
        mode = int(request.form.get('mode', None))
    except Exception:
        return exception_factory('Could not determine mode', runid=runid)

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climatestation_mode = ClimateStationMode(int(mode))
    except Exception:
        return exception_factory('Building setting climate station mode', runid=runid)

    return success_factory()


@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_climatestation/', methods=['POST'])
def set_climatestation(runid, config):

    try:
        station = request.form.get('station', None)
    except Exception:
        return exception_factory('Station not provided', runid=runid)

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climatestation = station
    except Exception:
        return exception_factory('Building setting climate station mode', runid=runid)

    return success_factory()


@climate_bp.route('/runs/<string:runid>/<config>/tasks/upload_cli/', methods=['POST'])
def task_upload_cli(runid, config):
    wd = get_wd(runid)

    ron = Ron.getInstance(wd)
    climate = Climate.getInstance(wd)

    try:
        file = request.files['input_upload_cli']
    except Exception:
        return exception_factory('Could not find file', runid=runid)

    try:
        if file.filename == '':
            return error_factory('no filename specified')

        filename = secure_filename(file.filename)
    except Exception:
        return exception_factory('Could not obtain filename', runid=runid)

    try:
        file.save(_join(climate.cli_dir, filename))
    except Exception:
        return exception_factory('Could not save file', runid=runid)

    try:
        res = climate.set_user_defined_cli(filename)
    except Exception:
        return exception_factory('Failed validating file', runid=runid)

    return success_factory()


@climate_bp.route('/runs/<string:runid>/<config>/query/climatestation')
@climate_bp.route('/runs/<string:runid>/<config>/query/climatestation/')
def query_climatestation(runid, config):
    wd = get_wd(runid)
    return jsonify(Climate.getInstance(wd).climatestation)


@climate_bp.route('/runs/<string:runid>/<config>/query/climate_has_observed')
@climate_bp.route('/runs/<string:runid>/<config>/query/climate_has_observed/')
def query_climate_has_observed(runid, config):
    wd = get_wd(runid)
    return jsonify(Climate.getInstance(wd).has_observed)


@climate_bp.route('/runs/<string:runid>/<config>/report/climate/')
def report_climate(runid, config):
    wd = get_wd(runid)
 
    climate = Climate.getInstance(wd)
    return render_template('reports/climate.htm', runid=runid, config=config,
                           station_meta=climate.climatestation_meta,
                           climate=climate)


@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_climate_mode/', methods=['POST'])
def set_climate_mode(runid, config):
    try:
        mode = int(request.form.get('mode', None))
    except Exception:
        return exception_factory('Could not determine mode', runid=runid)

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climate_mode = mode
    except Exception:
        return exception_factory('Building setting climate mode', runid=runid)

    return success_factory()


@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_climate_spatialmode/', methods=['POST'])
def set_climate_spatialmode(runid, config):
    try:
        spatialmode = int(request.form.get('spatialmode', None))
    except Exception:
        return exception_factory('Could not determine mode', runid=runid)

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climate_spatialmode = spatialmode
    except Exception:
        return exception_factory('Building setting climate spatial mode', runid=runid)

    return success_factory()


@climate_bp.route('/runs/<string:runid>/<config>/view/closest_stations/')
def view_closest_stations(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd, ignore_lock=True)

    if climate.readonly:
        results = climate.closest_stations
    else:
        try:
            results = climate.find_closest_stations()
        except Exception:
            return exception_factory('Error finding closest stations', runid=runid)

    if results is None:
        return Response('<!-- closest_stations is None -->', mimetype='text/html')

    options = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]
        options.append('<option value="{id}" {selected}>'
                       '{desc} ({distance_to_query_location:0.1f} km | {years} years)</option>'
                       .format(**r))

    return Response('n'.join(options), mimetype='text/html')


@climate_bp.route('/runs/<string:runid>/<config>/view/heuristic_stations/')
def view_heuristic_stations(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd, ignore_lock=True)

    if climate.readonly:
        results = climate.heuristic_stations
    else:
        try:
            results = climate.find_heuristic_stations()
        except Exception:
            return exception_factory('Error finding heuristic stations', runid=runid)

    if results is None:
        return Response('<!-- heuristic_stations is None -->', mimetype='text/html')

#    return jsonify(results)

    options = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]

        if r['distance_to_query_location'] is None:
            r['distance_to_query_location'] == -1

        options.append('<option value="{id}" {selected}>'
                       '{desc} ({rank_based_on_query_location} | '
                       '{distance_to_query_location:0.1f} km | {years} years)</option>'
                       .format(**r))

    return Response('n'.join(options), mimetype='text/html')


@climate_bp.route('/runs/<string:runid>/<config>/view/par/')
def view_station_par(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd, ignore_lock=True)
    contents = climate.climatestation_par_contents
    return Response(contents, content_type='text/plain;charset=utf-8')


@climate_bp.route('/runs/<string:runid>/<config>/view/eu_heuristic_stations/')
def view_eu_heuristic_stations(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        results = climate.find_eu_heuristic_stations()
    except Exception:
        return exception_factory('Error finding heuristic stations', runid=runid)

    if results is None:
        return Response('<!-- heuristic_stations is None -->', mimetype='text/html')

    options = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]
        options.append('<option value="{id}" {selected}>'
                       '{desc} ({rank_based_on_query_location} | {years} years)</option>'
                       .format(**r))

    return Response('n'.join(options), mimetype='text/html')


@climate_bp.route('/runs/<string:runid>/<config>/view/au_heuristic_stations/')
def view_au_heuristic_stations(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        results = climate.find_au_heuristic_stations()
    except Exception:
        return exception_factory('Error finding heuristic stations', runid=runid)

    if results is None:
        return Response('<!-- heuristic_stations is None -->', mimetype='text/html')

    options = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]
        options.append('<option value="{id}" {selected}>'
                       '{desc} ({rank_based_on_query_location} | {years} years)</option>'
                       .format(**r))

    return Response('n'.join(options), mimetype='text/html')


@climate_bp.route('/runs/<string:runid>/<config>/view/climate_monthlies')
@climate_bp.route('/runs/<string:runid>/<config>/view/climate_monthlies/')
def view_climate_monthlies(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        station_meta = climate.climatestation_meta
    except Exception:
        return exception_factory('Could not find climatestation_meta', runid=runid)

    if station_meta is None:
        return error_factory('Climate Station not Set')

    assert isinstance(station_meta, StationMeta)
    return render_template('controls/climate_monthlies.htm',
                           title='Summary for the selected station',
                           station=station_meta.as_dict(include_monthlies=True))


@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_use_gridmet_wind_when_applicable', methods=['POST'])
@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_use_gridmet_wind_when_applicable/', methods=['POST'])
def task_set_use_gridmet_wind_when_applicable(runid, config):

    try:
        state = request.json.get('state', None)
    except Exception:
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        climate = Climate.getInstance(wd)
        climate.use_gridmet_wind_when_applicable = state

    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()
