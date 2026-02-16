from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.nodir.errors import NoDirError
from wepppy.nodir.fs import resolve

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
