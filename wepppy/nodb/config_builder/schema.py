"""Immutable data contracts for project configuration components."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping, TypeAlias

from wepppy.project_config_serialization import CanonicalScalar, CanonicalValue

__all__ = [
    "BuilderDescription",
    "BuilderSelections",
    "ComponentDefinition",
    "ComponentKind",
    "ComponentSummary",
    "ConfigKey",
    "ConfigProvenance",
    "ConfigWrite",
    "ConstraintSet",
    "Registry",
    "RegistryValue",
    "ResolvedBuilderConfig",
]

ConfigKey: TypeAlias = tuple[str, str]
RegistryValue: TypeAlias = CanonicalScalar | tuple[CanonicalScalar, ...]


class ComponentKind(str, Enum):
    LOCALE = "locale"
    DEM = "dem"
    DELINEATION = "delineation"
    REPRESENTATION = "representation"
    WEPP_BINARY = "wepp_binary"
    MOD = "mod"
    SOIL = "soil"
    LANDUSE = "landuse"
    CLIMATE = "climate"
    CAPABILITY = "capability"


@dataclass(frozen=True, slots=True)
class ConfigWrite:
    section: str
    option: str
    value: RegistryValue

    @property
    def key(self) -> ConfigKey:
        return self.section, self.option


@dataclass(frozen=True, slots=True)
class ConstraintSet:
    requires: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    allowed_dem: tuple[str, ...] = ()
    allowed_delineation: tuple[str, ...] = ()
    allowed_representation: tuple[str, ...] = ()
    allowed_wepp_binary: tuple[str, ...] = ()
    allowed_soil: tuple[str, ...] = ()
    allowed_landuse: tuple[str, ...] = ()
    allowed_climate: tuple[str, ...] = ()
    allowed_mods: tuple[str, ...] = ()
    allowed_capability_profiles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ComponentDefinition:
    component_id: str
    kind: ComponentKind
    schema_version: int
    source_revision: str
    label: str
    description: str
    owns: tuple[ConfigKey, ...]
    overrides: tuple[ConfigKey, ...]
    writes: tuple[ConfigWrite, ...]
    constraints: ConstraintSet
    default_cellsize: int | None = None
    source_path: str = ""


@dataclass(frozen=True, slots=True)
class Registry:
    revision: str
    components: Mapping[str, ComponentDefinition]

    @classmethod
    def create(
        cls,
        revision: str,
        components: Mapping[str, ComponentDefinition],
    ) -> "Registry":
        return cls(revision, MappingProxyType(dict(components)))

    def get(self, component_id: str) -> ComponentDefinition:
        try:
            return self.components[component_id]
        except KeyError as exc:
            raise KeyError(f"Unknown component ID: {component_id}") from exc

    def by_kind(self, kind: ComponentKind) -> tuple[ComponentDefinition, ...]:
        return tuple(
            sorted(
                (item for item in self.components.values() if item.kind is kind),
                key=lambda item: item.component_id,
            )
        )


@dataclass(frozen=True, slots=True)
class BuilderSelections:
    locale: str
    dem: str
    delineation_backend: str
    watershed_representation: str
    wepp_binary: str
    soil: str
    landuse: str
    climate: str
    mods: tuple[str, ...] = ()
    capability_profile: str = "continental-us-capabilities"
    cellsize_override: int | None = None


@dataclass(frozen=True, slots=True)
class ConfigProvenance:
    kind: str
    component_id: str
    revision: str


@dataclass(frozen=True, slots=True)
class ComponentSummary:
    component_id: str
    kind: str
    label: str
    description: str
    default_cellsize: int | None = None
    constraints: ConstraintSet = ConstraintSet()


@dataclass(frozen=True, slots=True)
class BuilderDescription:
    schema_version: int
    registry_revision: str
    components: tuple[ComponentSummary, ...]
    allowed_cell_sizes: tuple[int, ...]
    default_selections: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class ResolvedBuilderConfig:
    registry_revision: str
    selections: BuilderSelections
    config: Mapping[str, Mapping[str, CanonicalValue]]
    config_bytes: bytes
    parent_chain: tuple[ConfigProvenance, ...]
    effective_writers: Mapping[ConfigKey, str]
    dem_default_cellsize: int
    effective_cellsize: int
    cellsize_source: str
