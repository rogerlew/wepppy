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
from wepppy.nodb.mods.rap.rap import RAP_Band
from wepppy.nodb.mods.rap.rap_ts import RAP_TS

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
        self.data = {
            RAP_Band.TREE: {
                "2010": {"5": 30.0, "6": 10.0, "7": 30.0, "8": 35.0},
            },
            RAP_Band.SHRUB: {
                "2010": {"5": 20.0, "6": 10.0, "7": 20.0, "8": 25.0},
            },
            RAP_Band.PERENNIAL_FORB_AND_GRASS: {
                "2010": {"5": 6.0, "6": 8.0, "7": 12.0, "8": 12.0},
            },
            RAP_Band.ANNUAL_FORB_AND_GRASS: {
                "2010": {"5": 5.0, "6": 5.0, "7": 10.0, "8": 12.0},
            },
        }

    def get_cover(self, topaz_id, year, fallback=True):  # noqa: ANN001
        topaz = str(topaz_id)
        self.calls.append((topaz, int(year), bool(fallback)))
        return RAP_TS.get_cover(self, topaz, str(year), fallback=fallback)


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
    deciduous_summary = _DummyManagementSummary("deciduous forest")
    mixed_summary = _DummyManagementSummary("mixed forest")
    young_summary = _DummyManagementSummary("young forest")
    fire_summary = _DummyManagementSummary("forest high sev fire")

    landuse_stub = type("LanduseStub", (), {})()
    landuse_stub.hillslope_cancovs = None
    landuse_stub.domlc_d = {
        "5": "forest_dom",
        "6": "fire_dom",
        "7": "deciduous_dom",
        "8": "mixed_dom",
        "9": "young_dom",
    }
    landuse_stub.managements = {
        "forest_dom": forest_summary,
        "fire_dom": fire_summary,
        "deciduous_dom": deciduous_summary,
        "mixed_dom": mixed_summary,
        "young_dom": young_summary,
    }

    climate_stub = type("ClimateStub", (), {"input_years": [2010], "year0": 2010})()
    watershed_stub = object()

    soils_stub = type("SoilsStub", (), {})()
    soils_stub.domsoil_d = {
        "5": "mukey_1",
        "6": "mukey_2",
        "7": "mukey_3",
        "8": "mukey_4",
        "9": "mukey_5",
    }
    soils_stub.bd_d = {
        "mukey_1": 1.2,
        "mukey_2": 1.3,
        "mukey_3": 1.4,
        "mukey_4": 1.5,
        "mukey_5": 1.6,
    }
    soils_stub.soils = {
        "mukey_1": type("SoilStub", (), {"clay": 20.0, "sand": 40.0})(),
        "mukey_2": type("SoilStub", (), {"clay": 25.0, "sand": 35.0})(),
        "mukey_3": type("SoilStub", (), {"clay": 25.0, "sand": 35.0})(),
        "mukey_4": type("SoilStub", (), {"clay": 25.0, "sand": 35.0})(),
        "mukey_5": type("SoilStub", (), {"clay": 25.0, "sand": 35.0})(),
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
    assert deciduous_summary.last_management is not None
    assert mixed_summary.last_management is not None
    assert young_summary.last_management is not None
    assert forest_summary.last_management.cancov_values == [0.61]
    assert fire_summary.last_management.cancov_values == []
    assert deciduous_summary.last_management.cancov_values == [0.72]
    assert mixed_summary.last_management.cancov_values == [0.84]
    assert young_summary.last_management.cancov_values == []
    assert rap_ts.calls == [("5", 2010, True), ("7", 2010, True), ("8", 2010, True)]
