"""Read-only previews and crash-recoverable project config amendments."""

from __future__ import annotations

from base64 import b64decode, b64encode
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import MappingProxyType
from typing import Callable, Iterator, Mapping

from wepppy.nodb.config_builder.registry import DEFAULT_PROFILES_ROOT, RegistryError, load_registry
from wepppy.nodb.config_builder.resolver import BuilderConstraintError, resolve_builder_config
from wepppy.nodb.config_builder.schema import BuilderSelections, Registry
from wepppy.nodb.project_config_snapshot import CONFIGS_ROOT, PresetPolicyError, load_preset_policies
from wepppy.project_config_sanitization import ConfigMaterializationError, assert_materialization_safe, scan_manifest_text
from wepppy.project_config_serialization import CanonicalConfigError, CanonicalValue, parse_config_text, serialize_config

__all__ = [
    "CONFIG_UPDATE_FLAG",
    "ConfigUpdateAddition",
    "ConfigUpdateError",
    "ConfigUpdatePreview",
    "ConfigUpdateResult",
    "ConfigUpdateUnavailableError",
    "StaleConfigPreviewError",
    "apply_project_config_update",
    "preview_project_config_update",
    "project_config_digest_warning",
    "project_config_lifecycle_guard",
    "project_config_update_enabled",
    "recover_project_config_update",
]

CONFIG_UPDATE_FLAG = "WEPPPY_PROJECT_CONFIG_UPDATE_ENABLED"
MANIFEST_NAME = "config-manifest.json"
JOURNAL_NAME = ".config-amendment.pending.json"
LOCK_NAME = ".config-amendment.lock"
_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"", "0", "false", "no", "off"})


class ConfigUpdateError(ValueError):
    """Base error for a rejected or failed project config update."""


class ConfigUpdateUnavailableError(ConfigUpdateError):
    """Raised when no safe registered update can be produced."""


class StaleConfigPreviewError(ConfigUpdateError):
    """Raised when an apply request no longer matches the complete preview."""


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


@dataclass(frozen=True, slots=True)
class ConfigUpdateResult:
    applied: bool
    sequence: int | None
    prior_digest: str
    resulting_digest: str
    additions: tuple[ConfigUpdateAddition, ...]


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

    _path, config_bytes, _manifest_bytes, manifest = _read_artifacts(Path(working_directory))
    config_meta = manifest.get("config")
    declared = config_meta.get("sha256") if isinstance(config_meta, dict) else None
    return isinstance(declared, str) and declared != _sha256(config_bytes)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read_artifacts(root: Path) -> tuple[Path, bytes, bytes, dict[str, object]]:
    manifest_path = root / MANIFEST_NAME
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigUpdateUnavailableError("Project config manifest is unavailable or malformed") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or manifest.get("resolver_version") != 1:
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
        parse_config_text(config_bytes.decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ConfigUpdateUnavailableError("Project-owned config is unavailable or invalid") from exc
    if not isinstance(manifest.get("parent_chain"), list) or not manifest["parent_chain"]:
        raise ConfigUpdateUnavailableError("Project config parent chain is invalid")
    if not isinstance(manifest.get("selections"), dict) or not isinstance(manifest.get("amendments"), list):
        raise ConfigUpdateUnavailableError("Project config manifest is incomplete")
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
    override = effective if source == "privileged_override" else None
    if override is not None and (isinstance(override, bool) or not isinstance(override, int)):
        raise ConfigUpdateUnavailableError("Builder cell-size selection is invalid")
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
    manifest: Mapping[str, object], registry: Registry, *, capability_schema_version: int,
) -> tuple[dict[str, dict[str, CanonicalValue]], dict[tuple[str, str], tuple[str, str]]]:
    selections = _builder_selections(
        manifest["selections"],  # type: ignore[arg-type,index]
        capability_schema_version=capability_schema_version,
    )
    resolved = resolve_builder_config(
        selections,
        registry=registry,
        capability_schema_version=capability_schema_version,
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
    return deepcopy({section: dict(options) for section, options in resolved.config.items()}), provenance


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


def _preview_id(config_bytes: bytes, manifest_bytes: bytes, additions: tuple[ConfigUpdateAddition, ...]) -> str:
    payload = json.dumps(
        [addition.__dict__ if hasattr(addition, "__dict__") else {
            "section": addition.section, "option": addition.option, "value": addition.value,
            "source_id": addition.source_id, "source_revision": addition.source_revision,
        } for addition in additions],
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(config_bytes + b"\0" + manifest_bytes + b"\0" + payload).hexdigest()
    return f"pcu1-{digest}"


def preview_project_config_update(
    working_directory: str | Path, *, registry: Registry | None = None,
    registry_root: str | Path = DEFAULT_PROFILES_ROOT,
    configs_root: str | Path = CONFIGS_ROOT,
) -> ConfigUpdatePreview:
    """Resolve the complete merge-only delta without writing any file."""

    root = Path(working_directory)
    config_path, config_bytes, manifest_bytes, manifest = _read_artifacts(root)
    current = parse_config_text(config_bytes.decode("utf-8"))
    source_kind = manifest.get("source_kind")
    try:
        if source_kind == "builder":
            capability_schema_version = current.get("capabilities", {}).get(
                "schema_version", 2
            )
            if (
                isinstance(capability_schema_version, bool)
                or not isinstance(capability_schema_version, int)
                or capability_schema_version not in {2, 3}
            ):
                raise ConfigUpdateUnavailableError(
                    "Stored Builder capability schema is unsupported"
                )
            target, provenance = _builder_target(
                manifest,
                registry or load_registry(registry_root),
                capability_schema_version=capability_schema_version,
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
    except (BuilderConstraintError, RegistryError, PresetPolicyError, ConfigMaterializationError, CanonicalConfigError) as exc:
        raise ConfigUpdateUnavailableError("Registered project config update sources are invalid") from exc
    result = tuple(additions)
    config_meta = manifest.get("config")
    declared_digest = config_meta.get("sha256") if isinstance(config_meta, dict) else None
    declared_digest = declared_digest if isinstance(declared_digest, str) else None
    current_digest = _sha256(config_bytes)
    return ConfigUpdatePreview(
        bool(result), _preview_id(config_bytes, manifest_bytes, result) if result else None,
        result, config_path.name, current_digest, declared_digest,
        bool(declared_digest and declared_digest != current_digest),
    )


@contextmanager
def _amendment_lock(root: Path) -> Iterator[None]:
    descriptor = os.open(root / LOCK_NAME, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


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


def _decode_journal(journal_bytes: bytes) -> tuple[bytes, bytes, bytes, bytes]:
    try:
        payload = json.loads(journal_bytes.decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") != 1 or set(payload) != {"schema_version", "config", "manifest"}:
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
    config_prior, config_result, manifest_prior, manifest_result = _decode_journal(journal_path.read_bytes())
    manifest_payload = json.loads(manifest_result.decode("utf-8"))
    config_path = root / manifest_payload["config"]["filename"]
    manifest_path = root / MANIFEST_NAME
    config_current = config_path.read_bytes()
    manifest_current = manifest_path.read_bytes()
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


def apply_project_config_update(
    working_directory: str | Path, preview_id: str, *, trigger_section: str,
    trigger_option: str, application_revision: str,
    registry: Registry | None = None, registry_root: str | Path = DEFAULT_PROFILES_ROOT,
    configs_root: str | Path = CONFIGS_ROOT,
    resolved_at: datetime | None = None,
    fault_hook: Callable[[str], None] | None = None,
) -> ConfigUpdateResult:
    """Revalidate and atomically apply one reviewed merge-only amendment."""

    if not preview_id or not trigger_section or not trigger_option or not application_revision:
        raise ConfigUpdateError("Preview, trigger, and application revision are required")
    root = Path(working_directory)
    with _amendment_lock(root):
        _recover_locked(root)
        preview = preview_project_config_update(
            root, registry=registry, registry_root=registry_root, configs_root=configs_root,
        )
        if not preview.available or preview.preview_id is None:
            raise ConfigUpdateUnavailableError("No registered project config update is available")
        if preview.preview_id != preview_id:
            raise StaleConfigPreviewError("Project config preview is stale; refresh before applying")
        if not any(
            item.section == trigger_section and item.option == trigger_option
            for item in preview.additions
        ):
            raise ConfigUpdateUnavailableError(
                "Trigger does not identify a registered missing attribute in this preview"
            )
        config_path, config_prior, manifest_prior, manifest = _read_artifacts(root)
        merged = parse_config_text(config_prior.decode("utf-8"))
        for addition in preview.additions:
            if addition.section in merged and addition.option in merged[addition.section]:
                raise StaleConfigPreviewError("Project config changed while applying the preview")
            parsed_value = parse_config_text(
                f"[{addition.section}]\n{addition.option} = {addition.value}\n"
            )[addition.section][addition.option]
            merged.setdefault(addition.section, {})[addition.option] = parsed_value
        config_result = serialize_config(merged)
        assert_materialization_safe(config_result.decode("utf-8"))
        prior_digest = _sha256(config_prior)
        resulting_digest = _sha256(config_result)
        amendments = manifest["amendments"]
        sequence = len(amendments) + 1
        timestamp = (resolved_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        amendment = {
            "sequence": sequence, "applied_at": timestamp,
            "application_revision": application_revision, "resolver_version": 1,
            "trigger": {"section": trigger_section, "option": trigger_option},
            "additions": [
                {"section": item.section, "option": item.option, "value": item.value,
                 "source_id": item.source_id, "source_revision": item.source_revision}
                for item in preview.additions
            ],
            "prior_sha256": prior_digest, "resulting_sha256": resulting_digest,
            "reason": "missing_registered_attribute_merge",
        }
        amendments.append(amendment)
        manifest["config"]["sha256"] = resulting_digest  # type: ignore[index]
        manifest_result = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        if scan_manifest_text(manifest_result.decode("utf-8"), source=MANIFEST_NAME):
            raise ConfigUpdateError("Generated amendment manifest is unsafe")
        config_temp = _write_temp(root, f".{config_path.name}.amendment.", config_result)
        manifest_temp = _write_temp(root, ".config-manifest.json.amendment.", manifest_result)
        journal_temp: Path | None = None
        try:
            journal_temp = _write_temp(root, ".config-amendment.journal.", _journal_bytes(config_prior, manifest_prior, config_result, manifest_result))
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
        return ConfigUpdateResult(True, sequence, prior_digest, resulting_digest, preview.additions)
