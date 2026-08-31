"""Secret and runtime-host-bound value gate for project configuration artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
from typing import Iterable, Iterator
import zipfile

__all__ = [
    "ConfigMaterializationError",
    "ConfigMaterializationViolation",
    "assert_materialization_safe",
    "scan_archive",
    "scan_config_text",
    "scan_manifest_text",
    "scan_path",
]

_ASSIGNMENT_RE = re.compile(r"^\s*([^#;\s][^=:#]*?)\s*(?:=|:)\s*(.*?)\s*$")
_SECRET_KEY_RE = re.compile(
    r"(?:^|_)(?:api_?key|access_?key|private_?key|password|passwd|secret|token|credential)(?:$|_)",
    re.IGNORECASE,
)
_HOST_BOUND_KEYS = frozenset(
    {
        "database_url",
        "dsn",
        "host",
        "hostname",
        "port",
        "redis_host",
        "redis_port",
        "redis_url",
        "socket",
        "socket_path",
    }
)
_ENV_REFERENCE_RE = re.compile(r"(?:\$\{[A-Za-z_][A-Za-z0-9_]*\}|\$[A-Za-z_][A-Za-z0-9_]*)")
_URI_CREDENTIAL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://[^\s/@:]+:[^\s/@]+@")
_SECRET_PATH_RE = re.compile(r"(?:^|[/\\])(?:run[/\\]secrets|docker[/\\]secrets)(?:[/\\]|$)", re.IGNORECASE)
_CONFIG_SUFFIXES = frozenset({".cfg", ".toml"})
_MANIFEST_NAME = "config-manifest.json"
_MAX_ARCHIVE_MEMBER_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ConfigMaterializationViolation:
    """A redacted materialization violation; raw values are never retained."""

    source: str
    location: str
    key: str
    rule: str

    def describe(self) -> str:
        return f"{self.source}:{self.location}: {self.key!r} violates {self.rule}"


class ConfigMaterializationError(ValueError):
    """Raised when a configuration or manifest is unsafe to materialize."""

    def __init__(self, violations: Iterable[ConfigMaterializationViolation]) -> None:
        self.violations = tuple(violations)
        super().__init__("; ".join(item.describe() for item in self.violations))


def _unquote(raw_value: str) -> str:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _classify(source: str, location: str, key: str, raw_value: object) -> Iterator[ConfigMaterializationViolation]:
    normalized_key = key.strip().casefold().replace("-", "_")
    if _SECRET_KEY_RE.search(normalized_key):
        yield ConfigMaterializationViolation(source, location, key, "secret-bearing option name")
    if normalized_key in _HOST_BOUND_KEYS:
        yield ConfigMaterializationViolation(source, location, key, "runtime-host-bound option name")

    if not isinstance(raw_value, str):
        return
    value = _unquote(raw_value)
    if _ENV_REFERENCE_RE.search(value):
        yield ConfigMaterializationViolation(source, location, key, "environment-variable reference")
    if _SECRET_PATH_RE.search(value):
        yield ConfigMaterializationViolation(source, location, key, "runtime secret-file path")
    if _URI_CREDENTIAL_RE.search(value):
        yield ConfigMaterializationViolation(source, location, key, "credential-bearing URI")


def scan_config_text(text: str, *, source: str = "<config>") -> tuple[ConfigMaterializationViolation, ...]:
    """Scan INI-style config text without logging or retaining raw values."""

    violations: list[ConfigMaterializationViolation] = []
    section = ""
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            continue
        match = _ASSIGNMENT_RE.match(line)
        if match is None:
            continue
        key, raw_value = match.groups()
        location = f"line {line_number} [{section}]" if section else f"line {line_number}"
        violations.extend(_classify(source, location, key.strip(), raw_value))
    return tuple(violations)


def scan_manifest_text(text: str, *, source: str = "<manifest>") -> tuple[ConfigMaterializationViolation, ...]:
    """Scan a JSON manifest recursively; invalid JSON is reported without content."""

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return (ConfigMaterializationViolation(source, f"line {exc.lineno}", "<json>", "invalid JSON"),)

    violations: list[ConfigMaterializationViolation] = []

    def visit(value: object, location: str, key: str) -> None:
        violations.extend(_classify(source, location, key, value))
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                child_location = f"{location}.{child_key}" if location else str(child_key)
                visit(child_value, child_location, str(child_key))
        elif isinstance(value, list):
            for index, child_value in enumerate(value):
                visit(child_value, f"{location}[{index}]", "<item>")

    if isinstance(payload, dict):
        for root_key, root_value in payload.items():
            visit(root_value, str(root_key), str(root_key))
    else:
        visit(payload, "$", "<root>")
    return tuple(violations)


def assert_materialization_safe(config_text: str, manifest_text: str | None = None) -> None:
    """Fail closed before config/manifest bytes are written to a project root."""

    violations = list(scan_config_text(config_text))
    if manifest_text is not None:
        violations.extend(scan_manifest_text(manifest_text))
    if violations:
        raise ConfigMaterializationError(violations)


def _scan_named_text(name: str, text: str) -> tuple[ConfigMaterializationViolation, ...]:
    if PurePosixPath(name).name == _MANIFEST_NAME:
        return scan_manifest_text(text, source=name)
    return scan_config_text(text, source=name)


def _is_config_artifact(name: str) -> bool:
    path = PurePosixPath(name)
    return path.name == _MANIFEST_NAME or path.suffix.casefold() in _CONFIG_SUFFIXES


def scan_archive(path: Path) -> tuple[ConfigMaterializationViolation, ...]:
    """Inspect config artifacts in ZIP or tar archives without extracting them."""

    violations: list[ConfigMaterializationViolation] = []

    def scan_member(name: str, size: int, data: bytes) -> None:
        if not _is_config_artifact(name):
            return
        if size > _MAX_ARCHIVE_MEMBER_BYTES:
            violations.append(ConfigMaterializationViolation(str(path), name, "<member>", "oversize config artifact"))
            return
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            violations.append(ConfigMaterializationViolation(str(path), name, "<member>", "non-UTF-8 config artifact"))
            return
        violations.extend(_scan_named_text(f"{path}!{name}", text))

    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zip_archive:
            for zip_member in zip_archive.infolist():
                if zip_member.is_dir() or not _is_config_artifact(zip_member.filename):
                    continue
                if zip_member.file_size > _MAX_ARCHIVE_MEMBER_BYTES:
                    scan_member(zip_member.filename, zip_member.file_size, b"")
                else:
                    scan_member(zip_member.filename, zip_member.file_size, zip_archive.read(zip_member))
        return tuple(violations)

    try:
        with tarfile.open(path, mode="r:*") as tar_archive:
            for tar_member in tar_archive.getmembers():
                if not tar_member.isfile() or not _is_config_artifact(tar_member.name):
                    continue
                if tar_member.size > _MAX_ARCHIVE_MEMBER_BYTES:
                    scan_member(tar_member.name, tar_member.size, b"")
                    continue
                stream = tar_archive.extractfile(tar_member)
                if stream is not None:
                    scan_member(tar_member.name, tar_member.size, stream.read(_MAX_ARCHIVE_MEMBER_BYTES + 1))
    except tarfile.ReadError as exc:
        raise ValueError(f"Unsupported archive format: {path}") from exc
    return tuple(violations)


def scan_path(path: Path) -> tuple[ConfigMaterializationViolation, ...]:
    """Scan one config/manifest, a directory tree, or a ZIP/tar archive."""

    path = Path(path)
    if path.is_dir():
        violations: list[ConfigMaterializationViolation] = []
        for child in sorted(item for item in path.rglob("*") if item.is_file() and _is_config_artifact(item.name)):
            violations.extend(scan_path(child))
        return tuple(violations)
    if path.name == _MANIFEST_NAME:
        return scan_manifest_text(path.read_text(encoding="utf-8"), source=str(path))
    if path.suffix.casefold() in _CONFIG_SUFFIXES:
        return scan_config_text(path.read_text(encoding="utf-8"), source=str(path))
    return scan_archive(path)
