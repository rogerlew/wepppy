from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import pytest

import wepppy.nodb.core as nodb_core_module
import wepppy.nodb.mods.disturbed.disturbed as disturbed_module
import wepppy.runtime_paths.wepp_inputs as wepp_inputs_module
from wepppy.nodb.mods.disturbed.disturbed import Disturbed

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


@pytest.fixture(autouse=True)
def translator(monkeypatch):
    monkeypatch.setattr(nodb_core_module.Watershed, 'getInstance',
                        classmethod(lambda cls, wd: SimpleNamespace(
                            translator_factory=lambda: SimpleNamespace(wepp=lambda top: top - 100))))


def stage_management(run_dir, names):
    from tests.wepp.management.test_multiple_ofe import HIGH_SEVERITY_FIRE_MAN
    for index, name in enumerate(names, 1):
        (run_dir / 'wepp' / 'runs' / f'p{index}.man').write_text(
            HIGH_SEVERITY_FIRE_MAN.replace('Tah_6892', name))


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
        classmethod(lambda cls, _wd: SimpleNamespace(runs_dir=str(run_dir / "wepp" / "runs"), multi_ofe=False)),
    )
    monkeypatch.setattr(wepp_inputs_module, "materialize_input_file", lambda wd, relpath, purpose: str(run_dir / relpath))
    monkeypatch.setattr(disturbed_module, "WeppSoilUtil", _FakeWeppSoilUtil)
    monkeypatch.setattr(disturbed_module, "simple_texture", lambda clay, sand: "mock-texture")
    monkeypatch.setattr(
        Disturbed,
        "land_soil_replacements_d",
        property(
            lambda self: {
                ("mock-texture", "forest high sev fire"): {
                    "pmet_kcb": "0.77",
                    "pmet_rawp": "0.66",
                }
            }
        ),
    )

    stage_management(run_dir, ['pine', 'urban'])
    disturbed.pmetpara_prep()

    pmetpara_path = run_dir / "wepp" / "runs" / "pmetpara.txt"
    lines = pmetpara_path.read_text().strip().splitlines()

    assert lines[0] == "2"
    assert lines[1].startswith("pine,0.77,0.66,1,mock-texture-forest_high_sev_fire")
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
        classmethod(lambda cls, _wd: SimpleNamespace(runs_dir=str(run_dir / "wepp" / "runs"), multi_ofe=False)),
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

    stage_management(run_dir, ['pine'])
    disturbed.pmetpara_prep()

    pmetpara_path = run_dir / "wepp" / "runs" / "pmetpara.txt"
    lines = pmetpara_path.read_text().strip().splitlines()

    assert lines[0] == "1"
    assert lines[1].startswith("pine,0.61,0.52,1,fallback-texture-thinning")


def test_mofe_uses_each_staged_soil_and_final_landuse(disturbed_factory, monkeypatch):
    from copy import deepcopy
    from wepppy.wepp.management import read_management
    from wepppy.wepp.management.utils import ManagementMultipleOfeSynth
    from wepppy.wepp.soils.utils import WeppSoilUtil, simple_texture
    from tests.wepp.management.test_mofe_input_identity import CORN

    disturbed, run_dir = disturbed_factory('pmetpara-mofe')
    runs = run_dir / 'wepp' / 'runs'
    runs.mkdir(parents=True, exist_ok=True)
    source = read_management(str(CORN))
    ManagementMultipleOfeSynth([source, source], deduplicate_scenarios=True).write(str(runs / 'p1.man'))
    soil = WeppSoilUtil(str(Path(__file__).resolve().parents[3] / 'wepp_runner/fixtures/hillslope_smoke/runs/p1.sol'))
    soil.obj['ofes'].append(deepcopy(soil.obj['ofes'][0]))
    soil.obj['ntemp'] = 2
    textures = [(10.0, 80.0), (40.0, 20.0)]
    for ofe, (clay, sand) in zip(soil.obj['ofes'], textures):
        ofe['horizons'][0].update(clay=clay, sand=sand)
    soil.write(str(runs / 'p1.sol'))
    landuse = SimpleNamespace(domlc_d={'101': 'first'}, domlc_mofe_d={'101': {'2': 'second', '1': 'first'}},
                             managements={'first': _ManagementSummary('forest', 'unused'),
                                          'second': _ManagementSummary('shrub', 'unused')})
    lookup = {(simple_texture(clay=clay, sand=sand), label): {'pmet_kcb': kcb, 'pmet_rawp': rawp}
              for (clay, sand), label, kcb, rawp in zip(textures, ['forest', 'shrub'], [0.31, 0.79], [0.42, 0.86])}
    monkeypatch.setattr(Disturbed, 'landuse_instance', property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, 'soils_instance', property(lambda self: SimpleNamespace()))
    monkeypatch.setattr(Disturbed, 'land_soil_replacements_d', property(lambda self: lookup))
    monkeypatch.setattr(nodb_core_module.Wepp, 'getInstance', classmethod(
        lambda cls, wd: SimpleNamespace(runs_dir=str(runs), multi_ofe=True)))
    disturbed.pmetpara_prep()
    result = read_management(str(runs / 'p1.man'))
    rows = {parts[0]: tuple(map(float, parts[1:3])) for parts in
            (line.split(',') for line in (runs / 'pmetpara.txt').read_text().splitlines()[1:])}
    years = {year.name: year for year in result.years}
    for rotation in result.man.loops:
        for year in rotation.years:
            for ofe, data in enumerate(year):
                for ref in data.manindx:
                    assert rows[years[ref.loop_name].data.itype.loop_name] == [(0.31, 0.42), (0.79, 0.86)][ofe]
    before = {p.name: p.read_bytes() for p in runs.iterdir()}
    disturbed.pmetpara_prep()
    assert before == {p.name: p.read_bytes() for p in runs.iterdir()}
