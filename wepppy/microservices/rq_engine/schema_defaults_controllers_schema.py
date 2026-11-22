"""Build the controller parameter schemas served by run discovery."""

from __future__ import annotations

import copy
from typing import Any

from wepppy.nodb.locales.capability_graph import CapabilityGraph
from wepppy.nodb.locales.climate_catalog import (
    CLIMATE_SPATIAL_METHOD_RUNTIME,
    CLIMATE_STATION_METHOD_RUNTIME,
)

from .schema_defaults_descriptors import _predicate
from .schema_defaults_fields import (
    _CLIMATE_SPATIAL_STABLE_BY_RUNTIME,
    _CLIMATE_STATION_STABLE_BY_RUNTIME,
    _available_climate_modes,
    _available_landuse_method_ids,
    _disturbed_sol_ver_options,
    _effective_model_binaries,
    _effective_model_tuples,
    _landuse_dataset_field,
    _landuse_method_field,
    _model_tuple_binaries_for_runtime,
    _soil_mode_field,
    _stable_runtime_state,
)
from .schema_defaults_runtime import RuntimeState


def _climate_catalog_fields(
    runtime: RuntimeState,
    graph: CapabilityGraph,
    current_catalog_id: str | None,
) -> dict[str, Any]:
    resolved_at = runtime.generated_at
    selected_catalog_id = current_catalog_id or graph.defaults["climate_dataset"]
    climate_catalog_values = list(graph.climate_datasets)
    if (
        current_catalog_id
        and current_catalog_id not in climate_catalog_values
    ):
        climate_catalog_values.append(current_catalog_id)
    current_station_method = _stable_runtime_state(
        runtime, "climate_station_mode_code", _CLIMATE_STATION_STABLE_BY_RUNTIME
    )
    current_spatial_method = _stable_runtime_state(
        runtime, "climate_spatial_mode_code", _CLIMATE_SPATIAL_STABLE_BY_RUNTIME
    )
    allowed_station_methods = graph.climate_station_methods_by_dataset.get(
        selected_catalog_id, ()
    )
    allowed_spatial_methods = graph.climate_spatial_methods_by_dataset.get(
        selected_catalog_id, ()
    )
    return {
        "climate_catalog_id": {
            "type": "string",
            "required": True,
            "constraint_mode": "run_resolved",
            "constraint_source": "project_capability_graph",
            "resolved_at": resolved_at,
            "enum": climate_catalog_values,
            "enum_available": list(graph.climate_datasets),
            "current_value": current_catalog_id,
            "current_value_authorized": current_catalog_id in graph.climate_datasets,
            "disabled_values": (
                [current_catalog_id]
                if current_catalog_id and current_catalog_id not in graph.climate_datasets
                else []
            ),
        },
        "climate_station_method": {
            "type": "string",
            "required": True,
            "constraint_mode": "run_resolved",
            "constraint_source": "project_capability_graph",
            "resolved_at": resolved_at,
            "enum": list(graph.climate_station_methods),
            "enum_available": list(allowed_station_methods),
            "current_value": current_station_method,
            "current_value_authorized": current_station_method in allowed_station_methods,
            "disabled_values": (
                [current_station_method]
                if current_station_method
                and current_station_method not in allowed_station_methods
                else []
            ),
            "allowed_by_climate_catalog_id": {
                key: list(value)
                for key, value in graph.climate_station_methods_by_dataset.items()
            },
            "defaults_by_climate_catalog_id": dict(graph.climate_station_defaults),
            "runtime_mapping": dict(CLIMATE_STATION_METHOD_RUNTIME),
        },
        "climate_spatial_method": {
            "type": "string",
            "required": True,
            "constraint_mode": "run_resolved",
            "constraint_source": "project_capability_graph",
            "resolved_at": resolved_at,
            "enum": list(graph.climate_spatial_methods),
            "enum_available": list(allowed_spatial_methods),
            "current_value": current_spatial_method,
            "current_value_authorized": current_spatial_method in allowed_spatial_methods,
            "disabled_values": (
                [current_spatial_method]
                if current_spatial_method
                and current_spatial_method not in allowed_spatial_methods
                else []
            ),
            "allowed_by_climate_catalog_id": {
                key: list(value)
                for key, value in graph.climate_spatial_methods_by_dataset.items()
            },
            "defaults_by_climate_catalog_id": dict(graph.climate_spatial_defaults),
            "runtime_mapping": dict(CLIMATE_SPATIAL_METHOD_RUNTIME),
        },
    }


def _climate_schema(runtime: RuntimeState) -> dict[str, Any]:
    resolved_at = runtime.generated_at
    available_modes = _available_climate_modes(runtime)
    graph = runtime.capability_graph
    current_mode = runtime.states.get("climate_mode_code")
    current_catalog_id = str(runtime.states.get("climate_catalog_id") or "").strip() or None

    fields: dict[str, Any] = {
        "climate_mode": {
            "type": "integer",
            "required": True,
            "constraint_mode": "run_resolved",
            "constraint_source": "controller_state",
            "resolved_at": resolved_at,
            "enum": (
                available_modes
                if graph is not None or runtime.v1_capabilities is not None
                else [0, 2, 3, 5, 6, 11]
            ),
            "enum_available": available_modes,
            "enum_labels": {
                "0": "Synthetic CLIGEN",
                "2": "Observed station",
                "3": "Future MACA CMIP5",
                "17": "Future EDDE v2",
                "5": "Stochastic PRISM",
                "6": "Observed database",
                "9": "Observed DAYMET",
                "11": "Observed GRIDMET",
            },
            **(
                {
                    "current_value": current_mode,
                    "current_value_authorized": current_mode in available_modes,
                    "disabled_values": (
                        [current_mode] if current_mode not in available_modes else []
                    ),
                }
                if graph is not None and current_mode is not None
                else {}
            ),
        },
    }
    if graph is not None:
        fields.update(_climate_catalog_fields(runtime, graph, current_catalog_id))

    return {
        "schema_version": 1,
        "fields": {
            **fields,
            "climatestation": {
                "type": "string",
                "required": False,
                "constraint_mode": "run_resolved",
                "constraint_source": "controller_state",
                "resolved_at": resolved_at,
                "available_if": _predicate("climate_mode", "in", [2, 6]),
                "required_if": _predicate("climate_mode", "in", [2, 6]),
            },
            "observed_start_year": {
                "type": "integer",
                "minimum": 1900,
                "maximum": 2100,
                "constraint_mode": "static",
                "required_if": _predicate("climate_mode", "in", [2, 9, 11, 16]),
            },
            "observed_end_year": {
                "type": "integer",
                "minimum": 1900,
                "maximum": 2100,
                "constraint_mode": "static",
                "required_if": _predicate("climate_mode", "in", [2, 9, 11, 16]),
            },
            "edde_projection": {
                "type": "string",
                "enum": ["WRF-MPI/SSP2-4.5", "WRF-MPI/SSP3-7.0", "WRF-Nor/SSP2-4.5"],
                "required_if": _predicate("climate_mode", "eq", 17),
                "description": "EDDE full years: 2025–2099 MPI; 2025–2079 Nor.",
            },
            "future_start_year": {
                "type": "integer",
                "minimum": 2006,
                "maximum": 2099,
                "constraint_mode": "static",
                "required_if": _predicate("climate_mode", "in", [3, 17]),
            },
            "future_end_year": {
                "type": "integer",
                "minimum": 2006,
                "maximum": 2099,
                "constraint_mode": "static",
                "required_if": _predicate("climate_mode", "in", [3, 17]),
            },
            "cligen_seed": {
                "type": "integer",
                "minimum": 0,
                "maximum": 99999,
                "required": False,
                "constraint_mode": "static",
            },
        },
    }


def _landuse_schema(runtime: RuntimeState, disturbed_enabled: bool) -> dict[str, Any]:
    resolved_at = runtime.generated_at
    if runtime.capability_graph is not None or (
        runtime.v1_capabilities and "landuse_methods" in runtime.v1_capabilities
    ):
        modes = _available_landuse_method_ids(runtime)
    else:
        modes = ["nlcd", "custom"]
        if disturbed_enabled:
            modes.append("disturbed")

    if runtime.capability_graph is not None:
        landuse_mode_field = _landuse_method_field(runtime)
    else:
        landuse_mode_field = {
            "type": "string",
            "constraint_mode": "run_resolved",
            "constraint_source": "controller_state",
            "resolved_at": resolved_at,
            "enum": sorted(modes),
            "enum_available": sorted(modes),
        }
    return {
        "schema_version": 1,
        "fields": {
            "landuse_db": {
                **_landuse_dataset_field(runtime),
                "required": True,
            },
            "landuse_mode": {
                **landuse_mode_field,
                "required": True,
            },
            "cover_transform_uploaded": {
                "type": "boolean",
                "required": False,
                "constraint_mode": "run_resolved",
                "constraint_source": "controller_state",
                "resolved_at": resolved_at,
                "available_if": _predicate("context.active_mods", "contains", "disturbed"),
            },
        },
    }


def _soils_schema(
    runtime: RuntimeState,
    disturbed_enabled: bool,
    sol_ver_available: list[float],
) -> dict[str, Any]:
    resolved_at = runtime.generated_at
    sol_ver_labels = {
        "2006.0": "Legacy disturbed defaults",
        "2018.0": "Updated disturbed defaults",
        "9002.0": "Disturbed9002 calibration defaults",
    }
    soil_mode_field = _soil_mode_field(runtime)
    return {
        "schema_version": 1,
        "fields": {
            "soil_mode": {
                **copy.deepcopy(soil_mode_field),
                "required": True,
            },
            "soils_mode": {
                **copy.deepcopy(soil_mode_field),
                "required": True,
                "alias_of": "soil_mode",
            },
            "sol_ver": {
                "type": "number",
                "required": False,
                "constraint_mode": "run_resolved",
                "constraint_source": "controller_state",
                "resolved_at": resolved_at,
                "enum_available": sol_ver_available if disturbed_enabled else [],
                "enum_labels": {
                    key: value
                    for key, value in sol_ver_labels.items()
                    if float(key) in sol_ver_available
                },
                "available_if": _predicate("context.active_mods", "contains", "disturbed"),
                "required_if": _predicate("context.active_mods", "contains", "disturbed"),
            },
        },
    }


def _watershed_schema(runtime: RuntimeState) -> dict[str, Any]:
    resolved_at = runtime.generated_at
    return {
        "schema_version": 1,
        "fields": {
            "csa": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5000,
                "required": False,
                "constraint_mode": "run_resolved",
                "constraint_source": "geospatial_metadata",
                "resolved_at": resolved_at,
            },
            "mcl": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5000,
                "required": False,
                "constraint_mode": "run_resolved",
                "constraint_source": "geospatial_metadata",
                "resolved_at": resolved_at,
            },
            "expected_run_state_revision": {
                "type": "string",
                "required": False,
                "constraint_mode": "static",
            },
        },
    }


def _wepp_schema(runtime: RuntimeState) -> dict[str, Any]:
    resolved_at = runtime.generated_at
    fields = {
        "clip_soils": {
            "type": "boolean",
            "required": False,
            "constraint_mode": "static",
        },
        "clip_soils_depth": {
            "type": "number",
            "minimum": 0.0,
            "required": False,
            "constraint_mode": "static",
            "available_if": _predicate("clip_soils", "eq", True),
            "required_if": _predicate("clip_soils", "eq", True),
        },
        "initial_sat": {
            "type": "number",
            "required": False,
            "constraint_mode": "static",
        },
    }
    graph = runtime.model_capability_graph
    if graph is not None or runtime.wepp_binary_options is not None:
        allowed_binaries = _model_tuple_binaries_for_runtime(runtime)
        current_binary = str(runtime.states.get("wepp_binary") or "").strip() or None
        fields["wepp_bin"] = {
            "type": "string",
            "required": False,
            "constraint_mode": "run_resolved",
            "constraint_source": "installed_release_capabilities" if runtime.wepp_binary_options is not None else "project_capability_graph",
            "resolved_at": resolved_at,
            "enum": allowed_binaries,
            "enum_available": allowed_binaries,
            "current_value": current_binary,
            "current_value_authorized": current_binary in allowed_binaries,
            "disabled_values": (
                [current_binary]
                if current_binary and current_binary not in allowed_binaries
                else []
            ),
        }
    elif runtime.v1_capabilities and "wepp_binaries" in runtime.v1_capabilities:
        allowed_binaries = list(runtime.v1_capabilities["wepp_binaries"])
        fields["wepp_bin"] = {
            "type": "string",
            "required": False,
            "constraint_mode": "run_resolved",
            "constraint_source": "project_capability_axis_v1",
            "resolved_at": resolved_at,
            "enum": allowed_binaries,
            "enum_available": allowed_binaries,
        }
    result = {
        "schema_version": 1,
        "fields": fields,
    }
    if graph is not None:
        result["model_authority"] = {
            "delineation_backends": list(graph.delineation_backends),
            "watershed_representations": list(graph.watershed_representations),
            "wepp_binaries": _effective_model_binaries(runtime, graph),
            "allowed_model_tuples": _effective_model_tuples(runtime, graph),
            "executable_revision": runtime.wepp_binary_revision,
        }
    return result


def _disturbed_schema(runtime: RuntimeState, sol_ver_available: list[float]) -> dict[str, Any]:
    resolved_at = runtime.generated_at
    return {
        "schema_version": 1,
        "fields": {
            "sol_ver": {
                "type": "number",
                "required": True,
                "constraint_mode": "run_resolved",
                "constraint_source": "controller_state",
                "resolved_at": resolved_at,
                "enum_available": sol_ver_available,
            },
            "sbs_uploaded": {
                "type": "boolean",
                "required": False,
                "constraint_mode": "run_resolved",
                "constraint_source": "controller_state",
                "resolved_at": resolved_at,
            },
        },
    }


def _controller_schema(controller: str, runtime: RuntimeState) -> dict[str, Any]:
    disturbed_enabled = bool(runtime.states.get("disturbed_enabled", False))
    sol_ver_available = _disturbed_sol_ver_options(runtime)
    if controller == "climate":
        return _climate_schema(runtime)
    if controller == "landuse":
        return _landuse_schema(runtime, disturbed_enabled)
    if controller == "soils":
        return _soils_schema(runtime, disturbed_enabled, sol_ver_available)
    if controller == "watershed":
        return _watershed_schema(runtime)
    if controller == "wepp":
        return _wepp_schema(runtime)
    if controller == "disturbed":
        return _disturbed_schema(runtime, sol_ver_available)
    raise KeyError(controller)
