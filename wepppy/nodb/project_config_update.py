"""Read-only previews and crash-recoverable project config amendments."""

from __future__ import annotations

import ast
from base64 import b64decode, b64encode
from configparser import RawConfigParser
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Callable, Iterator, Mapping

from wepppy.nodb.config_builder.registry import DEFAULT_PROFILES_ROOT, RegistryError, load_registry
from wepppy.nodb.config_builder.resolver import (
    BuilderConstraintError,
    resolve_builder_capability_graph,
    resolve_builder_config,
)
from wepppy.nodb.config_builder.schema import (
    BuilderSelections,
    ComponentKind,
    Registry,
    ResolvedBuilderConfig,
)
from wepppy.nodb.locales.capability_graph import (
    CapabilityGraph,
    CapabilityGraphError,
    capability_structure_sha256,
)
from wepppy.nodb.project_config_capabilities import capability_authority
from wepppy.nodb.project_config_snapshot import CONFIGS_ROOT, PresetPolicyError, load_preset_policies
from wepppy.project_config_sanitization import ConfigMaterializationError, assert_materialization_safe, scan_manifest_text
from wepppy.project_config_serialization import CanonicalConfigError, CanonicalValue, parse_config_text, serialize_config

__all__ = [
    "CONFIG_UPDATE_FLAG",
    "CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION",
    "CAPABILITY_REFRESH_WARNING",
    "ConfigUpdateAcknowledgmentError",
    "ConfigUpdateAddition",
    "ConfigUpdateError",
    "ConfigUpdatePreview",
    "ConfigUpdateRegistryError",
    "ConfigUpdateResult",
    "ConfigUpdateStatus",
    "ConfigUpdateUnavailableError",
    "StaleConfigPreviewError",
    "apply_project_config_update",
    "preview_project_config_update",
    "project_config_digest_warning",
    "project_config_lifecycle_guard",
    "project_config_update_preview_guard",
    "project_config_update_reconciliation",
    "project_config_update_status",
    "project_config_update_enabled",
    "recover_project_config_update",
]

CONFIG_UPDATE_FLAG = "WEPPPY_PROJECT_CONFIG_UPDATE_ENABLED"
CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION = "PC-24-capability-refresh-v1"
CAPABILITY_REFRESH_WARNING = (
    "I understand that refreshing capability authority changes this project's "
    "modeling envelope, diminishes strict provenance continuity with its original "
    "configuration, and may expose Preview or otherwise unstable features."
)
MANIFEST_NAME = "config-manifest.json"
JOURNAL_NAME = ".config-amendment.pending.json"
LOCK_NAME = ".config-amendment.lock"
_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"", "0", "false", "no", "off"})
_MAX_CONFIG_ARTIFACT_BYTES = 8 * 1024 * 1024


class _StoredCapabilityConfig:
    """Adapt canonical project bytes to the stored-capability reader contract."""

    def __init__(self, content: bytes) -> None:
        parser = RawConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read_string(content.decode("utf-8"))
        self._configparser = parser

    def config_get_raw(
        self, section: str, option: str, default: object = None
    ) -> object:
        if not self._configparser.has_option(section, option):
            return default
        return self._configparser.get(section, option, raw=True)

    def config_get_list(
        self, section: str, option: str, default: object = None
    ) -> object:
        raw = self.config_get_raw(section, option, default)
        if not isinstance(raw, str):
            return raw
        try:
            return ast.literal_eval(raw)
        except (SyntaxError, ValueError):
            return raw


class ConfigUpdateError(ValueError):
    """Base error for a rejected or failed project config update."""


class ConfigUpdateUnavailableError(ConfigUpdateError):
    """Raised when no safe registered update can be produced."""


class ConfigUpdateRegistryError(ConfigUpdateUnavailableError):
    """Raised when a refresh requires a live registry that cannot be loaded."""


class StaleConfigPreviewError(ConfigUpdateError):
    """Raised when an apply request no longer matches the complete preview."""


class ConfigUpdateAcknowledgmentError(ConfigUpdateError):
    """Raised when a capability refresh lacks the exact reviewed acknowledgment."""


@dataclass(frozen=True, slots=True)
class ConfigUpdateAddition:
    section: str
    option: str
    value: str
    source_id: str
    source_revision: str


@dataclass(frozen=True, slots=True)
class ConfigUpdatePreview:
    available: bool
    preview_id: str | None
    additions: tuple[ConfigUpdateAddition, ...]
    config_filename: str
    current_digest: str
    declared_digest: str | None
    digest_warning: bool
    resulting_digest: str = ""
    update_kind: str = "additive"
    capability_refresh: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class ConfigUpdateResult:
    applied: bool
    sequence: int | None
    prior_digest: str
    resulting_digest: str
    additions: tuple[ConfigUpdateAddition, ...]
    recovered: bool = False
    update_kind: str = "additive"


@dataclass(frozen=True, slots=True)
class ConfigUpdateStatus:
    current_digest: str
    last_update: Mapping[str, object] | None
    config_filename: str | None = None


def project_config_update_enabled(environ: Mapping[str, str] | None = None) -> bool:
    source = os.environ if environ is None else environ
    raw = source.get(CONFIG_UPDATE_FLAG, "").strip().casefold()
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    raise ValueError(f"{CONFIG_UPDATE_FLAG} must be a strict boolean")


def project_config_digest_warning(working_directory: str | Path) -> bool:
    """Return digest-mismatch state without resolving update sources or writing."""

    root = Path(working_directory)
    with _amendment_lock(root):
        _recover_locked(root)
        _path, config_bytes, _manifest_bytes, manifest = _read_artifacts(root)
    config_meta = manifest.get("config")
    declared = config_meta.get("sha256") if isinstance(config_meta, dict) else None
    return isinstance(declared, str) and declared != _sha256(config_bytes)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_canonical_utc_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError:
        return False
    return (
        parsed.tzinfo == timezone.utc
        and parsed.isoformat().replace("+00:00", "Z") == value
    )


def _is_canonical_json(value: object) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_canonical_json(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_canonical_json(item)
            for key, item in value.items()
        )
    return False


def _is_string_list(value: object, *, nonempty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (not nonempty or bool(value))
        and all(isinstance(item, str) and bool(item) for item in value)
        and len(value) == len(set(value))
    )


def _validate_capability_identity(value: object) -> None:
    expected = {
        "graph_sha256", "structure_sha256", "provider_revision",
        "wepp_binary_revisions", "selected_parent_chain",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise ConfigUpdateUnavailableError("Capability amendment identity shape is invalid")
    if not all(
        _is_sha256(value[key])
        for key in ("graph_sha256", "structure_sha256", "provider_revision")
    ):
        raise ConfigUpdateUnavailableError("Capability amendment identity hashes are invalid")
    revisions = value["wepp_binary_revisions"]
    if not isinstance(revisions, dict) or not revisions or not all(
        isinstance(key, str) and key and isinstance(revision, str) and revision
        for key, revision in revisions.items()
    ):
        raise ConfigUpdateUnavailableError("Capability amendment binary revisions are invalid")
    chain = value["selected_parent_chain"]
    if not isinstance(chain, list) or not chain:
        raise ConfigUpdateUnavailableError("Capability amendment parent chain is invalid")
    for row in chain:
        if not isinstance(row, dict) or set(row) != {"kind", "id", "revision"} or not all(
            isinstance(row[key], str) and row[key]
            for key in ("kind", "id", "revision")
        ):
            raise ConfigUpdateUnavailableError("Capability amendment parent chain is invalid")


def _validate_capability_changes(value: object) -> None:
    if not isinstance(value, list):
        raise ConfigUpdateUnavailableError("Capability amendment changes are invalid")
    expected = {
        "section", "option", "kind", "before", "after", "added_ids",
        "removed_ids", "added_support",
    }
    sort_keys: list[tuple[str, str, str]] = []
    for row in value:
        if not isinstance(row, dict) or set(row) != expected:
            raise ConfigUpdateUnavailableError("Capability amendment change shape is invalid")
        section = row["section"]
        option = row["option"]
        kind = row["kind"]
        if (
            not isinstance(section, str) or not section
            or not isinstance(option, str) or not option
            or kind not in {"added", "removed", "changed"}
            or not _is_canonical_json(row["before"])
            or not _is_canonical_json(row["after"])
        ):
            raise ConfigUpdateUnavailableError("Capability amendment change values are invalid")
        added_ids = row["added_ids"]
        removed_ids = row["removed_ids"]
        if (
            not _is_string_list(added_ids)
            or not _is_string_list(removed_ids)
            or added_ids != sorted(added_ids)
            or removed_ids != sorted(removed_ids)
        ):
            raise ConfigUpdateUnavailableError("Capability amendment change IDs are invalid")
        before = row["before"]
        after = row["after"]
        if (
            (kind == "added" and (before is not None or after is None))
            or (kind == "removed" and (before is None or after is not None))
            or (kind == "changed" and (before is None or after is None or before == after))
        ):
            raise ConfigUpdateUnavailableError("Capability amendment change semantics are invalid")
        expected_added_ids = sorted(_canonical_ids(after) - _canonical_ids(before))
        expected_removed_ids = sorted(_canonical_ids(before) - _canonical_ids(after))
        if added_ids != expected_added_ids or removed_ids != expected_removed_ids:
            raise ConfigUpdateUnavailableError("Capability amendment change delta is invalid")
        support = row["added_support"]
        if not isinstance(support, list):
            raise ConfigUpdateUnavailableError("Capability amendment support rows are invalid")
        support_ids: list[str] = []
        for support_row in support:
            if (
                not isinstance(support_row, dict)
                or set(support_row) != {"id", "support_state"}
                or not isinstance(support_row["id"], str)
                or not support_row["id"]
                or (
                    support_row["support_state"] is not None
                    and not isinstance(support_row["support_state"], str)
                )
            ):
                raise ConfigUpdateUnavailableError("Capability amendment support row is invalid")
            support_ids.append(support_row["id"])
        if support_ids != added_ids:
            raise ConfigUpdateUnavailableError("Capability amendment support IDs are invalid")
        sort_keys.append((section, option, str(kind)))
    if sort_keys != sorted(sort_keys):
        raise ConfigUpdateUnavailableError("Capability amendment changes are not sorted")
    if len(sort_keys) != len(set(sort_keys)):
        raise ConfigUpdateUnavailableError("Capability amendment changes are duplicated")


def _validate_durable_capability_refresh(value: object) -> None:
    expected = {
        "locale_profile", "locales", "preserved_project_selections",
        "acknowledgment_revision", "prior", "resulting", "changes",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise ConfigUpdateUnavailableError("Capability amendment refresh shape is invalid")
    if not isinstance(value["locale_profile"], str) or not value["locale_profile"]:
        raise ConfigUpdateUnavailableError("Capability amendment locale is invalid")
    if not _is_string_list(value["locales"], nonempty=True):
        raise ConfigUpdateUnavailableError("Capability amendment runtime locales are invalid")
    if value["acknowledgment_revision"] != CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION:
        raise ConfigUpdateUnavailableError("Capability amendment acknowledgment is invalid")
    preserved = value["preserved_project_selections"]
    if not isinstance(preserved, dict) or set(preserved) != {
        "capability_defaults", "nodb", "climate",
    }:
        raise ConfigUpdateUnavailableError("Capability amendment preserved selections are invalid")
    defaults = preserved["capability_defaults"]
    expected_defaults = {
        "locale_profile", "dem_source", "climate_dataset",
        "climate_station_database", "landuse_dataset", "soil_dataset",
        "delineation_backend", "watershed_representation", "wepp_binary",
    }
    if not isinstance(defaults, dict) or set(defaults) != expected_defaults or not all(
        isinstance(defaults[key], str) and defaults[key] for key in expected_defaults
    ):
        raise ConfigUpdateUnavailableError("Capability amendment preserved defaults are invalid")
    nodb = preserved["nodb"]
    climate = preserved["climate"]
    if (
        not isinstance(nodb, dict) or set(nodb) != {"mods"}
        or not _is_string_list(nodb["mods"])
        or not isinstance(climate, dict) or set(climate) != {"cligen_db"}
        or not isinstance(climate["cligen_db"], str) or not climate["cligen_db"]
    ):
        raise ConfigUpdateUnavailableError("Capability amendment preserved runtime values are invalid")
    _validate_capability_identity(value["prior"])
    _validate_capability_identity(value["resulting"])
    _validate_capability_changes(value["changes"])


def _validate_capability_amendments(amendments: object) -> None:
    if not isinstance(amendments, list):
        raise ConfigUpdateUnavailableError("Project config amendments are invalid")
    capability_only = {
        "sequence", "kind", "preview_id", "applied_at", "application_revision",
        "resolver_version", "prior_sha256", "resulting_sha256", "capability_refresh",
    }
    additive_only = {
        "sequence", "kind", "preview_id", "applied_at", "application_revision",
        "resolver_version", "prior_sha256", "resulting_sha256", "trigger",
        "additions", "reason",
    }
    combined = {
        *capability_only, "trigger", "additions", "reason",
    }
    for index, amendment in enumerate(amendments, start=1):
        if not isinstance(amendment, dict):
            raise ConfigUpdateUnavailableError("Project config amendment is invalid")
        if "kind" not in amendment:
            if "capability_refresh" in amendment:
                raise ConfigUpdateUnavailableError(
                    "Capability amendment kind is missing"
                )
            continue
        kind = amendment.get("kind")
        if kind not in {"additive", "capability_refresh", "combined"}:
            raise ConfigUpdateUnavailableError("Project config amendment kind is invalid")
        expected = {
            "additive": additive_only,
            "capability_refresh": capability_only,
            "combined": combined,
        }[kind]
        if set(amendment) != expected:
            raise ConfigUpdateUnavailableError("Project config amendment top-level shape is invalid")
        if (
            isinstance(amendment["sequence"], bool)
            or not isinstance(amendment["sequence"], int)
            or amendment["sequence"] != index
            or not isinstance(amendment["preview_id"], str)
            or not amendment["preview_id"]
            or not _is_canonical_utc_timestamp(amendment["applied_at"])
            or not isinstance(amendment["application_revision"], str)
            or not amendment["application_revision"]
            or isinstance(amendment["resolver_version"], bool)
            or not isinstance(amendment["resolver_version"], int)
            or amendment["resolver_version"] != 1
            or not _is_sha256(amendment["prior_sha256"])
            or not _is_sha256(amendment["resulting_sha256"])
        ):
            raise ConfigUpdateUnavailableError("Project config amendment metadata is invalid")
        if kind in {"additive", "combined"}:
            trigger = amendment["trigger"]
            additions = amendment["additions"]
            if (
                not isinstance(trigger, dict)
                or set(trigger) != {"section", "option"}
                or not all(isinstance(trigger[key], str) and trigger[key] for key in trigger)
                or not isinstance(additions, list)
                or not additions
                or amendment["reason"] != "missing_registered_attribute_merge"
                or any(
                    not isinstance(addition, dict)
                    or set(addition) != {
                        "section", "option", "value", "source_id", "source_revision",
                    }
                    or not all(
                        isinstance(addition[key], str) and addition[key]
                        for key in addition
                    )
                    for addition in additions
                )
            ):
                raise ConfigUpdateUnavailableError("Project config additive amendment is invalid")
        if kind in {"capability_refresh", "combined"}:
            _validate_durable_capability_refresh(amendment["capability_refresh"])


def _read_artifacts(root: Path) -> tuple[Path, bytes, bytes, dict[str, object]]:
    manifest_path = root / MANIFEST_NAME
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigUpdateUnavailableError("Project config manifest is unavailable or malformed") from exc
    if len(manifest_bytes) > _MAX_CONFIG_ARTIFACT_BYTES:
        raise ConfigUpdateUnavailableError("Project config manifest exceeds the canonical artifact size limit")
    if (
        not isinstance(manifest, dict)
        or isinstance(manifest.get("schema_version"), bool)
        or not isinstance(manifest.get("schema_version"), int)
        or manifest.get("schema_version") != 1
        or isinstance(manifest.get("resolver_version"), bool)
        or not isinstance(manifest.get("resolver_version"), int)
        or manifest.get("resolver_version") != 1
    ):
        raise ConfigUpdateUnavailableError("Project config manifest schema does not support updates")
    if scan_manifest_text(manifest_bytes.decode("utf-8"), source=MANIFEST_NAME):
        raise ConfigUpdateUnavailableError("Project config manifest is unsafe")
    config_meta = manifest.get("config")
    if not isinstance(config_meta, dict) or not isinstance(config_meta.get("filename"), str):
        raise ConfigUpdateUnavailableError("Project config manifest has invalid config metadata")
    filename = config_meta["filename"]
    if Path(filename).name != filename or filename in {"", ".", ".."}:
        raise ConfigUpdateUnavailableError("Project config filename is invalid")
    config_path = root / filename
    try:
        config_bytes = config_path.read_bytes()
        if len(config_bytes) > _MAX_CONFIG_ARTIFACT_BYTES:
            raise ConfigUpdateUnavailableError(
                "Project-owned config exceeds the canonical artifact size limit"
            )
        parse_config_text(config_bytes.decode("utf-8"))
    except ConfigUpdateUnavailableError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise ConfigUpdateUnavailableError("Project-owned config is unavailable or invalid") from exc
    if not isinstance(manifest.get("parent_chain"), list) or not manifest["parent_chain"]:
        raise ConfigUpdateUnavailableError("Project config parent chain is invalid")
    if not isinstance(manifest.get("selections"), dict) or not isinstance(manifest.get("amendments"), list):
        raise ConfigUpdateUnavailableError("Project config manifest is incomplete")
    _validate_capability_amendments(manifest["amendments"])
    return config_path, config_bytes, manifest_bytes, manifest


def _builder_selections(
    payload: Mapping[str, object], *, capability_schema_version: int
) -> BuilderSelections:
    required = (
        "locale", "dem", "delineation_backend", "watershed_representation",
        "wepp_binary", "soil", "landuse", "climate", "capability_profile",
    )
    if not all(isinstance(payload.get(key), str) and payload[key] for key in required):
        raise ConfigUpdateUnavailableError("Builder selections are incomplete")
    station_database = payload.get("climate_station_database")
    if capability_schema_version >= 3 and (
        not isinstance(station_database, str) or not station_database
    ):
        raise ConfigUpdateUnavailableError("Builder station-database selection is incomplete")
    mods = payload.get("mods", [])
    if not isinstance(mods, list) or not all(isinstance(item, str) for item in mods):
        raise ConfigUpdateUnavailableError("Builder mod selections are invalid")
    source = payload.get("cellsize_source")
    effective = payload.get("cellsize")
    dem_default = payload.get("dem_default_cellsize")
    if source not in {"dem_default", "privileged_override"}:
        raise ConfigUpdateUnavailableError("Builder cell-size source is invalid")
    if isinstance(effective, bool) or not isinstance(effective, int):
        raise ConfigUpdateUnavailableError("Builder effective cell-size selection is invalid")
    if capability_schema_version >= 3 and (
        isinstance(dem_default, bool) or not isinstance(dem_default, int)
    ):
        raise ConfigUpdateUnavailableError("Builder DEM-default cell-size selection is invalid")
    if source == "dem_default" and dem_default is not None and effective != dem_default:
        raise ConfigUpdateUnavailableError("Builder DEM-default cell-size selection is incongruent")
    if source == "privileged_override" and dem_default is not None and effective == dem_default:
        raise ConfigUpdateUnavailableError("Builder privileged cell-size selection is incongruent")
    override = effective if source == "privileged_override" else None
    return BuilderSelections(
        locale=str(payload["locale"]), dem=str(payload["dem"]),
        delineation_backend=str(payload["delineation_backend"]),
        watershed_representation=str(payload["watershed_representation"]),
        wepp_binary=str(payload["wepp_binary"]),
        soil=str(payload["soil"]), landuse=str(payload["landuse"]),
        climate=str(payload["climate"]), mods=tuple(mods),
        climate_station_database=(
            str(station_database) if isinstance(station_database, str)
            else "cligen-stations-2015"
        ),
        capability_profile=str(payload["capability_profile"]),
        cellsize_override=override,
    )


def _chain_entries(manifest: Mapping[str, object]) -> tuple[tuple[str, str, str], ...]:
    entries: list[tuple[str, str, str]] = []
    for item in manifest["parent_chain"]:  # type: ignore[index]
        if not isinstance(item, dict):
            raise ConfigUpdateUnavailableError("Project config parent chain is invalid")
        values = item.get("kind"), item.get("id"), item.get("revision")
        if not all(isinstance(value, str) and value for value in values):
            raise ConfigUpdateUnavailableError("Project config parent chain is invalid")
        entries.append((str(values[0]), str(values[1]), str(values[2])))
    return tuple(entries)


def _builder_target(
    manifest: Mapping[str, object],
    registry: Registry,
    *,
    capability_schema_version: int,
    capability_graph: CapabilityGraph | None,
) -> tuple[
    dict[str, dict[str, CanonicalValue]],
    dict[tuple[str, str], tuple[str, str]],
    ResolvedBuilderConfig,
]:
    selections = _builder_selections(
        manifest["selections"],  # type: ignore[arg-type,index]
        capability_schema_version=capability_schema_version,
    )
    resolved = resolve_builder_config(
        selections,
        registry=registry,
        capability_schema_version=capability_schema_version,
        capability_graph=capability_graph,
    )
    recorded = tuple((kind, component_id) for kind, component_id, _revision in _chain_entries(manifest))
    current = tuple((item.kind, item.component_id) for item in resolved.parent_chain)
    if recorded != current:
        raise ConfigUpdateUnavailableError("Recorded builder parent chain no longer resolves unambiguously")
    revisions = {item.component_id: item.revision for item in resolved.parent_chain}
    provenance: dict[tuple[str, str], tuple[str, str]] = {}
    for section, options in resolved.config.items():
        for option in options:
            writer = resolved.effective_writers[(section, option)]
            provenance[(section, option)] = (writer, revisions.get(writer, registry.revision))
    return (
        deepcopy({section: dict(options) for section, options in resolved.config.items()}),
        provenance,
        resolved,
    )


def _preset_target(
    manifest: Mapping[str, object], configs_root: Path,
) -> tuple[dict[str, dict[str, CanonicalValue]], dict[tuple[str, str], tuple[str, str]]]:
    preset_id = manifest.get("source_preset")
    if not isinstance(preset_id, str) or not preset_id:
        raise ConfigUpdateUnavailableError("Preset source identity is invalid")
    chain = _chain_entries(manifest)
    if tuple((kind, source_id) for kind, source_id, _revision in chain) != (
        ("defaults", "shared-defaults"), ("preset", preset_id)
    ):
        raise ConfigUpdateUnavailableError("Recorded preset parent chain is invalid")
    policies = load_preset_policies(configs_root=configs_root)
    if preset_id not in policies:
        raise ConfigUpdateUnavailableError("Recorded preset is no longer active")
    try:
        defaults_bytes = (configs_root / "_defaults.cfg").read_bytes()
        preset_bytes = (configs_root / f"{preset_id}.cfg").read_bytes()
        defaults = parse_config_text(defaults_bytes.decode("utf-8"))
        preset = parse_config_text(preset_bytes.decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ConfigUpdateUnavailableError("Recorded preset sources are unavailable") from exc
    target = deepcopy(defaults)
    provenance: dict[tuple[str, str], tuple[str, str]] = {
        (section, option): ("shared-defaults", _sha256(defaults_bytes))
        for section, options in defaults.items() for option in options
    }
    preset_revision = _sha256(preset_bytes)
    for section, options in preset.items():
        target.setdefault(section, {}).update(deepcopy(options))
        for option in options:
            provenance[(section, option)] = (preset_id, preset_revision)
    selections = manifest["selections"]
    overrides = selections.get("overrides", {}) if isinstance(selections, dict) else {}
    if not isinstance(overrides, dict):
        raise ConfigUpdateUnavailableError("Preset overrides are invalid")
    for key, entry in overrides.items():
        if not isinstance(key, str) or "." not in key or not isinstance(entry, dict) or entry.get("source") != "query":
            raise ConfigUpdateUnavailableError("Preset overrides are invalid")
        section, option = key.rsplit(".", 1)
        if section not in target or option not in target[section]:
            raise ConfigUpdateUnavailableError("Preset override target is no longer registered")
        target[section][option] = entry.get("value")  # type: ignore[assignment]
        provenance[(section, option)] = ("query-override", str(manifest.get("source_revision") or "unknown"))
    target.setdefault("config", {}).update({"flattened": True, "resolver_version": 1, "schema_version": 1})
    for option in ("flattened", "resolver_version", "schema_version"):
        provenance[("config", option)] = ("resolver-v1", str(manifest.get("source_revision") or "unknown"))
    return target, provenance


def _serialized_value(section: str, option: str, value: CanonicalValue) -> str:
    line = serialize_config({section: {option: value}}).decode("utf-8").splitlines()[1]
    return line.split(" = ", 1)[1]


def _addition_payload(additions: tuple[ConfigUpdateAddition, ...]) -> list[dict[str, str]]:
    return [
        {
            "section": item.section,
            "option": item.option,
            "value": item.value,
            "source_id": item.source_id,
            "source_revision": item.source_revision,
        }
        for item in additions
    ]


def _preview_id(
    config_bytes: bytes,
    manifest_bytes: bytes,
    additions: tuple[ConfigUpdateAddition, ...],
    capability_refresh: Mapping[str, object] | None,
) -> str:
    payload = json.dumps(
        {
            "additions": _addition_payload(additions),
            "capability_refresh": capability_refresh,
            "warning_revision": (
                CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION
                if capability_refresh is not None
                else None
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(config_bytes + b"\0" + manifest_bytes + b"\0" + payload).hexdigest()
    return f"pcu1-{digest}"


def _capability_sections(graph: CapabilityGraph) -> dict[str, dict[str, CanonicalValue]]:
    return deepcopy(graph.as_config_sections())


def _graph_sha256(graph: CapabilityGraph) -> str:
    return _sha256(serialize_config(_capability_sections(graph)))


def _selected_parent_chain(
    chain: tuple[tuple[str, str, str], ...],
) -> list[dict[str, str]]:
    return [
        {"kind": kind, "id": component_id, "revision": revision}
        for kind, component_id, revision in chain
    ]


def _current_selected_parent_chain(
    manifest: Mapping[str, object],
) -> list[dict[str, str]]:
    amendments = manifest.get("amendments")
    if isinstance(amendments, list):
        for amendment in reversed(amendments):
            if not isinstance(amendment, dict) or amendment.get("kind") not in {
                "capability_refresh",
                "combined",
            }:
                continue
            refresh = amendment.get("capability_refresh")
            resulting = refresh.get("resulting") if isinstance(refresh, dict) else None
            chain = (
                resulting.get("selected_parent_chain")
                if isinstance(resulting, dict)
                else None
            )
            if isinstance(chain, list):
                return deepcopy(chain)
    return _selected_parent_chain(_chain_entries(manifest))


def _canonical_ids(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str)}


def _capability_changes(
    prior: Mapping[str, Mapping[str, CanonicalValue]],
    resulting: Mapping[str, Mapping[str, CanonicalValue]],
    registry: Registry,
) -> list[dict[str, object]]:
    changes: list[dict[str, object]] = []
    for section in sorted(set(prior) | set(resulting)):
        before_options = prior.get(section, {})
        after_options = resulting.get(section, {})
        for option in sorted(set(before_options) | set(after_options)):
            before = before_options.get(option)
            after = after_options.get(option)
            if option in before_options and option in after_options and before == after:
                continue
            if option not in before_options:
                kind = "added"
            elif option not in after_options:
                kind = "removed"
            else:
                kind = "changed"
            before_ids = _canonical_ids(before)
            after_ids = _canonical_ids(after)
            added_ids = sorted(after_ids - before_ids)
            removed_ids = sorted(before_ids - after_ids)
            added_support = []
            for component_id in added_ids:
                component = registry.components.get(component_id)
                added_support.append({
                    "id": component_id,
                    "support_state": component.support_state if component is not None else None,
                })
            changes.append({
                "section": section,
                "option": option,
                "kind": kind,
                "before": deepcopy(before) if option in before_options else None,
                "after": deepcopy(after) if option in after_options else None,
                "added_ids": added_ids,
                "removed_ids": removed_ids,
                "added_support": added_support,
            })
    return changes


def _selection_preserving_graph(
    stored_graph: CapabilityGraph,
    current_graph: CapabilityGraph,
) -> CapabilityGraph:
    try:
        graph = current_graph.with_defaults(**dict(stored_graph.defaults))
    except (TypeError, ValueError) as exc:
        stable_ids = ", ".join(sorted(str(value) for value in stored_graph.defaults.values()))
        raise ConfigUpdateUnavailableError(
            f"Current capability graph is incompatible with preserved selections: {stable_ids}"
        ) from exc
    return graph


def _assert_builder_congruence(
    current: Mapping[str, Mapping[str, CanonicalValue]],
    manifest: Mapping[str, object],
    registry: Registry,
    stored_graph: CapabilityGraph,
    resolved: ResolvedBuilderConfig,
) -> None:
    selections = manifest["selections"]
    assert isinstance(selections, dict)
    locale_id = selections.get("locale")
    if not isinstance(locale_id, str):
        raise ConfigUpdateUnavailableError("Builder locale selection is invalid")
    locale = registry.components.get(locale_id)
    if locale is None or locale.kind is not ComponentKind.LOCALE:
        raise ConfigUpdateUnavailableError(f"Builder locale is unavailable: {locale_id}")
    expected_profile = f"{locale_id}-capabilities"
    expected_locales = list(locale.runtime_tokens)
    mismatches: list[str] = []
    if current.get("general", {}).get("locales") != expected_locales:
        mismatches.append("general.locales")
    if stored_graph.locale_profiles != (locale_id,):
        mismatches.append("capabilities.locale_profiles")
    if stored_graph.defaults.get("locale_profile") != locale_id:
        mismatches.append("capability_defaults.locale_profile")
    if selections.get("capability_profile") != expected_profile:
        mismatches.append("selections.capability_profile")
    selection_defaults = {
        "locale": "locale_profile",
        "dem": "dem_source",
        "climate": "climate_dataset",
        "climate_station_database": "climate_station_database",
        "landuse": "landuse_dataset",
        "soil": "soil_dataset",
        "delineation_backend": "delineation_backend",
        "watershed_representation": "watershed_representation",
        "wepp_binary": "wepp_binary",
    }
    for selection_key, default_key in selection_defaults.items():
        if selections.get(selection_key) != stored_graph.defaults.get(default_key):
            mismatches.append(f"selections.{selection_key}")
    if current.get("capability_defaults", {}) != dict(stored_graph.defaults):
        mismatches.append("capability_defaults")
    if resolved.config.get("capability_defaults", {}) != dict(stored_graph.defaults):
        mismatches.append("resolved.capability_defaults")

    dem_default = selections.get("dem_default_cellsize")
    effective_cellsize = selections.get("cellsize")
    cellsize_source = selections.get("cellsize_source")
    if dem_default != resolved.dem_default_cellsize:
        mismatches.append("selections.dem_default_cellsize")
    if effective_cellsize != resolved.effective_cellsize:
        mismatches.append("selections.cellsize")
    if cellsize_source != resolved.cellsize_source:
        mismatches.append("selections.cellsize_source")
    if current.get("general", {}).get("cellsize") != effective_cellsize:
        mismatches.append("general.cellsize")

    selection_ids = {
        str(selections[key])
        for key in selection_defaults
        if key != "locale" and isinstance(selections.get(key), str)
    }
    for key, writer in resolved.effective_writers.items():
        if writer not in selection_ids or key[0].startswith("capabilit"):
            continue
        section, option = key
        if option in current.get(section, {}) and current[section][option] != resolved.config[section][option]:
            mismatches.append(f"{section}.{option}")
    manifest_mods = selections.get("mods", [])
    if current.get("nodb", {}).get("mods", []) != manifest_mods:
        mismatches.append("nodb.mods")
    if mismatches:
        raise ConfigUpdateUnavailableError(
            "Builder manifest/config selection mismatch: " + ", ".join(sorted(set(mismatches)))
        )


def _assert_builder_refresh_completeness(
    current: Mapping[str, Mapping[str, CanonicalValue]],
    manifest: Mapping[str, object],
    resolved: ResolvedBuilderConfig,
) -> None:
    selections = manifest["selections"]
    assert isinstance(selections, dict)
    selection_keys = {
        "dem", "delineation_backend", "watershed_representation", "wepp_binary",
        "soil", "landuse", "climate", "climate_station_database",
    }
    selection_ids = {
        str(selections[key])
        for key in selection_keys
        if isinstance(selections.get(key), str)
    }
    mismatches: list[str] = []
    for (section, option), writer in resolved.effective_writers.items():
        if writer not in selection_ids or section.startswith("capabilit"):
            continue
        if option not in current.get(section, {}):
            mismatches.append(f"{section}.{option}")
        elif current[section][option] != resolved.config[section][option]:
            mismatches.append(f"{section}.{option}")
    mods = current.get("nodb", {}).get("mods")
    if not isinstance(mods, list) or not all(isinstance(item, str) for item in mods):
        mismatches.append("nodb.mods")
    cligen_db = current.get("climate", {}).get("cligen_db")
    if not isinstance(cligen_db, str) or not cligen_db:
        mismatches.append("climate.cligen_db")
    if mismatches:
        raise ConfigUpdateUnavailableError(
            "Builder refresh requires complete selection-bearing config values: "
            + ", ".join(sorted(set(mismatches)))
        )


def _capability_refresh_payload(
    current: Mapping[str, Mapping[str, CanonicalValue]],
    manifest: Mapping[str, object],
    registry: Registry,
    stored_graph: CapabilityGraph,
    resolved_stored: ResolvedBuilderConfig,
) -> tuple[dict[str, object] | None, CapabilityGraph | None]:
    if stored_graph.schema_version != 3:
        return None, None
    _assert_builder_congruence(current, manifest, registry, stored_graph, resolved_stored)
    selections = _builder_selections(manifest["selections"], capability_schema_version=3)  # type: ignore[arg-type,index]
    current_graph = resolve_builder_capability_graph(selections.locale, registry=registry)
    resulting_graph = _selection_preserving_graph(stored_graph, current_graph)
    resolved_result = resolve_builder_config(
        selections,
        registry=registry,
        capability_schema_version=3,
        capability_graph=resulting_graph,
    )
    prior_sections = _capability_sections(stored_graph)
    resulting_sections = _capability_sections(resulting_graph)
    changes = _capability_changes(prior_sections, resulting_sections, registry)
    runtime_locales = current.get("general", {}).get("locales")
    prior_chain = _current_selected_parent_chain(manifest)
    resulting_chain = [
        {"kind": item.kind, "id": item.component_id, "revision": item.revision}
        for item in resolved_result.parent_chain
    ]
    if not changes and prior_chain == resulting_chain:
        return None, resulting_graph
    _assert_builder_refresh_completeness(current, manifest, resolved_stored)
    preserved = {
        "capability_defaults": deepcopy(dict(stored_graph.defaults)),
        "nodb": {"mods": deepcopy(current["nodb"]["mods"])},
        "climate": {"cligen_db": deepcopy(current["climate"]["cligen_db"])},
    }
    payload: dict[str, object] = {
        "locale_profile": selections.locale,
        "locales": deepcopy(runtime_locales),
        "preserved_project_selections": preserved,
        "acknowledgment": {
            "required": True,
            "revision": CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION,
            "text": CAPABILITY_REFRESH_WARNING,
        },
        "prior": {
            "graph_sha256": _graph_sha256(stored_graph),
            "structure_sha256": capability_structure_sha256(stored_graph),
            "provider_revision": stored_graph.provider_revision,
            "wepp_binary_revisions": dict(stored_graph.wepp_binary_revisions),
            "selected_parent_chain": prior_chain,
        },
        "resulting": {
            "graph_sha256": _graph_sha256(resulting_graph),
            "structure_sha256": capability_structure_sha256(resulting_graph),
            "provider_revision": resulting_graph.provider_revision,
            "wepp_binary_revisions": dict(resulting_graph.wepp_binary_revisions),
            "selected_parent_chain": resulting_chain,
        },
        "changes": changes,
    }
    return payload, resulting_graph


def _merge_preview(
    current: Mapping[str, Mapping[str, CanonicalValue]],
    additions: tuple[ConfigUpdateAddition, ...],
    capability_refresh: Mapping[str, object] | None,
) -> dict[str, dict[str, CanonicalValue]]:
    merged = deepcopy({section: dict(options) for section, options in current.items()})
    for addition in additions:
        parsed_value = parse_config_text(
            f"[{addition.section}]\n{addition.option} = {addition.value}\n"
        )[addition.section][addition.option]
        merged.setdefault(addition.section, {})[addition.option] = parsed_value
    if capability_refresh is not None:
        changes = capability_refresh.get("changes")
        if not isinstance(changes, list):
            raise ConfigUpdateError("Capability refresh delta is invalid")
        for row in changes:
            if not isinstance(row, dict):
                raise ConfigUpdateError("Capability refresh delta is invalid")
            section, option = row.get("section"), row.get("option")
            if not isinstance(section, str) or not isinstance(option, str):
                raise ConfigUpdateError("Capability refresh delta is invalid")
            if row.get("after") is None:
                merged.get(section, {}).pop(option, None)
                if not merged.get(section):
                    merged.pop(section, None)
            else:
                merged.setdefault(section, {})[option] = deepcopy(row["after"])  # type: ignore[assignment]
    return merged


def _preview_project_config_update_locked(
    working_directory: str | Path, *, registry: Registry | None = None,
    registry_root: str | Path = DEFAULT_PROFILES_ROOT,
    configs_root: str | Path = CONFIGS_ROOT,
    application_revision: str = "dev",
) -> ConfigUpdatePreview:
    """Resolve a preview while the caller holds the amendment lock."""

    root = Path(working_directory)
    config_path, config_bytes, manifest_bytes, manifest = _read_artifacts(root)
    current = parse_config_text(config_bytes.decode("utf-8"))
    source_kind = manifest.get("source_kind")
    capability_refresh: Mapping[str, object] | None = None
    try:
        if source_kind == "builder":
            capability_schema_version = current.get("capabilities", {}).get(
                "schema_version"
            )
            if capability_schema_version is None:
                raise ConfigUpdateUnavailableError(
                    "Legacy/schema-v1 Builder capability authority does not support updates"
                )
            if (
                isinstance(capability_schema_version, bool)
                or not isinstance(capability_schema_version, int)
                or capability_schema_version not in {2, 3}
            ):
                raise ConfigUpdateUnavailableError(
                    "Stored Builder capability schema is unsupported"
                )
            try:
                stored_graph = capability_authority(
                    _StoredCapabilityConfig(config_bytes)
                )
            except (UnicodeError, ValueError) as exc:
                raise ConfigUpdateUnavailableError(
                    "Stored Builder capability authority is invalid"
                ) from exc
            resolved_registry = registry or load_registry(registry_root)
            target, provenance, resolved_stored = _builder_target(
                manifest,
                resolved_registry,
                capability_schema_version=capability_schema_version,
                capability_graph=stored_graph,
            )
            capability_refresh, _resulting_graph = _capability_refresh_payload(
                current,
                manifest,
                resolved_registry,
                stored_graph,
                resolved_stored,
            )
        elif source_kind == "preset":
            target, provenance = _preset_target(manifest, Path(configs_root))
        else:
            raise ConfigUpdateUnavailableError("Project config source kind is unsupported")
        additions: list[ConfigUpdateAddition] = []
        for section in sorted(target):
            for option in sorted(target[section]):
                if section in current and option in current[section]:
                    continue
                source_id, source_revision = provenance[(section, option)]
                additions.append(ConfigUpdateAddition(
                    section, option, _serialized_value(section, option, target[section][option]),
                    source_id, source_revision,
                ))
    except (RegistryError, CapabilityGraphError) as exc:
        raise ConfigUpdateRegistryError(
            f"Builder registry could not resolve the project update: {exc}"
        ) from exc
    except (BuilderConstraintError, PresetPolicyError, ConfigMaterializationError, CanonicalConfigError) as exc:
        raise ConfigUpdateUnavailableError("Registered project config update sources are invalid") from exc
    result = tuple(additions)
    config_meta = manifest.get("config")
    declared_digest = config_meta.get("sha256") if isinstance(config_meta, dict) else None
    declared_digest = declared_digest if isinstance(declared_digest, str) else None
    current_digest = _sha256(config_bytes)
    update_kind = (
        "combined"
        if result and capability_refresh is not None
        else "capability_refresh"
        if capability_refresh is not None
        else "additive"
    )
    merged = _merge_preview(current, result, capability_refresh)
    resulting_bytes = serialize_config(merged)
    assert_materialization_safe(resulting_bytes.decode("utf-8"))
    if len(resulting_bytes) > _MAX_CONFIG_ARTIFACT_BYTES:
        raise ConfigUpdateUnavailableError(
            "Resulting project config exceeds the canonical artifact size limit"
        )
    available = bool(result or capability_refresh is not None)
    preview_id = (
        _preview_id(config_bytes, manifest_bytes, result, capability_refresh)
        if available
        else None
    )
    preview = ConfigUpdatePreview(
        available,
        preview_id,
        result, config_path.name, current_digest, declared_digest,
        bool(declared_digest and declared_digest != current_digest),
        _sha256(resulting_bytes),
        update_kind,
        capability_refresh,
    )
    if available:
        trigger = max(
            result,
            key=lambda item: len(item.section.encode("utf-8")) + len(item.option.encode("utf-8")),
            default=None,
        )
        _build_transaction_artifacts(
            config_bytes,
            manifest_bytes,
            manifest,
            resulting_bytes,
            preview,
            trigger_section=trigger.section if trigger is not None else None,
            trigger_option=trigger.option if trigger is not None else None,
            application_revision=application_revision,
            resolved_at=datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc),
        )
    return preview


@contextmanager
def _amendment_lock(root: Path) -> Iterator[None]:
    descriptor = os.open(root / LOCK_NAME, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


@contextmanager
def project_config_update_preview_guard(
    working_directory: str | Path,
    *,
    registry: Registry | None = None,
    registry_root: str | Path = DEFAULT_PROFILES_ROOT,
    configs_root: str | Path = CONFIGS_ROOT,
    application_revision: str = "dev",
) -> Iterator[ConfigUpdatePreview]:
    """Recover, preview, and hold the project lock through caller acceptance."""

    root = Path(working_directory)
    with _amendment_lock(root):
        _recover_locked(root)
        yield _preview_project_config_update_locked(
            root,
            registry=registry,
            registry_root=registry_root,
            configs_root=configs_root,
            application_revision=application_revision,
        )


def preview_project_config_update(
    working_directory: str | Path,
    *,
    registry: Registry | None = None,
    registry_root: str | Path = DEFAULT_PROFILES_ROOT,
    configs_root: str | Path = CONFIGS_ROOT,
    application_revision: str = "dev",
) -> ConfigUpdatePreview:
    """Recover and resolve the complete delta without writing project authority."""

    with project_config_update_preview_guard(
        working_directory,
        registry=registry,
        registry_root=registry_root,
        configs_root=configs_root,
        application_revision=application_revision,
    ) as preview:
        return preview


def _write_temp(root: Path, prefix: str, content: bytes) -> Path:
    descriptor, raw_path = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=root)
    path = Path(raw_path)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        path.unlink(missing_ok=True)
        raise
    return path


def _fsync_directory(root: Path) -> None:
    descriptor = os.open(root, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _journal_bytes(config_prior: bytes, manifest_prior: bytes, config_result: bytes, manifest_result: bytes) -> bytes:
    payload = {
        "schema_version": 1,
        "config": {"prior_sha256": _sha256(config_prior), "result_sha256": _sha256(config_result),
                   "prior": b64encode(config_prior).decode("ascii"), "result": b64encode(config_result).decode("ascii")},
        "manifest": {"prior_sha256": _sha256(manifest_prior), "result_sha256": _sha256(manifest_result),
                     "prior": b64encode(manifest_prior).decode("ascii"), "result": b64encode(manifest_result).decode("ascii")},
    }
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _durable_capability_refresh(
    capability_refresh: Mapping[str, object],
) -> dict[str, object]:
    expected = {
        "locale_profile",
        "locales",
        "preserved_project_selections",
        "acknowledgment",
        "prior",
        "resulting",
        "changes",
    }
    if set(capability_refresh) != expected:
        raise ConfigUpdateUnavailableError("Capability refresh preview shape is invalid")
    return {
        "locale_profile": deepcopy(capability_refresh["locale_profile"]),
        "locales": deepcopy(capability_refresh["locales"]),
        "preserved_project_selections": deepcopy(
            capability_refresh["preserved_project_selections"]
        ),
        "acknowledgment_revision": CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION,
        "prior": deepcopy(capability_refresh["prior"]),
        "resulting": deepcopy(capability_refresh["resulting"]),
        "changes": deepcopy(capability_refresh["changes"]),
    }


def _build_amendment(
    preview: ConfigUpdatePreview,
    *,
    sequence: int,
    prior_digest: str,
    resulting_digest: str,
    trigger_section: str | None,
    trigger_option: str | None,
    application_revision: str,
    resolved_at: datetime,
) -> dict[str, object]:
    if preview.preview_id is None:
        raise ConfigUpdateUnavailableError("Available project config preview has no identity")
    timestamp = resolved_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    amendment: dict[str, object] = {
        "sequence": sequence,
        "kind": preview.update_kind,
        "preview_id": preview.preview_id,
        "applied_at": timestamp,
        "application_revision": application_revision,
        "resolver_version": 1,
        "prior_sha256": prior_digest,
        "resulting_sha256": resulting_digest,
    }
    if preview.additions:
        if not trigger_section or not trigger_option:
            raise ConfigUpdateUnavailableError("Additive update trigger is incomplete")
        amendment.update({
            "trigger": {"section": trigger_section, "option": trigger_option},
            "additions": _addition_payload(preview.additions),
            "reason": "missing_registered_attribute_merge",
        })
    if preview.capability_refresh is not None:
        amendment["capability_refresh"] = _durable_capability_refresh(
            preview.capability_refresh
        )
    return amendment


def _build_transaction_artifacts(
    config_prior: bytes,
    manifest_prior: bytes,
    manifest: Mapping[str, object],
    config_result: bytes,
    preview: ConfigUpdatePreview,
    *,
    trigger_section: str | None,
    trigger_option: str | None,
    application_revision: str,
    resolved_at: datetime,
) -> tuple[bytes, bytes]:
    """Build and bound the exact durable manifest and reversible journal."""

    prior_digest = _sha256(config_prior)
    resulting_digest = _sha256(config_result)
    projected_manifest = deepcopy(dict(manifest))
    amendments = projected_manifest.get("amendments")
    config_meta = projected_manifest.get("config")
    if not isinstance(amendments, list) or not isinstance(config_meta, dict):
        raise ConfigUpdateUnavailableError("Project config manifest is incomplete")
    amendments.append(_build_amendment(
        preview,
        sequence=len(amendments) + 1,
        prior_digest=prior_digest,
        resulting_digest=resulting_digest,
        trigger_section=trigger_section,
        trigger_option=trigger_option,
        application_revision=application_revision,
        resolved_at=resolved_at,
    ))
    config_meta["sha256"] = resulting_digest
    manifest_result = (
        json.dumps(projected_manifest, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    journal_result = _journal_bytes(
        config_prior, manifest_prior, config_result, manifest_result
    )
    artifacts = {
        "prior project config": config_prior,
        "prior project config manifest": manifest_prior,
        "resulting project config": config_result,
        "resulting project config manifest": manifest_result,
        "pending amendment journal": journal_result,
    }
    for label, content in artifacts.items():
        if len(content) > _MAX_CONFIG_ARTIFACT_BYTES:
            raise ConfigUpdateUnavailableError(
                f"{label.capitalize()} exceeds the canonical artifact size limit"
            )
    try:
        assert_materialization_safe(
            config_result.decode("utf-8"), manifest_result.decode("utf-8")
        )
    except (UnicodeError, ConfigMaterializationError) as exc:
        raise ConfigUpdateUnavailableError(
            "Generated config amendment artifacts are unsafe"
        ) from exc
    return manifest_result, journal_result


def _decode_journal(journal_bytes: bytes) -> tuple[bytes, bytes, bytes, bytes]:
    if len(journal_bytes) > _MAX_CONFIG_ARTIFACT_BYTES:
        raise ConfigUpdateError("Pending config amendment journal exceeds the canonical artifact size limit")
    try:
        payload = json.loads(journal_bytes.decode("utf-8"))
        if (
            not isinstance(payload, dict)
            or isinstance(payload.get("schema_version"), bool)
            or not isinstance(payload.get("schema_version"), int)
            or payload.get("schema_version") != 1
            or set(payload) != {"schema_version", "config", "manifest"}
        ):
            raise ValueError("shape")
        images: list[bytes] = []
        for name in ("config", "manifest"):
            item = payload[name]
            if not isinstance(item, dict) or set(item) != {"prior_sha256", "result_sha256", "prior", "result"}:
                raise ValueError("shape")
            for state in ("prior", "result"):
                image = b64decode(item[state], validate=True)
                if _sha256(image) != item[f"{state}_sha256"]:
                    raise ValueError("digest")
                images.append(image)
    except (KeyError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigUpdateError("Pending config amendment journal is invalid") from exc
    return images[0], images[1], images[2], images[3]


def _replace_bytes(root: Path, destination: Path, content: bytes) -> None:
    temporary = _write_temp(root, f".{destination.name}.recovery.", content)
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _recover_locked(root: Path) -> bool:
    journal_path = root / JOURNAL_NAME
    if not journal_path.exists():
        return False
    try:
        journal_bytes = journal_path.read_bytes()
    except OSError as exc:
        raise ConfigUpdateUnavailableError(
            "Pending config amendment journal is unavailable"
        ) from exc
    config_prior, config_result, manifest_prior, manifest_result = _decode_journal(
        journal_bytes
    )
    try:
        manifest_payloads = [
            json.loads(content.decode("utf-8"))
            for content in (manifest_prior, manifest_result)
        ]
        filenames: list[str] = []
        config_images = (config_prior, config_result)
        for index, manifest_payload in enumerate(manifest_payloads):
            if not isinstance(manifest_payload, dict):
                raise ValueError("manifest shape")
            if (
                isinstance(manifest_payload.get("schema_version"), bool)
                or not isinstance(manifest_payload.get("schema_version"), int)
                or manifest_payload.get("schema_version") != 1
                or isinstance(manifest_payload.get("resolver_version"), bool)
                or not isinstance(manifest_payload.get("resolver_version"), int)
                or manifest_payload.get("resolver_version") != 1
                or not isinstance(manifest_payload.get("parent_chain"), list)
                or not manifest_payload["parent_chain"]
                or not isinstance(manifest_payload.get("selections"), dict)
                or not isinstance(manifest_payload.get("amendments"), list)
            ):
                raise ValueError("manifest schema")
            config_meta = manifest_payload.get("config")
            filename = config_meta.get("filename") if isinstance(config_meta, dict) else None
            if (
                not isinstance(filename, str)
                or Path(filename).name != filename
                or filename in {"", ".", ".."}
            ):
                raise ValueError("filename")
            declared_config_digest = config_meta.get("sha256")
            if not _is_sha256(declared_config_digest):
                raise ValueError("config digest")
            if index == 1 and declared_config_digest != _sha256(config_images[index]):
                raise ValueError("config digest")
            _validate_capability_amendments(manifest_payload["amendments"])
            filenames.append(filename)
        if len(set(filenames)) != 1:
            raise ValueError("config filename changed")
        if len(config_prior) > _MAX_CONFIG_ARTIFACT_BYTES or len(config_result) > _MAX_CONFIG_ARTIFACT_BYTES:
            raise ValueError("config size")
        if len(manifest_prior) > _MAX_CONFIG_ARTIFACT_BYTES or len(manifest_result) > _MAX_CONFIG_ARTIFACT_BYTES:
            raise ValueError("manifest size")
        assert_materialization_safe(
            config_prior.decode("utf-8"), manifest_prior.decode("utf-8")
        )
        assert_materialization_safe(
            config_result.decode("utf-8"), manifest_result.decode("utf-8")
        )
        parse_config_text(config_prior.decode("utf-8"))
        parse_config_text(config_result.decode("utf-8"))
    except (AttributeError, UnicodeError, ValueError, json.JSONDecodeError, ConfigMaterializationError) as exc:
        raise ConfigUpdateError("Pending config amendment journal artifacts are invalid") from exc
    config_path = root / filenames[0]
    manifest_path = root / MANIFEST_NAME
    try:
        config_current = config_path.read_bytes()
        manifest_current = manifest_path.read_bytes()
    except OSError as exc:
        raise ConfigUpdateUnavailableError(
            "Pending config amendment target artifacts are unavailable"
        ) from exc
    pair = (_sha256(config_current), _sha256(manifest_current))
    prior_pair = (_sha256(config_prior), _sha256(manifest_prior))
    result_pair = (_sha256(config_result), _sha256(manifest_result))
    if pair == prior_pair or pair == result_pair:
        journal_path.unlink()
    elif pair == (result_pair[0], prior_pair[1]):
        _replace_bytes(root, manifest_path, manifest_result)
        journal_path.unlink()
    elif pair == (prior_pair[0], result_pair[1]):
        _replace_bytes(root, manifest_path, manifest_prior)
        journal_path.unlink()
    else:
        raise ConfigUpdateError("Pending config amendment does not match either recorded state")
    _fsync_directory(root)
    return True


def recover_project_config_update(working_directory: str | Path) -> bool:
    root = Path(working_directory)
    if not (root / JOURNAL_NAME).exists():
        return False
    with _amendment_lock(root):
        return _recover_locked(root)


@contextmanager
def project_config_lifecycle_guard(working_directory: str | Path) -> Iterator[None]:
    """Recover and hold the amendment lock across one lifecycle operation."""

    root = Path(working_directory)
    with _amendment_lock(root):
        _recover_locked(root)
        yield


def _idempotent_result(
    root: Path,
    preview_id: str,
) -> ConfigUpdateResult | None:
    _path, config_bytes, _manifest_bytes, manifest = _read_artifacts(root)
    amendments = manifest.get("amendments")
    if not isinstance(amendments, list) or not amendments:
        return None
    latest = amendments[-1]
    if not isinstance(latest, dict) or latest.get("preview_id") != preview_id:
        return None
    prior = latest.get("prior_sha256")
    resulting = latest.get("resulting_sha256")
    sequence = latest.get("sequence")
    if (
        not isinstance(prior, str)
        or not isinstance(resulting, str)
        or isinstance(sequence, bool)
        or not isinstance(sequence, int)
    ):
        raise ConfigUpdateUnavailableError(
            "Latest matching config amendment is incomplete"
        )
    if _sha256(config_bytes) != resulting:
        raise ConfigUpdateUnavailableError(
            "Latest matching config amendment does not match the current config digest"
        )
    kind = latest.get("kind", "additive")
    if kind not in {"additive", "capability_refresh", "combined"}:
        raise ConfigUpdateUnavailableError("Latest config amendment kind is invalid")
    return ConfigUpdateResult(
        True,
        sequence,
        prior,
        resulting,
        (),
        True,
        str(kind),
    )


def project_config_update_reconciliation(
    working_directory: str | Path,
    preview_id: str,
) -> ConfigUpdateResult | None:
    """Recover pending state and return an exact latest-preview commit match."""

    root = Path(working_directory)
    try:
        with _amendment_lock(root):
            _recover_locked(root)
            return _idempotent_result(root, preview_id)
    except OSError as exc:
        raise ConfigUpdateUnavailableError(
            "Project config reconciliation is unavailable"
        ) from exc


def project_config_update_status(
    working_directory: str | Path,
) -> ConfigUpdateStatus:
    """Return digest and latest amendment reconciliation metadata."""

    root = Path(working_directory)
    try:
        with _amendment_lock(root):
            _recover_locked(root)
            config_path, config_bytes, _manifest_bytes, manifest = _read_artifacts(root)
    except OSError as exc:
        raise ConfigUpdateUnavailableError("Project config status is unavailable") from exc
    amendments = manifest.get("amendments")
    latest = amendments[-1] if isinstance(amendments, list) and amendments else None
    last_update: dict[str, object] | None = None
    if isinstance(latest, dict):
        sequence = latest.get("sequence")
        prior = latest.get("prior_sha256")
        resulting = latest.get("resulting_sha256")
        kind = latest.get("kind", "additive")
        preview_id = latest.get("preview_id")
        if (
            isinstance(sequence, int)
            and not isinstance(sequence, bool)
            and isinstance(prior, str)
            and isinstance(resulting, str)
            and kind in {"additive", "capability_refresh", "combined"}
            and (preview_id is None or isinstance(preview_id, str))
        ):
            last_update = {
                "sequence": sequence,
                "kind": kind,
                "preview_id": preview_id,
                "prior_sha256": prior,
                "resulting_sha256": resulting,
            }
    return ConfigUpdateStatus(_sha256(config_bytes), last_update, config_path.name)


def apply_project_config_update(
    working_directory: str | Path, preview_id: str, *, trigger_section: str | None = None,
    trigger_option: str | None = None, application_revision: str,
    capability_acknowledgment_accepted: bool = False,
    capability_acknowledgment_revision: str | None = None,
    registry: Registry | None = None, registry_root: str | Path = DEFAULT_PROFILES_ROOT,
    configs_root: str | Path = CONFIGS_ROOT,
    resolved_at: datetime | None = None,
    fault_hook: Callable[[str], None] | None = None,
) -> ConfigUpdateResult:
    """Revalidate and atomically apply one reviewed project amendment."""

    if not preview_id or not application_revision:
        raise ConfigUpdateError("Preview and application revision are required")
    if bool(trigger_section) != bool(trigger_option):
        raise ConfigUpdateError("Trigger section and option must be supplied together")
    root = Path(working_directory)
    with _amendment_lock(root):
        _recover_locked(root)
        recovered = _idempotent_result(root, preview_id)
        if recovered is not None:
            return recovered
        preview = _preview_project_config_update_locked(
            root,
            registry=registry,
            registry_root=registry_root,
            configs_root=configs_root,
            application_revision=application_revision,
        )
        if not preview.available or preview.preview_id is None:
            raise ConfigUpdateUnavailableError("No registered project config update is available")
        if preview.preview_id != preview_id:
            raise StaleConfigPreviewError("Project config preview is stale; refresh before applying")
        if preview.additions and not any(
            item.section == trigger_section and item.option == trigger_option
            for item in preview.additions
        ):
            raise ConfigUpdateUnavailableError(
                "Trigger does not identify a registered missing attribute in this preview"
            )
        if not preview.additions and (trigger_section is not None or trigger_option is not None):
            raise ConfigUpdateUnavailableError(
                "Capability-only refresh does not accept an additive trigger"
            )
        if preview.capability_refresh is not None:
            if (
                capability_acknowledgment_accepted is not True
                or capability_acknowledgment_revision
                != CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION
            ):
                raise ConfigUpdateAcknowledgmentError(
                    "The exact capability refresh acknowledgment is required"
                )
        elif capability_acknowledgment_accepted or capability_acknowledgment_revision is not None:
            raise ConfigUpdateError(
                "Capability acknowledgment is not accepted for an additive-only update"
            )
        config_path, config_prior, manifest_prior, manifest = _read_artifacts(root)
        current = parse_config_text(config_prior.decode("utf-8"))
        for addition in preview.additions:
            if addition.section in current and addition.option in current[addition.section]:
                raise StaleConfigPreviewError("Project config changed while applying the preview")
        merged = _merge_preview(current, preview.additions, preview.capability_refresh)
        config_result = serialize_config(merged)
        assert_materialization_safe(config_result.decode("utf-8"))
        prior_digest = _sha256(config_prior)
        resulting_digest = _sha256(config_result)
        amendments = manifest["amendments"]
        assert isinstance(amendments, list)
        sequence = len(amendments) + 1
        manifest_result, journal_result = _build_transaction_artifacts(
            config_prior,
            manifest_prior,
            manifest,
            config_result,
            preview,
            trigger_section=trigger_section,
            trigger_option=trigger_option,
            application_revision=application_revision,
            resolved_at=resolved_at or datetime.now(timezone.utc),
        )
        config_temp = _write_temp(root, f".{config_path.name}.amendment.", config_result)
        manifest_temp = _write_temp(root, ".config-manifest.json.amendment.", manifest_result)
        journal_temp: Path | None = None
        try:
            journal_temp = _write_temp(root, ".config-amendment.journal.", journal_result)
            os.replace(journal_temp, root / JOURNAL_NAME)
            journal_temp = None
            _fsync_directory(root)
            if fault_hook is not None:
                fault_hook("journal_committed")
            os.replace(config_temp, config_path)
            config_temp = None  # type: ignore[assignment]
            if fault_hook is not None:
                fault_hook("config_replaced")
            os.replace(manifest_temp, root / MANIFEST_NAME)
            manifest_temp = None  # type: ignore[assignment]
            if fault_hook is not None:
                fault_hook("manifest_replaced")
            (root / JOURNAL_NAME).unlink()
            _fsync_directory(root)
        finally:
            if config_temp is not None:
                config_temp.unlink(missing_ok=True)
            if manifest_temp is not None:
                manifest_temp.unlink(missing_ok=True)
            if journal_temp is not None:
                journal_temp.unlink(missing_ok=True)
        return ConfigUpdateResult(
            True,
            sequence,
            prior_digest,
            resulting_digest,
            preview.additions,
            False,
            preview.update_kind,
        )
