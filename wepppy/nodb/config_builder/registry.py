"""Strict TOML loader for project configuration component definitions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import re
import tomllib

from wepppy.nodb.config_builder.schema import (
    ComponentDefinition,
    ComponentKind,
    ConfigKey,
    ConfigWrite,
    ConstraintSet,
    Registry,
    RegistryValue,
)
from wepppy.project_config_serialization import CanonicalScalar
from wepp_runner.wepp_runner import (
    get_linux_wepp_bin_opts,
    get_linux_wepp_bin_role_paths,
)

__all__ = ["DEFAULT_PROFILES_ROOT", "RegistryError", "load_registry"]

DEFAULT_PROFILES_ROOT = Path(__file__).with_name("profiles")
_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*$")
_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_CONSTRAINT_FIELDS = (
    "requires",
    "conflicts",
    "allowed_dem",
    "allowed_delineation",
    "allowed_representation",
    "allowed_wepp_binary",
    "allowed_soil",
    "allowed_landuse",
    "allowed_climate",
    "allowed_mods",
    "allowed_capability_profiles",
)
_ALLOWED_ROOT_FIELDS = frozenset(
    {
        "schema_version",
        "id",
        "kind",
        "source_revision",
        "label",
        "description",
        "owns",
        "overrides",
        "default_cellsize",
        "constraints",
        "writes",
    }
)
_DEFAULT_WEPP_BINARY = "wepp_260803"
_EXECUTABLE_DIGEST_CACHE: dict[tuple[str, int, int, int, int], str] = {}


class RegistryError(ValueError):
    """Raised when registry sources violate schema or reference contracts."""


def _string(value: object, field: str, source: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(f"{source}: {field} must be a non-empty string")
    return value


def _string_tuple(value: object, field: str, source: Path) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RegistryError(f"{source}: {field} must be an array of strings")
    items = tuple(value)
    if len(set(items)) != len(items):
        raise RegistryError(f"{source}: {field} contains duplicates")
    return items


def _config_key(raw: str, field: str, source: Path) -> ConfigKey:
    if "." not in raw:
        raise RegistryError(f"{source}: {field} key {raw!r} must be section.option")
    section, option = raw.rsplit(".", 1)
    if not section or not option or not _NAME_RE.fullmatch(section) or not _NAME_RE.fullmatch(option):
        raise RegistryError(f"{source}: invalid config key {raw!r}")
    return section, option


def _registry_scalar(value: object, field: str, source: Path) -> CanonicalScalar:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            raise RegistryError(f"{source}: {field} contains a non-finite float")
        return value
    raise RegistryError(f"{source}: {field} has unsupported value type")


def _registry_value(value: object, field: str, source: Path) -> RegistryValue:
    if isinstance(value, list):
        return tuple(
            _registry_scalar(item, f"{field}[]", source)
            for item in value
        )
    return _registry_scalar(value, field, source)


def _parse_constraints(payload: object, source: Path) -> ConstraintSet:
    if not isinstance(payload, dict):
        raise RegistryError(f"{source}: constraints table is required")
    unknown = set(payload) - set(_CONSTRAINT_FIELDS)
    if unknown:
        raise RegistryError(f"{source}: unknown constraint fields: {sorted(unknown)}")
    values = {
        field: _string_tuple(payload.get(field, []), f"constraints.{field}", source)
        for field in _CONSTRAINT_FIELDS
    }
    return ConstraintSet(**values)


def _parse_document(source: Path, root: Path) -> ComponentDefinition:
    try:
        payload = tomllib.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise RegistryError(f"{source}: unable to parse TOML") from exc
    if not isinstance(payload, dict):
        raise RegistryError(f"{source}: document root must be a table")
    unknown = set(payload) - _ALLOWED_ROOT_FIELDS
    if unknown:
        raise RegistryError(f"{source}: unknown fields: {sorted(unknown)}")
    if payload.get("schema_version") != 1:
        raise RegistryError(f"{source}: unsupported registry schema version")
    component_id = _string(payload.get("id"), "id", source)
    if _ID_RE.fullmatch(component_id) is None:
        raise RegistryError(f"{source}: invalid stable component ID {component_id!r}")
    try:
        kind = ComponentKind(_string(payload.get("kind"), "kind", source))
    except ValueError as exc:
        raise RegistryError(f"{source}: unknown component kind") from exc
    owns_raw = _string_tuple(payload.get("owns"), "owns", source)
    overrides_raw = _string_tuple(payload.get("overrides"), "overrides", source)
    owns = tuple(_config_key(item, "owns", source) for item in owns_raw)
    overrides = tuple(_config_key(item, "overrides", source) for item in overrides_raw)
    if len(set(owns)) != len(owns):
        raise RegistryError(f"{source}: owns contains duplicate config keys")
    if len(set(overrides)) != len(overrides):
        raise RegistryError(f"{source}: overrides contains duplicate config keys")
    if not set(overrides).issubset(owns):
        raise RegistryError(f"{source}: overrides must be a subset of owns")

    writes_payload = payload.get("writes")
    if not isinstance(writes_payload, list):
        raise RegistryError(f"{source}: writes must be an array of tables")
    writes: list[ConfigWrite] = []
    for index, item in enumerate(writes_payload):
        if not isinstance(item, dict) or set(item) != {"section", "option", "value"}:
            raise RegistryError(f"{source}: writes[{index}] has invalid fields")
        section = _string(item["section"], f"writes[{index}].section", source)
        option = _string(item["option"], f"writes[{index}].option", source)
        key = _config_key(f"{section}.{option}", f"writes[{index}]", source)
        writes.append(
            ConfigWrite(
                section,
                option,
                _registry_value(item["value"], f"writes[{index}].value", source),
            )
        )
        if key not in owns:
            raise RegistryError(f"{source}: write {section}.{option} is not declared in owns")
    write_keys = [item.key for item in writes]
    if len(set(write_keys)) != len(write_keys):
        raise RegistryError(f"{source}: duplicate component writes")

    default_cellsize = payload.get("default_cellsize")
    if default_cellsize is not None:
        if (
            kind is not ComponentKind.DEM
            or isinstance(default_cellsize, bool)
            or not isinstance(default_cellsize, int)
            or default_cellsize <= 0
        ):
            raise RegistryError(f"{source}: default_cellsize is valid only for DEM integers")
    elif kind is ComponentKind.DEM:
        raise RegistryError(f"{source}: DEM components require default_cellsize")
    return ComponentDefinition(
        component_id=component_id,
        kind=kind,
        schema_version=1,
        source_revision=_string(payload.get("source_revision"), "source_revision", source),
        label=_string(payload.get("label"), "label", source),
        description=_string(payload.get("description"), "description", source),
        owns=owns,
        overrides=overrides,
        writes=tuple(writes),
        constraints=_parse_constraints(payload.get("constraints"), source),
        default_cellsize=default_cellsize,
        source_path=source.relative_to(root).as_posix(),
    )


def _validate_reference(
    registry: Mapping[str, ComponentDefinition],
    source: ComponentDefinition,
    reference: str,
    expected_kind: ComponentKind | None = None,
) -> None:
    target = registry.get(reference)
    if target is None:
        raise RegistryError(f"{source.source_path}: unknown component reference {reference!r}")
    if expected_kind is not None and target.kind is not expected_kind:
        raise RegistryError(
            f"{source.source_path}: reference {reference!r} must be {expected_kind.value}"
        )


def _validate_references(components: Mapping[str, ComponentDefinition]) -> None:
    allowed_kinds = {
        "allowed_dem": ComponentKind.DEM,
        "allowed_delineation": ComponentKind.DELINEATION,
        "allowed_representation": ComponentKind.REPRESENTATION,
        "allowed_wepp_binary": ComponentKind.WEPP_BINARY,
        "allowed_soil": ComponentKind.SOIL,
        "allowed_landuse": ComponentKind.LANDUSE,
        "allowed_climate": ComponentKind.CLIMATE,
        "allowed_mods": ComponentKind.MOD,
        "allowed_capability_profiles": ComponentKind.CAPABILITY,
    }
    for component in components.values():
        for reference in component.constraints.requires + component.constraints.conflicts:
            _validate_reference(components, component, reference)
        for field, expected_kind in allowed_kinds.items():
            for reference in getattr(component.constraints, field):
                _validate_reference(components, component, reference, expected_kind)
        overlap = set(component.constraints.requires) & set(component.constraints.conflicts)
        if overlap:
            raise RegistryError(
                f"{component.source_path}: references cannot be both required and conflicting: {sorted(overlap)}"
            )


def _executable_sha256(path_text: str, binary_id: str, role: str) -> str:
    path = Path(path_text)
    if not path.is_file() or not os.access(path, os.R_OK | os.X_OK):
        raise RegistryError(
            f"WEPP binary provider value {binary_id!r} has unusable {role} executable {path}"
        )
    try:
        stat = path.stat()
        cache_key = (
            str(path.resolve()), stat.st_ino, stat.st_size, stat.st_mtime_ns,
            stat.st_ctime_ns,
        )
        cached = _EXECUTABLE_DIGEST_CACHE.get(cache_key)
        if cached is not None:
            return cached
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise RegistryError(
            f"WEPP binary provider value {binary_id!r} has unreadable {role} executable {path}"
        ) from exc
    identity = digest.hexdigest()
    _EXECUTABLE_DIGEST_CACHE[cache_key] = identity
    return identity


def _provider_wepp_components() -> tuple[ComponentDefinition, ...]:
    try:
        provider_values = get_linux_wepp_bin_opts()
    except (OSError, RuntimeError, ValueError) as exc:
        raise RegistryError("WEPP binary provider failed") from exc
    if not isinstance(provider_values, (list, tuple)):
        raise RegistryError("WEPP binary provider must return a list or tuple")

    binary_ids = tuple(dict.fromkeys(provider_values))
    if not binary_ids:
        raise RegistryError("WEPP binary provider returned no values")
    if _DEFAULT_WEPP_BINARY not in binary_ids:
        raise RegistryError(
            f"WEPP binary provider is missing required default {_DEFAULT_WEPP_BINARY!r}"
        )

    components: list[ComponentDefinition] = []
    for binary_id in binary_ids:
        if not isinstance(binary_id, str) or _ID_RE.fullmatch(binary_id) is None:
            raise RegistryError(f"WEPP binary provider returned invalid component ID {binary_id!r}")
        try:
            watershed_path, hillslope_path = get_linux_wepp_bin_role_paths(binary_id)
        except (OSError, RuntimeError, ValueError) as exc:
            raise RegistryError(
                f"WEPP binary provider value {binary_id!r} could not resolve executable roles"
            ) from exc
        watershed_digest = _executable_sha256(watershed_path, binary_id, "watershed")
        hillslope_digest = _executable_sha256(hillslope_path, binary_id, "hillslope")
        source_revision = (
            f"provider-v1:watershed={watershed_digest}:hillslope={hillslope_digest}"
        )
        components.append(
            ComponentDefinition(
                component_id=binary_id,
                kind=ComponentKind.WEPP_BINARY,
                schema_version=1,
                source_revision=source_revision,
                label=binary_id,
                description="WEPP binary supplied by the runtime binary provider.",
                owns=(("wepp", "bin"), ("capabilities", "wepp_binaries")),
                overrides=(("wepp", "bin"),),
                writes=(
                    ConfigWrite("wepp", "bin", binary_id),
                    ConfigWrite("capabilities", "wepp_binaries", binary_ids),
                ),
                constraints=ConstraintSet(requires=("continental-us",)),
                source_path=f"provider://wepp_binary/{binary_id}",
            )
        )
    return tuple(components)


def load_registry(root: str | Path = DEFAULT_PROFILES_ROOT) -> Registry:
    """Load and atomically validate every component document below ``root``."""

    profiles_root = Path(root)
    sources = sorted(profiles_root.rglob("*.toml"))
    if not sources:
        raise RegistryError(f"{profiles_root}: no component documents found")
    components: dict[str, ComponentDefinition] = {}
    folded_ids: dict[str, str] = {}
    digest = hashlib.sha256()
    for source in sources:
        relative = source.relative_to(profiles_root).as_posix()
        source_bytes = source.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source_bytes)
        digest.update(b"\0")
        component = _parse_document(source, profiles_root)
        folded = component.component_id.casefold()
        if folded in folded_ids:
            raise RegistryError(
                f"Duplicate or case-colliding component IDs: {folded_ids[folded]!r}, {component.component_id!r}"
            )
        components[component.component_id] = component
        folded_ids[folded] = component.component_id
    if "continental-us" not in components:
        _validate_references(components)
    provider_components = _provider_wepp_components()
    for component in provider_components:
        folded = component.component_id.casefold()
        if folded in folded_ids:
            raise RegistryError(
                f"Duplicate or case-colliding component IDs: {folded_ids[folded]!r}, "
                f"{component.component_id!r}"
            )
        components[component.component_id] = component
        folded_ids[folded] = component.component_id
        digest.update(component.component_id.encode("utf-8"))
        digest.update(b"\0")
        digest.update(component.source_revision.encode("ascii"))
        digest.update(b"\0")
    locale = components.get("continental-us")
    if locale is None or locale.kind is not ComponentKind.LOCALE:
        raise RegistryError("WEPP binary provider requires the continental-us locale")
    components[locale.component_id] = replace(
        locale,
        constraints=replace(
            locale.constraints,
            allowed_wepp_binary=tuple(item.component_id for item in provider_components),
        ),
    )
    _validate_references(components)
    return Registry.create(digest.hexdigest(), components)
