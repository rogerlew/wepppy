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
from wepppy.project_config_serialization import (
    CanonicalValue,
    parse_config_text,
    serialize_config,
)

__all__ = [
    "ALLOWED_CELL_SIZES",
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
    ComponentKind.MOD: 4,
    ComponentKind.SOIL: 5,
    ComponentKind.LANDUSE: 6,
    ComponentKind.CLIMATE: 7,
    ComponentKind.CAPABILITY: 8,
}


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


def _selection_chain(registry: Registry, selections: BuilderSelections) -> tuple[ComponentDefinition, ...]:
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
    soil = _component(registry, selections.soil, ComponentKind.SOIL, "soil")
    landuse = _component(registry, selections.landuse, ComponentKind.LANDUSE, "landuse")
    climate = _component(registry, selections.climate, ComponentKind.CLIMATE, "climate")
    capability = _component(
        registry,
        selections.capability_profile,
        ComponentKind.CAPABILITY,
        "capability_profile",
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
    _require_allowed("soil", soil.component_id, constraints.allowed_soil)
    _require_allowed("landuse", landuse.component_id, constraints.allowed_landuse)
    _require_allowed("climate", climate.component_id, constraints.allowed_climate)
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
    selected = (locale, dem, delineation, representation, *mods, soil, landuse, climate, capability)
    selected_ids = {item.component_id for item in selected}
    for component in selected:
        missing = set(component.constraints.requires) - selected_ids
        conflicts = set(component.constraints.conflicts) & selected_ids
        if missing:
            raise BuilderConstraintError(
                component.kind.value,
                "missing_required_component",
                f"{component.component_id!r} requires {sorted(missing)}",
            )
        if conflicts:
            raise BuilderConstraintError(
                component.kind.value,
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
    summaries = tuple(
        ComponentSummary(
            item.component_id,
            item.kind.value,
            item.label,
            item.description,
            item.default_cellsize,
        )
        for item in sorted(
            resolved_registry.components.values(),
            key=lambda item: (_KIND_ORDER[item.kind], item.component_id),
        )
    )
    return BuilderDescription(1, resolved_registry.revision, summaries, ALLOWED_CELL_SIZES)


def resolve_builder_config(
    selections: BuilderSelections,
    *,
    registry: Registry | None = None,
    base_config: Mapping[str, Mapping[str, CanonicalValue]] | None = None,
    base_revision: str | None = None,
) -> ResolvedBuilderConfig:
    """Resolve one supported selection into canonical bytes without file writes."""

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
    chain = _selection_chain(resolved_registry, selections)
    for component in chain:
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
    )
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
