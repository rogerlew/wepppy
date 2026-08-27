"""Deterministic project configuration composition over a validated registry."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from wepppy.nodb.config_builder.registry import load_registry
from wepppy.nodb.config_builder.schema import (
    BuilderDescription,
    BuilderSelections,
    ComponentDefinition,
    ComponentKind,
    ComponentSummary,
    ConfigKey,
    ConfigProvenance,
    Registry,
    RegistryValue,
    ResolvedBuilderConfig,
)
from wepppy.nodb.locales.capability_graph import (
    CAPABILITY_SCHEMA_VERSION,
    HISTORICAL_CAPABILITY_SCHEMA_VERSION,
    CapabilityGraph,
    build_continental_us_capability_graph,
    build_locale_capability_graph,
)
from wepppy.project_config_serialization import (
    CanonicalValue,
    parse_config_text,
    serialize_config,
)

__all__ = [
    "ALLOWED_CELL_SIZES",
    "DEFAULT_SELECTIONS",
    "BuilderConstraintError",
    "describe_builder",
    "resolve_builder_config",
]

ALLOWED_CELL_SIZES = (1, 2, 5, 10, 25, 30, 90, 100)
_DEFAULTS_PATH = Path(__file__).parents[1] / "configs" / "_defaults.cfg"
_KIND_ORDER = {
    ComponentKind.LOCALE: 0,
    ComponentKind.DEM: 1,
    ComponentKind.DELINEATION: 2,
    ComponentKind.REPRESENTATION: 3,
    ComponentKind.WEPP_BINARY: 4,
    ComponentKind.MOD: 5,
    ComponentKind.SOIL: 6,
    ComponentKind.LANDUSE: 7,
    ComponentKind.CLIMATE: 8,
    ComponentKind.CLIMATE_STATION_DATABASE: 9,
    ComponentKind.CAPABILITY: 10,
}
_KIND_FIELD = {
    ComponentKind.DELINEATION: "delineation_backend",
    ComponentKind.REPRESENTATION: "watershed_representation",
    ComponentKind.WEPP_BINARY: "wepp_binary",
}
DEFAULT_SELECTIONS = MappingProxyType({
    "delineation_backend": "wbt",
    "watershed_representation": "single-ofe",
    "wepp_binary": "wepp_260803",
})


def _capability_graph_for_registry(registry: Registry, locale_id: str):
    binary_components = registry.by_kind(ComponentKind.WEPP_BINARY)
    return build_locale_capability_graph(
        locale_id,
        tuple(item.component_id for item in binary_components),
        {item.component_id: item.source_revision for item in binary_components},
    )


def _historical_capability_graph_for_registry(registry: Registry):
    binary_components = registry.by_kind(ComponentKind.WEPP_BINARY)
    return build_continental_us_capability_graph(
        tuple(item.component_id for item in binary_components),
        {item.component_id: item.source_revision for item in binary_components},
    )


class BuilderConstraintError(ValueError):
    """Field-addressable rejection of an unsupported builder selection."""

    def __init__(self, field: str, code: str, message: str) -> None:
        self.field = field
        self.code = code
        super().__init__(message)


def _component(
    registry: Registry,
    component_id: str,
    kind: ComponentKind,
    field: str,
) -> ComponentDefinition:
    component = registry.components.get(component_id)
    if component is None:
        raise BuilderConstraintError(field, "unknown_component", f"Unknown {field} ID: {component_id}")
    if component.kind is not kind:
        raise BuilderConstraintError(
            field,
            "wrong_component_kind",
            f"Component {component_id!r} is not a {kind.value}",
        )
    return component


def _require_allowed(field: str, selected: str, allowed: tuple[str, ...]) -> None:
    if selected not in allowed:
        raise BuilderConstraintError(
            field,
            "unsupported_combination",
            f"{selected!r} is not allowed by the selected locale",
        )


def _selection_chain(
    registry: Registry,
    selections: BuilderSelections,
    *,
    capability_schema_version: int,
    capability_graph: CapabilityGraph | None = None,
) -> tuple[ComponentDefinition, ...]:
    locale = _component(registry, selections.locale, ComponentKind.LOCALE, "locale")
    dem = _component(registry, selections.dem, ComponentKind.DEM, "dem")
    delineation = _component(
        registry,
        selections.delineation_backend,
        ComponentKind.DELINEATION,
        "delineation_backend",
    )
    representation = _component(
        registry,
        selections.watershed_representation,
        ComponentKind.REPRESENTATION,
        "watershed_representation",
    )
    wepp_binary = _component(
        registry,
        selections.wepp_binary,
        ComponentKind.WEPP_BINARY,
        "wepp_binary",
    )
    soil = _component(registry, selections.soil, ComponentKind.SOIL, "soil")
    landuse = _component(registry, selections.landuse, ComponentKind.LANDUSE, "landuse")
    climate = _component(registry, selections.climate, ComponentKind.CLIMATE, "climate")
    climate_station_database = None
    if capability_schema_version == CAPABILITY_SCHEMA_VERSION:
        climate_station_database = _component(
            registry,
            selections.climate_station_database,
            ComponentKind.CLIMATE_STATION_DATABASE,
            "climate_station_database",
        )
    capability = _component(
        registry,
        selections.capability_profile,
        ComponentKind.CAPABILITY,
        "capability_profile",
    )
    graph = capability_graph or (
        _historical_capability_graph_for_registry(registry)
        if capability_schema_version == HISTORICAL_CAPABILITY_SCHEMA_VERSION
        else _capability_graph_for_registry(registry, selections.locale)
    )
    graph_axes = (
        ("locale", selections.locale, graph.locale_profiles),
        ("dem", selections.dem, graph.dem_sources),
        ("soil", selections.soil, graph.soil_datasets),
        ("landuse", selections.landuse, graph.landuse_datasets),
        ("climate", selections.climate, graph.climate_datasets),
    )
    if climate_station_database is not None:
        graph_axes += ((
            "climate_station_database",
            selections.climate_station_database,
            graph.climate_station_databases,
        ),)
    for field, selected_id, allowed_ids in graph_axes:
        _require_allowed(field, selected_id, allowed_ids)
    model_tuple = "|".join(
        (
            selections.delineation_backend,
            selections.watershed_representation,
            selections.wepp_binary,
        )
    )
    if model_tuple not in graph.allowed_model_tuples:
        raise BuilderConstraintError(
            "watershed_representation",
            "unsupported_combination",
            "The selected delineation, watershed representation, and WEPP binary are incompatible.",
        )
    constraints = locale.constraints
    _require_allowed("dem", dem.component_id, constraints.allowed_dem)
    _require_allowed(
        "delineation_backend",
        delineation.component_id,
        constraints.allowed_delineation,
    )
    _require_allowed(
        "watershed_representation",
        representation.component_id,
        constraints.allowed_representation,
    )
    _require_allowed("wepp_binary", wepp_binary.component_id, constraints.allowed_wepp_binary)
    _require_allowed("soil", soil.component_id, constraints.allowed_soil)
    _require_allowed("landuse", landuse.component_id, constraints.allowed_landuse)
    _require_allowed("climate", climate.component_id, constraints.allowed_climate)
    if climate_station_database is not None:
        _require_allowed(
            "climate_station_database",
            climate_station_database.component_id,
            constraints.allowed_climate_station_database,
        )
    _require_allowed(
        "capability_profile",
        capability.component_id,
        constraints.allowed_capability_profiles,
    )
    mods: list[ComponentDefinition] = []
    seen_mods: set[str] = set()
    for component_id in selections.mods:
        if component_id in seen_mods:
            raise BuilderConstraintError("mods", "duplicate_selection", f"Duplicate mod ID: {component_id}")
        mod = _component(registry, component_id, ComponentKind.MOD, "mods")
        _require_allowed("mods", component_id, constraints.allowed_mods)
        mods.append(mod)
        seen_mods.add(component_id)
    selected = (
        locale,
        dem,
        delineation,
        representation,
        wepp_binary,
        *mods,
        soil,
        landuse,
        climate,
        *((climate_station_database,) if climate_station_database is not None else ()),
        capability,
    )
    selected_ids = {item.component_id for item in selected}
    for component in selected:
        missing = set(component.constraints.requires) - selected_ids
        conflicts = set(component.constraints.conflicts) & selected_ids
        if missing:
            raise BuilderConstraintError(
                _KIND_FIELD.get(component.kind, component.kind.value),
                "missing_required_component",
                f"{component.component_id!r} requires {sorted(missing)}",
            )
        if conflicts:
            raise BuilderConstraintError(
                _KIND_FIELD.get(component.kind, component.kind.value),
                "conflicting_component",
                f"{component.component_id!r} conflicts with {sorted(conflicts)}",
            )
    return tuple(sorted(selected, key=lambda item: (_KIND_ORDER[item.kind], item.component_id)))


def _mutable_value(value: RegistryValue) -> CanonicalValue:
    return list(value) if isinstance(value, tuple) else value


def _freeze_config(
    config: Mapping[str, Mapping[str, CanonicalValue]],
) -> Mapping[str, Mapping[str, CanonicalValue]]:
    return MappingProxyType(
        {
            section: MappingProxyType(deepcopy(dict(options)))
            for section, options in config.items()
        }
    )

def describe_builder(registry: Registry | None = None) -> BuilderDescription:
    """Return a deterministic, immutable description for server consumers."""

    resolved_registry = load_registry() if registry is None else registry
    all_summaries = {
        item.component_id: ComponentSummary(
            item.component_id,
            item.kind.value,
            item.label,
            item.description,
            item.default_cellsize,
            item.constraints,
            item.profile_classification,
            item.support_state,
            item.runtime_tokens,
            item.base_profile_id,
            item.overlay_precedence,
        )
        for item in resolved_registry.components.values()
    }

    def summaries_for(locale_id: str, *, historical: bool = False) -> tuple[ComponentSummary, ...]:
        graph = (
            _historical_capability_graph_for_registry(resolved_registry)
            if historical
            else _capability_graph_for_registry(resolved_registry, locale_id)
        )
        component_ids = {
            locale_id,
            *graph.dem_sources,
            *graph.soil_datasets,
            *graph.landuse_datasets,
            *graph.climate_datasets,
            *graph.climate_station_databases,
            *graph.delineation_backends,
            *graph.watershed_representations,
            *graph.wepp_binaries,
            f"{locale_id}-capabilities",
        }
        return tuple(
            all_summaries[component_id]
            for component_id in sorted(
                component_ids,
                key=lambda value: (
                    _KIND_ORDER[resolved_registry.components[value].kind], value
                ),
            )
        )

    compatibility_summaries = summaries_for("continental-us", historical=True)
    graphs = {
        locale_id: _capability_graph_for_registry(resolved_registry, locale_id)
        for locale_id in (
            "continental-us", "europe", "canada", "australia", "global-earth"
        )
    }
    components_by_locale = MappingProxyType({
        locale_id: summaries_for(locale_id) for locale_id in graphs
    })
    graph_mappings = MappingProxyType({
        locale_id: MappingProxyType({
            section: MappingProxyType(dict(options))
            for section, options in graph.as_config_sections().items()
        })
        for locale_id, graph in graphs.items()
    })
    historical_graph = _historical_capability_graph_for_registry(resolved_registry)
    return BuilderDescription(
        2,
        resolved_registry.revision,
        compatibility_summaries,
        ALLOWED_CELL_SIZES,
        DEFAULT_SELECTIONS,
        MappingProxyType(
            {
                section: MappingProxyType(dict(options))
                for section, options in historical_graph.as_config_sections().items()
            }
        ),
        components_by_locale,
        graph_mappings,
    )


def resolve_builder_config(
    selections: BuilderSelections,
    *,
    registry: Registry | None = None,
    base_config: Mapping[str, Mapping[str, CanonicalValue]] | None = None,
    base_revision: str | None = None,
    capability_schema_version: int = CAPABILITY_SCHEMA_VERSION,
    capability_graph: CapabilityGraph | None = None,
) -> ResolvedBuilderConfig:
    """Resolve one supported selection into canonical bytes without file writes."""

    if capability_schema_version not in {
        HISTORICAL_CAPABILITY_SCHEMA_VERSION,
        CAPABILITY_SCHEMA_VERSION,
    }:
        raise BuilderConstraintError(
            "capability_schema_version",
            "unsupported_builder_schema",
            "Unsupported capability schema version.",
        )
    if (
        capability_schema_version == HISTORICAL_CAPABILITY_SCHEMA_VERSION
        and selections.locale != "continental-us"
    ):
        raise BuilderConstraintError(
            "locale", "unsupported_combination", "Schema v2 is Continental-US only."
        )
    if capability_graph is not None:
        if capability_graph.schema_version != capability_schema_version:
            raise BuilderConstraintError(
                "capability_schema_version",
                "unsupported_builder_schema",
                "Stored capability graph version does not match the requested resolver version.",
            )
        if capability_graph.locale_profiles != (selections.locale,):
            raise BuilderConstraintError(
                "locale",
                "unsupported_combination",
                "Stored capability graph does not authorize the selected locale.",
            )
    resolved_registry = load_registry() if registry is None else registry
    if base_config is None:
        defaults_bytes = _DEFAULTS_PATH.read_bytes()
        config = parse_config_text(defaults_bytes.decode("utf-8"))
        resolved_base_revision = sha256(defaults_bytes).hexdigest()
    else:
        config = deepcopy({section: dict(options) for section, options in base_config.items()})
        resolved_base_revision = base_revision or "caller-supplied"
    effective_writers: dict[ConfigKey, str] = {
        (section, option): "shared-defaults"
        for section, options in config.items()
        for option in options
    }
    chain = _selection_chain(
        resolved_registry,
        selections,
        capability_schema_version=capability_schema_version,
        capability_graph=capability_graph,
    )
    for component in chain:
        if (
            (
                capability_schema_version == HISTORICAL_CAPABILITY_SCHEMA_VERSION
                or capability_graph is not None
            )
            and component.kind is ComponentKind.CAPABILITY
        ):
            continue
        for write in component.writes:
            section = config.setdefault(write.section, {})
            if write.option in section and write.key not in component.overrides:
                raise BuilderConstraintError(
                    f"{write.section}.{write.option}",
                    "undeclared_writeover",
                    f"{component.component_id!r} does not declare override of {write.section}.{write.option}",
                )
            section[write.option] = _mutable_value(write.value)
            effective_writers[write.key] = component.component_id

    graph = capability_graph or (
        _historical_capability_graph_for_registry(resolved_registry)
        if capability_schema_version == HISTORICAL_CAPABILITY_SCHEMA_VERSION
        else _capability_graph_for_registry(resolved_registry, selections.locale)
    )
    if (
        capability_schema_version == HISTORICAL_CAPABILITY_SCHEMA_VERSION
        or capability_graph is not None
    ):
        for section_name, options in graph.as_config_sections().items():
            config[section_name] = deepcopy(options)
            for option_name in options:
                effective_writers[(section_name, option_name)] = selections.capability_profile
    else:
        for section_name in graph.as_config_sections():
            config.setdefault(section_name, {})

    dem = next(item for item in chain if item.kind is ComponentKind.DEM)
    if dem.default_cellsize not in ALLOWED_CELL_SIZES:
        raise BuilderConstraintError("dem", "invalid_dem_default", "DEM default cell size is not allowlisted")
    effective_cellsize = dem.default_cellsize
    cellsize_source = "dem_default"
    if selections.cellsize_override is not None:
        if selections.cellsize_override not in ALLOWED_CELL_SIZES:
            raise BuilderConstraintError(
                "cellsize_override",
                "invalid_cellsize",
                f"Cell size must be one of {ALLOWED_CELL_SIZES}",
            )
        effective_cellsize = selections.cellsize_override
        if effective_cellsize != dem.default_cellsize:
            cellsize_source = "privileged_override"

    explicit_writes: tuple[tuple[ConfigKey, CanonicalValue, str], ...] = (
        (("config", "flattened"), True, "resolver-v1"),
        (("config", "resolver_version"), 1, "resolver-v1"),
        (("config", "schema_version"), 1, "resolver-v1"),
        (("general", "cellsize"), effective_cellsize, "selection:cellsize"),
        (("nodb", "mods"), list(selections.mods), "selection:mods"),
        (("capability_defaults", "locale_profile"), selections.locale, "selection:locale"),
        (("capability_defaults", "dem_source"), selections.dem, "selection:dem"),
        (("capability_defaults", "climate_dataset"), selections.climate, "selection:climate"),
        (("capability_defaults", "soil_dataset"), selections.soil, "selection:soil"),
        (("capability_defaults", "landuse_dataset"), selections.landuse, "selection:landuse"),
        (("capability_defaults", "delineation_backend"), selections.delineation_backend, "selection:delineation"),
        (("capability_defaults", "watershed_representation"), selections.watershed_representation, "selection:representation"),
        (("capability_defaults", "wepp_binary"), selections.wepp_binary, "selection:wepp_binary"),
    )
    if capability_schema_version == CAPABILITY_SCHEMA_VERSION:
        explicit_writes += ((
            ("capability_defaults", "climate_station_database"),
            selections.climate_station_database,
            "selection:climate_station_database",
        ),)
    for (section_name, option_name), value, writer in explicit_writes:
        config.setdefault(section_name, {})[option_name] = deepcopy(value)
        effective_writers[(section_name, option_name)] = writer

    config_bytes = serialize_config(config)
    parent_chain = (
        ConfigProvenance("defaults", "shared-defaults", resolved_base_revision),
        *(
            ConfigProvenance(item.kind.value, item.component_id, item.source_revision)
            for item in chain
        ),
    )
    return ResolvedBuilderConfig(
        registry_revision=resolved_registry.revision,
        selections=selections,
        config=_freeze_config(config),
        config_bytes=config_bytes,
        parent_chain=parent_chain,
        effective_writers=MappingProxyType(dict(effective_writers)),
        dem_default_cellsize=dem.default_cellsize,
        effective_cellsize=effective_cellsize,
        cellsize_source=cellsize_source,
    )
