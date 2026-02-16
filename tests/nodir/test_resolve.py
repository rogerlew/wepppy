from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from wepppy.nodir.errors import NoDirError
from wepppy.nodir.fs import resolve
from wepppy.nodir.state import archive_fingerprint_from_path, write_state

pytestmark = pytest.mark.unit


def test_resolve_mixed_state_raises_conflict(tmp_path: Path) -> None:
    wd = tmp_path
    (wd / "watershed").mkdir()
    (wd / "watershed.nodir").write_bytes(b"not used")

    with pytest.raises(NoDirError) as exc:
        resolve(str(wd), "watershed/a", view="effective")

    err = exc.value
    assert err.http_status == 409
    assert err.code == "NODIR_MIXED_STATE"


def test_resolve_invalid_archive_raises_500(tmp_path: Path) -> None:
    wd = tmp_path
    (wd / "watershed.nodir").write_bytes(b"not a zip")

    with pytest.raises(NoDirError) as exc:
        resolve(str(wd), "watershed/a", view="effective")

    err = exc.value
    assert err.http_status == 500
    assert err.code == "NODIR_INVALID_ARCHIVE"


def test_resolve_archive_view_existing_nodir_not_regular_file_is_invalid(tmp_path: Path) -> None:
    wd = tmp_path
    (wd / "watershed.nodir").mkdir()

    with pytest.raises(NoDirError) as exc:
        resolve(str(wd), "watershed/a", view="archive")

    err = exc.value
    assert err.http_status == 500
    assert err.code == "NODIR_INVALID_ARCHIVE"


def test_resolve_transitional_sentinel_raises_locked(tmp_path: Path) -> None:
    wd = tmp_path
    (wd / "watershed.thaw.tmp").mkdir()

    with pytest.raises(NoDirError) as exc:
        resolve(str(wd), "watershed/a", view="effective")

    err = exc.value
    assert err.http_status == 503
    assert err.code == "NODIR_LOCKED"


def test_resolve_dir_view_populates_archive_fp_when_archive_exists(tmp_path: Path) -> None:
    wd = tmp_path
    (wd / "watershed").mkdir()
    archive_path = wd / "watershed.nodir"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.txt", b"a")

    target = resolve(str(wd), "watershed", view="dir")
    assert target is not None
    assert target.form == "dir"
    assert target.archive_fp is not None
    assert target.archive_fp[1] == archive_path.stat().st_size


def test_resolve_state_transition_raises_locked(tmp_path: Path) -> None:
    wd = tmp_path
    archive_path = wd / "watershed.nodir"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.txt", b"a")

    write_state(
        wd,
        "watershed",
        state="thawing",
        op_id="00000000-0000-4000-8000-000000000011",
        dirty=True,
        archive_fingerprint=archive_fingerprint_from_path(archive_path),
    )

    with pytest.raises(NoDirError) as exc:
        resolve(str(wd), "watershed/a", view="effective")

    err = exc.value
    assert err.http_status == 503
    assert err.code == "NODIR_LOCKED"
