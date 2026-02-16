from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from wepppy.nodir.errors import NoDirError
from wepppy.nodir.fs import open_read, resolve

pytestmark = pytest.mark.unit


def _write_zip(wd: Path, *, entries: list[tuple[str, bytes]]) -> None:
    archive_path = wd / "watershed.nodir"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries:
            zf.writestr(zipfile.ZipInfo(name), data)


@pytest.mark.parametrize(
    "bad_name",
    [
        "/abs.txt",
        "../evil.txt",
        r"a\b.txt",
        "C:/x.txt",
    ],
)
def test_resolve_rejects_invalid_zip_entry_names(tmp_path: Path, bad_name: str) -> None:
    wd = tmp_path
    _write_zip(wd, entries=[(bad_name, b"x")])

    with pytest.raises(NoDirError) as exc:
        resolve(str(wd), "watershed", view="archive")

    err = exc.value
    assert err.http_status == 500
    assert err.code == "NODIR_INVALID_ARCHIVE"


def test_resolve_rejects_file_dir_name_conflict(tmp_path: Path) -> None:
    wd = tmp_path
    _write_zip(wd, entries=[("a", b"x"), ("a/", b"")])

    with pytest.raises(NoDirError) as exc:
        resolve(str(wd), "watershed", view="archive")

    err = exc.value
    assert err.http_status == 500
    assert err.code == "NODIR_INVALID_ARCHIVE"


def test_open_read_enforces_max_uncompressed_size(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd, entries=[("big.txt", b"0123456789")])

    monkeypatch.setenv("NODIR_MAX_OPEN_READ_BYTES", "5")

    target = resolve(str(wd), "watershed/big.txt", view="archive")
    assert target is not None

    with pytest.raises(NoDirError) as exc:
        open_read(target)

    err = exc.value
    assert err.http_status == 413
    assert err.code == "NODIR_LIMIT_EXCEEDED"


def test_open_read_invalid_max_env_falls_back_to_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd, entries=[("a.txt", b"x")])

    monkeypatch.setenv("NODIR_MAX_OPEN_READ_BYTES", "5MB")

    target = resolve(str(wd), "watershed/a.txt", view="archive")
    assert target is not None

    with open_read(target) as fp:
        assert fp.read() == b"x"


def test_resolve_rejects_dir_entry_with_non_dir_unix_mode(tmp_path: Path) -> None:
    wd = tmp_path
    archive_path = wd / "watershed.nodir"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        info = zipfile.ZipInfo("a/")
        info.external_attr = (0o100644 << 16)
        zf.writestr(info, b"")

    with pytest.raises(NoDirError) as exc:
        resolve(str(wd), "watershed", view="archive")

    err = exc.value
    assert err.http_status == 500
    assert err.code == "NODIR_INVALID_ARCHIVE"
