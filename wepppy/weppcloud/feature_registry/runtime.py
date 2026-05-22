from __future__ import annotations

import configparser
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml

from .schema import (
    ConfigOverrideRule,
    ConfigSpec,
    FeatureRegistryValidationError,
    FeatureSpec,
    validate_config_registry_payload,
    validate_feature_registry_payload,
)

_REGISTRY_DIR = Path(__file__).resolve().parent
_FEATURE_REGISTRY_PATH = _REGISTRY_DIR / "feature_registry.yaml"
_CONFIG_REGISTRY_PATH = _REGISTRY_DIR / "config_registry.yaml"

_ROLE_RANK = {
    "user": 0,
    "poweruser": 1,
    "dev": 2,
    "admin": 2,
    "root": 3,
}


def _repository_root() -> Path:
    return _REGISTRY_DIR.parents[2]


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FeatureRegistryValidationError(f"Missing registry file: {path}")
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise FeatureRegistryValidationError(f"Failed to load registry YAML from {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise FeatureRegistryValidationError(f"Registry file must parse to a mapping: {path}")
    return loaded


def _config_path_for_entry(cfg_path: str) -> Path:
    return _repository_root() / cfg_path


def _load_cfg_parser(cfg_path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    with cfg_path.open(encoding="utf-8") as fp:
        parser.read_file(fp)
    return parser


def _read_cfg_bool_option(
    parser: configparser.ConfigParser,
    section: str,
    option: str,
    *,
    cfg_path: str,
) -> bool | None:
    try:
        token = parser.get(section, option)
    except (configparser.NoSectionError, configparser.NoOptionError):
        return None

    normalized = token.strip().lower()
    if normalized in {"", "none", "null"}:
        return None
    bool_states = configparser.ConfigParser.BOOLEAN_STATES
    if normalized in bool_states:
        return bool(bool_states[normalized])
    raise FeatureRegistryValidationError(
        f"Invalid boolean token in {cfg_path} [{section}] {option}: {token!r}"
    )


def _apply_config_attribute_overrides(
    entry: ConfigSpec, *, overrides: tuple[ConfigOverrideRule, ...]
) -> ConfigSpec:
    if not overrides:
        return entry

    cfg_abs_path = _config_path_for_entry(entry.cfg_path)
    try:
        parser = _load_cfg_parser(cfg_abs_path)
    except (OSError, configparser.Error) as exc:
        raise FeatureRegistryValidationError(
            f"Failed to read config override attributes from {entry.cfg_path}: {exc}"
        ) from exc

    effective = entry
    for rule in overrides:
        match_value = _read_cfg_bool_option(
            parser,
            rule.match_cfg_section,
            rule.match_cfg_option,
            cfg_path=entry.cfg_path,
        )
        if match_value is not rule.match_cfg_bool:
            continue
        effective = replace(
            effective,
            maturity=rule.set_maturity,
            internal_reason=rule.set_internal_reason,
            embargo_until=rule.set_embargo_until,
        )

    return effective


@lru_cache(maxsize=1)
def load_feature_registry() -> tuple[FeatureSpec, ...]:
    payload = _load_yaml_mapping(_FEATURE_REGISTRY_PATH)
    return validate_feature_registry_payload(payload, registry_dir=_REGISTRY_DIR)


@lru_cache(maxsize=1)
def load_config_registry() -> tuple[ConfigSpec, ...]:
    payload = _load_yaml_mapping(_CONFIG_REGISTRY_PATH)
    spec = validate_config_registry_payload(payload, registry_dir=_REGISTRY_DIR)
    return tuple(
        _apply_config_attribute_overrides(entry, overrides=spec.overrides)
        for entry in spec.configs
    )


@lru_cache(maxsize=1)
def feature_registry_by_id() -> Mapping[str, FeatureSpec]:
    return MappingProxyType({entry.id: entry for entry in load_feature_registry()})


@lru_cache(maxsize=1)
def config_registry_by_id() -> Mapping[str, ConfigSpec]:
    return MappingProxyType({entry.id: entry for entry in load_config_registry()})


def feature_maturity_badge(entry: FeatureSpec) -> str:
    return entry.maturity.capitalize()


def config_maturity_badge(entry: ConfigSpec) -> str:
    return entry.maturity.capitalize()


def user_effective_role(user: object) -> str:
    has_role = getattr(user, "has_role", None)
    if not callable(has_role):
        return "user"
    if has_role("Root"):
        return "root"
    if has_role("Admin"):
        return "admin"
    if has_role("Dev"):
        return "dev"
    if has_role("PowerUser"):
        return "poweruser"
    return "user"


def user_meets_min_role(user: object, min_role: str) -> bool:
    has_role = getattr(user, "has_role", None)
    if not callable(has_role):
        return min_role == "user"

    if min_role == "user":
        return True
    if min_role == "poweruser":
        return (
            has_role("PowerUser")
            or has_role("Admin")
            or has_role("Dev")
            or has_role("Root")
        )
    if min_role == "dev":
        return has_role("Dev") or has_role("Root")
    if min_role == "admin":
        return has_role("Admin") or has_role("Root")
    if min_role == "root":
        return has_role("Root")
    return False


def backend_matches_requirement(required_backend: str, *, is_wbt: bool) -> bool:
    if required_backend == "any":
        return True
    if required_backend == "wbt":
        return bool(is_wbt)
    if required_backend == "topaz":
        return not bool(is_wbt)
    return False


def build_header_mod_options(
    *,
    active_mods: set[str],
    user: object,
    is_wbt: bool,
    include_all: bool = False,
) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for entry in load_feature_registry():
        if include_all:
            visible = True
        else:
            visible = (
                user_meets_min_role(user, entry.min_role)
                and backend_matches_requirement(entry.requires_backend, is_wbt=is_wbt)
                and set(entry.requires_features).issubset(active_mods)
            )
        if not visible:
            continue

        options.append(
            {
                "id": entry.id,
                "label": entry.label,
                "maturity": entry.maturity,
                "maturity_badge": feature_maturity_badge(entry),
                "min_role": entry.min_role,
            }
        )
    return options


def invalidate_registry_caches() -> None:
    load_feature_registry.cache_clear()
    load_config_registry.cache_clear()
    feature_registry_by_id.cache_clear()
    config_registry_by_id.cache_clear()
