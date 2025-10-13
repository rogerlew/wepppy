from __future__ import annotations

import json
from pathlib import Path
import importlib.machinery
import importlib.util
import sys

import pyarrow as pa


def _load_versioning_module():
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "wepppy" / "wepp" / "interchange" / "versioning.py"
    loader = importlib.machinery.SourceFileLoader("wepppy.wepp.interchange._versioning_test", str(module_path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    sys.modules.setdefault("wepppy.wepp.interchange.versioning", module)
    return module


_versioning = _load_versioning_module()

INTERCHANGE_VERSION = _versioning.INTERCHANGE_VERSION
Version = _versioning.Version
needs_major_refresh = _versioning.needs_major_refresh
read_version_manifest = _versioning.read_version_manifest
remove_incompatible_interchange = _versioning.remove_incompatible_interchange
schema_with_version = _versioning.schema_with_version
write_version_manifest = _versioning.write_version_manifest


def test_schema_with_version_preserves_existing_metadata() -> None:
    base_schema = pa.schema(
        [pa.field("value", pa.int32()).with_metadata({b"units": b"kg"})]
    ).with_metadata({b"table": b"sample"})

    stamped = schema_with_version(base_schema)

    assert stamped.metadata is not None
    assert stamped.metadata[b"table"] == b"sample"
    assert stamped.metadata[b"dataset_version"] == str(INTERCHANGE_VERSION).encode("utf-8")
    assert stamped.metadata[b"dataset_version_major"] == str(INTERCHANGE_VERSION.major).encode("utf-8")
    assert stamped.metadata[b"dataset_version_minor"] == str(INTERCHANGE_VERSION.minor).encode("utf-8")

    field = stamped.field("value")
    assert field.metadata is not None
    assert field.metadata[b"units"] == b"kg"


def test_manifest_roundtrip(tmp_path: Path) -> None:
    target_dir = tmp_path / "interchange"
    version = Version(INTERCHANGE_VERSION.major + 2, INTERCHANGE_VERSION.minor + 3)

    manifest_path = write_version_manifest(target_dir, version=version)
    stored = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert stored["major"] == version.major
    assert stored["minor"] == version.minor
    assert stored["version"] == str(version)

    loaded = read_version_manifest(target_dir)
    assert loaded == version


def test_needs_major_refresh_behaviour(tmp_path: Path) -> None:
    target_dir = tmp_path / "interchange"
    target_dir.mkdir()

    assert needs_major_refresh(target_dir)

    write_version_manifest(target_dir, version=INTERCHANGE_VERSION)
    assert not needs_major_refresh(target_dir)

    newer_major = Version(INTERCHANGE_VERSION.major + 1, 0)
    write_version_manifest(target_dir, version=newer_major)
    assert needs_major_refresh(target_dir)


def test_remove_incompatible_interchange(tmp_path: Path) -> None:
    target_dir = tmp_path / "interchange"

    write_version_manifest(target_dir, version=INTERCHANGE_VERSION)
    (target_dir / "placeholder.txt").write_text("ok", encoding="utf-8")
    assert not remove_incompatible_interchange(target_dir)
    assert target_dir.exists()

    write_version_manifest(target_dir, version=Version(INTERCHANGE_VERSION.major + 1, 0))
    (target_dir / "placeholder.txt").write_text("stale", encoding="utf-8")

    removed = remove_incompatible_interchange(target_dir)
    assert removed
    assert not target_dir.exists()
