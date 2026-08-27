from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Self, TypeAlias
from wepppy.project_config_serialization import CanonicalScalar, CanonicalValue

__all__ = ["BuilderDescription", "BuilderSelections", "ComponentDefinition", "ComponentKind", "ComponentSummary", "ConfigKey", "ConfigProvenance", "ConfigWrite", "ConstraintSet", "Registry", "RegistryValue", "ResolvedBuilderConfig"]

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
    def __new__(cls, value: str) -> Self: ...

@dataclass(frozen=True, slots=True)
class ConfigWrite:
    section: str
    option: str
    value: RegistryValue
    def __init__(self, section: str, option: str, value: RegistryValue) -> None: ...
    @property
    def key(self) -> ConfigKey: ...

@dataclass(frozen=True, slots=True)
class ConstraintSet:
    requires: tuple[str, ...]
    conflicts: tuple[str, ...]
    allowed_dem: tuple[str, ...]
    allowed_delineation: tuple[str, ...]
    allowed_representation: tuple[str, ...]
    allowed_wepp_binary: tuple[str, ...]
    allowed_soil: tuple[str, ...]
    allowed_landuse: tuple[str, ...]
    allowed_climate: tuple[str, ...]
    allowed_mods: tuple[str, ...]
    allowed_capability_profiles: tuple[str, ...]
    def __init__(self, requires: tuple[str, ...] = ..., conflicts: tuple[str, ...] = ..., allowed_dem: tuple[str, ...] = ..., allowed_delineation: tuple[str, ...] = ..., allowed_representation: tuple[str, ...] = ..., allowed_wepp_binary: tuple[str, ...] = ..., allowed_soil: tuple[str, ...] = ..., allowed_landuse: tuple[str, ...] = ..., allowed_climate: tuple[str, ...] = ..., allowed_mods: tuple[str, ...] = ..., allowed_capability_profiles: tuple[str, ...] = ...) -> None: ...

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
    default_cellsize: int | None
    source_path: str
    profile_classification: str | None
    support_state: str | None
    runtime_tokens: tuple[str, ...]
    base_profile_id: str | None
    overlay_precedence: int | None
    def __init__(self, component_id: str, kind: ComponentKind, schema_version: int, source_revision: str, label: str, description: str, owns: tuple[ConfigKey, ...], overrides: tuple[ConfigKey, ...], writes: tuple[ConfigWrite, ...], constraints: ConstraintSet, default_cellsize: int | None = ..., source_path: str = ..., profile_classification: str | None = ..., support_state: str | None = ..., runtime_tokens: tuple[str, ...] = ..., base_profile_id: str | None = ..., overlay_precedence: int | None = ...) -> None: ...

@dataclass(frozen=True, slots=True)
class Registry:
    revision: str
    components: Mapping[str, ComponentDefinition]
    def __init__(self, revision: str, components: Mapping[str, ComponentDefinition]) -> None: ...
    @classmethod
    def create(cls, revision: str, components: Mapping[str, ComponentDefinition]) -> Registry: ...
    def get(self, component_id: str) -> ComponentDefinition: ...
    def by_kind(self, kind: ComponentKind) -> tuple[ComponentDefinition, ...]: ...

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
    mods: tuple[str, ...]
    capability_profile: str
    cellsize_override: int | None
    def __init__(self, locale: str, dem: str, delineation_backend: str, watershed_representation: str, wepp_binary: str, soil: str, landuse: str, climate: str, mods: tuple[str, ...] = ..., capability_profile: str = ..., cellsize_override: int | None = ...) -> None: ...

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
    default_cellsize: int | None
    constraints: ConstraintSet
    profile_classification: str | None
    support_state: str | None
    runtime_tokens: tuple[str, ...]
    base_profile_id: str | None
    overlay_precedence: int | None
    def __init__(self, component_id: str, kind: str, label: str, description: str, default_cellsize: int | None = ..., constraints: ConstraintSet = ..., profile_classification: str | None = ..., support_state: str | None = ..., runtime_tokens: tuple[str, ...] = ..., base_profile_id: str | None = ..., overlay_precedence: int | None = ...) -> None: ...

@dataclass(frozen=True, slots=True)
class BuilderDescription:
    schema_version: int
    registry_revision: str
    components: tuple[ComponentSummary, ...]
    allowed_cell_sizes: tuple[int, ...]
    default_selections: Mapping[str, str]
    capability_graph: Mapping[str, Mapping[str, CanonicalValue]]
    def __init__(self, schema_version: int, registry_revision: str, components: tuple[ComponentSummary, ...], allowed_cell_sizes: tuple[int, ...], default_selections: Mapping[str, str], capability_graph: Mapping[str, Mapping[str, CanonicalValue]]) -> None: ...

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
    def __init__(self, registry_revision: str, selections: BuilderSelections, config: Mapping[str, Mapping[str, CanonicalValue]], config_bytes: bytes, parent_chain: tuple[ConfigProvenance, ...], effective_writers: Mapping[ConfigKey, str], dem_default_cellsize: int, effective_cellsize: int, cellsize_source: str) -> None: ...
