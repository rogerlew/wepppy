"""Stable capability IDs shared by flattened-config presentation and validation."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping, Protocol

from wepppy.nodb.locales import available_climate_datasets, available_landuse_datasets
from wepppy.project_config_serialization import CanonicalValue

__all__ = ["CapabilityConfig", "SOIL_BUILDER_MODES", "capability_ids", "resolve_named_preset_capabilities", "runtime_value_allowed", "soil_capability_modes"]


class CapabilityConfig(Protocol):
    def config_get_list(self, section: str, option: str, default: object = ...) -> object: ...
    def config_get_raw(self, section: str, option: str, default: object = ...) -> object: ...


SOIL_BUILDER_MODES: Mapping[str, int] = MappingProxyType(
    {"gridded": 0, "single_mukey": 1, "single_database": 2}
)


def capability_ids(config: CapabilityConfig, option: str) -> frozenset[str] | None:
    raw_getter = getattr(config, "config_get_raw", None)
    if raw_getter is None or raw_getter("capabilities", option, None) is None:
        return None
    raw = config.config_get_list("capabilities", option, None)
    if raw in (None, []):
        raise ValueError(f"capabilities.{option} must not be empty")
    if not isinstance(raw, (list, tuple)) or not all(isinstance(item, str) and item.strip() for item in raw):
        raise ValueError(f"capabilities.{option} must be a non-empty string list")
    return frozenset(item.strip() for item in raw)


def runtime_value_allowed(config: CapabilityConfig, option: str, value: object, *, stable_to_runtime: Mapping[str, object] | None = None) -> bool:
    allowed = capability_ids(config, option)
    if allowed is None:
        return True
    if stable_to_runtime is None:
        return str(value) in allowed
    return any(stable_to_runtime[item] == value for item in allowed if item in stable_to_runtime)


def soil_capability_modes(config: CapabilityConfig) -> frozenset[int] | None:
    allowed = capability_ids(config, "soil_builders")
    if allowed is None:
        return None
    return frozenset(SOIL_BUILDER_MODES[item] for item in allowed if item in SOIL_BUILDER_MODES)


def resolve_named_preset_capabilities(config: Mapping[str, Mapping[str, CanonicalValue]]) -> dict[str, CanonicalValue]:
    locales_raw = config.get("general", {}).get("locales", [])
    locales = tuple(str(item) for item in locales_raw) if isinstance(locales_raw, list) else ()
    mods = tuple(config)
    climate_ids = [item.catalog_id for item in available_climate_datasets(locales, mods)]
    landuse_ids = [item.key for item in available_landuse_datasets(None, mods, locales) if item.kind == "landcover"]
    current_landuse = config.get("landuse", {}).get("nlcd_db")
    if isinstance(current_landuse, str) and current_landuse not in landuse_ids:
        landuse_ids.append(current_landuse)
    return {"climate_datasets": climate_ids, "soil_builders": list(SOIL_BUILDER_MODES), "landuse_datasets": landuse_ids}
