from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.mods.disturbed.disturbed as disturbed_module
from wepppy.nodb.mods.disturbed.disturbed import Disturbed

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


class _NoopLogger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return

    def warning(self, *_args: object, **_kwargs: object) -> None:
        return


class _ManagementSummary:
    def __init__(self, disturbed_class: str, *, sol_path: str | None = None) -> None:
        self.disturbed_class = disturbed_class
        self.sol_path = sol_path
        self.sol_fn = sol_path or ""


class _SoilStub:
    def __init__(
        self,
        *,
        clay: float,
        sand: float,
        fname: str,
        desc: str = "base-soil",
        meta_fn: str | None = None,
    ) -> None:
        self.clay = clay
        self.sand = sand
        self.fname = fname
        self.desc = desc
        self.meta_fn = meta_fn
        self.area = 0.0
        self.pct_coverage = 0.0


class _FakeLanduse:
    def __init__(self, domlc_d, managements) -> None:
        self.domlc_d = domlc_d
        self.managements = managements


class _FakeSoils:
    def __init__(self, *, domsoil_d, soils, soils_dir: str, parent_wd: str | None = None) -> None:
        self.domsoil_d = domsoil_d
        self.soils = soils
        self.soils_dir = soils_dir
        self.parent_wd = parent_wd
        self.logger = _NoopLogger()

    @contextmanager
    def locked(self):
        yield


class _FakeWatershed:
    def __init__(self, areas: dict[str, float]) -> None:
        self._areas = areas

    def hillslope_area(self, topaz_id: str) -> float:
        return self._areas[str(topaz_id)]


class _FakeWriter:
    def __init__(self, writes: list[str]) -> None:
        self._writes = writes

    def write(self, path: str) -> None:
        self._writes.append(path)


def test_modify_soil_uses_parent_soil_source_when_local_file_missing(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-soil-parent")

    parent_wd = run_dir / "parent"
    parent_soils_dir = parent_wd / "soils"
    parent_soils_dir.mkdir(parents=True)
    (parent_soils_dir / "763002.sol").write_text("parent soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "763002"},
        soils={"763002": _SoilStub(clay=30.0, sand=40.0, fname="763002.sol")},
        soils_dir=str(run_dir / "soils"),
        parent_wd=str(parent_wd),
    )
    landuse = _FakeLanduse(
        domlc_d={"101": "dom-1"},
        managements={"dom-1": _ManagementSummary("forest high sev fire")},
    )

    calls: list[str] = []
    writes: list[str] = []

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            calls.append(source_path)
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(self, replacements, h0_max_om=None, version=None):
            return _FakeWriter(writes)

    monkeypatch.setattr(disturbed_module, "simple_texture", lambda clay, sand: "mock-texture")
    monkeypatch.setattr(disturbed_module, "WeppSoilUtil", _FakeWeppSoilUtil)

    lookup = {("mock-texture", "forest high sev fire"): {"ki": "1"}}
    disturbed.modify_soil("101", landuse, soils, lookup)

    assert calls == [str(parent_soils_dir / "763002.sol")]
    assert writes == [str(run_dir / "soils" / "763002-mock-texture-forest high sev fire.sol")]


def test_modify_soil_strips_treatment_suffix_for_lookup(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-soil-suffix")

    source_file = run_dir / "soils" / "src.sol"
    source_file.write_text("soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "m1"},
        soils={"m1": _SoilStub(clay=30.0, sand=40.0, fname="src.sol")},
        soils_dir=str(run_dir / "soils"),
    )
    landuse = _FakeLanduse(
        domlc_d={"101": "dom-1"},
        managements={"dom-1": _ManagementSummary("forest moderate sev fire-mulch_15")},
    )

    seen_replacements: list[dict[str, str]] = []

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(self, replacements, h0_max_om=None, version=None):
            seen_replacements.append(dict(replacements))
            return _FakeWriter([])

    monkeypatch.setattr(disturbed_module, "simple_texture", lambda clay, sand: "mock-texture")
    monkeypatch.setattr(disturbed_module, "WeppSoilUtil", _FakeWeppSoilUtil)

    lookup = {("mock-texture", "forest moderate sev fire"): {"ki": "2"}}
    disturbed_mukey = disturbed.modify_soil("101", landuse, soils, lookup)

    assert disturbed_mukey == "m1-mock-texture-forest moderate sev fire-mulch_15"
    assert seen_replacements == [{"ki": "2"}]


def test_modify_soil_passes_copy_of_lookup_replacements(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-soil-copy")

    source_file = run_dir / "soils" / "src.sol"
    source_file.write_text("soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "m1"},
        soils={"m1": _SoilStub(clay=30.0, sand=40.0, fname="src.sol")},
        soils_dir=str(run_dir / "soils"),
    )
    landuse = _FakeLanduse(
        domlc_d={"101": "dom-1"},
        managements={"dom-1": _ManagementSummary("forest high sev fire")},
    )

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(self, replacements, h0_max_om=None, version=None):
            replacements["ki"] = "mutated-by-converter"
            return _FakeWriter([])

    monkeypatch.setattr(disturbed_module, "simple_texture", lambda clay, sand: "mock-texture")
    monkeypatch.setattr(disturbed_module, "WeppSoilUtil", _FakeWeppSoilUtil)

    lookup_row = {"ki": "original"}
    lookup = {("mock-texture", "forest high sev fire"): lookup_row}

    disturbed.modify_soil("101", landuse, soils, lookup)

    assert lookup_row["ki"] == "original"


def test_modify_soils_recomputes_area_and_pct_coverage(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, _ = disturbed_factory("modify-soils-area")

    soils = _FakeSoils(
        domsoil_d={"101": "base-1", "104": "base-chn", "105": "base-2"},
        soils={
            "base-1": _SoilStub(clay=20.0, sand=40.0, fname="a.sol"),
            "base-chn": _SoilStub(clay=20.0, sand=40.0, fname="b.sol"),
            "base-2": _SoilStub(clay=20.0, sand=40.0, fname="c.sol"),
            "dist-101": _SoilStub(clay=20.0, sand=40.0, fname="d.sol"),
            "dist-105": _SoilStub(clay=20.0, sand=40.0, fname="e.sol"),
        },
        soils_dir="/tmp/unused",
    )

    landuse = _FakeLanduse(domlc_d={"101": "a", "105": "b"}, managements={})
    watershed = _FakeWatershed({"101": 2.0, "105": 3.0})

    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "watershed_instance", property(lambda self: watershed))
    monkeypatch.setattr(Disturbed, "land_soil_replacements_d", property(lambda self: {}))
    monkeypatch.setattr(
        Disturbed,
        "modify_soil",
        lambda self, topaz_id, _landuse, _soils, _lookup: f"dist-{topaz_id}",
    )

    disturbed.modify_soils()

    assert soils.domsoil_d["101"] == "dist-101"
    assert soils.domsoil_d["104"] == "base-chn"
    assert soils.domsoil_d["105"] == "dist-105"

    assert soils.soils["dist-101"].area == pytest.approx(2.0)
    assert soils.soils["dist-105"].area == pytest.approx(3.0)
    assert soils.soils["dist-101"].pct_coverage == pytest.approx(40.0)
    assert soils.soils["dist-105"].pct_coverage == pytest.approx(60.0)


def test_modify_soils_sets_zero_pct_when_total_area_is_zero(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, _ = disturbed_factory("modify-soils-zero")

    soils = _FakeSoils(
        domsoil_d={"101": "base-1", "105": "base-2"},
        soils={
            "base-1": _SoilStub(clay=20.0, sand=40.0, fname="a.sol"),
            "base-2": _SoilStub(clay=20.0, sand=40.0, fname="b.sol"),
            "dist-101": _SoilStub(clay=20.0, sand=40.0, fname="d.sol"),
            "dist-105": _SoilStub(clay=20.0, sand=40.0, fname="e.sol"),
        },
        soils_dir="/tmp/unused",
    )

    landuse = _FakeLanduse(domlc_d={"101": "a", "105": "b"}, managements={})
    watershed = _FakeWatershed({"101": 0.0, "105": 0.0})

    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "watershed_instance", property(lambda self: watershed))
    monkeypatch.setattr(Disturbed, "land_soil_replacements_d", property(lambda self: {}))
    monkeypatch.setattr(
        Disturbed,
        "modify_soil",
        lambda self, topaz_id, _landuse, _soils, _lookup: f"dist-{topaz_id}",
    )

    disturbed.modify_soils()

    assert all(soil.pct_coverage == 0.0 for soil in soils.soils.values())
