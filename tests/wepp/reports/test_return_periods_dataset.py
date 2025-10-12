from __future__ import annotations

import json
import shutil
import sys
import types
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "deprecated" not in sys.modules:
    module = types.ModuleType("deprecated")

    def _noop_deprecated(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    module.deprecated = _noop_deprecated
    sys.modules["deprecated"] = module

sys.modules.setdefault("utm", types.ModuleType("utm"))
sys.modules.setdefault("pyproj", types.ModuleType("pyproj"))
sys.modules.setdefault("geopandas", types.ModuleType("geopandas"))

if "rasterio" not in sys.modules:
    rasterio_module = types.ModuleType("rasterio")

    class _Env:
        def __enter__(self):  # pragma: no cover - stub
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):  # pragma: no cover - stub
            return False

    rasterio_module.Env = _Env
    warp_module = types.ModuleType("rasterio.warp")
    warp_module.reproject = lambda *args, **kwargs: None  # pragma: no cover - stub
    warp_module.calculate_default_transform = lambda *args, **kwargs: (None, None, None)

    class _Resampling:  # pragma: no cover - stub
        nearest = 0

    warp_module.Resampling = _Resampling
    sys.modules["rasterio"] = rasterio_module
    sys.modules["rasterio.warp"] = warp_module

from wepppy.wepp.reports.return_periods import (
    ReturnPeriodDataset,
    ReturnPeriods,
    refresh_return_period_events,
)


def _prepare_totwatsed3(source_tot2: Path, target_tot3: Path) -> None:
    df = pd.read_parquet(source_tot2)

    runoff_m3 = df["Runoff (m^3)"].astype(float)
    runoff_mm = df["Runoff (mm)"].astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        area_m2 = np.where(runoff_mm > 0.0, runoff_m3 * 1000.0 / runoff_mm, np.nan)
    area_series = pd.Series(area_m2).ffill().bfill().fillna(1.0).astype(float)

    tot3 = pd.DataFrame(
        {
            "year": df["Year"].astype(int),
            "day": df["Day"].astype(int),
            "julian": df["Julian"].astype(int),
            "month": df["Month"].astype(int),
            "day_of_month": df["Day"].astype(int),
            "water_year": df["Water Year"].astype(int),
            "runvol": runoff_m3,
            "tdet": df["Sed Del (kg)"].astype(float),
            "Area": area_series,
            "Streamflow": df["Streamflow (mm)"].astype(float),
        }
    )

    target_tot3.parent.mkdir(parents=True, exist_ok=True)
    tot3.to_parquet(target_tot3, index=False)


def _prepare_run_directory(base: Path) -> Path:
    sample_root = Path("tests/wepp/interchange/test_project")
    source_output = sample_root / "output"

    run_dir = base / "run"
    output_dir = run_dir / "wepp" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy sample outputs to mimic a WEPP run layout
    shutil.copytree(source_output, output_dir, dirs_exist_ok=True)

    # Ensure ebe parquet is available at the expected location
    ebe_source = source_output / "ebe_pw0.parquet"
    ebe_df = pd.read_parquet(ebe_source)
    sim_year = ebe_df["year"].astype(int)
    calendar_year = sim_year + 1999
    dt = pd.to_datetime(
        {
            "year": calendar_year,
            "month": ebe_df["mo"].astype(int),
            "day": ebe_df["da"].astype(int),
        }
    )
    interchange_dir = output_dir / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)

    ebe_interchange = pd.DataFrame(
        {
            "year": calendar_year.astype(int),
            "simulation_year": sim_year,
            "month": ebe_df["mo"].astype(int),
            "day_of_month": ebe_df["da"].astype(int),
            "julian": dt.dt.dayofyear.astype(int),
            "water_year": calendar_year.astype(int),
            "precip": ebe_df["Precipitation Depth (mm)"].astype(float),
            "runoff_volume": ebe_df["Runoff Volume (m^3)"].astype(float),
            "peak_runoff": ebe_df["Peak Runoff (m^3/s)"].astype(float),
            "sediment_yield": ebe_df["Sediment Yield (kg)"].astype(float),
            "soluble_pollutant": ebe_df["Soluble Reactive P (kg)"].astype(float),
            "particulate_pollutant": ebe_df["Particulate P (kg)"].astype(float),
            "total_pollutant": ebe_df["Total P (kg)"].astype(float),
            "element_id": ebe_df["TopazID"].astype(int),
        }
    )

    ebe_interchange_path = interchange_dir / "ebe_pw0.parquet"
    ebe_interchange.to_parquet(ebe_interchange_path, index=False)

    # Synthesize totalwatsed3 from totwatsed2 for the staged pipeline
    tot2_path = source_output / "totwatsed2.parquet"
    tot3_path = interchange_dir / "totalwatsed3.parquet"
    _prepare_totwatsed3(tot2_path, tot3_path)

    return run_dir


def test_return_period_dataset_pipeline(tmp_path):
    run_dir = _prepare_run_directory(tmp_path)

    events_path, ranks_path = refresh_return_period_events(run_dir)
    assert events_path.exists()
    assert ranks_path.exists()

    dataset = ReturnPeriodDataset(run_dir, auto_refresh=False)
    report = dataset.create_report(
        (2, 5, 10),
        exclude_yr_indxs=None,
        exclude_months=None,
        method="cta",
        gringorten_correction=True,
    )

    assert report.return_periods, "Expected return-period metrics to be populated"
    assert "Precipitation Depth" in report.return_periods
    assert 2 in report.return_periods["Precipitation Depth"]
    assert report.units_d["Runoff"] == "mm"
    assert report.num_events > 0

    serialized = report.to_dict()
    round_trip = ReturnPeriods.from_dict(json.loads(json.dumps(serialized)))
    for measure in ("Runoff", "Precipitation Depth"):
        expected = report.return_periods.get(measure, {})
        actual = round_trip.return_periods.get(measure, {})
        assert actual.keys() == expected.keys()
        for rec, row in expected.items():
            assert pytest.approx(actual[rec].get(measure, 0.0)) == row.get(measure, 0.0)

    # Ensure cached dataset can be reloaded without recomputation
    cached = ReturnPeriodDataset(run_dir, auto_refresh=False)
    cached_report = cached.create_report(
        (2, 5),
        exclude_yr_indxs=None,
        exclude_months=None,
        method="cta",
        gringorten_correction=True,
    )
    assert cached_report.return_periods["Runoff"]


def test_refresh_return_period_events_handles_pyarrow_table(monkeypatch, tmp_path):
    run_dir = _prepare_run_directory(tmp_path)

    original_arrow = duckdb.DuckDBPyRelation.arrow

    def _table_arrow(self):
        result = original_arrow(self)
        if hasattr(result, "read_all"):
            return result.read_all()
        return result

    monkeypatch.setattr(duckdb.DuckDBPyRelation, "arrow", _table_arrow)

    events_path, ranks_path = refresh_return_period_events(run_dir)
    events_table = pq.read_table(events_path)
    ranks_table = pq.read_table(ranks_path)

    assert events_table.num_rows > 0
    assert ranks_table.num_rows > 0


def test_return_periods_export_summary_variants(tmp_path):
    run_dir = _prepare_run_directory(tmp_path)

    refresh_return_period_events(run_dir)
    dataset = ReturnPeriodDataset(run_dir, auto_refresh=False)
    report = dataset.create_report(
        (2, 5),
        exclude_yr_indxs=None,
        exclude_months=None,
        method="cta",
        gringorten_correction=True,
    )

    simple_path = tmp_path / "summary_simple.tsv"
    report.export_tsv_summary(simple_path)
    simple_text = simple_path.read_text(encoding="utf-8")
    assert "WEPPcloud Return Period Analysis" in simple_text
    assert "Runoff" in simple_text

    extraneous_path = tmp_path / "summary_extraneous.tsv"
    report.export_tsv_summary(extraneous_path, extraneous=True)
    extraneous_text = extraneous_path.read_text(encoding="utf-8")
    assert "Recurrence Interval (years)" in extraneous_text
    assert "Weibull T" in extraneous_text
