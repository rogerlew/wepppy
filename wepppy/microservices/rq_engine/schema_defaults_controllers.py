"""Run controller discovery, parameter defaults, templates, and editing hints."""

from __future__ import annotations

import copy
from typing import Any

from wepppy.nodb.locales.climate_catalog import (
    CLIMATE_SPATIAL_METHOD_RUNTIME,
    CLIMATE_STATION_METHOD_RUNTIME,
)

from .schema_defaults_fields import (
    _CLIMATE_SPATIAL_STABLE_BY_RUNTIME,
    _CLIMATE_STATION_STABLE_BY_RUNTIME,
    _LANDUSE_STABLE_BY_RUNTIME,
    _SOILS_STABLE_BY_RUNTIME,
    _available_climate_modes,
    _climate_mode_for_dataset,
    _default_disturbed_sol_ver,
    _domain_capability_graph,
    _resolved_watershed_defaults,
    _selected_landuse_dataset,
    _stable_runtime_state,
)
from .schema_defaults_runtime import RuntimeState


def _controller_names(runtime: RuntimeState) -> tuple[str, ...]:
    names = ["watershed", "climate", "landuse", "soils", "wepp"]
    if bool(runtime.states.get("disturbed_enabled", False)):
        names.append("disturbed")
    return tuple(sorted(names))


def _controller_catalog(runtime: RuntimeState) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for name in _controller_names(runtime):
        base_url = f"/api/runs/{runtime.runid}/{runtime.config}/controllers/{name}"
        catalog[name] = {
            "name": name,
            "enabled": True,
            "schema_url": f"{base_url}/schema",
            "hints_url": f"{base_url}/hints",
            "templates_url": f"{base_url}/templates",
            "capabilities": {
                "schema": True,
                "hints": True,
                "templates": True,
            },
        }
    return catalog


def _resolve_controller(controller: str, runtime: RuntimeState) -> str | None:
    normalized = str(controller or "").strip().lower()
    if normalized in _controller_catalog(runtime):
        return normalized
    return None


def _climate_defaults(runtime: RuntimeState, disturbed_enabled: bool) -> dict[str, Any]:
    climate_mode = runtime.states.get("climate_mode_code")
    default_climate_mode = 11 if disturbed_enabled else 0
    available_modes = _available_climate_modes(runtime)
    if runtime.capability_graph is not None:
        graph = runtime.capability_graph
        current_catalog_id = str(runtime.states.get("climate_catalog_id") or "").strip()
        selected_catalog_id = current_catalog_id or graph.defaults["climate_dataset"]
        graph_default = _climate_mode_for_dataset(selected_catalog_id)
        resolved_mode = graph_default if graph_default is not None else climate_mode
        if resolved_mode is None:
            resolved_mode = default_climate_mode
    else:
        resolved_mode = climate_mode if climate_mode in available_modes else default_climate_mode
    defaults: dict[str, Any] = {
        "climate_mode": resolved_mode,
        "cligen_seed": runtime.states.get("cligen_seed"),
    }
    if runtime.capability_graph is not None:
        graph = runtime.capability_graph
        defaults["climate_catalog_id"] = selected_catalog_id
        station_method = _stable_runtime_state(
            runtime, "climate_station_mode_code", _CLIMATE_STATION_STABLE_BY_RUNTIME
        )
        spatial_method = _stable_runtime_state(
            runtime, "climate_spatial_mode_code", _CLIMATE_SPATIAL_STABLE_BY_RUNTIME
        )
        if selected_catalog_id in graph.climate_datasets:
            station_method = station_method or graph.climate_station_defaults[selected_catalog_id]
            spatial_method = spatial_method or graph.climate_spatial_defaults[selected_catalog_id]
            defaults["climate_station_method"] = station_method
            defaults["climate_spatial_method"] = spatial_method
            defaults["climatestation_mode"] = CLIMATE_STATION_METHOD_RUNTIME[station_method]
            defaults["climate_spatialmode"] = CLIMATE_SPATIAL_METHOD_RUNTIME[spatial_method]
        else:
            if station_method is not None:
                defaults["climate_station_method"] = station_method
            if spatial_method is not None:
                defaults["climate_spatial_method"] = spatial_method
    if resolved_mode == 17:
        defaults.update({key: runtime.states.get(key, "") for key in
                         ("edde_projection", "future_start_year", "future_end_year")})
    elif resolved_mode == 3:
        defaults.update(
            {
                "future_start_year": 2040,
                "future_end_year": 2060,
            }
        )
    else:
        defaults.update(
            {
                "observed_start_year": 1990,
                "observed_end_year": 2020,
            }
        )
    return defaults


def _controller_defaults(controller: str, runtime: RuntimeState) -> dict[str, Any]:
    disturbed_enabled = bool(runtime.states.get("disturbed_enabled", False))
    if controller == "climate":
        return _climate_defaults(runtime, disturbed_enabled)
    if controller == "landuse":
        if runtime.capability_graph is not None:
            graph = runtime.capability_graph
            dataset = _selected_landuse_dataset(runtime, graph)
            current = _stable_runtime_state(
                runtime, "landuse_mode_code", _LANDUSE_STABLE_BY_RUNTIME
            )
            default = (
                graph.landuse_method_defaults[dataset]
                if dataset is not None
                else None
            )
            current_dataset = str(
                runtime.states.get("landuse_catalog_id")
                or runtime.states.get("landuse_runtime_dataset")
                or ""
            ).strip()
            return {
                "landuse_db": current_dataset or graph.defaults["landuse_dataset"],
                "landuse_mode": current or default,
            }
        return {
            "landuse_mode": runtime.states.get("landuse_mode") or "nlcd",
        }
    if controller == "soils":
        graph = _domain_capability_graph(runtime, "soil")
        if graph is not None:
            dataset = graph.defaults["soil_dataset"]
            current = _stable_runtime_state(
                runtime, "soils_mode_code", _SOILS_STABLE_BY_RUNTIME
            )
            soils_mode = current or graph.soil_builder_defaults[dataset]
        else:
            soils_mode = runtime.states.get("soils_mode") or "ssurgo"
        defaults = {
            "soil_mode": soils_mode,
            "soils_mode": soils_mode,
        }
        if disturbed_enabled:
            defaults["sol_ver"] = _default_disturbed_sol_ver(runtime)
        return defaults
    if controller == "watershed":
        return _resolved_watershed_defaults(runtime)
    if controller == "wepp":
        defaults = {
            "clip_soils": disturbed_enabled,
            "clip_soils_depth": 25.0,
        }
        if runtime.model_capability_graph is not None:
            graph = runtime.model_capability_graph
            defaults.update({
                "delineation_backend": (
                    runtime.states.get("delineation_backend")
                    or graph.defaults["delineation_backend"]
                ),
                "watershed_representation": (
                    runtime.states.get("watershed_representation")
                    or graph.defaults["watershed_representation"]
                ),
                "wepp_bin": runtime.states.get("wepp_binary") or graph.defaults["wepp_binary"],
            })
        return defaults
    if controller == "disturbed":
        return {
            "sol_ver": _default_disturbed_sol_ver(runtime),
        }
    return {}


_CONTROLLER_HINTS: dict[str, dict[str, Any]] = {
    "climate": {
        "schema_version": 1,
        "context_fields": ["context.active_mods", "context.region"],
        "groups": [
            {
                "id": "mode",
                "label": "Mode",
                "fields": ["climate_mode", "climatestation"],
            },
            {
                "id": "window",
                "label": "Observed window",
                "fields": ["observed_start_year", "observed_end_year"],
            },
            {
                "id": "future_window",
                "label": "Future window",
                "fields": ["future_start_year", "future_end_year"],
            },
        ],
        "field_hints": {
            "climate_mode": {
                "label": "Climate mode",
                "help": "Choose station or gridded mode before build-climate.",
            },
            "climatestation": {
                "label": "Climate station",
                "help": "Required only for observed station/database modes.",
            },
            "future_start_year": {
                "label": "Future start year",
                "help": "Required only for future climate mode.",
            },
            "future_end_year": {
                "label": "Future end year",
                "help": "Required only for future climate mode.",
            },
        },
    },
    "landuse": {
        "schema_version": 1,
        "context_fields": ["context.active_mods"],
        "groups": [
            {
                "id": "landuse",
                "label": "Landuse",
                "fields": ["landuse_mode", "cover_transform_uploaded"],
            }
        ],
        "field_hints": {
            "landuse_mode": {
                "label": "Landuse mode",
                "help": "Use disturbed mode after SBS/cover-transform uploads.",
            }
        },
    },
    "soils": {
        "schema_version": 1,
        "context_fields": ["context.active_mods"],
        "groups": [
            {
                "id": "soils",
                "label": "Soils",
                "fields": ["soils_mode", "sol_ver"],
            }
        ],
        "field_hints": {
            "sol_ver": {
                "label": "Disturbed soil profile",
                "help": "Needed when disturbed mod is active.",
            }
        },
    },
    "watershed": {
        "schema_version": 1,
        "context_fields": ["context.region"],
        "groups": [
            {
                "id": "delineation",
                "label": "Delineation",
                "fields": ["csa", "mcl"],
            }
        ],
        "field_hints": {
            "csa": {
                "label": "Critical source area",
                "help": "Higher values reduce channel density.",
            }
        },
    },
    "wepp": {
        "schema_version": 1,
        "context_fields": ["context.active_mods"],
        "groups": [
            {
                "id": "run_options",
                "label": "Run options",
                "fields": ["clip_soils", "clip_soils_depth", "initial_sat"],
            }
        ],
        "field_hints": {
            "clip_soils": {
                "label": "Clip soils",
                "help": "Enable for disturbed workflows to constrain soil updates.",
            },
            "initial_sat": {
                "label": "Initial saturation",
                "help": "Optional saturation override applied before running WEPP.",
            },
        },
    },
    "disturbed": {
        "schema_version": 1,
        "context_fields": ["context.active_mods"],
        "groups": [
            {
                "id": "disturbed",
                "label": "Disturbed",
                "fields": ["sol_ver", "sbs_uploaded"],
            }
        ],
        "field_hints": {
            "sbs_uploaded": {
                "label": "SBS uploaded",
                "help": "Upload SBS before build-soils/build-landuse reruns.",
            }
        },
    },
}


def _controller_hints(controller: str) -> dict[str, Any]:
    return copy.deepcopy(_CONTROLLER_HINTS[controller])


def _controller_templates(controller: str, runtime: RuntimeState) -> dict[str, Any]:
    active_mods = list(runtime.active_mods)
    region = runtime.region or "unknown"
    run_defaults = _controller_defaults(controller, runtime)

    if controller == "climate":
        templates = [
            {
                "template_id": "default_run_resolved",
                "display_name": "Run-resolved climate defaults",
                "applicability": {
                    "configs": [runtime.config],
                    "active_mods": active_mods,
                    "regions": [region],
                },
                "parameters": copy.deepcopy(run_defaults),
                "sufficient_without_overrides": True,
            },
        ]
        if 2 in _available_climate_modes(runtime):
            templates.append({
                "template_id": "observed_station_required",
                "display_name": "Observed station climate",
                "applicability": {
                    "configs": [runtime.config],
                    "active_mods": active_mods,
                    "regions": [region],
                },
                "parameters": {
                    "climate_mode": 2,
                    "observed_start_year": 1990,
                    "observed_end_year": 2020,
                },
                "sufficient_without_overrides": False,
                "missing_required_fields": ["climatestation"],
            })
    else:
        templates = [
            {
                "template_id": f"{controller}_default",
                "display_name": f"{controller.title()} default",
                "applicability": {
                    "configs": [runtime.config],
                    "active_mods": active_mods,
                    "regions": [region],
                },
                "parameters": copy.deepcopy(run_defaults),
                "sufficient_without_overrides": True,
            }
        ]

    return {
        "templates": templates,
        "run_resolved_defaults": run_defaults,
    }
