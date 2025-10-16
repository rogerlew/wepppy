from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Mapping, MutableMapping, Optional

import pyarrow as pa

from wepppy.wepp.interchange.versioning import Version

LOGGER = logging.getLogger(__name__)

MANIFEST_FILENAME = "ashpost_version.json"

ASHPOST_VERSION = Version(major=1, minor=0)


def manifest_path(ash_post_dir: Path) -> Path:
    return ash_post_dir / MANIFEST_FILENAME


def schema_with_version(schema: pa.Schema, *, version: Version = ASHPOST_VERSION) -> pa.Schema:
    metadata: MutableMapping[bytes, bytes] = dict(schema.metadata or {})
    metadata[b"dataset_name"] = b"ashpost"
    metadata[b"dataset_version"] = str(version).encode("utf-8")
    metadata[b"dataset_version_major"] = str(version.major).encode("utf-8")
    metadata[b"dataset_version_minor"] = str(version.minor).encode("utf-8")
    return schema.with_metadata(metadata)


def write_version_manifest(ash_post_dir: Path, *, version: Version = ASHPOST_VERSION) -> Path:
    ash_post_dir.mkdir(parents=True, exist_ok=True)
    payload = version.to_dict()
    path = manifest_path(ash_post_dir)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    LOGGER.debug("Wrote ashpost version manifest at %s (%s)", path, version)
    return path


def read_version_manifest(ash_post_dir: Path) -> Optional[Version]:
    path = manifest_path(ash_post_dir)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed ashpost version manifest: {path}") from exc
    if isinstance(payload, Mapping):
        return Version.from_dict(payload)
    if isinstance(payload, str):
        return Version.from_string(payload)
    raise ValueError(f"Unsupported manifest payload type in {path}: {type(payload).__name__}")


def needs_major_refresh(ash_post_dir: Path, *, version: Version = ASHPOST_VERSION) -> bool:
    if not ash_post_dir.exists():
        return False
    try:
        stored = read_version_manifest(ash_post_dir)
    except ValueError:
        LOGGER.warning("AshPost manifest invalid at %s; forcing rebuild", ash_post_dir)
        return True
    if stored is None:
        LOGGER.debug("No AshPost manifest present at %s; forcing rebuild", ash_post_dir)
        return True
    return stored.major != version.major


def remove_incompatible_outputs(ash_post_dir: Path, *, version: Version = ASHPOST_VERSION) -> bool:
    if not needs_major_refresh(ash_post_dir, version=version):
        return False
    if ash_post_dir.exists():
        LOGGER.info(
            "Removing AshPost directory %s due to version mismatch (expected major %s)",
            ash_post_dir,
            version.major,
        )
        shutil.rmtree(ash_post_dir, ignore_errors=True)
    return True

