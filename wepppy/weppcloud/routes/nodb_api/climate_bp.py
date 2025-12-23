"""Routes for climate blueprint extracted from app.py."""

from __future__ import annotations

from typing import Any, List, MutableMapping, Sequence

from flask import Response

from .._common import *  # noqa: F401,F403

from wepppy.climates.cligen import StationMeta
from wepppy.nodb.core import Ron
from wepppy.nodb.core.climate import Climate, ClimateStationMode
from wepppy.weppcloud.utils.uploads import (
    UploadError,
    log_upload_prefix_usage,
    save_run_file,
    upload_failure,
    upload_success,
)

StationOption = MutableMapping[str, Any]


climate_bp = Blueprint('climate', __name__)


@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_climatestation_mode/', methods=['POST'])
def set_climatestation_mode(runid: str, config: str) -> Response:
    """Persist the requested climate station mode for the active run.

    Args:
        runid: Identifier for the working directory.
        config: Name of the configuration profile (unused but required by the route schema).

    Returns:
        Response: JSON payload indicating success or detailing the failure reason.
    """
    payload = parse_request_payload(request)
    mode_value = payload.get('mode', None)

    try:
        mode = int(mode_value)
    except (TypeError, ValueError):
        return exception_factory('Could not determine mode', runid=runid)

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climatestation_mode = ClimateStationMode(int(mode))
    except Exception:
        return exception_factory('Building setting climate station mode', runid=runid)

    return success_factory()


@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_climatestation/', methods=['POST'])
def set_climatestation(runid: str, config: str) -> Response:
    """Set the selected station identifier on the Climate controller.

    Args:
        runid: Identifier for the active run.
        config: Name of the configuration profile.

    Returns:
        Response: JSON response describing success or the encountered error.
    """
    payload = parse_request_payload(request)
    station = payload.get('station', None)
    if station in (None, ''):
        return exception_factory('Station not provided', runid=runid)

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climatestation = station
    except Exception:
        return exception_factory('Building setting climate station mode', runid=runid)

    return success_factory()


@climate_bp.route('/runs/<string:runid>/<config>/tasks/upload_cli/', methods=['POST'])
def task_upload_cli(runid: str, config: str) -> Response:
    """Persist a user-uploaded CLIGEN `.cli` file for the active run.

    Args:
        runid: Identifier for the working directory.
        config: Configuration profile name.

    Returns:
        Response: JSON payload indicating success or identifying why the upload failed.
    """
    log_upload_prefix_usage("tasks/upload_cli")
    wd = get_wd(runid)

    ron = Ron.getInstance(wd)
    climate = Climate.getInstance(wd)

    cli_dir = climate.cli_dir

    try:
        saved_path = save_run_file(
            runid=runid,
            config=config,
            form_field='input_upload_cli',
            allowed_extensions=('cli',),
            dest_subdir='',
            run_root=cli_dir,
            filename_transform=lambda value: value,
            overwrite=True,
        )
    except UploadError as exc:
        return upload_failure(str(exc))
    except Exception:
        return exception_factory('Could not save file', runid=runid)

    try:
        climate.set_user_defined_cli(saved_path.name)
    except UploadError as exc:
        return upload_failure(str(exc))
    except Exception:
        return exception_factory('Failed validating file', runid=runid)

    return upload_success()


@climate_bp.route('/runs/<string:runid>/<config>/query/climatestation')
@climate_bp.route('/runs/<string:runid>/<config>/query/climatestation/')
def query_climatestation(runid: str, config: str) -> Response:
    """Return the currently selected climate station identifier.

    Args:
        runid: Identifier for the active run.
        config: Configuration profile (unused in handler).

    Returns:
        Response: JSON representation of the current station id.
    """
    wd = get_wd(runid)
    return jsonify(Climate.getInstance(wd).climatestation)


@climate_bp.route('/runs/<string:runid>/<config>/query/climate_has_observed')
@climate_bp.route('/runs/<string:runid>/<config>/query/climate_has_observed/')
def query_climate_has_observed(runid: str, config: str) -> Response:
    """Expose whether the climate run contains observed data.

    Args:
        runid: Identifier for the active run.
        config: Configuration profile name.

    Returns:
        Response: JSON boolean describing the presence of observed data.
    """
    wd = get_wd(runid)
    return jsonify(Climate.getInstance(wd).has_observed)


@climate_bp.route('/runs/<string:runid>/<config>/query/climate_catalog')
@climate_bp.route('/runs/<string:runid>/<config>/query/climate_catalog/')
def query_climate_catalog(runid: str, config: str) -> Response:
    """Return the catalogued climate datasets for the active run."""
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)
    try:
        payload = climate.catalog_datasets_payload()
    except Exception:
        return exception_factory('Error loading climate catalog', runid=runid)
    return jsonify(payload)


@climate_bp.route('/runs/<string:runid>/<config>/report/climate/')
def report_climate(runid: str, config: str) -> Response:
    """Render the HTML climate report for the selected station.

    Args:
        runid: Identifier for the working directory.
        config: Configuration profile name.

    Returns:
        Response: Rendered template response.
    """
    wd = get_wd(runid)
 
    climate = Climate.getInstance(wd)
    return render_template('reports/climate.htm', runid=runid, config=config,
                           station_meta=climate.climatestation_meta,
                           climate=climate)


@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_climate_mode/', methods=['POST'])
def set_climate_mode(runid: str, config: str) -> Response:
    """Set the climate mode enum on the Climate controller.

    Args:
        runid: Identifier for the active run.
        config: Configuration profile name.

    Returns:
        Response: JSON success payload or error description.
    """
    payload = parse_request_payload(request)
    mode_value = payload.get('mode', None)
    catalog_id = payload.get('catalog_id') or payload.get('climate_catalog_id')

    mode: int | None
    if mode_value is None or mode_value == '':
        mode = None
    else:
        try:
            mode = int(mode_value)
        except (TypeError, ValueError):
            return exception_factory('Could not determine mode', runid=runid)

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        if mode is not None:
            climate.climate_mode = mode
        if catalog_id:
            dataset = climate._resolve_catalog_dataset(str(catalog_id), include_hidden=True)
            if dataset is None:
                return exception_factory('Unknown climate catalog id', runid=runid)
            climate.catalog_id = dataset.catalog_id
    except Exception:
        return exception_factory('Building setting climate mode', runid=runid)

    return success_factory()


@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_climate_spatialmode/', methods=['POST'])
def set_climate_spatialmode(runid: str, config: str) -> Response:
    """Set the spatial climate mode flag for the active run.

    Args:
        runid: Identifier for the active run.
        config: Configuration profile name.

    Returns:
        Response: JSON success payload or an error response.
    """
    payload = parse_request_payload(request)
    spatial_value = payload.get('spatialmode', None)
    try:
        spatialmode = int(spatial_value)
    except (TypeError, ValueError):
        return exception_factory('Could not determine mode', runid=runid)

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climate_spatialmode = spatialmode
    except Exception:
        return exception_factory('Building setting climate spatial mode', runid=runid)

    return success_factory()


@climate_bp.route('/runs/<string:runid>/<config>/view/closest_stations/')
def view_closest_stations(runid: str, config: str) -> Response:
    """Render `<option>` markup for the closest climate stations.

    Args:
        runid: Identifier for the active run.
        config: Configuration profile name.

    Returns:
        Response: HTML response containing option rows or an error payload.
    """
    wd = get_wd(runid)
    climate = Climate.getInstance(wd, ignore_lock=True)

    if climate.readonly:
        results: Sequence[StationOption] | None = climate.closest_stations
    else:
        try:
            results = climate.find_closest_stations()
        except Exception:
            return exception_factory('Error finding closest stations', runid=runid)

    if results is None:
        return Response('<!-- closest_stations is None -->', mimetype='text/html')

    options: List[str] = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]
        options.append('<option value="{id}" {selected}>'
                       '{desc} ({distance_to_query_location:0.1f} km | {years} years)</option>'
                       .format(**r))

    return Response('\n'.join(options), mimetype='text/html')


@climate_bp.route('/runs/<string:runid>/<config>/view/heuristic_stations/')
def view_heuristic_stations(runid: str, config: str) -> Response:
    """Render heuristic station `<option>` markup for the UI selectors.

    Args:
        runid: Identifier for the active run.
        config: Configuration profile name.

    Returns:
        Response: HTML response containing option rows or an error payload.
    """
    wd = get_wd(runid)
    climate = Climate.getInstance(wd, ignore_lock=True)

    if climate.readonly:
        results: Sequence[StationOption] | None = climate.heuristic_stations
    else:
        try:
            results = climate.find_heuristic_stations()
        except Exception:
            return exception_factory('Error finding heuristic stations', runid=runid)

    if results is None:
        return Response('<!-- heuristic_stations is None -->', mimetype='text/html')

#    return jsonify(results)

    options: List[str] = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]

        if r['distance_to_query_location'] is None:
            r['distance_to_query_location'] == -1

        options.append('<option value="{id}" {selected}>'
                       '{desc} ({rank_based_on_query_location} | '
                       '{distance_to_query_location:0.1f} km | {years} years)</option>'
                       .format(**r))

    return Response('\n'.join(options), mimetype='text/html')


@climate_bp.route('/runs/<string:runid>/<config>/view/par/')
def view_station_par(runid: str, config: str) -> Response:
    """Return the raw contents of the active station `.par` file.

    Args:
        runid: Identifier for the active run.
        config: Configuration profile name.

    Returns:
        Response: Plain-text payload containing the `.par` contents.
    """
    wd = get_wd(runid)
    climate = Climate.getInstance(wd, ignore_lock=True)
    contents = climate.climatestation_par_contents
    return Response(contents, content_type='text/plain;charset=utf-8')


@climate_bp.route('/runs/<string:runid>/<config>/view/eu_heuristic_stations/')
def view_eu_heuristic_stations(runid: str, config: str) -> Response:
    """Render EU heuristic station options.

    Args:
        runid: Identifier for the active run.
        config: Configuration profile name.

    Returns:
        Response: HTML option list understood by the UI select component.
    """
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        results: Sequence[StationOption] | None = climate.find_eu_heuristic_stations()
    except Exception:
        return exception_factory('Error finding heuristic stations', runid=runid)

    if results is None:
        return Response('<!-- heuristic_stations is None -->', mimetype='text/html')

    options: List[str] = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]
        options.append('<option value="{id}" {selected}>'
                       '{desc} ({rank_based_on_query_location} | {years} years)</option>'
                       .format(**r))

    return Response('\n'.join(options), mimetype='text/html')


@climate_bp.route('/runs/<string:runid>/<config>/view/au_heuristic_stations/')
def view_au_heuristic_stations(runid: str, config: str) -> Response:
    """Render AU heuristic station options.

    Args:
        runid: Identifier for the active run.
        config: Configuration profile name.

    Returns:
        Response: HTML option list understood by the UI select component.
    """
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        results: Sequence[StationOption] | None = climate.find_au_heuristic_stations()
    except Exception:
        return exception_factory('Error finding heuristic stations', runid=runid)

    if results is None:
        return Response('<!-- heuristic_stations is None -->', mimetype='text/html')

    options: List[str] = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]
        options.append('<option value="{id}" {selected}>'
                       '{desc} ({rank_based_on_query_location} | {years} years)</option>'
                       .format(**r))

    return Response('\n'.join(options), mimetype='text/html')


@climate_bp.route('/runs/<string:runid>/<config>/view/climate_monthlies')
@climate_bp.route('/runs/<string:runid>/<config>/view/climate_monthlies/')
def view_climate_monthlies(runid: str, config: str) -> Response:
    """Render the monthly climate summary for the active station.

    Args:
        runid: Identifier for the active run.
        config: Configuration profile name.

    Returns:
        Response: HTML response with station monthly metadata.

    Raises:
        AssertionError: If the stored metadata is not a `StationMeta` instance.
    """
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        station_meta: StationMeta | None = climate.climatestation_meta
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
def task_set_use_gridmet_wind_when_applicable(runid: str, config: str) -> Response:
    """Toggle the GridMET wind fallback for the climate controller.

    Args:
        runid: Identifier for the active run.
        config: Configuration profile name.

    Returns:
        Response: JSON success payload or error description.
    """

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
