"""Default-off named-preset resolution and initial project materialization."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import tomllib
from types import MappingProxyType
from typing import Mapping

from wepppy.project_config_sanitization import (
    assert_materialization_safe,
    scan_manifest_text,
)
from wepppy.project_config_serialization import (
    CanonicalValue,
    parse_config_text,
    serialize_config,
)

__all__ = [
    "PRESET_WRITER_FLAG",
    "PresetPolicy",
    "PresetPolicyError",
    "PresetSnapshotCandidate",
    "PresetSnapshotError",
    "load_preset_policies",
    "materialize_preset_snapshot",
    "preset_writer_enabled",
    "resolve_preset_snapshot",
]

PRESET_WRITER_FLAG = "WEPPPY_PROJECT_CONFIG_PRESET_WRITER_ENABLED"
CONFIGS_ROOT = Path(__file__).with_name("configs")
POLICIES_PATH = Path(__file__).with_name("config_builder") / "preset_policies.toml"
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"", "0", "false", "no", "off"})
_PRESET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_OVERRIDE_VALIDATORS: Mapping[str, tuple[str, frozenset[str]]] = MappingProxyType(
    {
        "general.dem_db": ("string", frozenset({"ned1/2016"})),
        "unitizer.is_english": ("boolean", frozenset({"true", "false"})),
        "watershed.delineation_backend": ("string", frozenset({"wbt"})),
        "nodb.apply_nodir": ("boolean", frozenset({"true", "false"})),
    }
)


class PresetPolicyError(ValueError):
    """Raised when checked-in preset policy definitions are incomplete."""


class PresetSnapshotError(ValueError):
    """Raised when a named preset cannot be safely snapshotted."""


@dataclass(frozen=True, slots=True)
class PresetPolicy:
    preset_id: str
    overrides: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PresetSnapshotCandidate:
    preset_id: str
    config_filename: str
    config_bytes: bytes
    manifest_bytes: bytes
    normalized_overrides: Mapping[str, CanonicalValue]
    source_revision: str


def preset_writer_enabled(environ: Mapping[str, str] | None = None) -> bool:
    source = os.environ if environ is None else environ
    raw = source.get(PRESET_WRITER_FLAG, "").strip().casefold()
    if raw in _TRUE_VALUES:
        return True
    if raw in _FALSE_VALUES:
        return False
    raise ValueError(
        f"{PRESET_WRITER_FLAG} must be one of 1/true/yes/on or 0/false/no/off"
    )


def load_preset_policies(
    policies_path: str | Path = POLICIES_PATH,
    *,
    configs_root: str | Path = CONFIGS_ROOT,
) -> Mapping[str, PresetPolicy]:
    source = Path(policies_path)
    try:
        payload = tomllib.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise PresetPolicyError(f"Unable to parse preset policies: {source}") from exc
    if set(payload) != {"schema_version", "presets"} or payload["schema_version"] != 1:
        raise PresetPolicyError("Preset policies require exact schema version 1 fields")
    entries = payload["presets"]
    if not isinstance(entries, list):
        raise PresetPolicyError("Preset policies must contain an array of preset tables")
    policies: dict[str, PresetPolicy] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != {"id", "overrides"}:
            raise PresetPolicyError(f"Preset policy {index} has invalid fields")
        preset_id = entry["id"]
        overrides = entry["overrides"]
        if not isinstance(preset_id, str) or _PRESET_ID_RE.fullmatch(preset_id) is None:
            raise PresetPolicyError(f"Preset policy {index} has invalid ID")
        if preset_id in policies:
            raise PresetPolicyError(f"Duplicate preset policy: {preset_id}")
        if not isinstance(overrides, list) or not all(isinstance(item, str) for item in overrides):
            raise PresetPolicyError(f"Preset {preset_id} overrides must be strings")
        override_tuple = tuple(overrides)
        if len(set(override_tuple)) != len(override_tuple):
            raise PresetPolicyError(f"Preset {preset_id} has duplicate overrides")
        unknown = set(override_tuple) - set(_OVERRIDE_VALIDATORS)
        if unknown:
            raise PresetPolicyError(f"Preset {preset_id} has unknown validators: {sorted(unknown)}")
        policies[preset_id] = PresetPolicy(preset_id, override_tuple)

    config_ids = {
        path.stem
        for path in Path(configs_root).glob("*.cfg")
        if path.stem != "_defaults"
    }
    if set(policies) != config_ids:
        missing = sorted(config_ids - set(policies))
        stale = sorted(set(policies) - config_ids)
        raise PresetPolicyError(f"Preset policy corpus mismatch; missing={missing}, stale={stale}")
    return MappingProxyType(policies)


def _normalize_override(key: str, raw_value: object) -> CanonicalValue:
    validator_kind, allowed = _OVERRIDE_VALIDATORS[key]
    if isinstance(raw_value, (list, tuple)):
        if len(raw_value) != 1:
            raise PresetSnapshotError(f"Override {key!r} must have exactly one value")
        raw_value = raw_value[0]
    token = str(raw_value).strip()
    if token not in allowed:
        raise PresetSnapshotError(f"Override {key!r} has an unsupported value")
    if validator_kind == "boolean":
        return token == "true"
    return token


def _normalized_overrides(
    policy: PresetPolicy,
    overrides: Mapping[str, object],
) -> dict[str, CanonicalValue]:
    normalized: dict[str, CanonicalValue] = {}
    for raw_key, raw_value in overrides.items():
        key = str(raw_key).strip().replace(":", ".")
        if raw_value is None or raw_value == "":
            continue
        if key not in policy.overrides:
            raise PresetSnapshotError(f"Unknown durable query override: {raw_key}")
        if key in normalized:
            raise PresetSnapshotError(f"Duplicate durable query override: {raw_key}")
        normalized[key] = _normalize_override(key, raw_value)
    return normalized


def _merge_config(
    defaults: Mapping[str, Mapping[str, CanonicalValue]],
    preset: Mapping[str, Mapping[str, CanonicalValue]],
) -> dict[str, dict[str, CanonicalValue]]:
    result = deepcopy({section: dict(options) for section, options in defaults.items()})
    for section, options in preset.items():
        result.setdefault(section, {}).update(deepcopy(dict(options)))
    return result


def _manifest_bytes(
    *,
    preset_id: str,
    config_filename: str,
    config_digest: str,
    source_revision: str,
    defaults_revision: str,
    preset_revision: str,
    resolved_at: datetime,
    overrides: Mapping[str, CanonicalValue],
) -> bytes:
    timestamp = resolved_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {
        "schema_version": 1,
        "resolver_version": 1,
        "source_kind": "preset",
        "source_preset": preset_id,
        "source_revision": source_revision,
        "resolved_at": timestamp,
        "parent_chain": [
            {"kind": "defaults", "id": "shared-defaults", "revision": defaults_revision},
            {"kind": "preset", "id": preset_id, "revision": preset_revision},
        ],
        "selections": {
            "overrides": {
                key: {"value": value, "source": "query"}
                for key, value in sorted(overrides.items())
            }
        },
        "config": {"filename": config_filename, "sha256": config_digest},
        "amendments": [],
    }
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    violations = scan_manifest_text(text, source="config-manifest.json")
    if violations:
        raise PresetSnapshotError("Generated manifest failed materialization safety checks")
    return text.encode("utf-8")


def resolve_preset_snapshot(
    preset_id: str,
    overrides: Mapping[str, object],
    *,
    source_revision: str,
    resolved_at: datetime | None = None,
    configs_root: str | Path = CONFIGS_ROOT,
    policies: Mapping[str, PresetPolicy] | None = None,
) -> PresetSnapshotCandidate:
    root = Path(configs_root)
    resolved_policies = load_preset_policies(configs_root=root) if policies is None else policies
    policy = resolved_policies.get(preset_id)
    if policy is None:
        raise PresetSnapshotError(f"Unsupported named preset: {preset_id}")
    if not source_revision.strip():
        raise PresetSnapshotError("Deployment source revision is required")
    defaults_path = root / "_defaults.cfg"
    preset_path = root / f"{preset_id}.cfg"
    try:
        defaults_bytes = defaults_path.read_bytes()
        preset_bytes = preset_path.read_bytes()
        defaults = parse_config_text(defaults_bytes.decode("utf-8"))
        preset = parse_config_text(preset_bytes.decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise PresetSnapshotError(f"Unable to resolve named preset: {preset_id}") from exc
    normalized = _normalized_overrides(policy, overrides)
    config = _merge_config(defaults, preset)
    for key, value in normalized.items():
        section, option = key.rsplit(".", 1)
        if section not in config or option not in config[section]:
            raise PresetSnapshotError(f"Override target is absent from resolved preset: {key}")
        config[section][option] = value
    config.setdefault("config", {}).update(
        {"flattened": True, "resolver_version": 1, "schema_version": 1}
    )
    config_bytes = serialize_config(config)
    assert_materialization_safe(config_bytes.decode("utf-8"))
    config_filename = f"{preset_id}.cfg"
    manifest_bytes = _manifest_bytes(
        preset_id=preset_id,
        config_filename=config_filename,
        config_digest=hashlib.sha256(config_bytes).hexdigest(),
        source_revision=source_revision,
        defaults_revision=hashlib.sha256(defaults_bytes).hexdigest(),
        preset_revision=hashlib.sha256(preset_bytes).hexdigest(),
        resolved_at=resolved_at or datetime.now(timezone.utc),
        overrides=normalized,
    )
    return PresetSnapshotCandidate(
        preset_id,
        config_filename,
        config_bytes,
        manifest_bytes,
        MappingProxyType(dict(normalized)),
        source_revision,
    )


def _write_temp(directory: Path, prefix: str, content: bytes) -> Path:
    descriptor, raw_path = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=directory)
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


def materialize_preset_snapshot(
    working_directory: str | Path,
    candidate: PresetSnapshotCandidate,
) -> tuple[Path, Path]:
    root = Path(working_directory)
    if not root.is_dir():
        raise PresetSnapshotError("Snapshot working directory must already exist")
    config_path = root / candidate.config_filename
    manifest_path = root / "config-manifest.json"
    if config_path.exists() or manifest_path.exists():
        raise PresetSnapshotError("Project configuration artifacts already exist")
    config_temp: Path | None = None
    manifest_temp: Path | None = None
    config_committed = False
    try:
        config_temp = _write_temp(root, f".{candidate.config_filename}.", candidate.config_bytes)
        manifest_temp = _write_temp(root, ".config-manifest.json.", candidate.manifest_bytes)
        os.replace(config_temp, config_path)
        config_temp = None
        config_committed = True
        os.replace(manifest_temp, manifest_path)
        manifest_temp = None
        directory_fd = os.open(root, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        if config_committed and not manifest_path.exists():
            config_path.unlink(missing_ok=True)
        raise PresetSnapshotError("Unable to durably materialize project configuration") from exc
    finally:
        if config_temp is not None:
            config_temp.unlink(missing_ok=True)
        if manifest_temp is not None:
            manifest_temp.unlink(missing_ok=True)
    return config_path, manifest_path
