from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, MutableMapping, Optional

import pyarrow as pa

LOGGER = logging.getLogger(__name__)

MANIFEST_FILENAME = "interchange_version.json"


@dataclass(frozen=True, slots=True)
class Version:
    """Simple semantic version container with major/minor components."""

    major: int
    minor: int

    def __post_init__(self) -> None:
        if self.major < 0 or self.minor < 0:
            raise ValueError("Version components must be non-negative integers")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"

    def to_dict(self) -> dict[str, int | str]:
        return {
            "major": self.major,
            "minor": self.minor,
            "version": str(self),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> Version:
        try:
            major = int(payload["major"])
            minor = int(payload["minor"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid version payload: {payload}") from exc
        return cls(major=major, minor=minor)

    @classmethod
    def from_string(cls, value: str) -> Version:
        parts = value.split(".")
        if len(parts) != 2:
            raise ValueError(f"Unsupported version string '{value}'")
        try:
            major = int(parts[0])
            minor = int(parts[1])
        except ValueError as exc:
            raise ValueError(f"Unsupported version string '{value}'") from exc
        return cls(major=major, minor=minor)


INTERCHANGE_VERSION = Version(major=1, minor=0)


def manifest_path(interchange_dir: Path) -> Path:
    return interchange_dir / MANIFEST_FILENAME


def schema_with_version(schema: pa.Schema, *, version: Version = INTERCHANGE_VERSION) -> pa.Schema:
    """Attach the interchange version to schema metadata."""
    metadata: MutableMapping[bytes, bytes]
    metadata = dict(schema.metadata or {})
    metadata[b"dataset_version"] = str(version).encode("utf-8")
    metadata[b"dataset_version_major"] = str(version.major).encode("utf-8")
    metadata[b"dataset_version_minor"] = str(version.minor).encode("utf-8")
    metadata[b"schema_version"] = str(version.major).encode("utf-8")
    return schema.with_metadata(metadata)


def write_version_manifest(interchange_dir: Path, *, version: Version = INTERCHANGE_VERSION) -> Path:
    interchange_dir.mkdir(parents=True, exist_ok=True)
    payload = version.to_dict()
    path = manifest_path(interchange_dir)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    LOGGER.debug("Wrote interchange version manifest at %s (%s)", path, version)
    return path


def read_version_manifest(interchange_dir: Path) -> Optional[Version]:
    path = manifest_path(interchange_dir)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed interchange version manifest: {path}") from exc

    if isinstance(payload, Mapping):
        return Version.from_dict(payload)
    if isinstance(payload, str):
        return Version.from_string(payload)
    raise ValueError(f"Unsupported manifest payload type in {path}: {type(payload).__name__}")


def needs_major_refresh(interchange_dir: Path, *, version: Version = INTERCHANGE_VERSION) -> bool:
    if not interchange_dir.exists():
        return False
    try:
        stored = read_version_manifest(interchange_dir)
    except ValueError:
        LOGGER.warning("Interchange manifest invalid at %s; forcing rebuild", interchange_dir)
        return True
    if stored is None:
        LOGGER.debug("No interchange manifest present at %s; forcing rebuild", interchange_dir)
        return True
    return stored.major != version.major


def remove_incompatible_interchange(interchange_dir: Path, *, version: Version = INTERCHANGE_VERSION) -> bool:
    if not needs_major_refresh(interchange_dir, version=version):
        return False
    if interchange_dir.exists():
        LOGGER.info(
            "Removing interchange directory %s due to version mismatch (expected major %s)",
            interchange_dir,
            version.major,
        )
        shutil.rmtree(interchange_dir, ignore_errors=True)
    return True
