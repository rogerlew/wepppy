from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.core.climate_build_helpers as helper_module

pytestmark = pytest.mark.unit


class _WatershedStub:
    centroid = (-120.5, 45.5)

    def __init__(self) -> None:
        self._coords = {
            "1": (-120.4, 45.4),
            "2": (-120.3, 45.3),
        }

    def centroid_hillslope_iter(self):
        return iter((topaz_id, coord) for topaz_id, coord in self._coords.items())

    def hillslope_centroid_lnglat(self, topaz_id: str):
        return self._coords[topaz_id]


class _ClimateStub:
    def __init__(self, tmp_path: Path) -> None:
        self.wd = str(tmp_path)
        self.cli_dir = str(tmp_path)
        self.cli_path = str(tmp_path / "base.cli")
        self.logger = logging.getLogger(f"tests.nodb.climate_helpers.{tmp_path.name}")
        self.ron_instance = SimpleNamespace(map=SimpleNamespace(extent=(0, 0, 1, 1), cellsize=1.0))
        self.wmesque_version = "v1"
        self.wmesque_endpoint = "endpoint"
        self.watershed_instance = _WatershedStub()
        self.observed_start_year = 2001
        self.observed_end_year = 2002
        self._observed_start_year = 2001
        self._observed_end_year = 2002
        self.daymet_last_available_year = 2100
        self.climate_daily_temp_ds = "none"
        self.climatestation = "station-x"
        self.cligen_db = "legacy"
        self._input_years = 0
        self._cligen_seed = None
        self.adjust_mx_pt5 = False
        self.use_gridmet_wind_when_applicable = False
        self.monthlies = None
        self.par_fn = None
        self.cli_fn = None
        self.sub_par_fns = None
        self.sub_cli_fns = None
        self.climate_spatialmode = 0  # ClimateSpatialMode.Single
        self.attrs_seen: list[object] = []
        self.dump_called = False

    @contextlib.contextmanager
    def locked(self):
        yield

    @contextlib.contextmanager
    def timed(self, _label: str):
        yield

    def set_attrs(self, attrs):
        self.attrs_seen.append(attrs)

    def dump(self) -> None:
        self.dump_called = True


class _MonthliesClimateFile:
    def __init__(self, _path: str) -> None:
        self.input_years = 2
        self.cli_fn = "template.cli"
        self.breakpoint = False

    def calc_monthlies(self) -> list[float]:
        return [1.0] * 12


class _FutureStub:
    def __init__(self, *, value=None, exc: Exception | None = None, done: bool = True) -> None:
        self._value = value
        self._exc = exc
        self._done = done
        self.cancel_called = False

    def result(self):
        if self._exc is not None:
            raise self._exc
        return self._value

    def done(self) -> bool:
        return self._done

    def cancel(self) -> None:
        self.cancel_called = True
        self._done = True


class _ExecutorStub:
    def __init__(self) -> None:
        self.shutdown_args = None

    def shutdown(self, *, wait: bool, cancel_futures: bool) -> None:
        self.shutdown_args = (wait, cancel_futures)


def test_cap_ncpu_limits_to_24() -> None:
    assert helper_module._cap_ncpu(8) == 8
    assert helper_module._cap_ncpu(24) == 24
    assert helper_module._cap_ncpu(32) == 24
    assert helper_module.NCPU <= 24


def test_run_depnexrad_build_sets_expected_single_mode_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _ClimateStub(tmp_path)
    downloaded: list[tuple[str, str]] = []

    monkeypatch.setattr(helper_module, "download_file", lambda url, dst: downloaded.append((url, dst)))
    monkeypatch.setattr(helper_module, "_clip_cli_to_observed_years", lambda *_args, **_kwargs: _MonthliesClimateFile("x"))

    helper_module.run_depnexrad_build(climate, attrs={"k": "v"})

    assert climate.attrs_seen == [{"k": "v"}]
    assert climate.par_fn == ".par"
    assert climate.cli_fn is not None and climate.cli_fn.endswith(".cli")
    assert climate._input_years == 2
    assert climate.monthlies == [1.0] * 12
    assert len(downloaded) == 1


def test_run_depnexrad_build_assigns_multiple_mode_maps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _ClimateStub(tmp_path)
    climate.climate_spatialmode = 1  # ClimateSpatialMode.Multiple

    monkeypatch.setattr(helper_module, "download_file", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(helper_module, "_clip_cli_to_observed_years", lambda *_args, **_kwargs: _MonthliesClimateFile("x"))
    monkeypatch.setattr(
        helper_module,
        "_build_depnexrad_hillslope_files",
        lambda *_args, **_kwargs: ({"1": ".par"}, {"1": "a.cli"}),
    )

    helper_module.run_depnexrad_build(climate)

    assert climate.sub_par_fns == {"1": ".par"}
    assert climate.sub_cli_fns == {"1": "a.cli"}


def test_run_prism_revision_updates_catalog_and_sub_maps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _ClimateStub(tmp_path)
    catalog_updates: list[tuple[str, str]] = []

    monkeypatch.setattr(helper_module, "_retrieve_prism_revision_tiles", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(helper_module, "_collect_prism_revision_monthlies", lambda *_args, **_kwargs: ([1.0] * 12, [2.0] * 12, [3.0] * 12))
    monkeypatch.setattr(helper_module, "ClimateFile", _MonthliesClimateFile)
    monkeypatch.setattr(
        helper_module,
        "_submit_prism_revision_futures",
        lambda *_args, **_kwargs: ({}, {"1": ".par"}, {"1": "a.cli"}),
    )
    monkeypatch.setattr(helper_module, "_wait_for_prism_revision_futures", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(helper_module, "update_catalog_entry", lambda wd, area: catalog_updates.append((wd, area)))

    helper_module.run_prism_revision(climate)

    assert climate.sub_par_fns == {"1": ".par"}
    assert climate.sub_cli_fns == {"1": "a.cli"}
    assert catalog_updates == [(climate.wd, "climate")]


def test_run_mod_build_sets_seed_and_single_outputs(tmp_path: Path) -> None:
    climate = _ClimateStub(tmp_path)

    def _mod_function(**_kwargs):
        return {"ppts": [1.0, 2.0, 3.0]}

    helper_module.run_mod_build(climate, _mod_function, attrs={"mode": "mod"})

    assert climate.attrs_seen == [{"mode": "mod"}]
    assert climate.dump_called is True
    assert climate._cligen_seed is not None
    assert climate.par_fn == "station-x.par"
    assert climate.cli_fn == "station-x.cli"
    assert climate.monthlies == {"ppts": [1.0, 2.0, 3.0]}


def test_run_mod_build_assigns_multiple_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _ClimateStub(tmp_path)
    climate._cligen_seed = 99
    climate.climate_spatialmode = 1  # ClimateSpatialMode.Multiple

    def _mod_function(**_kwargs):
        return {"ppts": [1.0]}

    monkeypatch.setattr(
        helper_module,
        "_build_mod_multiple_climates",
        lambda *_args, **_kwargs: ({"1": "x.par"}, {"1": "x.cli"}),
    )

    helper_module.run_mod_build(climate, _mod_function)

    assert climate.sub_par_fns == {"1": "x.par"}
    assert climate.sub_cli_fns == {"1": "x.cli"}


def test_wait_for_prism_revision_futures_cancels_all_on_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _ClimateStub(tmp_path)
    bad = _FutureStub(exc=RuntimeError("boom"))
    pending = _FutureStub(value="ok")
    future_map = {bad: "1", pending: "2"}

    monkeypatch.setattr(helper_module, "wait", lambda *_args, **_kwargs: ({bad}, {pending}))

    with pytest.raises(RuntimeError, match="boom"):
        helper_module._wait_for_prism_revision_futures(climate, future_map)

    assert bad.cancel_called is True
    assert pending.cancel_called is True


def test_wait_for_mod_build_futures_cancels_pending_on_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _ClimateStub(tmp_path)
    bad = _FutureStub(exc=RuntimeError("worker fail"))
    pending = _FutureStub(value={"ppts": [1.0]})
    futures = {bad: "1", pending: "2"}

    monkeypatch.setattr(helper_module, "wait", lambda *_args, **_kwargs: ({bad}, {pending}))

    with pytest.raises(RuntimeError, match="worker fail"):
        helper_module._wait_for_mod_build_futures(climate, futures)

    assert pending.cancel_called is True


def test_wait_for_daymet_futures_cancels_and_shutdowns_on_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _ClimateStub(tmp_path)
    bad = _FutureStub(exc=RuntimeError("daymet fail"), done=True)
    pending = _FutureStub(value="ok", done=False)
    executor = _ExecutorStub()

    monkeypatch.setattr(helper_module, "wait", lambda *_args, **_kwargs: ({bad}, {pending}))

    with pytest.raises(RuntimeError, match="daymet fail"):
        helper_module._wait_for_daymet_futures(climate, [bad, pending], executor)

    assert pending.cancel_called is True
    assert executor.shutdown_args == (False, True)


def test_run_observed_daymet_multiple_build_sets_final_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _ClimateStub(tmp_path)
    climate.use_gridmet_wind_when_applicable = True

    captured_executor_workers: list[int] = []

    class _ProcessPoolExecutorStub:
        def __init__(self, max_workers: int):
            captured_executor_workers.append(max_workers)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        helper_module,
        "_prepare_daymet_multiple_context",
        lambda *_args, **_kwargs: (
            climate.watershed_instance,
            -120.5,
            45.5,
            climate.cli_dir,
            2001,
            2002,
            "ws.par",
            object(),
        ),
    )
    monkeypatch.setattr(helper_module, "_build_daymet_hillslope_locations", lambda *_args, **_kwargs: {"ws": {}})
    monkeypatch.setattr(helper_module, "_interpolate_daymet_hillslope_series", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(helper_module, "_resolve_daymet_wind", lambda *_args, **_kwargs: ("wind_vs", "wind_dir"))
    monkeypatch.setattr(helper_module, "_resolve_daymet_worker_count", lambda: 7)
    monkeypatch.setattr(helper_module, "ProcessPoolExecutor", _ProcessPoolExecutorStub)
    monkeypatch.setattr(
        helper_module,
        "_submit_daymet_futures",
        lambda *_args, **_kwargs: ([], {"1": "a.prn"}, {"1": "a.cli"}, "wepp.cli"),
    )
    monkeypatch.setattr(helper_module, "_wait_for_daymet_futures", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(helper_module, "ClimateFile", _MonthliesClimateFile)

    helper_module.run_observed_daymet_multiple_build(climate, attrs={"mode": "daymet"})

    assert captured_executor_workers == [7]
    assert climate.attrs_seen == [{"mode": "daymet"}]
    assert climate.monthlies == [1.0] * 12
    assert climate.cli_fn == "wepp.cli"
    assert climate.par_fn == "ws.par"
    assert climate.sub_par_fns == {"1": "a.prn"}
    assert climate.sub_cli_fns == {"1": "a.cli"}
