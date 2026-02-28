from __future__ import annotations

from types import SimpleNamespace

import pytest

from wepppy.runtime_paths.errors import NoDirError
from wepppy.rq.wepp_rq_stage_helpers import (
    assert_supported_climate,
    recover_mixed_nodir_roots,
    with_stage_read_projections,
)

pytestmark = pytest.mark.unit


def test_assert_supported_climate_rejects_single_storm() -> None:
    with pytest.raises(ValueError, match="Single-storm climate modes are deprecated"):
        assert_supported_climate(SimpleNamespace(is_single_storm=True))


def test_assert_supported_climate_accepts_continuous_mode() -> None:
    assert_supported_climate(SimpleNamespace(is_single_storm=False))


def test_recover_mixed_nodir_roots_returns_empty_when_directory_only(tmp_path) -> None:
    wd = tmp_path / "run"
    (wd / "watershed").mkdir(parents=True, exist_ok=True)

    assert recover_mixed_nodir_roots(str(wd), roots=("watershed",)) == tuple()


def test_recover_mixed_nodir_roots_raises_for_archive_only_root(tmp_path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "watershed.nodir").write_bytes(b"archive")

    with pytest.raises(NoDirError) as exc_info:
        recover_mixed_nodir_roots(str(wd), roots=("watershed",))

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"


def test_recover_mixed_nodir_roots_raises_for_mixed_root(tmp_path) -> None:
    wd = tmp_path / "run"
    (wd / "watershed").mkdir(parents=True, exist_ok=True)
    (wd / "watershed.nodir").write_bytes(b"archive")

    with pytest.raises(NoDirError) as exc_info:
        recover_mixed_nodir_roots(str(wd), roots=("watershed",))

    assert exc_info.value.code == "NODIR_MIXED_STATE"


def test_with_stage_read_projections_allows_directory_only_roots(tmp_path) -> None:
    wd = tmp_path / "run"
    (wd / "watershed").mkdir(parents=True, exist_ok=True)

    with with_stage_read_projections(
        str(wd),
        roots=("watershed",),
        purpose="unit",
    ):
        pass


def test_with_stage_read_projections_raises_for_archive_only_root(tmp_path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "watershed.nodir").write_bytes(b"archive")

    with pytest.raises(NoDirError) as exc_info:
        with with_stage_read_projections(
            str(wd),
            roots=("watershed",),
            purpose="unit",
        ):
            pass

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"


def test_with_stage_read_projections_raises_for_mixed_root(tmp_path) -> None:
    wd = tmp_path / "run"
    (wd / "watershed").mkdir(parents=True, exist_ok=True)
    (wd / "watershed.nodir").write_bytes(b"archive")

    with pytest.raises(NoDirError) as exc_info:
        with with_stage_read_projections(
            str(wd),
            roots=("watershed",),
            purpose="unit",
        ):
            pass

    assert exc_info.value.code == "NODIR_MIXED_STATE"
