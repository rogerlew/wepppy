from __future__ import annotations

from types import SimpleNamespace

import pytest

import wepppy.nodb.core as nodb_core_module
import wepppy.nodb.mods.disturbed.disturbed as disturbed_module
import wepppy.runtime_paths.wepp_inputs as wepp_inputs_module
from wepppy.nodb.mods.disturbed.disturbed import Disturbed

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


class _Plant:
    def __init__(self, name: str) -> None:
        self.name = name


class _Management:
    def __init__(self, name: str) -> None:
        self.plants = [_Plant(name)]


class _ManagementSummary:
    def __init__(self, disturbed_class: str, plant_name: str) -> None:
        self.disturbed_class = disturbed_class
        self._management = _Management(plant_name)

    def get_management(self) -> _Management:
        return self._management


class _SoilStub:
    def __init__(self, *, fname: str, clay: float, sand: float) -> None:
        self.fname = fname
        self.clay = clay
        self.sand = sand


class _FakeLanduse:
    def __init__(self, domlc_d, managements) -> None:
        self.domlc_d = domlc_d
        self.managements = managements


class _FakeSoils:
    def __init__(self, domsoil_d, soils) -> None:
        self.domsoil_d = domsoil_d
        self.soils = soils


def test_pmetpara_prep_writes_lookup_and_default_rows(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("pmetpara-main")

    landuse = _FakeLanduse(
        domlc_d={"101": "dom-1", "102": "dom-2", "104": "dom-chn"},
        managements={
            "dom-1": _ManagementSummary("forest high sev fire-mulch_15", "pine"),
            "dom-2": _ManagementSummary("developed low intensity", "urban"),
            "dom-chn": _ManagementSummary("forest", "channel"),
        },
    )
    soils = _FakeSoils(
        domsoil_d={"101": "m1", "102": "m2"},
        soils={
            "m1": _SoilStub(fname="m1.sol", clay=20.0, sand=40.0),
            "m2": _SoilStub(fname="m2.sol", clay=15.0, sand=55.0),
        },
    )

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(
        nodb_core_module.Wepp,
        "getInstance",
        classmethod(lambda cls, _wd: SimpleNamespace(runs_dir=str(run_dir / "wepp" / "runs"))),
    )
    monkeypatch.setattr(wepp_inputs_module, "materialize_input_file", lambda wd, relpath, purpose: str(run_dir / relpath))
    monkeypatch.setattr(disturbed_module, "WeppSoilUtil", _FakeWeppSoilUtil)
    monkeypatch.setattr(disturbed_module, "simple_texture", lambda clay, sand: "mock-texture")
    monkeypatch.setattr(
        Disturbed,
        "land_soil_replacements_d",
        property(lambda self: {("mock-texture", "mulch"): {"pmet_kcb": "0.77", "pmet_rawp": "0.66"}}),
    )

    disturbed.pmetpara_prep()

    pmetpara_path = run_dir / "wepp" / "runs" / "pmetpara.txt"
    lines = pmetpara_path.read_text().strip().splitlines()

    assert lines[0] == "2"
    assert lines[1].startswith("pine,0.77,0.66,1,mock-texture-mulch")
    assert lines[2].startswith("urban,0.95,0.8,2,mock-texture-developed_low_intensity")


def test_pmetpara_prep_falls_back_to_soil_summary_texture_when_archive_materialization_fails(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("pmetpara-fallback")

    landuse = _FakeLanduse(
        domlc_d={"101": "dom-1"},
        managements={"dom-1": _ManagementSummary("thinning_40_75", "pine")},
    )
    soils = _FakeSoils(
        domsoil_d={"101": "m1"},
        soils={"m1": _SoilStub(fname="m1.sol", clay=22.0, sand=44.0)},
    )

    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(
        nodb_core_module.Wepp,
        "getInstance",
        classmethod(lambda cls, _wd: SimpleNamespace(runs_dir=str(run_dir / "wepp" / "runs"))),
    )
    monkeypatch.setattr(
        wepp_inputs_module,
        "materialize_input_file",
        lambda wd, relpath, purpose: (_ for _ in ()).throw(RuntimeError("archive unavailable")),
    )
    monkeypatch.setattr(disturbed_module, "simple_texture", lambda clay, sand: "fallback-texture")
    monkeypatch.setattr(
        Disturbed,
        "land_soil_replacements_d",
        property(lambda self: {("fallback-texture", "thinning"): {"pmet_kcb": "0.61", "pmet_rawp": "0.52"}}),
    )

    disturbed.pmetpara_prep()

    pmetpara_path = run_dir / "wepp" / "runs" / "pmetpara.txt"
    lines = pmetpara_path.read_text().strip().splitlines()

    assert lines[0] == "1"
    assert lines[1].startswith("pine,0.61,0.52,1,fallback-texture-thinning")
