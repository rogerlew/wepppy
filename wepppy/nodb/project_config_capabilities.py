"""Stored project capability authority for presentation and mutation checks."""

from __future__ import annotations

import ast
from types import MappingProxyType
from typing import Mapping, Protocol

from wepppy.nodb.locales.capability_graph import (
    CAPABILITY_SCHEMA_VERSION,
    HISTORICAL_CAPABILITY_SCHEMA_VERSION,
    CapabilityGraph,
    CapabilityGraphError,
)
from wepppy.nodb.locales.climate_catalog import (
    CLIMATE_SPATIAL_METHOD_RUNTIME,
    CLIMATE_STATION_METHOD_RUNTIME,
    get_climate_station_database,
)
from wepppy.nodb.locales.landuse_catalog import get_landcover_entry
from wepppy.nodb.locales import available_climate_datasets, available_landuse_datasets
from wepppy.project_config_serialization import CanonicalValue

__all__ = [
    "CapabilityConfig",
    "LANDUSE_METHOD_MODES",
    "SOIL_BUILDER_MODES",
    "capability_authority",
    "capability_default",
    "capability_ids",
    "climate_spatial_capability_modes",
    "climate_station_capability_modes",
    "landuse_capability_modes",
    "landuse_runtime_dataset_allowed",
    "model_tuple_allowed",
    "model_tuple_binaries",
    "resolve_landuse_runtime_dataset",
    "resolve_named_preset_capabilities",
    "runtime_value_allowed",
    "soil_capability_modes",
]


class CapabilityConfig(Protocol):
    def config_get_list(self, section: str, option: str, default: object = ...) -> object: ...
    def config_get_raw(self, section: str, option: str, default: object = ...) -> object: ...


SOIL_BUILDER_MODES: Mapping[str, int] = MappingProxyType(
    {"gridded": 0, "single_mukey": 1, "single_database": 2}
)
LANDUSE_METHOD_MODES: Mapping[str, int] = MappingProxyType(
    {"gridded": 0, "single": 1, "rred_unburned": 2, "rred_burned": 3, "upload": 4}
)
_MANDATORY_V2_AXES = (
    "locale_profiles",
    "dem_sources",
    "climate_datasets",
    "climate_station_methods",
    "climate_spatial_methods",
    "soil_datasets",
    "soil_builders",
    "landuse_datasets",
    "landuse_methods",
    "delineation_backends",
    "watershed_representations",
    "wepp_binaries",
    "mods",
    "allowed_model_tuples",
)
_MANDATORY_V3_AXES = (
    *_MANDATORY_V2_AXES[:3],
    "climate_station_databases",
    *_MANDATORY_V2_AXES[3:],
)
_V2_RELATION_SECTIONS = (
    "capabilities.climate_station_methods",
    "capabilities.climate_spatial_methods",
    "capabilities.climate_station_defaults",
    "capabilities.climate_spatial_defaults",
    "capabilities.landuse_methods",
    "capabilities.landuse_method_defaults",
    "capabilities.landuse_methods_by_representation",
    "capabilities.soil_builders",
    "capabilities.soil_builder_defaults",
    "capabilities.wepp_binary_revisions",
    "capabilities.mod_requires",
    "capabilities.mod_conflicts",
    "capability_defaults",
)


def _scalar(config: CapabilityConfig, section: str, option: str, default: object = None) -> object:
    raw = config.config_get_raw(section, option, default)
    if not isinstance(raw, str):
        return raw
    try:
        return ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return raw.strip()


def _schema_version(config: CapabilityConfig) -> int | None:
    raw = config.config_get_raw("capabilities", "schema_version", None)
    if raw is None:
        return None
    parsed = _scalar(config, "capabilities", "schema_version")
    if isinstance(parsed, bool) or not isinstance(parsed, int):
        raise ValueError("capabilities.schema_version must be an integer")
    return parsed


def capability_ids(config: CapabilityConfig, option: str) -> frozenset[str] | None:
    """Read one stable-ID axis while preserving absent/v1 compatibility."""

    raw_getter = getattr(config, "config_get_raw", None)
    if raw_getter is None or raw_getter("capabilities", option, None) is None:
        return None
    raw = config.config_get_list("capabilities", option, None)
    if raw == [] and option == "mods":
        return frozenset()
    if raw in (None, []):
        raise ValueError(f"capabilities.{option} must not be empty")
    if not isinstance(raw, (list, tuple)) or not all(
        isinstance(item, str) and item.strip() for item in raw
    ):
        raise ValueError(f"capabilities.{option} must be a non-empty string list")
    values = tuple(item.strip() for item in raw)
    if len(set(values)) != len(values):
        raise ValueError(f"capabilities.{option} must not contain duplicates")
    return frozenset(values)


def _ordered_axis(config: CapabilityConfig, option: str) -> tuple[str, ...]:
    values = capability_ids(config, option)
    if values is None:
        raise ValueError(f"capabilities.{option} is required for schema v2")
    raw = config.config_get_list("capabilities", option, None)
    assert isinstance(raw, (list, tuple))
    return tuple(str(item).strip() for item in raw)


def _section_options(config: CapabilityConfig, section: str) -> tuple[str, ...] | None:
    explicit = getattr(config, "config_section_options", None)
    if callable(explicit):
        return tuple(str(item) for item in explicit(section))
    parser = getattr(config, "_configparser", None)
    if parser is not None and hasattr(parser, "has_section") and parser.has_section(section):
        return tuple(str(item) for item in parser.options(section))
    return None


def _validate_section_inventory(config: CapabilityConfig, version: int) -> None:
    parser = getattr(config, "_configparser", None)
    if parser is None or not hasattr(parser, "sections"):
        return
    observed_sections = {
        str(section)
        for section in parser.sections()
        if str(section) == "capability_defaults" or str(section).startswith("capabilities")
    }
    expected_sections = {"capabilities", *_V2_RELATION_SECTIONS}
    if observed_sections != expected_sections:
        raise ValueError("schema-v2 capability sections must be complete and contain no unknown sections")

    observed_options = set(parser.options("capabilities"))
    mandatory_axes = (
        _MANDATORY_V3_AXES
        if version == CAPABILITY_SCHEMA_VERSION
        else _MANDATORY_V2_AXES
    )
    expected_options = {"schema_version", "provider_revision", *mandatory_axes}
    if observed_options != expected_options:
        raise ValueError("capabilities keys must be complete and contain no unknown axes")


def _relation(
    config: CapabilityConfig,
    section: str,
    expected_keys: tuple[str, ...],
    *,
    allow_empty_values: bool = False,
) -> Mapping[str, tuple[str, ...]]:
    observed = _section_options(config, section)
    if observed is not None and set(observed) != set(expected_keys):
        raise ValueError(f"{section} keys must exhaust their source axis")
    result: dict[str, tuple[str, ...]] = {}
    for key in expected_keys:
        raw = config.config_get_list(section, key, None)
        if raw is None or not isinstance(raw, (list, tuple)):
            raise ValueError(f"{section}.{key} must be a string list")
        if not allow_empty_values and not raw:
            raise ValueError(f"{section}.{key} must not be empty")
        if not all(isinstance(item, str) and item.strip() for item in raw):
            raise ValueError(f"{section}.{key} must be a string list")
        values = tuple(item.strip() for item in raw)
        if len(set(values)) != len(values):
            raise ValueError(f"{section}.{key} must not contain duplicates")
        result[key] = values
    return MappingProxyType(result)


def _defaults(
    config: CapabilityConfig,
    section: str,
    expected_keys: tuple[str, ...],
) -> Mapping[str, str]:
    observed = _section_options(config, section)
    if observed is not None and set(observed) != set(expected_keys):
        raise ValueError(f"{section} keys must exhaust their source axis")
    result: dict[str, str] = {}
    for key in expected_keys:
        value = _scalar(config, section, key, None)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{section}.{key} must be a stable ID")
        result[key] = value.strip()
    return MappingProxyType(result)


def capability_authority(config: CapabilityConfig) -> CapabilityGraph | None:
    """Return validated schema-v2/v3 authority, or ``None`` for legacy/v1."""

    version = _schema_version(config)
    if version is None:
        return None
    if version not in {HISTORICAL_CAPABILITY_SCHEMA_VERSION, CAPABILITY_SCHEMA_VERSION}:
        raise ValueError(f"unsupported capabilities.schema_version: {version}")
    _validate_section_inventory(config, version)
    mandatory_axes = (
        _MANDATORY_V3_AXES
        if version == CAPABILITY_SCHEMA_VERSION
        else _MANDATORY_V2_AXES
    )
    axes = {option: _ordered_axis(config, option) for option in mandatory_axes}
    mods = axes["mods"]
    provider_revision = _scalar(config, "capabilities", "provider_revision", None)
    if (
        not isinstance(provider_revision, str)
        or len(provider_revision) != 64
        or any(character not in "0123456789abcdef" for character in provider_revision)
    ):
        raise ValueError("capabilities.provider_revision must be a SHA-256 identity")
    graph = CapabilityGraph(
        schema_version=version,
        locale_profiles=axes["locale_profiles"],
        dem_sources=axes["dem_sources"],
        climate_datasets=axes["climate_datasets"],
        climate_station_databases=axes.get("climate_station_databases", ()),
        climate_station_methods=axes["climate_station_methods"],
        climate_spatial_methods=axes["climate_spatial_methods"],
        soil_datasets=axes["soil_datasets"],
        soil_builders=axes["soil_builders"],
        landuse_datasets=axes["landuse_datasets"],
        landuse_methods=axes["landuse_methods"],
        delineation_backends=axes["delineation_backends"],
        watershed_representations=axes["watershed_representations"],
        wepp_binaries=axes["wepp_binaries"],
        wepp_binary_revisions=_defaults(
            config, "capabilities.wepp_binary_revisions", axes["wepp_binaries"]
        ),
        mods=mods,
        allowed_model_tuples=axes["allowed_model_tuples"],
        climate_station_methods_by_dataset=_relation(
            config, "capabilities.climate_station_methods", axes["climate_datasets"]
        ),
        climate_spatial_methods_by_dataset=_relation(
            config, "capabilities.climate_spatial_methods", axes["climate_datasets"]
        ),
        climate_station_defaults=_defaults(
            config, "capabilities.climate_station_defaults", axes["climate_datasets"]
        ),
        climate_spatial_defaults=_defaults(
            config, "capabilities.climate_spatial_defaults", axes["climate_datasets"]
        ),
        landuse_methods_by_dataset=_relation(
            config, "capabilities.landuse_methods", axes["landuse_datasets"]
        ),
        landuse_method_defaults=_defaults(
            config, "capabilities.landuse_method_defaults", axes["landuse_datasets"]
        ),
        landuse_methods_by_representation=_relation(
            config,
            "capabilities.landuse_methods_by_representation",
            axes["watershed_representations"],
        ),
        soil_builders_by_dataset=_relation(
            config, "capabilities.soil_builders", axes["soil_datasets"]
        ),
        soil_builder_defaults=_defaults(
            config, "capabilities.soil_builder_defaults", axes["soil_datasets"]
        ),
        mod_requires=_relation(config, "capabilities.mod_requires", mods),
        mod_conflicts=_relation(
            config, "capabilities.mod_conflicts", mods, allow_empty_values=True
        ),
        defaults=_defaults(
            config,
            "capability_defaults",
            (
                "locale_profile",
                "dem_source",
                "climate_dataset",
                *(("climate_station_database",) if version == CAPABILITY_SCHEMA_VERSION else ()),
                "landuse_dataset",
                "soil_dataset",
                "delineation_backend",
                "watershed_representation",
                "wepp_binary",
            ),
        ),
        provider_revision=provider_revision,
    )
    try:
        graph.validate()
    except CapabilityGraphError as exc:
        raise ValueError(str(exc)) from exc
    if version == CAPABILITY_SCHEMA_VERSION:
        selected_station_database = graph.defaults["climate_station_database"]
        station_database = get_climate_station_database(selected_station_database)
        runtime_selector = _scalar(config, "climate", "cligen_db", None)
        if station_database is None or runtime_selector != station_database.selector:
            raise ValueError(
                "climate.cligen_db does not match the stored climate-station database selection"
            )
    return graph


def capability_default(config: CapabilityConfig, option: str) -> str | None:
    authority = capability_authority(config)
    return None if authority is None else authority.defaults.get(option)


def runtime_value_allowed(
    config: CapabilityConfig,
    option: str,
    value: object,
    *,
    stable_to_runtime: Mapping[str, object] | None = None,
) -> bool:
    allowed = capability_ids(config, option)
    if allowed is None:
        return True
    if stable_to_runtime is None:
        return str(value) in allowed
    return any(stable_to_runtime[item] == value for item in allowed if item in stable_to_runtime)


def model_tuple_allowed(
    config: CapabilityConfig,
    delineation_backend: str,
    watershed_representation: str,
    wepp_binary: str,
) -> bool:
    """Return whether one stable model tuple is authorized for this project."""

    authority = capability_authority(config)
    if authority is None:
        return True
    token = "|".join((delineation_backend, watershed_representation, wepp_binary))
    return token in authority.allowed_model_tuples


def model_tuple_binaries(
    config: CapabilityConfig,
    delineation_backend: str,
    watershed_representation: str,
) -> tuple[str, ...] | None:
    """Return stored binaries participating in a backend/representation tuple."""

    authority = capability_authority(config)
    if authority is None:
        return None
    prefix = f"{delineation_backend}|{watershed_representation}|"
    return tuple(
        token[len(prefix):]
        for token in authority.allowed_model_tuples
        if token.startswith(prefix)
    )


def soil_capability_modes(
    config: CapabilityConfig,
    *,
    soil_dataset: str | None = None,
) -> frozenset[int] | None:
    authority = capability_authority(config)
    if authority is None:
        allowed = capability_ids(config, "soil_builders")
        if allowed is None:
            return None
    else:
        selected = soil_dataset or authority.defaults["soil_dataset"]
        allowed = frozenset(authority.soil_builders_by_dataset.get(selected, ()))
    return frozenset(SOIL_BUILDER_MODES[item] for item in allowed if item in SOIL_BUILDER_MODES)


def climate_station_capability_modes(
    config: CapabilityConfig,
    climate_dataset: str,
) -> frozenset[int] | None:
    authority = capability_authority(config)
    if authority is None:
        return None
    return frozenset(
        CLIMATE_STATION_METHOD_RUNTIME[item]
        for item in authority.climate_station_methods_by_dataset.get(climate_dataset, ())
    )


def climate_spatial_capability_modes(
    config: CapabilityConfig,
    climate_dataset: str,
) -> frozenset[int] | None:
    authority = capability_authority(config)
    if authority is None:
        return None
    return frozenset(
        CLIMATE_SPATIAL_METHOD_RUNTIME[item]
        for item in authority.climate_spatial_methods_by_dataset.get(climate_dataset, ())
    )


def landuse_capability_modes(
    config: CapabilityConfig,
    landuse_dataset: str,
    watershed_representation: str,
) -> frozenset[int] | None:
    authority = capability_authority(config)
    if authority is None:
        return None
    dataset_methods = set(authority.landuse_methods_by_dataset.get(landuse_dataset, ()))
    representation_methods = set(
        authority.landuse_methods_by_representation.get(watershed_representation, ())
    )
    return frozenset(
        LANDUSE_METHOD_MODES[item]
        for item in dataset_methods & representation_methods
        if item in LANDUSE_METHOD_MODES
    )


def landuse_runtime_dataset_allowed(config: CapabilityConfig, runtime_value: str) -> bool:
    authority = capability_authority(config)
    if authority is None:
        return runtime_value_allowed(config, "landuse_datasets", runtime_value)
    return any(
        entry is not None and entry.runtime_value == runtime_value
        for entry in (get_landcover_entry(item) for item in authority.landuse_datasets)
    )


def resolve_landuse_runtime_dataset(
    config: CapabilityConfig,
    submitted_value: str,
) -> str | None:
    """Map an allowed stable catalog ID or legacy runtime token to its runtime value."""

    authority = capability_authority(config)
    if authority is None:
        allowed = capability_ids(config, "landuse_datasets")
        if allowed is None:
            return submitted_value
        if submitted_value in allowed:
            entry = get_landcover_entry(submitted_value)
            return submitted_value if entry is None else entry.runtime_value
        entry = get_landcover_entry(submitted_value)
        if entry is not None and entry.catalog_id in allowed:
            return entry.runtime_value
        for stable_id in allowed:
            allowed_entry = get_landcover_entry(stable_id)
            if allowed_entry is not None and allowed_entry.runtime_value == submitted_value:
                return submitted_value
        return None
    if submitted_value in authority.landuse_datasets:
        entry = get_landcover_entry(submitted_value)
        return None if entry is None else entry.runtime_value
    if landuse_runtime_dataset_allowed(config, submitted_value):
        return submitted_value
    return None


def resolve_named_preset_capabilities(
    config: Mapping[str, Mapping[str, CanonicalValue]],
) -> dict[str, CanonicalValue]:
    """Preserve schema-v1, merge-only capability snapshots for named presets."""

    locales_raw = config.get("general", {}).get("locales", [])
    locales = tuple(str(item) for item in locales_raw) if isinstance(locales_raw, list) else ()
    mods_raw = config.get("nodb", {}).get("mods", [])
    mods = tuple(str(item) for item in mods_raw) if isinstance(mods_raw, list) else ()
    climate_ids = [item.catalog_id for item in available_climate_datasets(locales, mods)]
    landuse_ids = [
        item.key
        for item in available_landuse_datasets(None, mods, locales)
        if item.kind == "landcover"
    ]
    current_landuse = config.get("landuse", {}).get("nlcd_db")
    if isinstance(current_landuse, str) and current_landuse not in landuse_ids:
        landuse_ids.append(current_landuse)
    return {
        "climate_datasets": climate_ids,
        "soil_builders": list(SOIL_BUILDER_MODES),
        "landuse_datasets": landuse_ids,
        "mods": list(mods),
    }
