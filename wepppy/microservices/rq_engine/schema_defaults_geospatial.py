"""Describe run-specific map defaults, availability, and DEM coverage."""
from __future__ import annotations

from typing import Any

from .schema_defaults_fields import (
    _available_climate_modes,
    _disturbed_sol_ver_options,
    _resolved_watershed_defaults,
    _supported_soils_modes,
)
from .schema_defaults_runtime import RuntimeState, _float_list


def _availability(available: bool, pending_reason: str) -> dict[str, str]:
    if available:
        return {"state": "available"}
    return {"state": "pending", "reason_code": pending_reason}


def _dem_coverage(runtime: RuntimeState, map_bounds: list[float] | None) -> dict[str, Any]:
    dem_coverage: dict[str, Any] = {
        "supported": True,
        "source": str(runtime.states.get("dem_coverage_source") or "unknown"),
        "has_dem": bool(runtime.states.get("has_dem", False)),
        "extent_bbox": map_bounds,
    }
    uploaded_dem_filename = runtime.states.get("uploaded_dem_filename")
    if isinstance(uploaded_dem_filename, str) and uploaded_dem_filename:
        dem_coverage["uploaded_dem_filename"] = uploaded_dem_filename
    delineation_backend = runtime.states.get("delineation_backend")
    if isinstance(delineation_backend, str) and delineation_backend:
        dem_coverage["delineation_backend"] = delineation_backend
    return dem_coverage


def _geospatial_payload(runtime: RuntimeState) -> dict[str, Any]:
    map_center = _float_list(runtime.states.get("map_center"), expected_len=2)
    map_bounds_raw = _float_list(runtime.states.get("map_bounds"), expected_len=4)
    map_bounds = map_bounds_raw
    map_bounds_is_run_resolved = map_bounds_raw is not None

    if map_bounds is None and map_center is not None:
        # Deterministic fallback extent for runs without a resolved DEM/map object yet.
        lon, lat = map_center
        map_bounds = [lon - 0.1, lat - 0.1, lon + 0.1, lat + 0.1]

    try:
        map_zoom = int(round(float(runtime.states.get("map_zoom"))))
    except (TypeError, ValueError):
        map_zoom = 11

    try:
        zoom_resolution = float(runtime.states.get("map_zoom_resolution_m_per_px"))
    except (TypeError, ValueError):
        zoom_resolution = 30.0

    csa_value = runtime.states.get("watershed_csa")
    mcl_value = runtime.states.get("watershed_mcl")
    stream_pruning_method_value = runtime.states.get("watershed_stream_pruning_method")
    watershed_defaults = _resolved_watershed_defaults(runtime)
    csa = watershed_defaults["csa"]
    mcl = watershed_defaults["mcl"]
    stream_pruning_method = watershed_defaults["stream_pruning_method"]

    climate_modes = _available_climate_modes(runtime)

    soils_modes_available = _supported_soils_modes(runtime)

    sol_ver_available = _disturbed_sol_ver_options(runtime)

    map_center_available = map_center is not None
    map_bounds_available = map_bounds_is_run_resolved
    csa_available = isinstance(csa_value, (int, float))
    mcl_available = isinstance(mcl_value, (int, float))
    stream_pruning_method_available = isinstance(stream_pruning_method_value, str)
    station_catalog_available = bool(runtime.states.get("has_dem", False) or map_bounds_is_run_resolved)

    field_availability = {
        "map_center": _availability(map_center_available, "awaiting_dem_upload"),
        "map_bounds": _availability(map_bounds_available, "awaiting_dem_upload"),
        "map_zoom": {"state": "available"},
        "csa": _availability(csa_available, "awaiting_watershed_defaults"),
        "mcl": _availability(mcl_available, "awaiting_watershed_defaults"),
        "stream_pruning_method": _availability(stream_pruning_method_available, "awaiting_watershed_defaults"),
        "station_catalog": _availability(station_catalog_available, "awaiting_dem_fetch"),
    }
    dem_coverage = _dem_coverage(runtime, map_bounds_raw)

    return {
        "runid": runtime.runid,
        "config": runtime.config,
        "region": runtime.region,
        "dem_coverage": dem_coverage,
        "recommended_defaults": {
            "map_center": map_center,
            "map_bounds": map_bounds,
            "map_zoom": map_zoom,
            "map_zoom_resolution_m_per_px": zoom_resolution,
            "csa": csa,
            "mcl": mcl,
            "stream_pruning_method": stream_pruning_method,
        },
        "dynamic_constraints": {
            "climate_mode": {
                "enum_available": climate_modes,
            },
            "soils_mode": {
                "enum_available": soils_modes_available,
            },
            "sol_ver": {
                "enum_available": sol_ver_available,
            },
        },
        "field_availability": field_availability,
        "computed_at": runtime.generated_at,
    }
