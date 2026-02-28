from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import listdir, open_read, resolve, stat

pytestmark = pytest.mark.unit


def _resolve_landuse_parquet_target(tmp_path: Path):
    target = resolve(str(tmp_path), "landuse/landuse.parquet")
    assert target is not None
    return target


def test_stat_and_open_read_use_canonical_directory_parquet(tmp_path: Path) -> None:
    canonical = tmp_path / "landuse" / "landuse.parquet"
    canonical.parent.mkdir(parents=True)
    canonical.write_bytes(b"PARQUET")

    target = _resolve_landuse_parquet_target(tmp_path)

    entry = stat(target)
    assert entry.name == "landuse.parquet"
    assert entry.size_bytes == len(b"PARQUET")

    with open_read(target) as handle:
        assert handle.read() == b"PARQUET"


def test_stat_and_open_read_raise_migration_required_for_retired_root_sidecar(tmp_path: Path) -> None:
    (tmp_path / "landuse.parquet").write_bytes(b"RET")
    target = _resolve_landuse_parquet_target(tmp_path)

    with pytest.raises(NoDirError, match="NODIR_MIGRATION_REQUIRED"):
        stat(target)

    with pytest.raises(NoDirError, match="NODIR_MIGRATION_REQUIRED"):
        open_read(target)


def test_stat_and_open_read_raise_file_not_found_when_parquet_missing(tmp_path: Path) -> None:
    target = _resolve_landuse_parquet_target(tmp_path)

    with pytest.raises(FileNotFoundError):
        stat(target)

    with pytest.raises(FileNotFoundError):
        open_read(target)


def test_resolve_archive_view_returns_none_for_directory_only_runtime(tmp_path: Path) -> None:
    assert resolve(str(tmp_path), "landuse", view="archive") is None


def test_resolve_raises_archive_retired_when_archive_exists_without_directory(tmp_path: Path) -> None:
    (tmp_path / "landuse.nodir").write_bytes(b"zip-bytes")

    with pytest.raises(NoDirError) as exc_info:
        resolve(str(tmp_path), "landuse")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"


def test_listdir_orders_directories_before_files_case_insensitive(tmp_path: Path) -> None:
    root = tmp_path / "landuse"
    root.mkdir(parents=True, exist_ok=True)
    (root / "zDir").mkdir()
    (root / "aDir").mkdir()
    (root / "B.txt").write_text("b", encoding="utf-8")
    (root / "a.txt").write_text("a", encoding="utf-8")

    target = resolve(str(tmp_path), "landuse")
    assert target is not None

    entries = listdir(target)
    assert [entry.name for entry in entries] == ["aDir", "zDir", "a.txt", "B.txt"]
    assert entries[0].is_dir is True
    assert entries[-1].is_dir is False


def test_listdir_raises_file_not_found_for_missing_target(tmp_path: Path) -> None:
    target = resolve(str(tmp_path), "landuse")
    assert target is not None

    with pytest.raises(FileNotFoundError):
        listdir(target)


def test_listdir_raises_not_a_directory_for_file_target(tmp_path: Path) -> None:
    root = tmp_path / "landuse"
    root.mkdir(parents=True, exist_ok=True)
    (root / "data.txt").write_text("x", encoding="utf-8")

    target = resolve(str(tmp_path), "landuse/data.txt")
    assert target is not None

    with pytest.raises(NotADirectoryError):
        listdir(target)


def test_open_read_rejects_symlink_escaping_root(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    root = wd / "landuse"
    root.mkdir()

    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    (root / "hosts.txt").symlink_to(outside)

    target = resolve(str(wd), "landuse/hosts.txt")
    assert target is not None

    with pytest.raises(FileNotFoundError):
        open_read(target)


def test_stat_rejects_symlinked_root_outside_workspace(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    outside_root = tmp_path / "outside-root"
    outside_root.mkdir()
    (outside_root / "data.txt").write_text("outside", encoding="utf-8")
    (wd / "landuse").symlink_to(outside_root, target_is_directory=True)

    target = resolve(str(wd), "landuse/data.txt")
    assert target is not None

    with pytest.raises(FileNotFoundError):
        stat(target)
