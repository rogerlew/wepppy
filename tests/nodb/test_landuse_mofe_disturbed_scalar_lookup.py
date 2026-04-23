from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.core.landuse as landuse_module
from wepppy.nodb.core.landuse import Landuse

pytestmark = pytest.mark.unit


class _LoggerStub:
    def info(self, *_args, **_kwargs) -> None:
        return None

    def warning(self, *_args, **_kwargs) -> None:
        return None

    def error(self, *_args, **_kwargs) -> None:
        return None


class _ManagementStub:
    def __init__(self) -> None:
        self.rdmax_values: list[float] = []
        self.xmxlai_values: list[float] = []
        self.cancov_values: list[float] = []
        self.overrides: dict[str, float] = {}

    def set_rdmax(self, value: float) -> None:
        self.rdmax_values.append(value)

    def set_xmxlai(self, value: float) -> None:
        self.xmxlai_values.append(value)

    def set_cancov(self, value: float) -> None:
        self.cancov_values.append(value)
        self.overrides["ini.data.cancov"] = float(value)

    def __setitem__(self, attr: str, value: str | float | int) -> None:
        self.overrides[attr] = float(value)

    def __str__(self) -> str:
        return "management-stub\n"


class _ManagementSummaryStub:
    def __init__(self, management: _ManagementStub, disturbed_class: str) -> None:
        self._management = management
        self.disturbed_class = disturbed_class

    def get_management(self) -> _ManagementStub:
        return self._management


def test_build_multiple_ofe_accepts_extended_rdmax_xmxlai_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "landuse").mkdir(parents=True, exist_ok=True)

    management = _ManagementStub()
    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(run_dir)
    landuse._mods = []
    landuse.managements = {
        "forest-dom": _ManagementSummaryStub(
            management=management,
            disturbed_class="forest moderate sev fire",
        )
    }
    landuse.locked = lambda: nullcontext()
    landuse.logger = _LoggerStub()

    watershed = SimpleNamespace(
        _subs_summary={"101": {}},
        mofe_nsegments={"101": "1"},
        mofe_buffer=False,
        subwta=str(run_dir / "watershed" / "subwta.tif"),
        mofe_map=str(run_dir / "watershed" / "mofe_map.tif"),
    )
    monkeypatch.setattr(
        Landuse,
        "watershed_instance",
        property(lambda _self: watershed),
    )

    class _LandcoverMapStub:
        def __init__(self, _lc_fn: str) -> None:
            pass

        def build_lcgrid(self, _subwta: str, _mofe_map: str) -> dict[str, dict[str, str]]:
            return {"101": {"1": "forest-dom"}}

    monkeypatch.setattr(landuse_module, "LandcoverMap", _LandcoverMapStub)
    monkeypatch.setattr(landuse_module, "wepppyo3", None)

    class _DisturbedStub:
        burn_shrubs = False
        burn_grass = False
        land_soil_replacements_d = {
            ("sand loam", "forest moderate sev fire"): {
                "plant.data.rdmax": "0.33",
                "plant.data.xmxlai": "5.7",
                "plant.data.decfct": "1.0",
            }
        }

        def get_disturbed_key_lookup(self) -> dict[str, str]:
            return {}

        def get_sbs(self) -> None:
            return None

    disturbed = _DisturbedStub()
    monkeypatch.setattr(
        "wepppy.nodb.mods.disturbed.Disturbed.tryGetInstance",
        lambda _wd: disturbed,
    )

    landuse._build_multiple_ofe()

    assert management.rdmax_values == [0.33]
    assert management.xmxlai_values == [5.7]
    assert management.overrides["plant.data.decfct"] == pytest.approx(1.0)
    assert (run_dir / "landuse" / "hill_101.mofe.man").exists()


def test_build_multiple_ofe_rap_cancov_overrides_lookup_ini_cancov(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "landuse").mkdir(parents=True, exist_ok=True)

    management = _ManagementStub()
    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(run_dir)
    landuse._mods = ["rap"]
    landuse.managements = {
        "forest-dom": _ManagementSummaryStub(
            management=management,
            disturbed_class="forest moderate sev fire",
        )
    }
    landuse.locked = lambda: nullcontext()
    landuse.logger = _LoggerStub()

    watershed = SimpleNamespace(
        _subs_summary={"101": {}},
        mofe_nsegments={"101": "1"},
        mofe_buffer=False,
        subwta=str(run_dir / "watershed" / "subwta.tif"),
        mofe_map=str(run_dir / "watershed" / "mofe_map.tif"),
    )
    monkeypatch.setattr(
        Landuse,
        "watershed_instance",
        property(lambda _self: watershed),
    )

    class _LandcoverMapStub:
        def __init__(self, _lc_fn: str) -> None:
            pass

        def build_lcgrid(self, _subwta: str, _mofe_map: str) -> dict[str, dict[str, str]]:
            return {"101": {"1": "forest-dom"}}

    monkeypatch.setattr(landuse_module, "LandcoverMap", _LandcoverMapStub)
    monkeypatch.setattr(landuse_module, "wepppyo3", None)

    class _DisturbedStub:
        burn_shrubs = False
        burn_grass = False
        land_soil_replacements_d = {
            ("sand loam", "forest moderate sev fire"): {
                "ini.data.cancov": "0.11",
                "plant.data.rdmax": "0.33",
                "plant.data.xmxlai": "5.7",
            }
        }

        def get_disturbed_key_lookup(self) -> dict[str, str]:
            return {}

        def get_sbs(self) -> None:
            return None

    class _RapStub:
        mofe_data = {
            landuse_module.RAP_Band.TREE: {"101": {"1": 70.0}},
            landuse_module.RAP_Band.SHRUB: {"101": {"1": 20.0}},
            landuse_module.RAP_Band.ANNUAL_FORB_AND_GRASS: {"101": {"1": 5.0}},
            landuse_module.RAP_Band.PERENNIAL_FORB_AND_GRASS: {"101": {"1": 5.0}},
        }

    disturbed = _DisturbedStub()
    monkeypatch.setattr(
        "wepppy.nodb.mods.disturbed.Disturbed.tryGetInstance",
        lambda _wd: disturbed,
    )
    monkeypatch.setattr(
        "wepppy.nodb.mods.rap.RAP.getInstance",
        lambda _wd: _RapStub(),
    )

    landuse._build_multiple_ofe()

    assert management.cancov_values == [pytest.approx(1.0)]
    assert management.overrides["ini.data.cancov"] == pytest.approx(1.0)
    assert management.rdmax_values == [0.33]
    assert management.xmxlai_values == [5.7]
