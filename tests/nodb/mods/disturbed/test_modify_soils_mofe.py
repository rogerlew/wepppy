from __future__ import annotations

from concurrent.futures import Future
from concurrent.futures.process import BrokenProcessPool
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

import wepppy.nodb.mods.disturbed.disturbed as disturbed_module
from wepppy.nodb.mods.disturbed.disturbed import Disturbed

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


class _NoopLogger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return

    def debug(self, *_args: object, **_kwargs: object) -> None:
        return

    def warning(self, *_args: object, **_kwargs: object) -> None:
        return


class _RecordingLogger(_NoopLogger):
    def __init__(self) -> None:
        self.info_messages: list[str] = []
        self.debug_messages: list[str] = []

    @staticmethod
    def _format(message: str, *args: object) -> str:
        if args:
            return message % args
        return str(message)

    def info(self, message: str, *args: object, **_kwargs: object) -> None:
        self.info_messages.append(self._format(message, *args))

    def debug(self, message: str, *args: object, **_kwargs: object) -> None:
        self.debug_messages.append(self._format(message, *args))


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
    def __init__(self, *, domsoil_d, soils, soils_dir: str, logger=None) -> None:
        self.domsoil_d = domsoil_d
        self.soils = soils
        self.soils_dir = soils_dir
        self.logger = logger or _NoopLogger()

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


class _InlineProcessPoolExecutor:
    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> bool:
        return False

    def submit(self, fn, task):
        future: Future = Future()
        try:
            future.set_result(fn(task))
        except Exception as exc:
            future.set_exception(exc)
        return future


@pytest.fixture(autouse=True)
def _inline_process_pool_executor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        disturbed_module,
        "createProcessPoolExecutor",
        lambda max_workers, logger=None, prefer_spawn=True: _InlineProcessPoolExecutor(),
    )


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

        def to_over9000(
            self,
            replacements,
            h0_max_om=None,
            recompute_wp_fc_using_rosetta_on_bd_override=False,
            version=None,
        ):
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


def test_modify_mofe_soils_9002_lookup_hit_uses_lookup_row_and_class_key(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-9002-hit")
    disturbed._sol_ver = 9002.0
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

    replacements_seen: list[dict[str, object]] = []
    versions_seen: list[float | None] = []
    stack_paths: list[list[str]] = []

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(
            self,
            replacements,
            h0_max_om=None,
            recompute_wp_fc_using_rosetta_on_bd_override=False,
            version=None,
        ):
            replacements_seen.append(dict(replacements))
            versions_seen.append(version)
            return _FakeWriter([])

    class _FakeMofeSynth:
        def __init__(self, stack):
            stack_paths.append(list(stack))

        def write(self, path: str) -> None:
            return

    lookup_row = {"ki": "1", "ksatfac": "1.5", "ksatrec": "0.3"}

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

    assert "m1-mock-texture-forest high sev fire" in soils.soils
    assert replacements_seen == [lookup_row]
    assert versions_seen == [9002.0]
    assert stack_paths == [[str(run_dir / "soils" / "m1-mock-texture-forest high sev fire.sol")]]


def test_modify_mofe_soils_9002_strips_treatment_suffix_for_lookup(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-9002-suffix")
    disturbed._sol_ver = 9002.0
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
    watershed = _FakeWatershed({"101": 1.0})

    replacements_seen: list[dict[str, str]] = []

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(
            self,
            replacements,
            h0_max_om=None,
            recompute_wp_fc_using_rosetta_on_bd_override=False,
            version=None,
        ):
            replacements_seen.append(dict(replacements))
            return _FakeWriter([])

    class _FakeMofeSynth:
        def __init__(self, stack):
            self.stack = stack

        def write(self, path: str) -> None:
            return

    lookup_row = {"ki": "1"}

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

    assert "m1-mock-texture-forest high sev fire-mulch_15" in soils.soils
    assert "m1-mock-texture-forest high sev fire" in soils.soils
    assert replacements_seen == [{"ki": "1"}, {"ki": "1"}]


def test_modify_mofe_soils_9002_lookup_miss_uses_explicit_fallback_replacements(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-9002-miss")
    disturbed._sol_ver = 9002.0
    (run_dir / "soils" / "src.sol").write_text("soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "m1"},
        soils={"m1": _SoilStub(clay=30.0, sand=40.0, fname="src.sol")},
        soils_dir=str(run_dir / "soils"),
    )
    landuse = _FakeLanduse(
        domlc_mofe_d={"101": {"1": "dom-1"}},
        managements={"dom-1": _ManagementSummary("developed low intensity")},
    )
    watershed = _FakeWatershed({"101": 1.0})

    replacements_seen: list[dict[str, object]] = []
    versions_seen: list[float | None] = []

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(
            self,
            replacements,
            h0_max_om=None,
            recompute_wp_fc_using_rosetta_on_bd_override=False,
            version=None,
        ):
            replacements_seen.append(dict(replacements))
            versions_seen.append(version)
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
    monkeypatch.setattr(Disturbed, "land_soil_replacements_d", property(lambda self: {}))

    disturbed.modify_mofe_soils()

    assert replacements_seen == [
        {
            "luse": "developed low intensity",
            "stext": "mock-texture",
            "ksatfac": 0.0,
            "ksatrec": 0.0,
        }
    ]
    assert versions_seen == [9002.0]
    assert "m1-mock-texture-developed low intensity" in soils.soils
    assert "m1-mock-texture" not in soils.soils


def test_modify_mofe_soils_9002_lookup_miss_uses_class_aware_keys(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-9002-miss-class-keys")
    disturbed._sol_ver = 9002.0
    (run_dir / "soils" / "src.sol").write_text("soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "m1"},
        soils={"m1": _SoilStub(clay=30.0, sand=40.0, fname="src.sol")},
        soils_dir=str(run_dir / "soils"),
    )
    landuse = _FakeLanduse(
        domlc_mofe_d={"101": {"1": "dom-1", "2": "dom-2"}},
        managements={
            "dom-1": _ManagementSummary("developed low intensity"),
            "dom-2": _ManagementSummary("developed med intensity"),
        },
    )
    watershed = _FakeWatershed({"101": 1.0})

    replacement_classes: list[str] = []
    stack_paths: list[list[str]] = []

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(
            self,
            replacements,
            h0_max_om=None,
            recompute_wp_fc_using_rosetta_on_bd_override=False,
            version=None,
        ):
            replacement_classes.append(str(replacements["luse"]))
            return _FakeWriter([])

    class _FakeMofeSynth:
        def __init__(self, stack):
            stack_paths.append(list(stack))

        def write(self, path: str) -> None:
            return

    monkeypatch.setattr(disturbed_module, "Ron", SimpleNamespace(getInstance=lambda _wd: object()))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "watershed_instance", property(lambda self: watershed))
    monkeypatch.setattr(disturbed_module, "simple_texture", lambda clay, sand: "mock-texture")
    monkeypatch.setattr(disturbed_module, "WeppSoilUtil", _FakeWeppSoilUtil)
    monkeypatch.setattr(disturbed_module, "SoilMultipleOfeSynth", _FakeMofeSynth)
    monkeypatch.setattr(Disturbed, "land_soil_replacements_d", property(lambda self: {}))

    disturbed.modify_mofe_soils()

    assert replacement_classes == ["developed low intensity", "developed med intensity"]
    assert "m1-mock-texture-developed low intensity" in soils.soils
    assert "m1-mock-texture-developed med intensity" in soils.soils
    assert "m1-mock-texture" not in soils.soils
    assert stack_paths == [
        [
            str(run_dir / "soils" / "m1-mock-texture-developed low intensity.sol"),
            str(run_dir / "soils" / "m1-mock-texture-developed med intensity.sol"),
        ]
    ]


def test_modify_mofe_soils_9002_recomputes_area_and_pct_coverage(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-9002-area")
    disturbed._sol_ver = 9002.0
    (run_dir / "soils" / "src-1.sol").write_text("soil", encoding="utf-8")
    (run_dir / "soils" / "src-2.sol").write_text("soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "m1", "102": "m2"},
        soils={
            "m1": _SoilStub(clay=30.0, sand=40.0, fname="src-1.sol"),
            "m2": _SoilStub(clay=30.0, sand=40.0, fname="src-2.sol"),
        },
        soils_dir=str(run_dir / "soils"),
    )
    landuse = _FakeLanduse(
        domlc_mofe_d={"101": {"1": "dom-1"}, "102": {"1": "dom-2"}},
        managements={
            "dom-1": _ManagementSummary("forest high sev fire"),
            "dom-2": _ManagementSummary("forest high sev fire"),
        },
    )
    watershed = _FakeWatershed({"101": 2.0, "102": 3.0})

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(
            self,
            replacements,
            h0_max_om=None,
            recompute_wp_fc_using_rosetta_on_bd_override=False,
            version=None,
        ):
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

    assert soils.domsoil_d["101"] == "hill_101.mofe"
    assert soils.domsoil_d["102"] == "hill_102.mofe"
    assert soils.soils["hill_101.mofe"].area == pytest.approx(2.0)
    assert soils.soils["hill_102.mofe"].area == pytest.approx(3.0)
    assert soils.soils["hill_101.mofe"].pct_coverage == pytest.approx(40.0)
    assert soils.soils["hill_102.mofe"].pct_coverage == pytest.approx(60.0)


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

        def to_over9000(
            self,
            replacements,
            h0_max_om=None,
            recompute_wp_fc_using_rosetta_on_bd_override=False,
            version=None,
        ):
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

        def to_over9000(
            self,
            replacements,
            h0_max_om=None,
            recompute_wp_fc_using_rosetta_on_bd_override=False,
            version=None,
        ):
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


def test_modify_mofe_soils_forwards_rosetta_bd_toggle_to_converter(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-rosetta-toggle")
    disturbed._sol_ver = 9005.0
    (run_dir / "soils" / "src.sol").write_text("soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "m1"},
        soils={"m1": _SoilStub(clay=30.0, sand=40.0, fname="src.sol")},
        soils_dir=str(run_dir / "soils"),
    )
    soils.rosetta_wc_fc_from_disturbed_bd_override = True
    landuse = _FakeLanduse(
        domlc_mofe_d={"101": {"1": "dom-1"}},
        managements={"dom-1": _ManagementSummary("forest high sev fire")},
    )
    watershed = _FakeWatershed({"101": 1.0})

    forwarded_flags: list[bool] = []

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(
            self,
            replacements,
            h0_max_om=None,
            recompute_wp_fc_using_rosetta_on_bd_override=False,
            version=None,
        ):
            forwarded_flags.append(bool(recompute_wp_fc_using_rosetta_on_bd_override))
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
        property(lambda self: {("mock-texture", "forest high sev fire"): {"ki": "1", "bd": "1.6"}}),
    )

    disturbed.modify_mofe_soils()

    assert forwarded_flags == [True]


def test_modify_mofe_soils_forwards_rosetta_bd_toggle_to_7778_converter(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-rosetta-toggle-7778")
    disturbed._sol_ver = 7778.0
    (run_dir / "soils" / "src.sol").write_text("soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "m1"},
        soils={"m1": _SoilStub(clay=30.0, sand=40.0, fname="src.sol")},
        soils_dir=str(run_dir / "soils"),
    )
    soils.rosetta_wc_fc_from_disturbed_bd_override = True
    landuse = _FakeLanduse(
        domlc_mofe_d={"101": {"1": "dom-1"}},
        managements={"dom-1": _ManagementSummary("forest high sev fire")},
    )
    watershed = _FakeWatershed({"101": 1.0})

    forwarded_flags: list[bool] = []

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

        def to_7778disturbed(
            self,
            replacements,
            h0_max_om=None,
            recompute_wp_fc_using_rosetta_on_bd_override=False,
        ):
            forwarded_flags.append(bool(recompute_wp_fc_using_rosetta_on_bd_override))
            return _FakeWriter([])

        def to_over9000(self, *args, **kwargs):  # pragma: no cover - defensive guard
            raise AssertionError("to_over9000 should not be called for 7778 runs")

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
        property(lambda self: {("mock-texture", "forest high sev fire"): {"ki": "1", "bd": "1.6"}}),
    )

    disturbed.modify_mofe_soils()

    assert forwarded_flags == [True]


def test_modify_mofe_soils_uses_process_pool_for_concurrent_generation(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-concurrent")
    disturbed._sol_ver = 9005.0
    (run_dir / "soils" / "src-1.sol").write_text("soil", encoding="utf-8")
    (run_dir / "soils" / "src-2.sol").write_text("soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "m1", "102": "m2"},
        soils={
            "m1": _SoilStub(clay=30.0, sand=40.0, fname="src-1.sol"),
            "m2": _SoilStub(clay=28.0, sand=42.0, fname="src-2.sol"),
        },
        soils_dir=str(run_dir / "soils"),
    )
    landuse = _FakeLanduse(
        domlc_mofe_d={"101": {"1": "dom-1"}, "102": {"1": "dom-2"}},
        managements={
            "dom-1": _ManagementSummary("forest high sev fire"),
            "dom-2": _ManagementSummary("forest moderate sev fire"),
        },
    )
    watershed = _FakeWatershed({"101": 1.0, "102": 2.0})

    prefer_spawn_calls: list[bool] = []
    submitted_tasks: list[str] = []

    class _RecordingExecutor(_InlineProcessPoolExecutor):
        def submit(self, fn, task):
            submitted_tasks.append(str(task["disturbed_mukey"]))
            return super().submit(fn, task)

    def _recording_pool(max_workers, logger=None, prefer_spawn=True):
        prefer_spawn_calls.append(bool(prefer_spawn))
        return _RecordingExecutor()

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(
            self,
            replacements,
            h0_max_om=None,
            recompute_wp_fc_using_rosetta_on_bd_override=False,
            version=None,
        ):
            return _FakeWriter([])

    class _FakeMofeSynth:
        def __init__(self, stack):
            self.stack = stack

        def write(self, path: str) -> None:
            return

    monkeypatch.setattr(disturbed_module, "createProcessPoolExecutor", _recording_pool)
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
        property(
            lambda self: {
                ("mock-texture", "forest high sev fire"): {"ki": "1"},
                ("mock-texture", "forest moderate sev fire"): {"ki": "2"},
            }
        ),
    )

    disturbed.modify_mofe_soils()

    assert prefer_spawn_calls == [True]
    assert submitted_tasks == [
        "m1-mock-texture-forest high sev fire",
        "m2-mock-texture-forest moderate sev fire",
    ]


def test_modify_mofe_soils_retries_with_fork_after_spawn_pool_failure(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-spawn-retry")
    disturbed._sol_ver = 9005.0
    (run_dir / "soils" / "src-1.sol").write_text("soil", encoding="utf-8")
    (run_dir / "soils" / "src-2.sol").write_text("soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "m1", "102": "m2"},
        soils={
            "m1": _SoilStub(clay=30.0, sand=40.0, fname="src-1.sol"),
            "m2": _SoilStub(clay=28.0, sand=42.0, fname="src-2.sol"),
        },
        soils_dir=str(run_dir / "soils"),
    )
    landuse = _FakeLanduse(
        domlc_mofe_d={"101": {"1": "dom-1"}, "102": {"1": "dom-2"}},
        managements={
            "dom-1": _ManagementSummary("forest high sev fire"),
            "dom-2": _ManagementSummary("forest moderate sev fire"),
        },
    )
    watershed = _FakeWatershed({"101": 1.0, "102": 1.0})

    prefer_spawn_calls: list[bool] = []

    def _pool_with_spawn_failure(max_workers, logger=None, prefer_spawn=True):
        prefer_spawn_calls.append(bool(prefer_spawn))
        if prefer_spawn:
            raise BrokenProcessPool("spawn context failed")
        return _InlineProcessPoolExecutor()

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(
            self,
            replacements,
            h0_max_om=None,
            recompute_wp_fc_using_rosetta_on_bd_override=False,
            version=None,
        ):
            return _FakeWriter([])

    class _FakeMofeSynth:
        def __init__(self, stack):
            self.stack = stack

        def write(self, path: str) -> None:
            return

    monkeypatch.setattr(disturbed_module, "createProcessPoolExecutor", _pool_with_spawn_failure)
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
        property(
            lambda self: {
                ("mock-texture", "forest high sev fire"): {"ki": "1"},
                ("mock-texture", "forest moderate sev fire"): {"ki": "2"},
            }
        ),
    )

    disturbed.modify_mofe_soils()

    assert prefer_spawn_calls == [True, False]


def test_modify_mofe_soils_falls_back_to_sequential_after_broken_pools(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-sequential-fallback")
    disturbed._sol_ver = 9005.0
    (run_dir / "soils" / "src-1.sol").write_text("soil", encoding="utf-8")
    (run_dir / "soils" / "src-2.sol").write_text("soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "m1", "102": "m2"},
        soils={
            "m1": _SoilStub(clay=30.0, sand=40.0, fname="src-1.sol"),
            "m2": _SoilStub(clay=28.0, sand=42.0, fname="src-2.sol"),
        },
        soils_dir=str(run_dir / "soils"),
    )
    landuse = _FakeLanduse(
        domlc_mofe_d={"101": {"1": "dom-1"}, "102": {"1": "dom-2"}},
        managements={
            "dom-1": _ManagementSummary("forest high sev fire"),
            "dom-2": _ManagementSummary("forest moderate sev fire"),
        },
    )
    watershed = _FakeWatershed({"101": 1.0, "102": 2.0})

    prefer_spawn_calls: list[bool] = []
    sequential_keys: list[str] = []

    def _always_broken_pool(max_workers, logger=None, prefer_spawn=True):
        prefer_spawn_calls.append(bool(prefer_spawn))
        raise BrokenProcessPool("pool startup failed")

    def _sequential_build(task_args):
        sequential_keys.append(str(task_args["disturbed_mukey"]))
        return task_args["disturbed_mukey"], 0.0

    class _FakeMofeSynth:
        def __init__(self, stack):
            self.stack = stack

        def write(self, path: str) -> None:
            return

    monkeypatch.setattr(disturbed_module, "createProcessPoolExecutor", _always_broken_pool)
    monkeypatch.setattr(disturbed_module, "_build_disturbed_mofe_soil", _sequential_build)
    monkeypatch.setattr(disturbed_module, "Ron", SimpleNamespace(getInstance=lambda _wd: object()))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "watershed_instance", property(lambda self: watershed))
    monkeypatch.setattr(disturbed_module, "simple_texture", lambda clay, sand: "mock-texture")
    monkeypatch.setattr(disturbed_module, "SoilMultipleOfeSynth", _FakeMofeSynth)
    monkeypatch.setattr(
        Disturbed,
        "land_soil_replacements_d",
        property(
            lambda self: {
                ("mock-texture", "forest high sev fire"): {"ki": "1"},
                ("mock-texture", "forest moderate sev fire"): {"ki": "2"},
            }
        ),
    )

    disturbed.modify_mofe_soils()

    assert prefer_spawn_calls == [True, False]
    assert sequential_keys == [
        "m1-mock-texture-forest high sev fire",
        "m2-mock-texture-forest moderate sev fire",
    ]


def test_modify_mofe_soils_propagates_non_broken_pool_task_failure(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-task-failure")
    disturbed._sol_ver = 9005.0
    (run_dir / "soils" / "src-1.sol").write_text("soil", encoding="utf-8")
    (run_dir / "soils" / "src-2.sol").write_text("soil", encoding="utf-8")

    soils = _FakeSoils(
        domsoil_d={"101": "m1", "102": "m2"},
        soils={
            "m1": _SoilStub(clay=30.0, sand=40.0, fname="src-1.sol"),
            "m2": _SoilStub(clay=28.0, sand=42.0, fname="src-2.sol"),
        },
        soils_dir=str(run_dir / "soils"),
    )
    landuse = _FakeLanduse(
        domlc_mofe_d={"101": {"1": "dom-1"}, "102": {"1": "dom-2"}},
        managements={
            "dom-1": _ManagementSummary("forest high sev fire"),
            "dom-2": _ManagementSummary("forest moderate sev fire"),
        },
    )
    watershed = _FakeWatershed({"101": 1.0, "102": 1.0})

    prefer_spawn_calls: list[bool] = []

    def _recording_pool(max_workers, logger=None, prefer_spawn=True):
        prefer_spawn_calls.append(bool(prefer_spawn))
        return _InlineProcessPoolExecutor()

    def _raise_task_failure(task_args):
        raise RuntimeError("disturbed task failed")

    monkeypatch.setattr(disturbed_module, "createProcessPoolExecutor", _recording_pool)
    monkeypatch.setattr(disturbed_module, "_build_disturbed_mofe_soil", _raise_task_failure)
    monkeypatch.setattr(disturbed_module, "Ron", SimpleNamespace(getInstance=lambda _wd: object()))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "watershed_instance", property(lambda self: watershed))
    monkeypatch.setattr(disturbed_module, "simple_texture", lambda clay, sand: "mock-texture")
    monkeypatch.setattr(
        Disturbed,
        "land_soil_replacements_d",
        property(
            lambda self: {
                ("mock-texture", "forest high sev fire"): {"ki": "1"},
                ("mock-texture", "forest moderate sev fire"): {"ki": "2"},
            }
        ),
    )

    with pytest.raises(RuntimeError, match="disturbed task failed"):
        disturbed.modify_mofe_soils()

    assert prefer_spawn_calls == [True]


def test_modify_mofe_soils_compacts_info_logging_and_keeps_debug_detail(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("modify-mofe-logging")
    disturbed._sol_ver = 9005.0
    (run_dir / "soils" / "src.sol").write_text("soil", encoding="utf-8")

    recording_logger = _RecordingLogger()
    disturbed.logger = recording_logger

    soils = _FakeSoils(
        domsoil_d={"101": "m1"},
        soils={"m1": _SoilStub(clay=30.0, sand=40.0, fname="src.sol")},
        soils_dir=str(run_dir / "soils"),
        logger=recording_logger,
    )
    landuse = _FakeLanduse(
        domlc_mofe_d={"101": {"1": "dom-1"}},
        managements={"dom-1": _ManagementSummary("forest high sev fire")},
    )
    watershed = _FakeWatershed({"101": 1.0})

    class _FakeWeppSoilUtil:
        def __init__(self, source_path: str) -> None:
            self.source_path = source_path
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(
            self,
            replacements,
            h0_max_om=None,
            recompute_wp_fc_using_rosetta_on_bd_override=False,
            version=None,
        ):
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

    assert any(
        "Prepared MOFE soil modification plans:" in message
        for message in recording_logger.info_messages
    )
    assert any(
        "Completed MOFE soil generation:" in message
        for message in recording_logger.info_messages
    )
    assert not any("topaz_id=" in message for message in recording_logger.info_messages)
    assert any("topaz_id=" in message for message in recording_logger.debug_messages)
