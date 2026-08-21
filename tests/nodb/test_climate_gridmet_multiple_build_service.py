from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import wepppy.nodb.core.climate_gridmet_multiple_build_service as service_module
import wepppy.climates.gridmet.client as gridmet_client
from wepppy.nodb.core.climate_gridmet_multiple_build_service import (
    ClimateGridmetMultipleBuildService,
)
from wepppy.nodb.core.climate_multiple_build import ClimateMultipleBuildResult

pytestmark = pytest.mark.unit


class _RecordingLogger:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    def warning(self, message: str) -> None:
        self.warnings.append(message)


class _RecordingExecutor:
    def __init__(self) -> None:
        self.shutdown_calls: list[tuple[bool, bool]] = []

    def shutdown(self, *, wait: bool, cancel_futures: bool) -> None:
        self.shutdown_calls.append((wait, cancel_futures))


def test_wait_for_futures_logs_warning_until_work_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ClimateGridmetMultipleBuildService()
    logger = _RecordingLogger()
    climate = SimpleNamespace(logger=logger)

    completed = Future()
    completed.set_result("ws")

    rounds = {"count": 0}

    def _fake_wait(_pending, timeout, return_when):
        rounds["count"] += 1
        assert timeout == 60
        assert return_when is service_module.FIRST_COMPLETED
        if rounds["count"] == 1:
            return set(), {completed}
        return {completed}, set()

    monkeypatch.setattr(service_module, "wait", _fake_wait)

    seen: list[str] = []
    service._wait_for_futures(
        futures=[completed],
        climate=climate,
        timeout=60,
        waiting_message="still waiting",
        on_done=seen.append,
    )

    assert logger.warnings == ["still waiting"]
    assert seen == ["ws"]


def test_wait_for_futures_cancels_pending_and_stops_executor_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateGridmetMultipleBuildService()
    logger = _RecordingLogger()
    climate = SimpleNamespace(logger=logger)
    executor = _RecordingExecutor()

    failed = Future()
    failed.set_exception(RuntimeError("boom"))
    pending = Future()

    monkeypatch.setattr(
        service_module,
        "wait",
        lambda _pending, timeout, return_when: ({failed}, {pending}),
    )

    with pytest.raises(RuntimeError, match="boom"):
        service._wait_for_futures(
            futures=[failed, pending],
            climate=climate,
            timeout=60,
            waiting_message="still waiting",
            executor=executor,
        )

    assert pending.cancelled()
    assert executor.shutdown_calls == [(False, True)]


def test_worker_count_honors_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ClimateGridmetMultipleBuildService()

    monkeypatch.delenv("WEPPPY_NCPU", raising=False)
    assert service._worker_count(default_workers=12, ncpu=8) == 12

    monkeypatch.setenv("WEPPPY_NCPU", "1")
    assert service._worker_count(default_workers=12, ncpu=8) == 8


def test_load_raw_gridmet_data_preserves_unpublished_suffix_as_nan(tmp_path: Path) -> None:
    service = ClimateGridmetMultipleBuildService()

    def _read_nc(_path, _measure):
        values = np.array([[[1.0]], [[2.0]]])
        return values, "pr", "mm"

    raw_data, longitudes, latitudes = service._load_raw_gridmet_data(
        read_nc=_read_nc,
        read_nc_longlat=lambda _path: (np.array([1.0]), np.array([2.0])),
        measures=["precip"],
        start_year=2026,
        end_year=2026,
        cli_dir=str(tmp_path),
        ndates=5,
    )

    series = raw_data["pr(mm)"][0, 0, :]
    np.testing.assert_allclose(series[:2], [1.0, 2.0])
    assert np.isnan(series[2:]).all()
    np.testing.assert_allclose(longitudes, [1.0])
    np.testing.assert_allclose(latitudes, [2.0])


def test_load_raw_gridmet_data_places_final_partial_year_at_calendar_offset(
    tmp_path: Path,
) -> None:
    service = ClimateGridmetMultipleBuildService()

    def _read_nc(path, _measure):
        year = int(Path(path).stem.rsplit("_", 1)[1])
        days = 365 if year == 2025 else 2
        values = np.arange(days, dtype=float).reshape(days, 1, 1)
        return values, "pr", "mm"

    raw_data, _, _ = service._load_raw_gridmet_data(
        read_nc=_read_nc,
        read_nc_longlat=lambda _path: (np.array([1.0]), np.array([2.0])),
        measures=["precip"],
        start_year=2025,
        end_year=2026,
        cli_dir=str(tmp_path),
        ndates=730,
    )

    series = raw_data["pr(mm)"][0, 0, :]
    assert series[364] == pytest.approx(364.0)
    assert series[365] == pytest.approx(0.0)
    assert series[366] == pytest.approx(1.0)
    assert np.isnan(series[367:]).all()


def test_load_raw_gridmet_data_rejects_partial_nonfinal_year(tmp_path: Path) -> None:
    service = ClimateGridmetMultipleBuildService()

    with pytest.raises(
        ValueError,
        match=r"2025 returned 2 days; only the final requested year",
    ):
        service._load_raw_gridmet_data(
            read_nc=lambda _path, _measure: (
                np.arange(2, dtype=float).reshape(2, 1, 1),
                "pr",
                "mm",
            ),
            read_nc_longlat=lambda _path: (np.array([1.0]), np.array([2.0])),
            measures=["precip"],
            start_year=2025,
            end_year=2026,
            cli_dir=str(tmp_path),
            ndates=730,
        )


def test_read_nc_preserves_masked_gridmet_values_as_nan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    measure = object()

    class _Variable:
        description = "test"
        units = "mm"

        def __getitem__(self, _key):
            return np.ma.array([1.0, -9999.0, 3.0], mask=[False, True, False])

    monkeypatch.setitem(gridmet_client._var_meta, measure, ("pr", "precipitation"))
    monkeypatch.setattr(
        gridmet_client.netCDF4,
        "Dataset",
        lambda _path: SimpleNamespace(variables={"precipitation": _Variable()}),
    )

    values, abbrv, units = gridmet_client.read_nc("test.nc", measure)

    np.testing.assert_allclose(values[[0, 2]], [1.0, 3.0])
    assert np.isnan(values[1])
    assert abbrv == "pr"
    assert units == "mm"


def test_gridmet_interpolation_propagates_unpublished_suffix_to_parquet_and_prn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = pd.date_range("2026-07-23", periods=3)
    columns = {
        "pr(mm)": [1.0, np.nan, np.nan],
        "tmmx(degc)": [20.0, np.nan, np.nan],
        "tmmn(degc)": [10.0, np.nan, np.nan],
        "rmin(%)": [40.0, np.nan, np.nan],
        "rmax(%)": [60.0, np.nan, np.nan],
        "srad(Wm-2)": [200.0, np.nan, np.nan],
        "vs(m/s)": [2.0, np.nan, np.nan],
        "th(DegreesClockwisefromnorth)": [180.0, np.nan, np.nan],
    }
    raw_data = {
        name: np.asarray(values, dtype=float).reshape(1, 1, len(dates))
        for name, values in columns.items()
    }
    monkeypatch.setattr(
        gridmet_client,
        "interpolate_geospatial",
        lambda _lng, _lat, _longitudes, _latitudes, values, _method, a_min=None: values[0, 0, :],
    )

    gridmet_client.interpolate_daily_timeseries_for_location(
        "p1",
        {"longitude": -116.0, "latitude": 43.0},
        dates,
        np.array([-116.0]),
        np.array([43.0]),
        raw_data,
        {name: {"method": "nearest"} for name in columns},
        str(tmp_path),
        2026,
        2026,
    )

    parquet = pd.read_parquet(tmp_path / "gridmet_observed_p1_2026-2026.parquet")
    assert parquet.iloc[0]["tdew(degc)"] == pytest.approx(10.0)
    assert parquet.iloc[1:].isna().all().all()

    prn_lines = (
        tmp_path / "gridmet_observed_p1_2026-2026.prn"
    ).read_text(encoding="ascii").splitlines()
    assert prn_lines[0].split()[3:] != ["9999", "9999", "9999"]
    assert prn_lines[1].split()[3:] == ["9999", "9999", "9999"]
    assert prn_lines[2].split()[3:] == ["9999", "9999", "9999"]


def test_gridmet_interpolation_rejects_internal_primary_variable_hole(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = pd.date_range("2026-07-23", periods=3)
    columns = {
        "pr(mm)": [1.0, np.nan, 2.0],
        "tmmx(degc)": [20.0, 21.0, 22.0],
        "tmmn(degc)": [10.0, 11.0, 12.0],
        "rmin(%)": [40.0, 40.0, 40.0],
        "rmax(%)": [60.0, 60.0, 60.0],
        "srad(Wm-2)": [200.0, 200.0, 200.0],
        "vs(m/s)": [2.0, 2.0, 2.0],
        "th(DegreesClockwisefromnorth)": [180.0, 180.0, 180.0],
    }
    raw_data = {
        name: np.asarray(values, dtype=float).reshape(1, 1, len(dates))
        for name, values in columns.items()
    }
    monkeypatch.setattr(
        gridmet_client,
        "interpolate_geospatial",
        lambda _lng, _lat, _longitudes, _latitudes, values, _method, a_min=None: values[0, 0, :],
    )

    with pytest.raises(ValueError, match="pr\\(mm\\).*internal missing-data hole"):
        gridmet_client.interpolate_daily_timeseries_for_location(
            "p1",
            {"longitude": -116.0, "latitude": 43.0},
            dates,
            np.array([-116.0]),
            np.array([43.0]),
            raw_data,
            {name: {"method": "nearest"} for name in columns},
            str(tmp_path),
            2026,
            2026,
        )


def test_gridmet_build_stages_station_before_cli_worker_pool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateGridmetMultipleBuildService()
    events: list[str] = []

    class _StationManager:
        def __init__(self, version):
            assert version == "2015"

        def get_station_fromid(self, station_id):
            assert station_id == "id1"
            return SimpleNamespace(par="id1.par")

    class _Cligen:
        def __init__(self, station_meta, wd):
            assert station_meta.par == "id1.par"
            assert wd == str(tmp_path)

        def stage_station_parameter_file(self):
            events.append("stage")

    class _ClimateFile:
        def __init__(self, _path):
            pass

        def calc_monthlies(self):
            return [1.0] * 12

    monkeypatch.setattr(service_module, "CligenStationsManager", _StationManager)
    monkeypatch.setattr(service_module, "Cligen", _Cligen)
    monkeypatch.setattr(service_module, "ClimateFile", _ClimateFile)
    monkeypatch.setattr(
        service,
        "_load_gridmet_client_functions",
        lambda: (SimpleNamespace(), object(), object(), object(), object()),
    )
    monkeypatch.setattr(service, "_build_measures", lambda _enum: [])
    monkeypatch.setattr(service, "_build_interpolation_spec", lambda: {})
    monkeypatch.setattr(service, "_build_hillslope_locations", lambda *_args: {})
    monkeypatch.setattr(
        service,
        "_build_dates_and_bbox",
        lambda *_args: (pd.date_range("2026-01-01", periods=1), [0.0] * 4),
    )
    monkeypatch.setattr(service, "_retrieve_gridmet_netcdfs", lambda **_kwargs: None)
    monkeypatch.setattr(
        service,
        "_load_raw_gridmet_data",
        lambda **_kwargs: ({}, np.array([]), np.array([])),
    )
    monkeypatch.setattr(service, "_interpolate_hillslope_timeseries", lambda **_kwargs: None)

    def _build_cli_files(**_kwargs):
        events.append("pool")
        return {}, {}, "wepp.cli", False

    monkeypatch.setattr(service, "_build_interpolated_cli_files", _build_cli_files)

    climate = SimpleNamespace(
        watershed_instance=SimpleNamespace(centroid=(-116.0, 43.0)),
        cli_dir=str(tmp_path),
        cligen_db="2015",
        climatestation="id1",
        _require_observed_year_bounds_for_build=lambda: (2026, 2026),
    )

    result = service.build(
        climate,
        build_observed_gridmet_interpolated_fn=lambda *_args, **_kwargs: ("ws", False),
        ncpu=2,
    )
    assert isinstance(result, ClimateMultipleBuildResult)
    assert result.quality_guard_bypassed is False
    assert result.input_years == 1
    assert not hasattr(climate, "monthlies")
    assert not hasattr(climate, "cli_fn")
    assert events == ["stage", "pool"]


def test_build_rejects_invalid_observed_year_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ClimateGridmetMultipleBuildService()

    monkeypatch.setattr(
        service,
        "_load_gridmet_client_functions",
        lambda: (object(), object(), object(), object(), object()),
    )
    monkeypatch.setattr(service, "_build_measures", lambda _enum: [])
    monkeypatch.setattr(service, "_build_interpolation_spec", lambda: {})

    climate = SimpleNamespace(
        logger=_RecordingLogger(),
        watershed_instance=SimpleNamespace(centroid=(-116.0, 43.0)),
        cli_dir="/tmp",
        _require_observed_year_bounds_for_build=lambda: (_ for _ in ()).throw(
            ValueError("observed_end_year must be an integer year")
        ),
    )

    with pytest.raises(ValueError, match="observed_end_year must be an integer year"):
        service.build(
            climate,
            build_observed_gridmet_interpolated_fn=lambda *_args, **_kwargs: "unused",
            ncpu=1,
        )
