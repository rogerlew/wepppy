import logging
from pathlib import Path

import pytest

import wepppy.nodb.core.wepp as wepp_module
import wepppy.nodb.mods as nodb_mods
from wepppy.nodb.core.climate import Climate
from wepppy.nodb.core.landuse import Landuse
from wepppy.nodb.core.soils import Soils
from wepppy.nodb.core.watershed import Watershed
from wepppy.nodb.core.wepp import Wepp

pytestmark = pytest.mark.unit


class _DummyManagement:
    def __init__(self) -> None:
        self.cancov_values: list[float] = []

    def set_bdtill(self, value: float) -> None:
        pass

    def set_cancov(self, value: float) -> None:
        self.cancov_values.append(float(value))

    def set_rdmax(self, value: float) -> None:
        pass

    def set_xmxlai(self, value: float) -> None:
        pass

    def __setitem__(self, attr: str, value: float) -> None:
        pass

    def build_multiple_year_man(self, years):  # noqa: ANN001
        return self

    def __str__(self) -> str:
        return "dummy\n"


class _DummyManagementSummary:
    def __init__(self, disturbed_class: str) -> None:
        self.disturbed_class = disturbed_class
        self.cancov_override = None
        self.last_management: _DummyManagement | None = None

    def get_management(self) -> _DummyManagement:
        self.last_management = _DummyManagement()
        return self.last_management


class _TranslatorStub:
    @staticmethod
    def wepp(top: int) -> int:
        return int(top)


class _RapTsStub:
    def __init__(self) -> None:
        self.rap_start_year = 2000
        self.rap_end_year = 2020
        self.calls: list[tuple[str, int, bool]] = []

    def get_cover(self, topaz_id, year, fallback=True):  # noqa: ANN001
        topaz = str(topaz_id)
        self.calls.append((topaz, int(year), bool(fallback)))
        return {"5": 0.61, "6": 0.33}[topaz]


def test_prep_managements_rap_ts_only_updates_undisturbed_classes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = Wepp.__new__(Wepp)
    wepp.wd = str(tmp_path)
    Path(wepp.runs_dir).mkdir(parents=True, exist_ok=True)
    Path(wepp.fp_runs_dir).mkdir(parents=True, exist_ok=True)
    wepp.logger = logging.getLogger("tests.wepp.rap_ts_cover_scope")
    wepp._mods = []

    forest_summary = _DummyManagementSummary("forest")
    fire_summary = _DummyManagementSummary("forest high sev fire")

    landuse_stub = type("LanduseStub", (), {})()
    landuse_stub.hillslope_cancovs = None
    landuse_stub.domlc_d = {"5": "forest_dom", "6": "fire_dom"}
    landuse_stub.managements = {
        "forest_dom": forest_summary,
        "fire_dom": fire_summary,
    }

    climate_stub = type("ClimateStub", (), {"input_years": [2010], "year0": 2010})()
    watershed_stub = object()

    soils_stub = type("SoilsStub", (), {})()
    soils_stub.domsoil_d = {"5": "mukey_1", "6": "mukey_2"}
    soils_stub.bd_d = {"mukey_1": 1.2, "mukey_2": 1.3}
    soils_stub.soils = {
        "mukey_1": type("SoilStub", (), {"clay": 20.0, "sand": 40.0})(),
        "mukey_2": type("SoilStub", (), {"clay": 25.0, "sand": 35.0})(),
    }
    monkeypatch.setattr(Landuse, "getInstance", classmethod(lambda cls, wd: landuse_stub))
    monkeypatch.setattr(Climate, "getInstance", classmethod(lambda cls, wd: climate_stub))
    monkeypatch.setattr(Soils, "getInstance", classmethod(lambda cls, wd: soils_stub))
    monkeypatch.setattr(Watershed, "getInstance", classmethod(lambda cls, wd: watershed_stub))

    disturbed_instance = type("DisturbedInstanceStub", (), {"land_soil_replacements_d": {}})()
    disturbed_stub = type(
        "DisturbedStub",
        (),
        {"tryGetInstance": staticmethod(lambda wd: disturbed_instance)},
    )
    monkeypatch.setattr(wepp_module, "Disturbed", disturbed_stub)

    rap_ts = _RapTsStub()
    rap_ts_stub = type(
        "RAP_TS_Stub",
        (),
        {"tryGetInstance": staticmethod(lambda wd: rap_ts)},
    )
    monkeypatch.setattr(nodb_mods, "RAP_TS", rap_ts_stub)

    wepp._prep_managements(_TranslatorStub())

    assert forest_summary.last_management is not None
    assert fire_summary.last_management is not None
    assert forest_summary.last_management.cancov_values == [0.61]
    assert fire_summary.last_management.cancov_values == []
    assert rap_ts.calls == [("5", 2010, True)]
