"""Routes for climate blueprint extracted from app.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, MutableMapping, Sequence
import uuid

from flask import Response

from wepppy.weppcloud.utils.helpers import (
    authorize_and_handle_with_exception_factory,
    exception_factory,
    get_batch_root_dir,
    handle_with_exception_factory,
)

from .._common import *  # noqa: F401,F403

from wepppy.climates.cligen import StationMeta
from wepppy.nodb.core.climate import (
    Climate,
    ClimateMode,
    ClimateStationMode,
    _assert_supported_climate_mode,
)
from wepppy.nodb.locales.climate_catalog import (
    CLIMATE_SPATIAL_METHOD_RUNTIME,
    CLIMATE_STATION_METHOD_RUNTIME,
    get_climate_dataset,
)
from wepppy.nodb.project_config_capabilities import (
    BuilderRegistryUnavailableError,
    CapabilityAuthorityInvalidError,
    LocaleAuthorityInvalidError,
    capability_default,
    climate_spatial_capability_modes,
    climate_station_capability_modes,
    resolve_run_capability_authority,
)
from wepppy.weppcloud.utils.cap_guard import requires_cap

StationOption = MutableMapping[str, Any]


climate_bp = Blueprint('climate', __name__)


class _ClimateSelectionRejected(ValueError):
    """Carry a stable client error from selection validation."""

    def __init__(self, message: str, *, code: str, details: str) -> None:
        super().__init__(details)
        self.message = message
        self.code = code
        self.details = details


def _run_authority_error(exc: Exception) -> Response:
    if isinstance(exc, LocaleAuthorityInvalidError):
        return error_factory(
            "Run locale authority is invalid.",
            status_code=409,
            code="locale_authority_invalid",
            details=str(exc),
            error_id=uuid.uuid4().hex,
        )
    if isinstance(exc, CapabilityAuthorityInvalidError):
        return error_factory(
            "Project capability authority is invalid.",
            status_code=409,
            code="capability_authority_invalid",
            details=str(exc),
            error_id=uuid.uuid4().hex,
        )
    response = error_factory(
        "Builder registry is unavailable.",
        status_code=503,
        code="builder_registry_error",
        details=str(exc),
        error_id=uuid.uuid4().hex,
    )
    response.headers["Retry-After"] = "5"
    return response


def _climate_selection_error(exc: _ClimateSelectionRejected) -> Response:
    return error_factory(
        exc.message,
        status_code=400,
        code=exc.code,
        details=exc.details,
    )


def _resolve_valid_climate_selection(
    climate: Climate,
    *,
    catalog_id: str | None,
    mode: int | None,
) -> Any | None:
    """Resolve one capability-authorized catalog/mode pair without mutation."""

    authority = resolve_run_capability_authority(climate).graph
    if authority is not None and mode is not None and not catalog_id:
        raise _ClimateSelectionRejected(
            'Climate catalog id is required for this project.',
            code='missing_capability_id',
            details='catalog_id is required when selecting a schema-v2 climate dataset.',
        )
    if authority is not None and catalog_id and mode is None:
        raise _ClimateSelectionRejected(
            'Climate mode is required for this project.',
            code='missing_capability_id',
            details='mode is required when selecting a climate catalog id.',
        )

    dataset = None
    if catalog_id:
        dataset = climate._resolve_catalog_dataset(str(catalog_id), include_hidden=True)
        if dataset is None:
            raise _ClimateSelectionRejected(
                'Climate dataset is not supported by this project.',
                code='unsupported_capability',
                details=f'Unsupported climate catalog id: {catalog_id}',
            )
        allowed_dataset_ids = (
            set(authority.climate_datasets)
            if authority is not None and hasattr(authority, 'climate_datasets')
            else None
        )
        if (
            allowed_dataset_ids is not None
            and str(catalog_id) not in allowed_dataset_ids
            and str(catalog_id) != str(climate.catalog_id or '')
        ):
            raise _ClimateSelectionRejected(
                'Climate dataset is not supported by this project.',
                code='unsupported_capability',
                details=f'Unsupported capabilities.climate_datasets value: {catalog_id}',
            )
        if mode is not None and int(dataset.climate_mode) != mode:
            raise _ClimateSelectionRejected(
                'Climate mode does not match the selected dataset.',
                code='capability_mismatch',
                details=(
                    f'Climate catalog {catalog_id} uses mode {int(dataset.climate_mode)}, '
                    f'not submitted mode {mode}.'
                ),
            )
    return dataset


def _apply_climate_selection_pair(
    climate: Climate,
    *,
    catalog_id: str,
    mode: int,
) -> None:
    """Revalidate and persist a catalog/mode pair in one NoDb transaction."""

    with climate.locked():
        missing = object()
        snapshot_mode = getattr(climate, '_climate_mode', missing)
        snapshot_catalog_id = getattr(climate, '_catalog_id', missing)
        dataset = _resolve_valid_climate_selection(
            climate,
            catalog_id=catalog_id,
            mode=mode,
        )
        if dataset is None:
            raise RuntimeError('Climate dataset disappeared during locked validation.')
        mode_member = ClimateMode(mode)
        _assert_supported_climate_mode(mode_member)
        climate._validate_station_catalog_constraints(climate_mode=mode_member)
        try:
            climate._climate_mode = mode_member
            climate._catalog_id = dataset.catalog_id
        except (AttributeError, RuntimeError, TypeError, ValueError):
            if snapshot_mode is missing:
                if hasattr(climate, '_climate_mode'):
                    delattr(climate, '_climate_mode')
            else:
                climate._climate_mode = snapshot_mode
            if snapshot_catalog_id is missing:
                if hasattr(climate, '_catalog_id'):
                    delattr(climate, '_catalog_id')
            else:
                climate._catalog_id = snapshot_catalog_id
            raise


def _resolved_climate_dataset_id(climate: Climate) -> str | None:
    current = str(climate.catalog_id or "").strip()
    if current:
        return current
    authority = resolve_run_capability_authority(climate).graph
    if authority is not None:
        return authority.defaults["climate_dataset"]
    return capability_default(climate, "climate_dataset")


def _with_exact_current_climate_dataset(
    climate: Climate,
    payload: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    current_catalog_id = str(climate.catalog_id or "").strip()
    if not current_catalog_id:
        return payload
    current_payload = next(
        (
            dict(item)
            for item in payload
            if item.get("catalog_id") == current_catalog_id
        ),
        None,
    )
    current_authorized = current_payload is not None
    if current_payload is None:
        current = get_climate_dataset(current_catalog_id)
        if current is not None:
            current_payload = current.to_mapping()
    if current_payload is None:
        return payload
    station_mode = int(climate.climatestation_mode)
    spatial_mode = int(climate.climate_spatialmode)
    station_method = next(
        (
            key for key, value in CLIMATE_STATION_METHOD_RUNTIME.items()
            if value == station_mode
        ),
        None,
    )
    spatial_method = next(
        (
            key for key, value in CLIMATE_SPATIAL_METHOD_RUNTIME.items()
            if value == spatial_mode
        ),
        None,
    )
    authorized_station_modes = list(current_payload.get("station_modes") or [])
    authorized_spatial_modes = list(current_payload.get("spatial_modes") or [])
    current_payload.update({
        "current_station_mode": station_mode,
        "current_station_mode_authorized": (
            current_authorized and station_mode in authorized_station_modes
        ),
        "disabled_station_modes": (
            [station_mode]
            if not current_authorized or station_mode not in authorized_station_modes
            else []
        ),
        "current_spatial_mode": spatial_mode,
        "current_spatial_mode_authorized": (
            current_authorized and spatial_mode in authorized_spatial_modes
        ),
        "disabled_spatial_modes": (
            [spatial_mode]
            if not current_authorized or spatial_mode not in authorized_spatial_modes
            else []
        ),
    })
    if not current_authorized:
        current_payload.update({
            "station_modes": [station_mode],
            "default_station_mode": station_mode,
            "spatial_modes": [spatial_mode],
            "default_spatial_mode": spatial_mode,
            "current_selection_disabled": True,
        })
        if station_method is not None:
            current_payload.update({
                "station_method_ids": [station_method],
                "default_station_method_id": station_method,
            })
        if spatial_method is not None:
            current_payload.update({
                "spatial_method_ids": [spatial_method],
                "default_spatial_method_id": spatial_method,
            })
        return [*payload, current_payload]
    if station_mode not in authorized_station_modes:
        current_payload["station_modes"] = [*authorized_station_modes, station_mode]
    if spatial_mode not in authorized_spatial_modes:
        current_payload["spatial_modes"] = [*authorized_spatial_modes, spatial_mode]
    return [
        current_payload if item.get("catalog_id") == current_catalog_id else item
        for item in payload
    ]

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
@authorize_and_handle_with_exception_factory
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
        dataset_id = _resolved_climate_dataset_id(climate)
        allowed_modes = (
            climate_station_capability_modes(climate, dataset_id)
            if dataset_id is not None
            else None
        )
    except (LocaleAuthorityInvalidError, BuilderRegistryUnavailableError, CapabilityAuthorityInvalidError) as exc:
        return _run_authority_error(exc)
    current_mode = int(climate.climatestation_mode)
    if (
        allowed_modes is not None
        and mode not in allowed_modes
        and mode != current_mode
    ):
        return error_factory(
            'Climate station method is not supported by this project.',
            status_code=400,
            code='unsupported_capability',
            details=f'Unsupported climate station method: {mode}',
        )

    try:
        climate.climatestation_mode = ClimateStationMode(int(mode))
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:189", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Building setting climate station mode', runid=runid)

    return success_factory()


@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_climatestation/', methods=['POST'])
@authorize_and_handle_with_exception_factory
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
@authorize_and_handle_with_exception_factory
def query_climate_catalog(runid: str, config: str) -> Response:
    """Return the cataloged climate datasets for the active run."""
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)
    try:
        payload = _with_exact_current_climate_dataset(
            climate, climate.catalog_datasets_payload()
        )
    except (
        LocaleAuthorityInvalidError,
        BuilderRegistryUnavailableError,
        CapabilityAuthorityInvalidError,
    ) as exc:
        return _run_authority_error(exc)
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
@authorize_and_handle_with_exception_factory
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
    catalog_id_value = payload.get('catalog_id')
    catalog_alias_value = payload.get('climate_catalog_id')
    if (
        catalog_id_value not in (None, '')
        and catalog_alias_value not in (None, '')
        and str(catalog_id_value) != str(catalog_alias_value)
    ):
        return error_factory(
            'Climate catalog aliases must identify the same dataset.',
            status_code=400,
            code='capability_mismatch',
            details='catalog_id and climate_catalog_id disagree.',
        )
    catalog_id = (
        catalog_id_value
        if catalog_id_value not in (None, '')
        else catalog_alias_value
    )

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
        dataset = _resolve_valid_climate_selection(
            climate,
            catalog_id=str(catalog_id) if catalog_id else None,
            mode=mode,
        )
    except (LocaleAuthorityInvalidError, BuilderRegistryUnavailableError, CapabilityAuthorityInvalidError) as exc:
        return _run_authority_error(exc)
    except _ClimateSelectionRejected as exc:
        return _climate_selection_error(exc)

    try:
        if mode is not None and dataset is not None:
            _apply_climate_selection_pair(
                climate,
                catalog_id=dataset.catalog_id,
                mode=mode,
            )
        elif mode is not None:
            climate.climate_mode = mode
        elif dataset is not None:
            climate.catalog_id = dataset.catalog_id
    except (LocaleAuthorityInvalidError, BuilderRegistryUnavailableError, CapabilityAuthorityInvalidError) as exc:
        return _run_authority_error(exc)
    except _ClimateSelectionRejected as exc:
        return _climate_selection_error(exc)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:327", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Building setting climate mode', runid=runid)

    return success_factory()


@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_climate_spatialmode/', methods=['POST'])
@authorize_and_handle_with_exception_factory
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
        dataset_id = _resolved_climate_dataset_id(climate)
        allowed_modes = (
            climate_spatial_capability_modes(climate, dataset_id)
            if dataset_id is not None
            else None
        )
    except (LocaleAuthorityInvalidError, BuilderRegistryUnavailableError, CapabilityAuthorityInvalidError) as exc:
        return _run_authority_error(exc)
    current_spatialmode = int(climate.climate_spatialmode)
    if (
        allowed_modes is not None
        and spatialmode not in allowed_modes
        and spatialmode != current_spatialmode
    ):
        return error_factory(
            'Climate spatial method is not supported by this project.',
            status_code=400,
            code='unsupported_capability',
            details=f'Unsupported climate spatial method: {spatialmode}',
        )

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
@authorize_and_handle_with_exception_factory
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
@authorize_and_handle_with_exception_factory
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


@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_silent_pass_observed_quality_guard', methods=['POST'])
@climate_bp.route('/runs/<string:runid>/<config>/tasks/set_silent_pass_observed_quality_guard/', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_set_silent_pass_observed_quality_guard(runid: str, config: str) -> Response:
    """Toggle silent-pass behavior for observed CLIGEN quality-guard failures.

    Args:
        runid: Identifier for the active run.
        config: Configuration profile name.

    Returns:
        Response: JSON success payload or error description.
    """
    payload = parse_request_payload(request, boolean_fields={"state"})
    state = payload.get('state', None)
    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        climate = Climate.getInstance(wd)
        climate.silent_pass_observed_quality_guard = state
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/climate_bp.py:set_silent_pass_observed_quality_guard", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error setting state', runid=runid)

    return success_factory()
