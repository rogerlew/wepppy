"""Read-only resolution for legacy and project-owned NoDb configuration."""

from __future__ import annotations

from configparser import Error as ConfigParserError, RawConfigParser
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import re
from typing import Callable

from wepppy.project_config_sanitization import scan_manifest_text

__all__ = [
    "PROJECT_CONFIG_READER_FLAG",
    "ProjectConfigAuthorityError",
    "ProjectConfigError",
    "ProjectConfigLoadResult",
    "ProjectConfigSchemaError",
    "ProjectConfigStatus",
    "ProjectConfigWarning",
    "load_project_config",
    "project_config_manifest_source_kind",
    "project_config_reader_enabled",
]

PROJECT_CONFIG_READER_FLAG = "WEPPPY_PROJECT_CONFIG_READER_ENABLED"
_MANIFEST_NAME = "config-manifest.json"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"", "0", "false", "no", "off"})
_LOG = logging.getLogger(__name__)


class ProjectConfigError(ValueError):
    """Base error for a recognized but unusable project-owned config."""


class ProjectConfigSchemaError(ProjectConfigError):
    """Raised when a flattened config marker or schema is unsupported."""


class ProjectConfigAuthorityError(ProjectConfigError):
    """Raised when nested config authority is unsafe or contradictory."""


@dataclass(frozen=True, slots=True)
class ProjectConfigWarning:
    """Secret-safe warning state exposed to operators and later UI work."""

    code: str
    run_id: str
    config_filename: str
    declared_digest: str | None = None
    observed_digest: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectConfigStatus:
    """Read-only status for the most recent configuration resolution."""

    mode: str
    authority_root: str | None
    config_filename: str | None
    manifest_valid: bool
    updates_enabled: bool
    warnings: tuple[ProjectConfigWarning, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectConfigLoadResult:
    """Parser and status returned to the stable NoDb facade."""

    parser: RawConfigParser
    status: ProjectConfigStatus


def project_config_reader_enabled(environ: dict[str, str] | None = None) -> bool:
    """Return the explicit reader flag; absence is deliberately disabled."""

    source = os.environ if environ is None else environ
    raw = source.get(PROJECT_CONFIG_READER_FLAG, "").strip().casefold()
    if raw in _TRUE_VALUES:
        return True
    if raw in _FALSE_VALUES:
        return False
    raise ValueError(
        f"{PROJECT_CONFIG_READER_FLAG} must be one of "
        "1/true/yes/on or 0/false/no/off"
    )


def project_config_manifest_source_kind(
    authority_root: str | Path,
    config_filename: str,
    *,
    run_id: str = "manifest-inspection",
) -> str | None:
    """Return a validated project-config manifest source kind, if present."""

    root = Path(authority_root).resolve()
    if Path(config_filename).name != config_filename:
        return None
    config_path = root / config_filename
    try:
        config_bytes = config_path.read_bytes()
    except OSError:
        return None
    manifest_valid, _updates_enabled, _warnings = _manifest_status(
        root,
        config_path,
        config_bytes,
        run_id,
    )
    if not manifest_valid:
        return None
    try:
        payload = json.loads((root / _MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    source_kind = payload.get("source_kind") if isinstance(payload, dict) else None
    return source_kind if isinstance(source_kind, str) else None


def _contained_parent(wd: Path, parent_wd: str | Path) -> Path:
    child = wd.resolve()
    parent = Path(parent_wd).resolve()
    try:
        relative = child.relative_to(parent)
    except ValueError as exc:
        raise ProjectConfigAuthorityError(
            "Persisted parent_wd does not contain the nested working directory"
        ) from exc
    if relative == Path("."):
        raise ProjectConfigAuthorityError(
            "Persisted parent_wd must identify an ancestor of the nested working directory"
        )
    return parent


def _read_parser(path: Path, parser_factory: Callable[..., RawConfigParser]) -> RawConfigParser:
    parser = parser_factory(allow_no_value=True)
    with path.open(encoding="utf-8") as stream:
        parser.read_file(stream)
    return parser


def _flattened_state(parser: RawConfigParser, filename: str) -> bool:
    if not parser.has_option("config", "flattened"):
        return False
    try:
        flattened = parser.getboolean("config", "flattened")
    except ValueError as exc:
        raise ProjectConfigSchemaError(
            f"Flattened marker in {filename!r} must be boolean"
        ) from exc
    if not flattened:
        return False
    try:
        schema_version = parser.getint("config", "schema_version")
        resolver_version = parser.getint("config", "resolver_version")
    except (ValueError, ConfigParserError) as exc:
        raise ProjectConfigSchemaError(
            f"Flattened config {filename!r} requires integer schema and resolver versions"
        ) from exc
    if schema_version != 1 or resolver_version != 1:
        raise ProjectConfigSchemaError(
            f"Unsupported flattened config schema/resolver in {filename!r}: "
            f"{schema_version}/{resolver_version}"
        )
    return True


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def _manifest_payload_is_valid(payload: object, filename: str) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("schema_version") != 1 or payload.get("resolver_version") != 1:
        return False
    source_kind = payload.get("source_kind")
    if source_kind not in {"builder", "preset"}:
        return False
    source_preset = payload.get("source_preset")
    if source_kind == "builder" and source_preset is not None:
        return False
    if source_kind == "preset" and not _nonempty_string(source_preset):
        return False
    if not _nonempty_string(payload.get("source_revision")):
        return False
    if not _valid_timestamp(payload.get("resolved_at")):
        return False
    parent_chain = payload.get("parent_chain")
    if not isinstance(parent_chain, list) or not parent_chain:
        return False
    for parent in parent_chain:
        if not isinstance(parent, dict):
            return False
        required = ("kind", "id", "revision")
        if not all(_nonempty_string(parent.get(key)) for key in required):
            return False
    if not isinstance(payload.get("selections"), dict):
        return False
    config = payload.get("config")
    if not isinstance(config, dict) or config.get("filename") != filename:
        return False
    digest = config.get("sha256")
    if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
        return False
    if not isinstance(payload.get("amendments"), list):
        return False
    return True


def _manifest_status(
    authority_root: Path,
    config_path: Path,
    config_bytes: bytes,
    run_id: str,
) -> tuple[bool, bool, tuple[ProjectConfigWarning, ...]]:
    manifest_path = authority_root / _MANIFEST_NAME
    if not manifest_path.is_file():
        warning = ProjectConfigWarning("manifest_missing", run_id, config_path.name)
        return False, False, (warning,)
    if manifest_path.resolve().parent != authority_root.resolve():
        warning = ProjectConfigWarning(
            "manifest_authority_invalid", run_id, config_path.name
        )
        return False, False, (warning,)
    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        warning = ProjectConfigWarning("manifest_unreadable", run_id, config_path.name)
        return False, False, (warning,)
    if scan_manifest_text(manifest_text, source=_MANIFEST_NAME):
        warning = ProjectConfigWarning(
            "manifest_unsafe_or_malformed", run_id, config_path.name
        )
        return False, False, (warning,)
    try:
        payload = json.loads(manifest_text)
    except json.JSONDecodeError:
        warning = ProjectConfigWarning("manifest_malformed", run_id, config_path.name)
        return False, False, (warning,)
    if isinstance(payload, dict) and isinstance(payload.get("schema_version"), int):
        if payload["schema_version"] > 1:
            warning = ProjectConfigWarning("manifest_schema_newer", run_id, config_path.name)
            return False, False, (warning,)
    if not _manifest_payload_is_valid(payload, config_path.name):
        warning = ProjectConfigWarning("manifest_invalid", run_id, config_path.name)
        return False, False, (warning,)

    declared = payload["config"]["sha256"]
    observed = hashlib.sha256(config_bytes).hexdigest()
    if declared != observed:
        warning = ProjectConfigWarning(
            "config_digest_mismatch",
            run_id,
            config_path.name,
            declared_digest=declared,
            observed_digest=observed,
        )
        return True, True, (warning,)
    return True, True, ()


def _legacy_result(
    *,
    token: str,
    wd: Path,
    config_path: Path,
    defaults_resolver: Callable[[str | Path | None], str],
    parser_factory: Callable[..., RawConfigParser],
) -> ProjectConfigLoadResult:
    parser = parser_factory(allow_no_value=True)
    with Path(defaults_resolver(wd)).open(encoding="utf-8") as stream:
        parser.read_file(stream)
    with config_path.open(encoding="utf-8") as stream:
        parser.read_file(stream)

    parts = token.split("?")
    if len(parts) == 2:
        overrides: dict[str, dict[str, str]] = {}
        for override in parts[1].split("&"):
            key, value = override.split("=")
            section, name = key.split(":")
            if (section.casefold(), name.casefold()) == ("general", "locales"):
                raise ProjectConfigAuthorityError(
                    "Legacy config overrides may not set general.locales"
                )
            overrides.setdefault(section, {})[name] = value
        parser.read_dict(overrides)
    return ProjectConfigLoadResult(
        parser,
        ProjectConfigStatus("legacy", str(wd), config_path.name, False, False),
    )


def load_project_config(
    *,
    wd: str | Path,
    config_token: str,
    parent_wd: str | Path | None,
    config_dir: str | Path,
    defaults_resolver: Callable[[str | Path | None], str],
    parser_factory: Callable[..., RawConfigParser],
    run_id: str,
) -> ProjectConfigLoadResult:
    """Load project configuration, recovering only a recorded pending amendment."""

    working_root = Path(wd).resolve()
    if (working_root / ".config-amendment.pending.json").exists():
        from wepppy.nodb.project_config_update import recover_project_config_update

        recover_project_config_update(working_root)
    raw_token_path = Path(config_token.split("?", 1)[0])
    if not raw_token_path.suffix:
        raw_token_path = raw_token_path.with_suffix(".cfg")
    filename = raw_token_path.name
    child_candidate = (
        raw_token_path
        if raw_token_path.is_absolute()
        else working_root / filename
    )
    authority_root = working_root
    candidate = child_candidate

    child_parser: RawConfigParser | None = None
    child_flattened = False
    if child_candidate.is_file():
        child_parser = _read_parser(child_candidate, parser_factory)
        child_flattened = _flattened_state(child_parser, filename)

    if parent_wd is not None:
        parent_root = _contained_parent(working_root, parent_wd)
        if child_candidate.is_file():
            if child_flattened:
                raise ProjectConfigAuthorityError(
                    "Nested working directories cannot own flattened project configs"
                )
        else:
            if (parent_root / ".config-amendment.pending.json").exists():
                from wepppy.nodb.project_config_update import recover_project_config_update

                recover_project_config_update(parent_root)
            authority_root = parent_root
            candidate = parent_root / filename

    if candidate.is_file():
        parser = (
            child_parser
            if candidate == child_candidate and child_parser is not None
            else _read_parser(candidate, parser_factory)
        )
        if _flattened_state(parser, filename):
            if candidate.resolve().parent != authority_root.resolve():
                raise ProjectConfigAuthorityError(
                    "Flattened config must be a direct child of its authority root"
                )
            try:
                config_bytes = candidate.read_bytes()
            except OSError as exc:
                raise ProjectConfigError(
                    f"Unable to read configuration file {filename!r}"
                ) from exc
            valid, updates_enabled, warnings = _manifest_status(
                authority_root, candidate, config_bytes, run_id
            )
            return ProjectConfigLoadResult(
                parser,
                ProjectConfigStatus(
                    "flattened",
                    str(authority_root),
                    filename,
                    valid,
                    updates_enabled,
                    warnings,
                ),
            )
        return _legacy_result(
            token=config_token,
            wd=authority_root,
            config_path=candidate,
            defaults_resolver=defaults_resolver,
            parser_factory=parser_factory,
        )

    if raw_token_path.is_absolute():
        shared_candidate = raw_token_path
    else:
        nested = Path(config_dir) / raw_token_path
        shared_candidate = (
            nested if nested.exists() else Path(config_dir) / raw_token_path.name
        )
    return _legacy_result(
        token=config_token,
        wd=authority_root,
        config_path=shared_candidate,
        defaults_resolver=defaults_resolver,
        parser_factory=parser_factory,
    )


def log_project_config_warning(warning: ProjectConfigWarning) -> None:
    """Emit one allowlisted structured warning without artifact contents."""

    _LOG.warning(
        "project_config_warning code=%s run_id=%s config_filename=%s "
        "declared_digest=%s observed_digest=%s",
        warning.code,
        warning.run_id,
        warning.config_filename,
        warning.declared_digest,
        warning.observed_digest,
    )
