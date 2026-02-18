from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from wepppy.nodir.fs import listdir, open_read, resolve, stat

pytestmark = pytest.mark.unit


def _make_watershed_archive(wd: Path) -> Path:
    archive_path = wd / "watershed.nodir"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.txt", b"root-a")
        zf.writestr("subdir/b.txt", b"sub-b")
    return archive_path


def test_archive_listdir_stat_open_read(tmp_path: Path) -> None:
    wd = tmp_path
    _make_watershed_archive(wd)

    root = resolve(str(wd), "watershed", view="archive")
    assert root is not None
    assert root.form == "archive"

    entries = listdir(root)
    assert {(e.name, e.is_dir) for e in entries} == {("subdir", True), ("a.txt", False)}

    a = resolve(str(wd), "watershed/a.txt", view="archive")
    assert a is not None
    a_stat = stat(a)
    assert a_stat.is_dir is False
    assert a_stat.name == "a.txt"

    b = resolve(str(wd), "watershed/subdir/b.txt", view="archive")
    assert b is not None
    with open_read(b) as fp:
        assert fp.read() == b"sub-b"


def test_archive_listdir_missing_directory_raises(tmp_path: Path) -> None:
    wd = tmp_path
    _make_watershed_archive(wd)

    missing = resolve(str(wd), "watershed/missing", view="archive")
    assert missing is not None
    with pytest.raises(FileNotFoundError):
        listdir(missing)


def test_archive_listdir_explicit_empty_directory_returns_empty(tmp_path: Path) -> None:
    wd = tmp_path
    archive_path = wd / "watershed.nodir"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("empty/", b"")

    empty_dir = resolve(str(wd), "watershed/empty", view="archive")
    assert empty_dir is not None
    assert listdir(empty_dir) == []
