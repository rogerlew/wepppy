from __future__ import annotations

import logging
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.core.soils import Soils

pytestmark = pytest.mark.unit


class _StopBuild(Exception):
    """Sentinel used to stop _build_gridded after pre-retrieve assertions."""


def test_build_gridded_creates_soils_dir_before_retrieve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    soils = Soils.__new__(Soils)
    soils.wd = str(wd)
    soils.logger = logging.getLogger("tests.nodb.soils_gridded")
    soils._soils_is_vrt = False
    soils._ssurgo_db = "ssurgo"
    soils._initial_sat = 0.75
    soils._ksflag = True

    soils.locked = lambda: nullcontext()
    soils.timed = lambda _label: nullcontext()
    soils.config_get_int = lambda *_args, **_kwargs: 1
    soils.config_get_str = lambda *_args, **_kwargs: None

    map_stub = SimpleNamespace(extent=(-116.1, 47.0, -116.0, 47.1), cellsize=30.0)
    watershed_stub = SimpleNamespace(subwta=str(wd / "watershed" / "subwta.tif"))

    monkeypatch.setattr(Soils, "ron_instance", property(lambda _self: SimpleNamespace(map=map_stub)))
    monkeypatch.setattr(Soils, "watershed_instance", property(lambda _self: watershed_stub))

    expected_soils_dir = wd / "soils"

    def _fake_wmesque_retrieve(*_args, **_kwargs):
        assert expected_soils_dir.is_dir(), "Soils directory must exist before ssurgo retrieval"
        raise _StopBuild()

    monkeypatch.setattr("wepppy.nodb.core.soils.wmesque_retrieve", _fake_wmesque_retrieve)

    with pytest.raises(_StopBuild):
        soils._build_gridded()

    assert expected_soils_dir.is_dir()


def test_post_dump_skips_parquet_when_soils_dir_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    soils = Soils.__new__(Soils)
    soils.wd = str(tmp_path / "run")
    Path(soils.wd).mkdir(parents=True, exist_ok=True)

    called = {"dump": False}

    def _fake_dump(_self):
        called["dump"] = True

    monkeypatch.setattr(Soils, "dump_soils_parquet", _fake_dump)

    result = soils._post_dump_and_unlock()

    assert result is soils
    assert called["dump"] is False


def test_post_dump_writes_parquet_when_soils_dir_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    soils = Soils.__new__(Soils)
    soils.wd = str(tmp_path / "run")
    Path(soils.wd).mkdir(parents=True, exist_ok=True)
    Path(soils.soils_dir).mkdir(parents=True, exist_ok=True)

    called = {"dump": False}

    def _fake_dump(_self):
        called["dump"] = True

    monkeypatch.setattr(Soils, "dump_soils_parquet", _fake_dump)

    result = soils._post_dump_and_unlock()

    assert result is soils
    assert called["dump"] is True


def test_post_instance_loaded_rebinds_soil_summary_soils_dir(tmp_path: Path) -> None:
    from wepppy.soils.ssurgo import SoilSummary

    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    stale_soils_dir = tmp_path / "stale" / "soils"
    stale_soils_dir.mkdir(parents=True, exist_ok=True)

    summary = SoilSummary(
        mukey="123",
        fname="123.sol",
        soils_dir=str(stale_soils_dir),
        build_date="2026-02-18",
        desc="stale",
    )
    summary._weppsoilutil = object()

    instance = Soils.__new__(Soils)
    instance.wd = str(wd)
    instance.soils = {"123": summary}

    result = Soils._post_instance_loaded(instance)

    assert result is instance
    assert summary.soils_dir == str(wd / "soils")
    assert not hasattr(summary, "_weppsoilutil")


def test_soil_summary_path_skips_runid_resolution_for_absolute_soils_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wepppy.soils.ssurgo import SoilSummary

    absolute_soils_dir = tmp_path / "missing" / "soils"
    summary = SoilSummary(
        mukey="123",
        fname="123.sol",
        soils_dir=str(absolute_soils_dir),
        build_date="2026-02-18",
        desc="stale",
    )

    def _unexpected_get_wd(_runid: str) -> str:
        raise AssertionError("get_wd should not be used for absolute soils_dir")

    monkeypatch.setattr("wepppy.weppcloud.utils.helpers.get_wd", _unexpected_get_wd)

    assert summary.path == str(absolute_soils_dir / "123.sol")
