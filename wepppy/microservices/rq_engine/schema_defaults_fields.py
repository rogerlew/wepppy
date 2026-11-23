"""Project capability projections and schema fields for discovery responses."""

from __future__ import annotations

from typing import Any, Mapping

from wepppy.nodb.locales.capability_graph import CapabilityGraph
from wepppy.nodb.locales.climate_catalog import (
    CLIMATE_SPATIAL_METHOD_RUNTIME,
    CLIMATE_STATION_METHOD_RUNTIME,
    iter_climate_datasets,
)
from wepppy.nodb.project_config_capabilities import LANDUSE_METHOD_MODES, SOIL_BUILDER_MODES

from .schema_defaults_runtime import RuntimeState


def _domain_capability_graph(
    runtime: RuntimeState,
    domain: str,
) -> CapabilityGraph | None:
    if runtime.capability_graph is None:
        return None
    if runtime.projected_domains and domain not in runtime.projected_domains:
        return None
    return runtime.capability_graph


def _climate_mode_for_dataset(catalog_id: str) -> int | None:
    for descriptor in iter_climate_datasets():
        if descriptor.catalog_id == catalog_id:
            return descriptor.climate_mode
    return None


_LANDUSE_STABLE_BY_RUNTIME = {value: key for key, value in LANDUSE_METHOD_MODES.items()}
_SOILS_STABLE_BY_RUNTIME = {value: key for key, value in SOIL_BUILDER_MODES.items()}
_CLIMATE_STATION_STABLE_BY_RUNTIME = {
    value: key for key, value in CLIMATE_STATION_METHOD_RUNTIME.items()
}
_CLIMATE_SPATIAL_STABLE_BY_RUNTIME = {
    value: key for key, value in CLIMATE_SPATIAL_METHOD_RUNTIME.items()
}


def _selected_landuse_dataset(
    runtime: RuntimeState,
    graph: CapabilityGraph,
) -> str | None:
    current_runtime = str(runtime.states.get("landuse_runtime_dataset") or "").strip()
    current_dataset = str(runtime.states.get("landuse_catalog_id") or "").strip()
    if not current_runtime:
        return graph.defaults["landuse_dataset"]
    return current_dataset if current_dataset in graph.landuse_datasets else None


def _stable_runtime_state(
    runtime: RuntimeState,
    code_key: str,
    stable_by_runtime: Mapping[int, str],
) -> str | None:
    raw = runtime.states.get(code_key)
    try:
        code = int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None
    return stable_by_runtime.get(code) if code is not None else None


def _model_tuple_binaries_for_runtime(runtime: RuntimeState) -> list[str]:
    if runtime.wepp_binary_options is not None:
        return list(runtime.wepp_binary_options)
    graph = runtime.model_capability_graph
    if graph is None:
        return []
    backend = str(
        runtime.states.get("delineation_backend") or graph.defaults["delineation_backend"]
    ).lower()
    representation = str(
        runtime.states.get("watershed_representation")
        or graph.defaults["watershed_representation"]
    )
    prefix = f"{backend}|{representation}|"
    return [
        token[len(prefix):]
        for token in graph.allowed_model_tuples
        if token.startswith(prefix)
    ]


def _effective_model_tuples(runtime: RuntimeState, graph: CapabilityGraph) -> list[str]:
    return list(runtime.wepp_model_tuples if runtime.wepp_model_tuples is not None else graph.allowed_model_tuples)


def _effective_model_binaries(runtime: RuntimeState, graph: CapabilityGraph) -> list[str]:
    if runtime.wepp_model_tuples is None:
        return list(graph.wepp_binaries)
    return list(dict.fromkeys(value.rsplit("|", 1)[1] for value in _effective_model_tuples(runtime, graph)))


def _operation_capability_authority(runtime: RuntimeState) -> dict[str, Any] | None:
    graph = runtime.capability_graph
    if graph is None:
        return None
    authority = {
        "schema_version": graph.schema_version,
        "provider_revision": graph.provider_revision,
        "climate_datasets": list(graph.climate_datasets),
        "climate_station_methods": list(graph.climate_station_methods),
        "climate_spatial_methods": list(graph.climate_spatial_methods),
        "climate_station_methods_by_dataset": {
            key: list(value) for key, value in graph.climate_station_methods_by_dataset.items()
        },
        "climate_spatial_methods_by_dataset": {
            key: list(value) for key, value in graph.climate_spatial_methods_by_dataset.items()
        },
        "climate_station_defaults": dict(graph.climate_station_defaults),
        "climate_spatial_defaults": dict(graph.climate_spatial_defaults),
        "defaults": dict(graph.defaults),
    }
    if runtime.projected_domains:
        projected_default_keys: set[str] = set()
        if "climate" in runtime.projected_domains:
            projected_default_keys.update(
                {"climate_dataset", "climate_station_database"}
            )
        if "landuse" in runtime.projected_domains:
            projected_default_keys.add("landuse_dataset")
        if "soil" in runtime.projected_domains:
            projected_default_keys.add("soil_dataset")
        for key in tuple(authority["defaults"]):
            if key not in projected_default_keys:
                authority["defaults"].pop(key)
    model_graph = runtime.model_capability_graph
    if model_graph is None:
        for key in (
            "delineation_backend", "watershed_representation", "wepp_binary",
        ):
            authority["defaults"].pop(key, None)
    else:
        authority.update({
            "delineation_backends": list(model_graph.delineation_backends),
            "watershed_representations": list(model_graph.watershed_representations),
            "wepp_binaries": _effective_model_binaries(runtime, model_graph),
            "allowed_model_tuples": _effective_model_tuples(runtime, model_graph),
            "executable_revision": runtime.wepp_binary_revision,
        })
    return authority


def _model_operation_capability_authority(
    runtime: RuntimeState,
) -> dict[str, Any] | None:
    graph = runtime.model_capability_graph
    if graph is None:
        return None
    return {
        "schema_version": graph.schema_version,
        "provider_revision": graph.provider_revision,
        "delineation_backends": list(graph.delineation_backends),
        "watershed_representations": list(graph.watershed_representations),
        "wepp_binaries": _effective_model_binaries(runtime, graph),
        "allowed_model_tuples": _effective_model_tuples(runtime, graph),
        "executable_revision": runtime.wepp_binary_revision,
        "defaults": {
            key: graph.defaults[key]
            for key in (
                "delineation_backend", "watershed_representation", "wepp_binary",
            )
        },
    }


def _available_climate_modes(runtime: RuntimeState) -> list[int]:
    if runtime.capability_graph is not None:
        modes = [
            mode
            for catalog_id in runtime.capability_graph.climate_datasets
            if (mode := _climate_mode_for_dataset(catalog_id)) is not None
        ]
        return list(dict.fromkeys(modes))
    if runtime.v1_capabilities and "climate_datasets" in runtime.v1_capabilities:
        modes = [
            mode
            for catalog_id in runtime.v1_capabilities["climate_datasets"]
            if (mode := _climate_mode_for_dataset(catalog_id)) is not None
        ]
        return list(dict.fromkeys(modes))

    modes = [0, 5, 6, 11]
    if bool(runtime.states.get("climate_has_station", False)):
        modes.insert(1, 2)

    supported_runtime_modes = {
        0,  # Vanilla
        2,  # Observed
        3,  # Future
        5,  # PRISM
        6,  # ObservedDb
        7,  # FutureDb
        8,  # EOBS
        9,  # ObservedPRISM
        10,  # AGDC
        11,  # GridMetPRISM
        12,  # UserDefined
        13,  # DepNexrad
        17,  # EddeV2
    }

    current_mode_raw = runtime.states.get("climate_mode_code")
    try:
        current_mode = int(current_mode_raw) if current_mode_raw is not None else None
    except (TypeError, ValueError):
        current_mode = None
    if current_mode is not None and current_mode in supported_runtime_modes and current_mode not in modes:
        modes.append(current_mode)

    return modes


def _available_landuse_method_ids(runtime: RuntimeState) -> list[str]:
    graph = runtime.capability_graph
    if graph is None:
        if runtime.v1_capabilities and "landuse_methods" in runtime.v1_capabilities:
            return list(runtime.v1_capabilities["landuse_methods"])
        return []
    dataset = _selected_landuse_dataset(runtime, graph)
    if dataset is None:
        return []
    representation = str(runtime.states.get("watershed_representation") or "single-ofe")
    representation_methods = set(graph.landuse_methods_by_representation[representation])
    return [
        method
        for method in graph.landuse_methods_by_dataset[dataset]
        if method in representation_methods
    ]


def _landuse_method_field(
    runtime: RuntimeState, *, runtime_values: bool = False
) -> dict[str, Any]:
    graph = runtime.capability_graph
    field: dict[str, Any] = {
        "type": "integer" if runtime_values else "string",
        "constraint_mode": "static",
    }
    if graph is None:
        return field
    available_ids = _available_landuse_method_ids(runtime)
    current_id = _stable_runtime_state(
        runtime, "landuse_mode_code", _LANDUSE_STABLE_BY_RUNTIME
    )
    enum_ids = list(available_ids)
    if current_id is not None and current_id not in enum_ids:
        enum_ids.append(current_id)
    representation = str(
        runtime.states.get("watershed_representation") or "single-ofe"
    )
    representation_methods = set(
        graph.landuse_methods_by_representation[representation]
    )
    allowed_by_dataset = {
        key: [
            method for method in methods if method in representation_methods
        ]
        for key, methods in graph.landuse_methods_by_dataset.items()
    }

    def _values(methods: list[str]) -> list[str] | list[int]:
        if not runtime_values:
            return methods
        return [
            LANDUSE_METHOD_MODES[method]
            for method in methods
            if method in LANDUSE_METHOD_MODES
        ]

    current_value = (
        LANDUSE_METHOD_MODES.get(current_id)
        if runtime_values and current_id is not None
        else current_id
    )
    current_authorized = current_id in available_ids if current_id is not None else False
    field.update({
        "constraint_mode": "run_resolved",
        "constraint_source": "project_capability_graph",
        "resolved_at": runtime.generated_at,
        "enum": _values(enum_ids),
        "enum_available": _values(available_ids),
        "current_value": current_value,
        "current_value_authorized": current_authorized,
        "disabled_values": (
            [current_value]
            if current_value is not None and not current_authorized
            else []
        ),
        "allowed_by_landuse_catalog_id": {
            key: _values(methods)
            for key, methods in allowed_by_dataset.items()
        },
        "defaults_by_landuse_catalog_id": (
            {
                key: LANDUSE_METHOD_MODES[value]
                for key, value in graph.landuse_method_defaults.items()
            }
            if runtime_values
            else dict(graph.landuse_method_defaults)
        ),
        "runtime_mapping": dict(LANDUSE_METHOD_MODES),
    })
    return field


def _runtime_method_field(
    stable_field: Mapping[str, Any],
    runtime_mapping: Mapping[str, int],
    *,
    relation_key: str,
    defaults_key: str,
    current_runtime_value: int | None = None,
) -> dict[str, Any]:
    def _runtime_values(values: object) -> list[int]:
        if not isinstance(values, list):
            return []
        return [
            runtime_mapping[value]
            for value in values
            if isinstance(value, str) and value in runtime_mapping
        ]

    current_stable = stable_field.get("current_value")
    mapped_current_runtime = (
        runtime_mapping.get(current_stable)
        if isinstance(current_stable, str)
        else None
    )
    current_runtime = (
        current_runtime_value
        if current_runtime_value is not None
        else mapped_current_runtime
    )
    relations = stable_field.get(relation_key)
    defaults = stable_field.get(defaults_key)
    enum_values = _runtime_values(stable_field.get("enum"))
    available_values = _runtime_values(stable_field.get("enum_available"))
    if current_runtime is not None and current_runtime not in enum_values:
        enum_values.append(current_runtime)
    current_authorized = (
        current_runtime in available_values
        if current_runtime is not None
        else False
    )
    field: dict[str, Any] = {
        "type": "integer",
        "constraint_mode": stable_field.get("constraint_mode", "run_resolved"),
        "constraint_source": stable_field.get(
            "constraint_source", "project_capability_graph"
        ),
        "resolved_at": stable_field.get("resolved_at"),
        "enum": enum_values,
        "enum_available": available_values,
        "current_value": current_runtime,
        "current_value_authorized": current_authorized,
        "disabled_values": (
            [current_runtime]
            if current_runtime is not None
            and not current_authorized
            else []
        ),
        "runtime_mapping": dict(runtime_mapping),
    }
    if isinstance(relations, Mapping):
        field[relation_key] = {
            key: _runtime_values(list(values))
            for key, values in relations.items()
        }
    if isinstance(defaults, Mapping):
        field[defaults_key] = {
            key: runtime_mapping[value]
            for key, value in defaults.items()
            if value in runtime_mapping
        }
    return field


def _landuse_dataset_field(runtime: RuntimeState) -> dict[str, Any]:
    field: dict[str, Any] = {"type": "string", "constraint_mode": "static"}
    graph = runtime.capability_graph
    if graph is None:
        return field
    allowed = list(graph.landuse_datasets)
    current_runtime = str(runtime.states.get("landuse_runtime_dataset") or "").strip()
    current_catalog_id = str(runtime.states.get("landuse_catalog_id") or "").strip()
    current_value = current_catalog_id or current_runtime or None
    current_authorized = bool(current_catalog_id and current_catalog_id in allowed)
    enum_values = list(allowed)
    if current_value is not None and current_value not in enum_values:
        enum_values.append(current_value)
    field.update({
        "constraint_mode": "run_resolved",
        "constraint_source": "project_capability_graph",
        "resolved_at": runtime.generated_at,
        "enum": enum_values,
        "enum_available": allowed,
        "current_value": current_value,
        "current_value_authorized": current_authorized,
        "disabled_values": (
            [current_value]
            if current_value is not None and not current_authorized
            else []
        ),
    })
    return field


def _supported_soils_modes(runtime: RuntimeState) -> list[str]:
    graph = _domain_capability_graph(runtime, "soil")
    if graph is not None:
        return list(graph.soil_builders_by_dataset[graph.defaults["soil_dataset"]])
    if runtime.v1_capabilities and "soil_builders" in runtime.v1_capabilities:
        return list(runtime.v1_capabilities["soil_builders"])
    return ["ssurgo", "statsgo"]


def _soil_mode_field(
    runtime: RuntimeState, *, runtime_values: bool = False
) -> dict[str, Any]:
    allowed_ids = _supported_soils_modes(runtime)
    current_id = _stable_runtime_state(
        runtime, "soils_mode_code", _SOILS_STABLE_BY_RUNTIME
    )
    enum_ids = list(allowed_ids)
    if current_id is not None and current_id not in enum_ids:
        enum_ids.append(current_id)

    def _values(methods: list[str]) -> list[str] | list[int]:
        if not runtime_values:
            return methods
        return [
            SOIL_BUILDER_MODES[method]
            for method in methods
            if method in SOIL_BUILDER_MODES
        ]

    current_value = (
        SOIL_BUILDER_MODES.get(current_id)
        if runtime_values and current_id is not None
        else current_id
    )
    current_authorized = current_id in allowed_ids if current_id is not None else False
    enum_values = _values(enum_ids)
    available_values = _values(allowed_ids)
    graph = _domain_capability_graph(runtime, "soil")
    field: dict[str, Any] = {
        "type": "integer" if runtime_values else "string",
        "constraint_mode": (
            "run_resolved" if graph is not None else "static"
        ),
    }
    if enum_values or not runtime_values:
        field["enum"] = enum_values
        field["enum_available"] = available_values
    if graph is not None:
        field.update({
            "constraint_source": "project_capability_graph",
            "resolved_at": runtime.generated_at,
            "current_value": current_value,
            "current_value_authorized": current_authorized,
            "disabled_values": (
                [current_value]
                if current_value is not None and not current_authorized
                else []
            ),
            "allowed_by_soil_dataset_id": {
                key: _values(list(values))
                for key, values in graph.soil_builders_by_dataset.items()
            },
            "defaults_by_soil_dataset_id": (
                {
                    key: SOIL_BUILDER_MODES[value]
                    for key, value in graph.soil_builder_defaults.items()
                }
                if runtime_values
                else dict(graph.soil_builder_defaults)
            ),
            "runtime_mapping": dict(SOIL_BUILDER_MODES),
        })
    return field


def _inferred_config_sol_ver(config: str) -> float | None:
    token = str(config or "").strip().lower()
    if "9002" in token:
        return 9002.0
    return None


def _runtime_disturbed_sol_ver(runtime: RuntimeState) -> float | None:
    raw_value = runtime.states.get("disturbed_sol_ver")
    try:
        value = float(raw_value) if raw_value is not None else None
    except (TypeError, ValueError):
        return None
    return value if value is not None and value > 0 else None


def _default_disturbed_sol_ver(runtime: RuntimeState) -> float:
    runtime_value = _runtime_disturbed_sol_ver(runtime)
    if runtime_value is not None:
        return runtime_value

    inferred = _inferred_config_sol_ver(runtime.config)
    if inferred is not None:
        return inferred

    return 2018.0


def _disturbed_sol_ver_options(runtime: RuntimeState) -> list[float]:
    if not bool(runtime.states.get("disturbed_enabled", False)):
        return []

    options: list[float] = []
    for candidate in [2006.0, 2018.0, _inferred_config_sol_ver(runtime.config), _runtime_disturbed_sol_ver(runtime)]:
        if candidate is None:
            continue
        value = float(candidate)
        if value not in options:
            options.append(value)
    return options


def _resolved_watershed_defaults(runtime: RuntimeState) -> dict[str, Any]:
    csa_value = runtime.states.get("watershed_csa")
    mcl_value = runtime.states.get("watershed_mcl")
    stream_pruning_method_value = runtime.states.get("watershed_stream_pruning_method")
    csa = float(csa_value) if isinstance(csa_value, (int, float)) else 10.0
    mcl = float(mcl_value) if isinstance(mcl_value, (int, float)) else 75.0
    if isinstance(stream_pruning_method_value, str):
        stream_pruning_method = stream_pruning_method_value.strip().lower()
    else:
        stream_pruning_method = "ifolp"
    if stream_pruning_method not in {"ifolp", "remove_short_streams"}:
        stream_pruning_method = "ifolp"
    return {
        "csa": csa,
        "mcl": mcl,
        "stream_pruning_method": stream_pruning_method,
    }
