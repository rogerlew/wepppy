from __future__ import annotations

from contextlib import contextmanager
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
    def __init__(self, disturbed_class: str) -> None:
        self.disturbed_class = disturbed_class


class _SoilStub:
    def __init__(self, *, clay: float, sand: float, fname: str, desc: str = "base", meta_fn: str | None = None):
        self.clay = clay
        self.sand = sand
        self.fname = fname
        self.desc = desc
        self.meta_fn = meta_fn
        self.area = 0.0
        self.pct_coverage = 0.0


class _FakeLanduse:
    def __init__(self, *, domlc_mofe_d, managements) -> None:
        self.domlc_mofe_d = domlc_mofe_d
        self.managements = managements


class _FakeSoils:
    def __init__(self, *, domsoil_d, soils, soils_dir: str) -> None:
        self.domsoil_d = domsoil_d
        self.soils = soils
        self.soils_dir = soils_dir
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


def test_modify_mofe_soils_uses_base_lookup_class_for_treatments(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-suffix")
    disturbed._sol_ver = 9005.0
    (run_dir / "soils" / "src.sol").write_text("soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "m1"},
        soils={"m1": _SoilStub(clay=30.0, sand=40.0, fname="src.sol")},
        soils_dir=str(run_dir / "soils"),
    )
    landuse = _FakeLanduse(
        domlc_mofe_d={"101": {"1": "dom-1", "2": "dom-2"}},
        managements={
            "dom-1": _ManagementSummary("forest high sev fire-mulch_15"),
            "dom-2": _ManagementSummary("forest high sev fire"),
        },
    )
    watershed = _FakeWatershed({"101": 5.0})

    replacements_seen: list[dict[str, str]] = []
    stack_writes: list[list[str]] = []
    write_paths: list[str] = []

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(self, replacements, h0_max_om=None, version=None):
            replacements_seen.append(dict(replacements))
            return _FakeWriter(write_paths)

    class _FakeMofeSynth:
        def __init__(self, stack):
            stack_writes.append(list(stack))

        def write(self, path: str) -> None:
            write_paths.append(path)

    monkeypatch.setattr(disturbed_module, "Ron", SimpleNamespace(getInstance=lambda _wd: object()))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "watershed_instance", property(lambda self: watershed))
    monkeypatch.setattr(disturbed_module, "simple_texture", lambda clay, sand: "mock-texture")
    monkeypatch.setattr(disturbed_module, "WeppSoilUtil", _FakeWeppSoilUtil)
    monkeypatch.setattr(disturbed_module, "SoilMultipleOfeSynth", _FakeMofeSynth)

    lookup_row = {"ki": "1"}
    monkeypatch.setattr(
        Disturbed,
        "land_soil_replacements_d",
        property(lambda self: {("mock-texture", "forest high sev fire"): lookup_row}),
    )

    disturbed.modify_mofe_soils()

    assert ("m1-mock-texture-forest high sev fire-mulch_15") in soils.soils
    assert ("m1-mock-texture-forest high sev fire") in soils.soils
    assert replacements_seen == [{"ki": "1"}, {"ki": "1"}]
    assert soils.domsoil_d["101"] == "hill_101.mofe"
    assert soils.soils["hill_101.mofe"].pct_coverage == pytest.approx(100.0)


def test_modify_mofe_soils_passes_copy_of_lookup_replacements(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-copy")
    disturbed._sol_ver = 9005.0
    (run_dir / "soils" / "src.sol").write_text("soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "m1"},
        soils={"m1": _SoilStub(clay=30.0, sand=40.0, fname="src.sol")},
        soils_dir=str(run_dir / "soils"),
    )
    landuse = _FakeLanduse(
        domlc_mofe_d={"101": {"1": "dom-1"}},
        managements={"dom-1": _ManagementSummary("forest high sev fire")},
    )
    watershed = _FakeWatershed({"101": 1.0})

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(self, replacements, h0_max_om=None, version=None):
            replacements["ki"] = "mutated"
            return _FakeWriter([])

    class _FakeMofeSynth:
        def __init__(self, stack):
            self.stack = stack

        def write(self, path: str) -> None:
            return

    lookup_row = {"ki": "original"}

    monkeypatch.setattr(disturbed_module, "Ron", SimpleNamespace(getInstance=lambda _wd: object()))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "watershed_instance", property(lambda self: watershed))
    monkeypatch.setattr(disturbed_module, "simple_texture", lambda clay, sand: "mock-texture")
    monkeypatch.setattr(disturbed_module, "WeppSoilUtil", _FakeWeppSoilUtil)
    monkeypatch.setattr(disturbed_module, "SoilMultipleOfeSynth", _FakeMofeSynth)
    monkeypatch.setattr(
        Disturbed,
        "land_soil_replacements_d",
        property(lambda self: {("mock-texture", "forest high sev fire"): lookup_row}),
    )

    disturbed.modify_mofe_soils()

    assert lookup_row["ki"] == "original"


def test_modify_mofe_soils_sets_zero_pct_when_total_area_is_zero(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-zero")
    disturbed._sol_ver = 9005.0
    (run_dir / "soils" / "src.sol").write_text("soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "m1"},
        soils={"m1": _SoilStub(clay=30.0, sand=40.0, fname="src.sol")},
        soils_dir=str(run_dir / "soils"),
    )
    landuse = _FakeLanduse(
        domlc_mofe_d={"101": {"1": "dom-1"}},
        managements={"dom-1": _ManagementSummary("forest high sev fire")},
    )
    watershed = _FakeWatershed({"101": 0.0})

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(self, replacements, h0_max_om=None, version=None):
            return _FakeWriter([])

    class _FakeMofeSynth:
        def __init__(self, stack):
            self.stack = stack

        def write(self, path: str) -> None:
            return

    monkeypatch.setattr(disturbed_module, "Ron", SimpleNamespace(getInstance=lambda _wd: object()))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "watershed_instance", property(lambda self: watershed))
    monkeypatch.setattr(disturbed_module, "simple_texture", lambda clay, sand: "mock-texture")
    monkeypatch.setattr(disturbed_module, "WeppSoilUtil", _FakeWeppSoilUtil)
    monkeypatch.setattr(disturbed_module, "SoilMultipleOfeSynth", _FakeMofeSynth)
    monkeypatch.setattr(
        Disturbed,
        "land_soil_replacements_d",
        property(lambda self: {("mock-texture", "forest high sev fire"): {"ki": "1"}}),
    )

    disturbed.modify_mofe_soils()

    assert all(soil.pct_coverage == 0.0 for soil in soils.soils.values())
