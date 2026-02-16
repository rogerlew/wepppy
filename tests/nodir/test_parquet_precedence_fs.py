from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from wepppy.nodir.errors import NoDirError
from wepppy.nodir.fs import open_read, resolve, stat

pytestmark = pytest.mark.unit


def _make_valid_archive(wd: Path) -> None:
    archive_path = wd / "watershed.nodir"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.txt", b"A")


def test_parquet_archive_does_not_fallback_to_zip_entry_when_sidecar_missing(tmp_path: Path) -> None:
    wd = tmp_path
    _make_valid_archive(wd)

    target = resolve(str(wd), "watershed/hillslopes.parquet", view="archive")
    assert target is not None
    with pytest.raises(FileNotFoundError):
        open_read(target)


def test_parquet_archive_prefers_sidecar_over_zip_entry(tmp_path: Path) -> None:
    wd = tmp_path
    _make_valid_archive(wd)

    sidecar = wd / "watershed.hillslopes.parquet"
    sidecar.write_bytes(b"SIDE")

    target = resolve(str(wd), "watershed/hillslopes.parquet", view="archive")
    assert target is not None

    entry = stat(target)
    assert entry.name == "hillslopes.parquet"
    assert entry.size_bytes == 4

    with open_read(target) as fp:
        assert fp.read() == b"SIDE"


def test_archive_with_parquet_entries_is_invalid(tmp_path: Path) -> None:
    wd = tmp_path
    archive_path = wd / "watershed.nodir"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.txt", b"A")
        zf.writestr("hillslopes.parquet", b"ZIP")
        zf.writestr("subdir/x.txt", b"X")

    with pytest.raises(NoDirError) as exc:
        resolve(str(wd), "watershed", view="archive")

    err = exc.value
    assert err.http_status == 500
    assert err.code == "NODIR_INVALID_ARCHIVE"
