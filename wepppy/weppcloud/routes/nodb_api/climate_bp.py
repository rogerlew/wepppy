"""Routes for climate blueprint extracted from app.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, MutableMapping, Sequence

from flask import Response

from wepppy.weppcloud.utils.helpers import exception_factory, get_batch_root_dir, handle_with_exception_factory

from .._common import *  # noqa: F401,F403

from wepppy.climates.cligen import StationMeta
from wepppy.nodb.core.climate import Climate, ClimateStationMode
from wepppy.weppcloud.utils.cap_guard import requires_cap

StationOption = MutableMapping[str, Any]


climate_bp = Blueprint('climate', __name__)

def _load_precip_frequency(cli_dir: str) -> dict[str, Any] | None:
    path = Path(cli_dir) / "wepp_cli_pds_mean_metric.csv"
    if not path.exists():
        return None

    lines = path.read_text().splitlines()
    header_idx = next(
        (idx for idx, line in enumerate(lines) if line.lower().startswith("by metric for ari")),
        None,
    )
    if header_idx is None:
        return None

    header_line = lines[header_idx]
    recurrence: list[int] = []
    for token in header_line.split(",")[1:]:
        value = token.strip()
        if not value:
            continue
        try:
            recurrence.append(int(float(value)))
        except ValueError:
            continue

    if not recurrence:
        return None

    rows: list[dict[str, Any]] = []
    for line in lines[header_idx + 1:]:
        if not line.strip():
            break
        lower_line = line.lower()
        if lower_line.startswith("date/time") or lower_line.startswith("pyruntime"):
            break
        if ":" not in line:
            continue
        label_part, values_part = line.split(":", 1)
        label = label_part.strip()
        unit = ""
        if "(" in label and label.endswith(")"):
            label_base, unit_part = label.rsplit("(", 1)
            label = label_base.strip()
            unit = unit_part.rstrip(")").strip()

        parsed_values: list[float | None] = []
        for raw_value in values_part.split(","):
            value = raw_value.strip()
            if not value:
                continue
            try:
                parsed_values.append(float(value))
            except ValueError:
                parsed_values.append(None)

        if len(parsed_values) < len(recurrence):
            parsed_values.extend([None] * (len(recurrence) - len(parsed_values)))
        elif len(parsed_values) > len(recurrence):
            parsed_values = parsed_values[:len(recurrence)]

        rows.append(
            {
                "label": label,
                "unit": unit,
                "unitize": unit in ("mm", "mm/hour"),
                "values": parsed_values,
            }
        )

    if not rows:
        return None

    return {"recurrence": recurrence, "rows": rows}

def _load_atlas14_intensity(cli_dir: str) -> dict[str, Any] | None:
    path = Path(cli_dir) / "atlas14_intensity_pds_mean_metric.csv"
    if not path.exists():
        return None

    lines = path.read_text().splitlines()
    header_idx = next(
        (idx for idx, line in enumerate(lines) if line.lower().startswith("by duration for ari")),
        None,
    )
    if header_idx is None:
        return None

    header_line = lines[header_idx]
    recurrence: list[int] = []
    for token in header_line.split(",")[1:]:
        value = token.strip()
        if not value:
            continue
        try:
            recurrence.append(int(float(value)))
        except ValueError:
            continue

    if not recurrence:
        return None

    rows: list[dict[str, Any]] = []
    for line in lines[header_idx + 1:]:
        if not line.strip():
            break
        lower_line = line.lower()
        if lower_line.startswith("date/time") or lower_line.startswith("pyruntime"):
            break
        if ":" not in line:
            continue
        label_part, values_part = line.split(":", 1)
        label = label_part.strip()

        parsed_values: list[float | None] = []
        for raw_value in values_part.split(","):
            value = raw_value.strip()
            if not value:
                continue
            try:
                parsed_values.append(float(value))
            except ValueError:
                parsed_values.append(None)

        if len(parsed_values) < len(recurrence):
            parsed_values.extend([None] * (len(recurrence) - len(parsed_values)))
        elif len(parsed_values) > len(recurrence):
            parsed_values = parsed_values[:len(recurrence)]

        rows.append(
            {
                "label": label,
                "unit": "mm/hour",
                "unitize": True,
                "values": parsed_values,
            }
        )

    if not rows:
        return None

    return {"recurrence": recurrence, "rows": rows}


@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_climatestation_mode/', methods=['POST'])
def set_climatestation_mode(runid: str, config: str) -> Response:
    """Persist the requested climate station mode for the active run.

    Args:
        runid: Identifier for the working directory.
        config: Name of the configuration profile (unused but required by the route schema).

    Returns:
        Response: JSON payload indicating success or detailing the failure reason.
    """
    payload = parse_request_payload(request, boolean_fields={"state"})
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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:189", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:216", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Building setting climate station mode', runid=runid)

    return success_factory()


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
    """Return the cataloged climate datasets for the active run."""
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)
    try:
        payload = climate.catalog_datasets_payload()
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:262", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error loading climate catalog', runid=runid)
    return jsonify(payload)


@climate_bp.route('/runs/<string:runid>/<config>/report/climate/')
@requires_cap(gate_reason="Complete verification to view climate reports.")
@handle_with_exception_factory
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
    precip_frequency = _load_precip_frequency(climate.cli_dir)
    atlas14_frequency = _load_atlas14_intensity(climate.cli_dir)
    return render_template('reports/climate.htm', runid=runid, config=config,
                           station_meta=climate.climatestation_meta,
                           climate=climate,
                           precip_frequency=precip_frequency,
                           atlas14_frequency=atlas14_frequency)


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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:327", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:356", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
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
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:381", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
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
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:416", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:472", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:504", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:540", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:567", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        climate = Climate.getInstance(wd)
        climate.use_gridmet_wind_when_applicable = state

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:578", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error setting state', runid=runid)

    return success_factory()


@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_adjust_mx_pt5', methods=['POST'])
@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_adjust_mx_pt5/', methods=['POST'])
def task_set_adjust_mx_pt5(runid: str, config: str) -> Response:
    """Toggle MX .5 P scaling for the CLIGEN localization pipeline.

    Args:
        runid: Identifier for the active run.
        config: Configuration profile name.

    Returns:
        Response: JSON success payload or error description.
    """
    payload = parse_request_payload(request)
    state = payload.get('state', None)
    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        climate = Climate.getInstance(wd)
        climate.adjust_mx_pt5 = state
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:605", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error setting state', runid=runid)

    return success_factory()
