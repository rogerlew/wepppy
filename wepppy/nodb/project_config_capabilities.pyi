from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol, Self

from wepppy.nodb.config_builder.schema import Registry
from wepppy.nodb.locales.capability_graph import CapabilityGraph
from wepppy.project_config_serialization import CanonicalValue

__all__ = [
    "CapabilityConfig",
    "CapabilityAuthorityInvalidError",
    "LANDUSE_METHOD_MODES",
    "BuilderRegistryUnavailableError",
    "LocaleAuthorityInvalidError",
    "RunCapabilityAuthority",
    "RunCapabilityMode",
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
    "resolve_run_capability_authority",
    "runtime_value_allowed",
    "soil_capability_modes",
]

class CapabilityConfig(Protocol):
    def config_get_list(self, section: str, option: str, default: object = ...) -> object: ...
    def config_get_raw(self, section: str, option: str, default: object = ...) -> object: ...

class RunCapabilityMode(str, Enum):
    STORED = "stored"
    LEGACY_BUILDER = "legacy_builder"
    COMPATIBILITY = "compatibility"
    def __new__(cls, value: str) -> Self: ...

@dataclass(frozen=True, slots=True)
class RunCapabilityAuthority:
    mode: RunCapabilityMode
    graph: CapabilityGraph | None
    runtime_tokens: tuple[str, ...]
    locale_profile: str | None

class LocaleAuthorityInvalidError(ValueError): ...
class BuilderRegistryUnavailableError(RuntimeError): ...
class CapabilityAuthorityInvalidError(ValueError): ...

LANDUSE_METHOD_MODES: Mapping[str, int]
SOIL_BUILDER_MODES: Mapping[str, int]

def capability_authority(config: CapabilityConfig) -> CapabilityGraph | None: ...
def capability_default(config: CapabilityConfig, option: str) -> str | None: ...
def capability_ids(config: CapabilityConfig, option: str) -> frozenset[str] | None: ...
def climate_spatial_capability_modes(config: CapabilityConfig, climate_dataset: str) -> frozenset[int] | None: ...
def climate_station_capability_modes(config: CapabilityConfig, climate_dataset: str) -> frozenset[int] | None: ...
def landuse_capability_modes(config: CapabilityConfig, landuse_dataset: str, watershed_representation: str) -> frozenset[int] | None: ...
def landuse_runtime_dataset_allowed(config: CapabilityConfig, runtime_value: str) -> bool: ...
def model_tuple_allowed(config: CapabilityConfig, delineation_backend: str, watershed_representation: str, wepp_binary: str) -> bool: ...
def model_tuple_binaries(config: CapabilityConfig, delineation_backend: str, watershed_representation: str) -> tuple[str, ...] | None: ...
def resolve_landuse_runtime_dataset(config: CapabilityConfig, submitted_value: str) -> str | None: ...
def resolve_named_preset_capabilities(config: Mapping[str, Mapping[str, CanonicalValue]]) -> dict[str, CanonicalValue]: ...
def resolve_run_capability_authority(config: CapabilityConfig, *, registry: Registry | None = ...) -> RunCapabilityAuthority: ...
def runtime_value_allowed(config: CapabilityConfig, option: str, value: object, *, stable_to_runtime: Mapping[str, object] | None = ...) -> bool: ...
def soil_capability_modes(config: CapabilityConfig, *, soil_dataset: str | None = ...) -> frozenset[int] | None: ...
