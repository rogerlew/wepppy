from __future__ import annotations

from concurrent.futures import Future
from concurrent.futures.process import BrokenProcessPool
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
    def __init__(self, dom: str) -> None:
        self.dom = dom
        self.rdmax_values: list[float] = []
        self.xmxlai_values: list[float] = []
        self.cancov_values: list[float] = []
        self.overrides: dict[str, float] = {}

    def set_rdmax(self, value: float) -> None:
        self.rdmax_values.append(float(value))

    def set_xmxlai(self, value: float) -> None:
        self.xmxlai_values.append(float(value))

    def set_cancov(self, value: float) -> None:
        value_f = float(value)
        self.cancov_values.append(value_f)
        self.overrides["ini.data.cancov"] = value_f

    def __setitem__(self, attr: str, value: str | float | int) -> None:
        self.overrides[attr] = float(value)

    def __str__(self) -> str:
        return f"{self.dom}\n"


class _ManagementSummaryStub:
    def __init__(self, dom: str, disturbed_class: str = "") -> None:
        self.dom = dom
        self.disturbed_class = disturbed_class
        self.created: list[_ManagementStub] = []

    def get_management(self) -> _ManagementStub:
        management = _ManagementStub(self.dom)
        self.created.append(management)
        return management


class _DisturbedStub:
    burn_shrubs = False
    burn_grass = False

    def __init__(self, replacements: dict[tuple[str, str], dict[str, str]]) -> None:
        self.land_soil_replacements_d = replacements

    def get_disturbed_key_lookup(self) -> dict[str, str]:
        return {}

    def get_sbs(self) -> None:
        return None


class _InlineProcessPoolExecutor:
    def __enter__(self) -> "_InlineProcessPoolExecutor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def submit(self, fn, args):
        future: Future[tuple[str, float]] = Future()
        try:
            future.set_result(fn(args))
        except Exception as exc:  # pragma: no cover - exercised by future.result()
            future.set_exception(exc)
        return future


def _make_managements() -> dict[str, _ManagementSummaryStub]:
    return {
        "forest-dom": _ManagementSummaryStub("forest-dom", "forest moderate sev fire"),
        "shrub-dom": _ManagementSummaryStub("shrub-dom", "shrub"),
        "999": _ManagementSummaryStub("999"),
    }


def _make_landuse_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    run_name: str,
    domlc_d: dict[str, dict[str, str]],
    managements: dict[str, _ManagementSummaryStub],
    mods: list[str] | None = None,
    disturbed: _DisturbedStub | None = None,
    rap: object | None = None,
    mofe_buffer: bool = False,
    buffer_selection: int | None = None,
) -> tuple[Landuse, Path]:
    run_dir = tmp_path / run_name
    (run_dir / "landuse").mkdir(parents=True, exist_ok=True)

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(run_dir)
    landuse._mods = list(mods or [])
    landuse._mapping = "mock-map"
    landuse.managements = managements
    landuse.locked = lambda: nullcontext()
    landuse.logger = _LoggerStub()
    landuse._mofe_buffer_selection = buffer_selection

    watershed = SimpleNamespace(
        _subs_summary={str(topaz_id): {} for topaz_id in domlc_d},
        mofe_nsegments={str(topaz_id): str(len(ofe_map)) for topaz_id, ofe_map in domlc_d.items()},
        mofe_buffer=mofe_buffer,
        subwta=str(run_dir / "watershed" / "subwta.tif"),
        mofe_map=str(run_dir / "watershed" / "mofe_map.tif"),
    )
    monkeypatch.setattr(Landuse, "watershed_instance", property(lambda _self: watershed))

    class _LandcoverMapStub:
        def __init__(self, _lc_fn: str) -> None:
            pass

        def build_lcgrid(self, _subwta: str, _mofe_map: str) -> dict[str, dict[str, str]]:
            return {
                str(topaz_id): {str(ofe_id): str(dom) for ofe_id, dom in ofe_map.items()}
                for topaz_id, ofe_map in domlc_d.items()
            }

    monkeypatch.setattr(landuse_module, "LandcoverMap", _LandcoverMapStub)
    monkeypatch.setattr(landuse_module, "wepppyo3", None)
    monkeypatch.setattr(
        "wepppy.nodb.mods.disturbed.Disturbed.tryGetInstance",
        lambda _wd: disturbed,
    )
    if rap is not None:
        monkeypatch.setattr(
            "wepppy.nodb.mods.rap.RAP.getInstance",
            lambda _wd: rap,
        )

    return landuse, run_dir


def _write_task_snapshot(task_args: tuple[str, str, int, list[dict[str, object]]]) -> tuple[str, float]:
    def _format_float(value: float) -> str:
        return repr(round(float(value), 12))

    def _format_float_list(values: list[float]) -> str:
        return "[" + ", ".join(_format_float(value) for value in values) + "]"

    topaz_id, output_path, expected_nsegments, segment_plans = task_args
    stack = [
        plan["preloaded_management"]
        for plan in segment_plans
        if isinstance(plan.get("preloaded_management"), _ManagementStub)
    ]
    lines = [f"segments={expected_nsegments}"]
    for index, management in enumerate(stack, start=1):
        override_items = ",".join(
            f"{key}={_format_float(value)}" for key, value in sorted(management.overrides.items())
        )
        lines.append(
            f"{index}|dom={management.dom}|rdmax={_format_float_list(management.rdmax_values)}|"
            f"xmxlai={_format_float_list(management.xmxlai_values)}|"
            f"cancov={_format_float_list(management.cancov_values)}|"
            f"overrides={override_items}"
        )
    Path(output_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(topaz_id), 0.0


def test_build_multiple_ofe_process_pool_success_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    domlc_d = {
        "101": {"1": "forest-dom", "2": "shrub-dom"},
        "102": {"1": "forest-dom", "2": "shrub-dom"},
    }
    landuse, run_dir = _make_landuse_fixture(
        tmp_path,
        monkeypatch,
        run_name="pool-success",
        domlc_d=domlc_d,
        managements=_make_managements(),
    )

    prefer_spawn_calls: list[bool] = []
    completed_tasks: list[tuple[str, int, list[str]]] = []

    def _recording_pool(max_workers, logger=None, prefer_spawn=True):
        prefer_spawn_calls.append(bool(prefer_spawn))
        return _InlineProcessPoolExecutor()

    def _recording_worker(task_args):
        topaz_id, output_path, expected_nsegments, segment_plans = task_args
        completed_tasks.append(
            (
                str(topaz_id),
                int(expected_nsegments),
                [
                    plan["preloaded_management"].dom
                    for plan in segment_plans
                    if isinstance(plan.get("preloaded_management"), _ManagementStub)
                ],
            )
        )
        Path(output_path).write_text(f"{topaz_id}\n", encoding="utf-8")
        return str(topaz_id), 0.0

    monkeypatch.setattr(landuse_module.os, "cpu_count", lambda: 4)
    monkeypatch.setattr(landuse_module, "createProcessPoolExecutor", _recording_pool)
    monkeypatch.setattr(landuse_module, "_write_mofe_management_file_task", _recording_worker)

    landuse._build_multiple_ofe()

    assert prefer_spawn_calls == [True]
    assert completed_tasks == [
        ("101", 2, ["forest-dom", "shrub-dom"]),
        ("102", 2, ["forest-dom", "shrub-dom"]),
    ]
    assert (run_dir / "landuse" / "hill_101.mofe.man").read_text(encoding="utf-8") == "101\n"
    assert (run_dir / "landuse" / "hill_102.mofe.man").read_text(encoding="utf-8") == "102\n"


def test_build_multiple_ofe_retries_spawn_failure_with_fork_pool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    domlc_d = {
        "101": {"1": "forest-dom", "2": "shrub-dom"},
        "102": {"1": "forest-dom", "2": "shrub-dom"},
    }
    landuse, run_dir = _make_landuse_fixture(
        tmp_path,
        monkeypatch,
        run_name="pool-retry",
        domlc_d=domlc_d,
        managements=_make_managements(),
    )

    prefer_spawn_calls: list[bool] = []

    def _pool_with_spawn_failure(max_workers, logger=None, prefer_spawn=True):
        prefer_spawn_calls.append(bool(prefer_spawn))
        if prefer_spawn:
            raise BrokenProcessPool("spawn failed")
        return _InlineProcessPoolExecutor()

    monkeypatch.setattr(landuse_module.os, "cpu_count", lambda: 4)
    monkeypatch.setattr(landuse_module, "createProcessPoolExecutor", _pool_with_spawn_failure)
    monkeypatch.setattr(landuse_module, "_write_mofe_management_file_task", _write_task_snapshot)

    landuse._build_multiple_ofe()

    assert prefer_spawn_calls == [True, False]
    assert (run_dir / "landuse" / "hill_101.mofe.man").exists()
    assert (run_dir / "landuse" / "hill_102.mofe.man").exists()


def test_build_multiple_ofe_falls_back_to_sequential_after_double_pool_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    domlc_d = {
        "101": {"1": "forest-dom", "2": "shrub-dom"},
        "102": {"1": "forest-dom", "2": "shrub-dom"},
    }
    landuse, run_dir = _make_landuse_fixture(
        tmp_path,
        monkeypatch,
        run_name="pool-sequential-fallback",
        domlc_d=domlc_d,
        managements=_make_managements(),
    )

    prefer_spawn_calls: list[bool] = []
    sequential_calls: list[str] = []

    def _always_broken_pool(max_workers, logger=None, prefer_spawn=True):
        prefer_spawn_calls.append(bool(prefer_spawn))
        raise BrokenProcessPool("pool startup failed")

    def _sequential_worker(task_args):
        topaz_id, output_path, _expected_nsegments, _segment_plans = task_args
        sequential_calls.append(str(topaz_id))
        Path(output_path).write_text(f"sequential:{topaz_id}\n", encoding="utf-8")
        return str(topaz_id), 0.0

    monkeypatch.setattr(landuse_module.os, "cpu_count", lambda: 4)
    monkeypatch.setattr(landuse_module, "createProcessPoolExecutor", _always_broken_pool)
    monkeypatch.setattr(landuse_module, "_write_mofe_management_file_task", _sequential_worker)

    landuse._build_multiple_ofe()

    assert prefer_spawn_calls == [True, False]
    assert sequential_calls == ["101", "102"]
    assert (run_dir / "landuse" / "hill_101.mofe.man").read_text(encoding="utf-8") == "sequential:101\n"
    assert (run_dir / "landuse" / "hill_102.mofe.man").read_text(encoding="utf-8") == "sequential:102\n"


def test_build_multiple_ofe_propagates_non_pool_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    domlc_d = {
        "101": {"1": "forest-dom", "2": "shrub-dom"},
        "102": {"1": "forest-dom", "2": "shrub-dom"},
    }
    landuse, _run_dir = _make_landuse_fixture(
        tmp_path,
        monkeypatch,
        run_name="pool-non-broken-failure",
        domlc_d=domlc_d,
        managements=_make_managements(),
    )

    prefer_spawn_calls: list[bool] = []

    class _FailingExecutor:
        def __enter__(self) -> "_FailingExecutor":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def submit(self, fn, args):  # noqa: ARG002
            future: Future[tuple[str, float]] = Future()
            future.set_exception(RuntimeError("synthesis boom"))
            return future

    def _recording_pool(max_workers, logger=None, prefer_spawn=True):
        prefer_spawn_calls.append(bool(prefer_spawn))
        return _FailingExecutor()

    monkeypatch.setattr(landuse_module.os, "cpu_count", lambda: 4)
    monkeypatch.setattr(landuse_module, "createProcessPoolExecutor", _recording_pool)

    with pytest.raises(RuntimeError, match="synthesis boom"):
        landuse._build_multiple_ofe()

    assert prefer_spawn_calls == [True]


def test_build_multiple_ofe_concurrent_output_matches_sequential_parity_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    domlc_d = {
        "101": {"1": "forest-dom", "2": "shrub-dom"},
        "102": {"1": "forest-dom", "2": "shrub-dom"},
    }
    replacements = {
        ("sand loam", "forest moderate sev fire"): {
            "plant.data.rdmax": "0.33",
            "plant.data.xmxlai": "5.7",
            "plant.data.decfct": "1.0",
        },
        ("sand loam", "shrub"): {
            "plant.data.rdmax": "0.11",
            "plant.data.xmxlai": "2.2",
            "plant.data.decfct": "0.5",
        },
    }
    rap = SimpleNamespace(
        mofe_data={
            landuse_module.RAP_Band.TREE: {
                "101": {"1": 70.0, "2": 0.0},
                "102": {"1": 55.0, "2": 10.0},
            },
            landuse_module.RAP_Band.SHRUB: {
                "101": {"1": 20.0, "2": 40.0},
                "102": {"1": 20.0, "2": 30.0},
            },
            landuse_module.RAP_Band.ANNUAL_FORB_AND_GRASS: {
                "101": {"1": 5.0, "2": 10.0},
                "102": {"1": 10.0, "2": 10.0},
            },
            landuse_module.RAP_Band.PERENNIAL_FORB_AND_GRASS: {
                "101": {"1": 5.0, "2": 10.0},
                "102": {"1": 10.0, "2": 10.0},
            },
        }
    )

    concurrent_landuse, concurrent_dir = _make_landuse_fixture(
        tmp_path,
        monkeypatch,
        run_name="parity-concurrent",
        domlc_d=domlc_d,
        managements=_make_managements(),
        mods=["rap"],
        disturbed=_DisturbedStub(replacements),
        rap=rap,
        mofe_buffer=True,
        buffer_selection=999,
    )

    def _recording_pool(max_workers, logger=None, prefer_spawn=True):
        return _InlineProcessPoolExecutor()

    monkeypatch.setattr(landuse_module.os, "cpu_count", lambda: 4)
    monkeypatch.setattr(landuse_module, "createProcessPoolExecutor", _recording_pool)
    monkeypatch.setattr(landuse_module, "_write_mofe_management_file_task", _write_task_snapshot)

    concurrent_landuse._build_multiple_ofe()

    sequential_landuse, sequential_dir = _make_landuse_fixture(
        tmp_path,
        monkeypatch,
        run_name="parity-sequential",
        domlc_d=domlc_d,
        managements=_make_managements(),
        mods=["rap"],
        disturbed=_DisturbedStub(replacements),
        rap=rap,
        mofe_buffer=True,
        buffer_selection=999,
    )

    monkeypatch.setattr(landuse_module.os, "cpu_count", lambda: 1)
    monkeypatch.setattr(landuse_module, "_write_mofe_management_file_task", _write_task_snapshot)

    sequential_landuse._build_multiple_ofe()

    for topaz_id in ("101", "102"):
        concurrent_output = (concurrent_dir / "landuse" / f"hill_{topaz_id}.mofe.man").read_text(
            encoding="utf-8"
        )
        sequential_output = (sequential_dir / "landuse" / f"hill_{topaz_id}.mofe.man").read_text(
            encoding="utf-8"
        )
        assert concurrent_output == sequential_output

    assert concurrent_landuse.domlc_mofe_d == sequential_landuse.domlc_mofe_d == {
        "101": {"1": "forest-dom", "2": "shrub-dom"},
        "102": {"1": "forest-dom", "2": "999"},
    }
    for cancovs in (
        concurrent_landuse._hillslope_mofe_cancovs,
        sequential_landuse._hillslope_mofe_cancovs,
    ):
        assert cancovs is not None
        assert cancovs["101"]["1"] == pytest.approx(1.0)
        assert cancovs["101"]["2"] == pytest.approx(0.6)
        assert cancovs["102"]["1"] == pytest.approx(0.95)
    assert (
        concurrent_dir / "landuse" / "hill_101.mofe.man"
    ).read_text(encoding="utf-8") == (
        "segments=2\n"
        "1|dom=forest-dom|rdmax=[0.33]|xmxlai=[5.7]|cancov=[1.0]|"
        "overrides=ini.data.cancov=1.0,plant.data.decfct=1.0,plant.data.rdmax=0.33,plant.data.xmxlai=5.7\n"
        "2|dom=shrub-dom|rdmax=[0.11]|xmxlai=[2.2]|cancov=[0.6]|"
        "overrides=ini.data.cancov=0.6,plant.data.decfct=0.5,plant.data.rdmax=0.11,plant.data.xmxlai=2.2\n"
    )
    assert (
        concurrent_dir / "landuse" / "hill_102.mofe.man"
    ).read_text(encoding="utf-8") == (
        "segments=2\n"
        "1|dom=forest-dom|rdmax=[0.33]|xmxlai=[5.7]|cancov=[0.95]|"
        "overrides=ini.data.cancov=0.95,plant.data.decfct=1.0,plant.data.rdmax=0.33,plant.data.xmxlai=5.7\n"
        "2|dom=999|rdmax=[]|xmxlai=[]|cancov=[]|overrides=\n"
    )
