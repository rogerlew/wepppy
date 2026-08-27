"""Strict TOML loader for project configuration component definitions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
import hashlib
import json
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
from wepppy.nodb.locales.capability_graph import (
    CapabilityGraph,
    build_locale_capability_graph,
)
from wepppy.nodb.locales.climate_catalog import (
    CLIMATE_PROVIDER_ADAPTER_REVISION,
    CLIMATE_STATION_DATABASE_ADAPTER_REVISION,
    get_climate_dataset,
    get_climate_station_database,
)
from wepppy.nodb.locales.landuse_catalog import (
    LANDCOVER_PROVIDER_ADAPTER_REVISION,
    get_landcover_entry,
)
from wepppy.nodb.locales.locale_profiles import (
    DEM_SOURCE_RUNTIME,
    SOIL_SOURCE_RUNTIME,
    LocaleProfile,
    get_locale_profile,
    locale_catalog_revision,
)
from wepppy.project_config_serialization import CanonicalScalar
from wepp_runner.wepp_runner import (
    get_linux_wepp_bin_opts,
    get_linux_wepp_bin_role_paths,
)

__all__ = ["DEFAULT_PROFILES_ROOT", "RegistryError", "load_registry"]

DEFAULT_PROFILES_ROOT = Path(__file__).with_name("profiles")
_DEM_PROVIDER_ADAPTER_REVISION = "dem-database-adapter-v1"
_SOIL_PROVIDER_ADAPTER_REVISION = "soils-builder-runtime-map-v2"
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
    "allowed_climate_station_database",
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
        "profile_classification",
        "support_state",
        "runtime_tokens",
        "base_profile_id",
        "overlay_precedence",
        "constraints",
        "writes",
    }
)
_DEFAULT_WEPP_BINARY = "wepp_260803"
_BUILDER_PROFILE_IDS = (
    "continental-us",
    "europe",
    "canada",
    "australia",
    "global-earth",
)
_DEM_METADATA = {
    "usgs-ned1-2024": ("USGS NED 1 arc-second (2024)", 30),
    "usgs-ned13-2022": ("USGS NED 1/3 arc-second (2022)", 10),
    "europe-eudem-v1-1": ("EUDEM v1.1", 25),
    "copernicus-dem-30": ("Copernicus DEM 30 m", 30),
    "australia-srtm-1s": ("Australia SRTM 1 second", 30),
}
_SOIL_LABELS = {
    "ssurgo-gnatsgso-2025": "SSURGO/gNATSGO 2025",
    "esdac-europe": "ESDAC",
    "isric-global": "ISRIC global",
    "asris-australia": "ASRIS",
}
_LOCALE_VIEW = {
    "continental-us": ((40.0, -99.0), 3, True),
    "europe": ((50.0, 10.5), 4, False),
    "canada": ((40.0, -99.0), 3, False),
    "australia": ((-27.0, 133.5), 4, False),
    "global-earth": ((40.0, -99.0), 3, False),
}
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
    profile_classification = payload.get("profile_classification")
    support_state = payload.get("support_state")
    runtime_tokens_raw = payload.get("runtime_tokens", [])
    base_profile_id = payload.get("base_profile_id")
    overlay_precedence = payload.get("overlay_precedence")
    if kind is ComponentKind.LOCALE:
        profile_classification = _string(
            profile_classification, "profile_classification", source
        )
        support_state = _string(support_state, "support_state", source)
        runtime_tokens = _string_tuple(runtime_tokens_raw, "runtime_tokens", source)
        if not runtime_tokens:
            raise RegistryError(f"{source}: runtime_tokens must not be empty")
        if base_profile_id is not None:
            base_profile_id = _string(base_profile_id, "base_profile_id", source)
        if overlay_precedence is not None and (
            isinstance(overlay_precedence, bool) or not isinstance(overlay_precedence, int)
        ):
            raise RegistryError(f"{source}: overlay_precedence must be an integer")
    else:
        if any(
            value is not None and value != []
            for value in (
                profile_classification,
                support_state,
                payload.get("runtime_tokens"),
                base_profile_id,
                overlay_precedence,
            )
        ):
            raise RegistryError(f"{source}: locale profile fields are valid only for locale components")
        runtime_tokens = ()
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
        profile_classification=profile_classification,
        support_state=support_state,
        runtime_tokens=runtime_tokens,
        base_profile_id=base_profile_id,
        overlay_precedence=overlay_precedence,
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
                owns=(("wepp", "bin"),),
                overrides=(("wepp", "bin"),),
                writes=(
                    ConfigWrite("wepp", "bin", binary_id),
                ),
                constraints=ConstraintSet(),
                source_path=f"provider://wepp_binary/{binary_id}",
            )
        )
    return tuple(components)


def _component_revision(kind: str, component_id: str, runtime_value: object) -> str:
    payload = json.dumps(
        {"kind": kind, "id": component_id, "runtime": runtime_value},
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"provider-v1:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def _builder_profiles() -> tuple[LocaleProfile, ...]:
    profiles = []
    for profile_id in _BUILDER_PROFILE_IDS:
        profile = get_locale_profile(profile_id)
        if profile is None or profile.support_state.value != "builder_exposed":
            raise RegistryError(f"canonical Builder locale {profile_id!r} is unavailable")
        profiles.append(profile)
    return tuple(profiles)


def _synthesized_builder_components(
    provider_components: tuple[ComponentDefinition, ...],
) -> tuple[dict[str, ComponentDefinition], dict[str, CapabilityGraph]]:
    profiles = _builder_profiles()
    binary_ids = tuple(item.component_id for item in provider_components)
    binary_revisions = {
        item.component_id: item.source_revision for item in provider_components
    }
    graphs = {
        profile.profile_id: build_locale_capability_graph(
            profile.profile_id, binary_ids, binary_revisions
        )
        for profile in profiles
    }
    components: dict[str, ComponentDefinition] = {}

    for profile in profiles:
        center, zoom, is_english = _LOCALE_VIEW[profile.profile_id]
        writes = (
            ConfigWrite("general", "locales", (profile.runtime_token,)),
            ConfigWrite("map", "center0", center),
            ConfigWrite("map", "zoom0", zoom),
            ConfigWrite("unitizer", "is_english", is_english),
        )
        components[profile.profile_id] = ComponentDefinition(
            component_id=profile.profile_id,
            kind=ComponentKind.LOCALE,
            schema_version=1,
            source_revision=f"locale-profile-{profile.source_revision}",
            label=profile.label,
            description=f"Authoritative Config Builder profile for {profile.label}.",
            owns=tuple(write.key for write in writes),
            overrides=(("unitizer", "is_english"),),
            writes=writes,
            constraints=ConstraintSet(
                allowed_dem=profile.dem_sources,
                allowed_delineation=("topaz", "wbt"),
                allowed_representation=("single-ofe", "multiple-ofe"),
                allowed_wepp_binary=binary_ids,
                allowed_soil=profile.soil_sources,
                allowed_landuse=profile.landuse_sources,
                allowed_climate=profile.climate_sources,
                allowed_climate_station_database=profile.climate_station_databases,
                allowed_capability_profiles=(f"{profile.profile_id}-capabilities",),
            ),
            source_path=f"provider://locale/{profile.profile_id}",
            profile_classification=profile.classification.value,
            support_state=profile.support_state.value,
            runtime_tokens=(profile.runtime_token,),
            base_profile_id=profile.base_profile_id,
            overlay_precedence=profile.overlay_precedence,
        )

    dem_ids = tuple(dict.fromkeys(
        source for profile in profiles for source in profile.dem_sources
    ))
    for component_id in dem_ids:
        label, cellsize = _DEM_METADATA[component_id]
        runtime_value = DEM_SOURCE_RUNTIME[component_id]
        components[component_id] = ComponentDefinition(
            component_id=component_id,
            kind=ComponentKind.DEM,
            schema_version=1,
            source_revision=_component_revision(
                "dem", component_id, (runtime_value, _DEM_PROVIDER_ADAPTER_REVISION)
            ),
            label=label,
            description=f"Terrain source {label}.",
            owns=(("general", "dem_db"),),
            overrides=(("general", "dem_db"),),
            writes=(ConfigWrite("general", "dem_db", runtime_value),),
            constraints=ConstraintSet(),
            default_cellsize=cellsize,
            source_path=f"provider://dem/{component_id}",
        )

    soil_ids = tuple(dict.fromkeys(
        source for profile in profiles for source in profile.soil_sources
    ))
    for component_id in soil_ids:
        runtime_value = SOIL_SOURCE_RUNTIME[component_id]
        writes = (ConfigWrite("soils", "ssurgo_db", runtime_value),)
        components[component_id] = ComponentDefinition(
            component_id=component_id,
            kind=ComponentKind.SOIL,
            schema_version=1,
            source_revision=_component_revision(
                "soil", component_id, (runtime_value, _SOIL_PROVIDER_ADAPTER_REVISION)
            ),
            label=_SOIL_LABELS[component_id],
            description=f"Soil source {_SOIL_LABELS[component_id]}.",
            owns=tuple(write.key for write in writes),
            overrides=tuple(write.key for write in writes),
            writes=writes,
            constraints=ConstraintSet(),
            source_path=f"provider://soil/{component_id}",
        )

    landuse_ids = tuple(dict.fromkeys(
        source for profile in profiles for source in profile.landuse_sources
    ))
    for component_id in landuse_ids:
        entry = get_landcover_entry(component_id)
        if entry is None:
            raise RegistryError(f"land-cover provider {component_id!r} is unavailable")
        writes_list = [ConfigWrite("landuse", "enable_landuse_change", True)]
        writes_list.insert(0, ConfigWrite("landuse", "nlcd_db", entry.runtime_value))
        if component_id.startswith("c3s-landcover-"):
            writes_list.append(ConfigWrite("landuse", "mapping", "c3s-disturbed"))
        writes = tuple(writes_list)
        components[component_id] = ComponentDefinition(
            component_id=component_id,
            kind=ComponentKind.LANDUSE,
            schema_version=1,
            source_revision=_component_revision(
                "landuse",
                component_id,
                (
                    entry.runtime_value,
                    entry.support_state,
                    LANDCOVER_PROVIDER_ADAPTER_REVISION,
                ),
            ),
            label=entry.label,
            description=f"Land-cover source {entry.label}.",
            owns=tuple(write.key for write in writes),
            overrides=tuple(write.key for write in writes),
            writes=writes,
            constraints=ConstraintSet(),
            source_path=f"provider://landuse/{component_id}",
        )

    climate_ids = tuple(dict.fromkeys(
        source for profile in profiles for source in profile.climate_sources
    ))
    for component_id in climate_ids:
        dataset = get_climate_dataset(component_id)
        if dataset is None:
            raise RegistryError(f"climate provider {component_id!r} is unavailable")
        components[component_id] = ComponentDefinition(
            component_id=component_id,
            kind=ComponentKind.CLIMATE,
            schema_version=1,
            source_revision=_component_revision(
                "climate",
                component_id,
                (dataset.to_mapping(), CLIMATE_PROVIDER_ADAPTER_REVISION),
            ),
            label=dataset.label,
            description=dataset.description,
            owns=(),
            overrides=(),
            writes=(),
            constraints=ConstraintSet(),
            source_path=f"provider://climate/{component_id}",
        )

    station_ids = tuple(dict.fromkeys(
        source for profile in profiles for source in profile.climate_station_databases
    ))
    for component_id in station_ids:
        database = get_climate_station_database(component_id)
        if database is None:
            raise RegistryError(f"station database provider {component_id!r} is unavailable")
        components[component_id] = ComponentDefinition(
            component_id=component_id,
            kind=ComponentKind.CLIMATE_STATION_DATABASE,
            schema_version=1,
            source_revision=_component_revision(
                "climate_station_database",
                component_id,
                (database.selector, CLIMATE_STATION_DATABASE_ADAPTER_REVISION),
            ),
            label=database.label,
            description=f"CLIGEN {database.label} station database.",
            owns=(("climate", "cligen_db"),),
            overrides=(("climate", "cligen_db"),),
            writes=(ConfigWrite("climate", "cligen_db", database.selector),),
            constraints=ConstraintSet(),
            source_path=f"provider://climate_station_database/{component_id}",
        )

    for profile in profiles:
        graph = graphs[profile.profile_id]
        graph_writes = tuple(
            ConfigWrite(
                section,
                option,
                _registry_value(value, f"{section}.{option}", DEFAULT_PROFILES_ROOT),
            )
            for section, options in graph.as_config_sections().items()
            for option, value in options.items()
        )
        component_id = f"{profile.profile_id}-capabilities"
        components[component_id] = ComponentDefinition(
            component_id=component_id,
            kind=ComponentKind.CAPABILITY,
            schema_version=1,
            source_revision=f"provider-v3:{graph.provider_revision}",
            label=f"{profile.label} capabilities",
            description=f"Resolved capability graph for {profile.label} projects.",
            owns=tuple(write.key for write in graph_writes),
            overrides=(),
            writes=graph_writes,
            constraints=ConstraintSet(requires=(profile.profile_id,)),
            source_path=f"provider://capability/{component_id}",
        )
    return components, graphs


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
    if "continental-us" not in components:
        raise RegistryError("WEPP binary provider requires the Builder profile registry")

    synthesized, graphs = _synthesized_builder_components(provider_components)
    for component_id, component in synthesized.items():
        existing = components.get(component_id)
        if existing is not None and existing.kind is not component.kind:
            raise RegistryError(
                f"component {component_id!r} conflicts with its typed provider kind"
            )
        components[component_id] = component
        digest.update(component_id.encode("utf-8"))
        digest.update(b"\0")
        digest.update(component.source_revision.encode("ascii"))
        digest.update(b"\0")

    for component_id in ("topaz", "wbt", "single-ofe", "multiple-ofe"):
        component = components.get(component_id)
        if component is None:
            raise RegistryError(f"shared Builder component {component_id!r} is missing")
        retained_requires = tuple(
            item for item in component.constraints.requires
            if item not in _BUILDER_PROFILE_IDS
        )
        components[component_id] = replace(
            component,
            constraints=replace(component.constraints, requires=retained_requires),
        )

    digest.update(locale_catalog_revision().encode("ascii"))
    digest.update(b"\0")
    for profile_id in _BUILDER_PROFILE_IDS:
        graph = graphs[profile_id]
        digest.update(profile_id.encode("utf-8"))
        digest.update(b"\0")
        digest.update(graph.provider_revision.encode("ascii"))
        digest.update(b"\0")
    _validate_references(components)
    return Registry.create(digest.hexdigest(), components)
