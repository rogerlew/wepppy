from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from wepppy.nodir.errors import NoDirError
from wepppy.nodir.fs import listdir, open_read, resolve, stat

pytestmark = pytest.mark.unit


def test_dir_form_rejects_symlink_escape(tmp_path: Path) -> None:
    wd = tmp_path
    (wd / "watershed").mkdir()

    outside = tmp_path.parent / "outside.txt"
    outside.write_bytes(b"outside")
    (wd / "watershed" / "link.txt").symlink_to(outside)

    target = resolve(str(wd), "watershed/link.txt", view="effective")
    assert target is not None
    assert target.form == "dir"

    with pytest.raises(FileNotFoundError):
        stat(target)

    with pytest.raises(FileNotFoundError):
        open_read(target)


def test_archive_form_rejects_nodir_symlink_escape(tmp_path: Path) -> None:
    wd = tmp_path

    outside_archive = tmp_path.parent / "watershed.nodir"
    with zipfile.ZipFile(outside_archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.txt", b"a")

    (wd / "watershed.nodir").symlink_to(outside_archive)

    with pytest.raises(NoDirError) as exc:
        resolve(str(wd), "watershed/a.txt", view="archive")

    err = exc.value
    assert err.http_status == 500
    assert err.code == "NODIR_INVALID_ARCHIVE"


def test_dir_form_allows_omni_child_run_symlink_into_parent_run_root(tmp_path: Path) -> None:
    parent = tmp_path / "parent_run"
    wd = parent / "_pups" / "omni" / "scenarios" / "scenario1"
    (wd / "watershed").mkdir(parents=True)

    shared = parent / "watershed"
    shared.mkdir(parents=True)
    (shared / "shared.txt").write_bytes(b"shared")

    (wd / "watershed" / "shared.txt").symlink_to(shared / "shared.txt")

    target = resolve(str(wd), "watershed/shared.txt", view="effective")
    assert target is not None
    assert target.form == "dir"

    with open_read(target) as fp:
        assert fp.read() == b"shared"


def test_archive_form_allows_omni_child_run_nodir_symlink_into_parent_run_root(tmp_path: Path) -> None:
    parent = tmp_path / "parent_run"
    wd = parent / "_pups" / "omni" / "scenarios" / "scenario1"
    wd.mkdir(parents=True)

    archive_path = parent / "watershed.nodir"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.txt", b"a")

    (wd / "watershed.nodir").symlink_to(archive_path)

    root = resolve(str(wd), "watershed", view="archive")
    assert root is not None
    assert root.form == "archive"
    assert {(e.name, e.is_dir) for e in listdir(root)} == {("a.txt", False)}

    a = resolve(str(wd), "watershed/a.txt", view="archive")
    assert a is not None
    with open_read(a) as fp:
        assert fp.read() == b"a"


def test_dir_form_lists_and_stats_symlinked_directory_within_allowed_roots(tmp_path: Path) -> None:
    wd = tmp_path
    (wd / "watershed").mkdir()

    shared = wd / "shared_dir"
    shared.mkdir()
    (shared / "a.txt").write_bytes(b"a")

    (wd / "watershed" / "linkdir").symlink_to(shared, target_is_directory=True)

    root = resolve(str(wd), "watershed", view="effective")
    assert root is not None
    assert root.form == "dir"

    entries = {e.name: e for e in listdir(root)}
    assert entries["linkdir"].is_dir is True

    linkdir = resolve(str(wd), "watershed/linkdir", view="effective")
    assert linkdir is not None
    assert stat(linkdir).is_dir is True
    assert {e.name for e in listdir(linkdir)} == {"a.txt"}

    nested = resolve(str(wd), "watershed/linkdir/a.txt", view="effective")
    assert nested is not None
    with open_read(nested) as fp:
        assert fp.read() == b"a"


def test_resolve_dir_view_treats_symlinked_root_dir_outside_allowed_roots_as_missing(tmp_path: Path) -> None:
    wd = tmp_path
    outside = tmp_path.parent / "outside_dir"
    outside.mkdir()
    (outside / "a.txt").write_bytes(b"a")

    (wd / "watershed").symlink_to(outside, target_is_directory=True)

    assert resolve(str(wd), "watershed", view="dir") is None


def test_resolve_dir_view_allows_symlinked_root_dir_into_parent_run_root(tmp_path: Path) -> None:
    parent = tmp_path / "parent_run"
    wd = parent / "_pups" / "omni" / "scenarios" / "scenario1"
    wd.mkdir(parents=True)

    shared = parent / "watershed"
    shared.mkdir(parents=True)
    (shared / "a.txt").write_bytes(b"a")

    (wd / "watershed").symlink_to(shared, target_is_directory=True)

    target = resolve(str(wd), "watershed", view="dir")
    assert target is not None
    assert target.form == "dir"
    assert {(e.name, e.is_dir) for e in listdir(target)} == {("a.txt", False)}
