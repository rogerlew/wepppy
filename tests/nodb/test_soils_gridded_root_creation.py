from __future__ import annotations

import importlib
import logging
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import jsonpickle
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


def test_build_gridded_coverage_uses_hillslope_area_not_wsarea(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "watershed").mkdir(parents=True, exist_ok=True)
    (wd / "soils").mkdir(parents=True, exist_ok=True)
    (wd / "soils" / "ssurgo.tif").write_text("stub", encoding="utf-8")

    soils = Soils.__new__(Soils)
    soils.wd = str(wd)
    soils.logger = logging.getLogger("tests.nodb.soils_gridded_coverage")
    soils._soils_is_vrt = False
    soils._ssurgo_db = "ssurgo"
    soils._initial_sat = 0.75
    soils._ksflag = True

    soils.locked = lambda: nullcontext()
    soils.timed = lambda _label: nullcontext()
    soils.trigger = lambda *_args, **_kwargs: None

    map_stub = SimpleNamespace(extent=(-116.1, 47.0, -116.0, 47.1), cellsize=30.0)

    class _WatershedStub:
        subwta = str(wd / "watershed" / "subwta.tif")
        sub_area = 5.0

        @property
        def wsarea(self) -> float:
            raise AssertionError("Soils coverage should not use watershed.wsarea")

        @staticmethod
        def hillslope_area(topaz_id: str) -> float:
            return {"11": 2.0, "12": 3.0}[str(topaz_id)]

    monkeypatch.setattr(
        Soils,
        "ron_instance",
        property(lambda _self: SimpleNamespace(map=map_stub)),
    )
    monkeypatch.setattr(
        Soils,
        "watershed_instance",
        property(lambda _self: _WatershedStub()),
    )
    monkeypatch.setattr(
        Soils,
        "getInstance",
        classmethod(lambda cls, _wd: soils),
    )
    monkeypatch.setattr("wepppy.nodb.core.soils.wepppyo3", None)

    class _SoilSummaryStub:
        def __init__(self) -> None:
            self.area = 0.0
            self.pct_coverage = 0.0

    class _SurgoMapStub:
        def __init__(self, _ssurgo_fn: str) -> None:
            self.mukeys = [1001, 1002]

        @staticmethod
        def build_soilgrid(_subwta: str) -> dict[str, str]:
            return {"11": "1001", "12": "1002"}

    class _SurgoCollectionStub:
        def __init__(self, _mukeys: set[int]) -> None:
            pass

        @staticmethod
        def makeWeppSoils(**_kwargs) -> None:
            return None

        @staticmethod
        def writeWeppSoils(**_kwargs) -> dict[int, _SoilSummaryStub]:
            return {1001: _SoilSummaryStub(), 1002: _SoilSummaryStub()}

        @staticmethod
        def logInvalidSoils(**_kwargs) -> None:
            return None

    monkeypatch.setattr("wepppy.nodb.core.soils.SurgoMap", _SurgoMapStub)
    monkeypatch.setattr("wepppy.nodb.core.soils.SurgoSoilCollection", _SurgoCollectionStub)

    soils._build_gridded(retrieve_gridded_ssurgo=False, max_workers=1)

    assert soils.soils["1001"].pct_coverage == pytest.approx(40.0)
    assert soils.soils["1002"].pct_coverage == pytest.approx(60.0)
    assert (
        soils.soils["1001"].pct_coverage + soils.soils["1002"].pct_coverage
    ) == pytest.approx(100.0)


def test_build_from_map_db_refreshes_existing_run_local_sol_from_db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    soils_dir = wd / "soils"
    soils_dir.mkdir(parents=True, exist_ok=True)

    locale_dir = tmp_path / "locale"
    soils_db_dir = locale_dir / "db"
    soils_db_dir.mkdir(parents=True, exist_ok=True)

    soils_map = locale_dir / "soils_map.tif"
    soils_map.write_text("stub-map", encoding="utf-8")

    src_sol = soils_db_dir / "30.sol"
    src_sol.write_text("fresh-from-db\n", encoding="utf-8")

    run_sol = soils_dir / "30.sol"
    run_sol.write_text("stale-run-copy\n", encoding="utf-8")

    soils = Soils.__new__(Soils)
    soils.wd = str(wd)
    soils.logger = logging.getLogger("tests.nodb.soils_map_db_refresh")
    soils._soils_map = str(soils_map)
    soils.locked = lambda: nullcontext()
    soils.trigger = lambda *_args, **_kwargs: None

    watershed_stub = SimpleNamespace(
        dem_fn=str(wd / "watershed" / "dem.tif"),
        subwta=str(wd / "watershed" / "subwta.tif"),
        sub_area=4.0,
        hillslope_area=lambda topaz_id: {"11": 1.0, "12": 3.0}[str(topaz_id)],
    )

    monkeypatch.setattr(Soils, "watershed_instance", property(lambda _self: watershed_stub))
    monkeypatch.setattr(Soils, "getInstance", classmethod(lambda cls, _wd: soils))
    monkeypatch.setattr("wepppy.nodb.core.soils.raster_stacker", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "wepppy.nodb.core.soils.identify_mode_single_raster_key",
        lambda **_kwargs: {"11": "30", "12": "30"},
        raising=False,
    )

    class _WeppSoilUtilStub:
        def __init__(self, _sol_path: str) -> None:
            self.obj = {"ofes": [{"slid": "stub soil"}]}

    soils_utils = importlib.import_module("wepppy.wepp.soils.utils")
    monkeypatch.setattr(soils_utils, "WeppSoilUtil", _WeppSoilUtilStub)

    soils._build_from_map_db()

    assert run_sol.read_text(encoding="utf-8") == "fresh-from-db\n"
    assert soils.domsoil_d == {"11": "30", "12": "30"}
    assert soils.soils["30"].pct_coverage == pytest.approx(100.0)


def test_build_singledb_handles_multidigit_topaz_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    soils_dir = wd / "soils"
    soils_dir.mkdir(parents=True, exist_ok=True)

    src_sol = tmp_path / "Forest silt loam.sol"
    src_sol.write_text("soil-body\n", encoding="utf-8")

    soils = Soils.__new__(Soils)
    soils.wd = str(wd)
    soils.logger = logging.getLogger("tests.nodb.soils_singledb")
    soils._single_dbselection = "Forest2006/Forest silt loam.sol"
    soils.locked = lambda: nullcontext()
    soils.trigger = lambda *_args, **_kwargs: None

    watershed_stub = SimpleNamespace(
        _subs_summary={"22": None, "123": None, "7": None},
        hillslope_area=lambda topaz_id: {"22": 1.5, "123": 3.0, "7": 0.5}[str(topaz_id)],
    )

    monkeypatch.setattr(Soils, "watershed_instance", property(lambda _self: watershed_stub))
    monkeypatch.setattr(Soils, "getInstance", classmethod(lambda cls, _wd: soils))
    monkeypatch.setattr("wepppy.nodb.core.soils.get_soil", lambda _key: str(src_sol))

    soils._build_singledb()

    mukey = "Forest2006-Forest silt loam"
    assert soils.domsoil_d == {"22": mukey, "123": mukey, "7": mukey}
    assert soils.ssurgo_domsoil_d == soils.domsoil_d
    assert soils.soils[mukey].pct_coverage == pytest.approx(100.0)
    assert soils.soils[mukey].area == pytest.approx(5.0)
    assert (soils_dir / "Forest silt loam.sol").read_text(encoding="utf-8") == "soil-body\n"


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


def test_soil_summary_meta_fn_resolves_legacy_runid_relative_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wepppy.soils.ssurgo import SoilSummary

    run_root = tmp_path / "legacy-run"
    meta_path = run_root / "soils" / "123.json"
    summary = SoilSummary(
        mukey="123",
        fname="123.sol",
        soils_dir=str(run_root / "soils"),
        build_date="2026-02-18",
        desc="legacy",
        meta_fn="legacy-run/soils/123.json",
    )

    def _fake_get_wd(runid: str) -> str:
        assert runid == "legacy-run"
        return str(run_root)

    monkeypatch.setattr("wepppy.weppcloud.utils.helpers.get_wd", _fake_get_wd)

    assert summary.meta_fn == str(meta_path)


def test_soil_summary_meta_fn_keeps_non_runid_relative_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wepppy.soils.ssurgo import SoilSummary

    summary = SoilSummary(
        mukey="123",
        fname="123.sol",
        soils_dir=str(tmp_path / "soils"),
        build_date="2026-02-18",
        desc="relative",
        meta_fn="soils/123.json",
    )

    def _unexpected_get_wd(_runid: str) -> str:
        raise AssertionError("get_wd should only be used for runid/soils metadata paths")

    monkeypatch.setattr("wepppy.weppcloud.utils.helpers.get_wd", _unexpected_get_wd)

    assert summary.meta_fn == "soils/123.json"


def test_init_reads_depth_config_keys_with_expected_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    float_calls: list[tuple[str, str, float | None]] = []

    def _fake_nodb_init(
        self: Soils,
        wd_arg: str,
        cfg_fn: str,
        run_group: str | None = None,
        group_name: str | None = None,
    ) -> None:
        self.wd = wd_arg
        self.logger = logging.getLogger("tests.nodb.soils_config")
        self._logger = self.logger

    monkeypatch.setattr("wepppy.nodb.core.soils.NoDbBase.__init__", _fake_nodb_init)
    monkeypatch.setattr(Soils, "locked", lambda self: nullcontext())
    monkeypatch.setattr(
        Soils,
        "config_get_path",
        lambda self, section, option, default=None: default,
    )
    monkeypatch.setattr(
        Soils,
        "config_get_bool",
        lambda self, section, option, default=False: bool(default),
    )
    monkeypatch.setattr(
        Soils,
        "config_get_float",
        lambda self, section, option, default=None: float_calls.append((section, option, default))
        or float(default if default is not None else 0.0),
    )

    _ = Soils(str(wd), "dummy.cfg")

    assert ("soils", "clip_soils_depth", 1000) in float_calls
    assert ("soils", "clip_soils_minimum_depth", 0) in float_calls


def test_rosetta_bd_toggle_round_trips_through_soils_nodb(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("wepppy.nodb.base.redis_nodb_cache_client", None)

    soils_nodb = wd / Soils.filename

    payload = Soils.__new__(Soils)
    payload.wd = str(wd)
    payload._config = "dummy.cfg"
    payload._rosetta_wc_fc_from_disturbed_bd_override = True

    soils_nodb.write_text(jsonpickle.encode(payload), encoding="utf-8")

    loaded = Soils.getInstance(str(wd), ignore_lock=True)
    assert loaded.rosetta_wc_fc_from_disturbed_bd_override is True

    loaded._rosetta_wc_fc_from_disturbed_bd_override = False
    soils_nodb.write_text(jsonpickle.encode(loaded), encoding="utf-8")

    loaded_again = Soils.getInstance(str(wd), ignore_lock=True)
    assert loaded_again.rosetta_wc_fc_from_disturbed_bd_override is False
