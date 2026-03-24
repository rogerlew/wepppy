from __future__ import annotations

import contextlib
import json
import os
import shutil
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tests.stubs import ensure_geopandas_stub

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

if "rasterio" not in sys.modules:
    rasterio_module = types.ModuleType("rasterio")

    class _Env(contextlib.AbstractContextManager):  # pragma: no cover - stub
        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    rasterio_module.Env = _Env
    warp_module = types.ModuleType("rasterio.warp")
    warp_module.reproject = lambda *args, **kwargs: None  # pragma: no cover - stub

    class _Resampling:  # pragma: no cover - stub
        nearest = 0

    warp_module.Resampling = _Resampling
    warp_module.calculate_default_transform = lambda *args, **kwargs: (None, None, None)
    sys.modules["rasterio"] = rasterio_module
    sys.modules["rasterio.warp"] = warp_module

ensure_geopandas_stub()


class _Translator:
    def __init__(self, mapping):
        self._mapping = mapping

    def top(self, wepp):
        return self._mapping[int(wepp)]


class _WatershedStub:
    def __init__(self, translator):
        self._translator = translator

    def translator_factory(self):
        return self._translator


def _write_h_wat_parquet(path: Path) -> None:
    records = []
    for wepp_id, topaz_id, area in [(1, 101, 1_000.0), (2, 202, 3_000.0)]:
        for ofe_id, ofe_area in enumerate([area * 0.6, area * 0.4], start=1):
            for water_year, scale in [(2000, 1.0), (2001, 2.0)]:
                for day in range(2):
                    records.append(
                        {
                            "wepp_id": wepp_id,
                            "ofe_id": ofe_id,
                            "sim_day_index": day + 1,
                            "water_year": water_year,
                            "P": 1.0 * scale,
                            "Dp": 0.5 * scale,
                            "QOFE": 0.2 * scale,
                            "latqcc": 0.1 * scale,
                            "Ep": 0.05 * scale,
                            "Es": 0.03 * scale,
                            "Er": 0.02 * scale,
                            "Area": ofe_area,
                        }
                    )

    frame = pd.DataFrame.from_records(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


@pytest.fixture(autouse=True)
def patch_watershed(monkeypatch):
    translator = _Translator({1: 101, 2: 202})

    core_module = types.ModuleType("wepppy.nodb.core")

    class _Watershed:
        @staticmethod
        def getInstance(_):
            return _WatershedStub(translator)

    core_module.Watershed = _Watershed

    nodb_module = types.ModuleType("wepppy.nodb")
    nodb_module.core = core_module

    monkeypatch.setitem(sys.modules, "wepppy.nodb", nodb_module)
    monkeypatch.setitem(sys.modules, "wepppy.nodb.core", core_module)


def test_hillslope_watbal_aggregates_from_interchange(tmp_path, monkeypatch):
    from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport

    run_dir = tmp_path / "run"
    source_path = run_dir / "wepp" / "output" / "interchange" / "H.wat.parquet"
    _write_h_wat_parquet(source_path)

    report = HillslopeWatbalReport(run_dir)

    avg_rows = list(report.avg_annual_iter())
    assert len(avg_rows) == 2
    first = dict(avg_rows[0].row)
    assert first["TopazID"] == 101
    assert np.isclose(first["Precipitation (mm)"], 12.0)

    yearly_rows = list(report.yearly_iter())
    assert [row.row["Year"] for row in yearly_rows] == [2000, 2001]
    assert np.isclose(yearly_rows[0].row["Lateral Flow (mm)"], 0.4)
    assert np.isclose(yearly_rows[1].row["Surface Runoff (mm)"], 1.6)


def test_hillslope_watbal_uses_cache(tmp_path, monkeypatch):
    from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport

    run_dir = tmp_path / "run"
    cache_path = run_dir / "wepp" / "output" / "interchange" / "hillslope_watbal_summary.parquet"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_df = pd.DataFrame(
        {
            "TopazID": [301],
            "WaterYear": [1999],
            "Area_m2": [500.0],
            "Precipitation (mm)": [2.0],
            "Percolation (mm)": [1.0],
            "Surface Runoff (mm)": [0.5],
            "Lateral Flow (mm)": [0.25],
            "Transpiration + Evaporation (mm)": [0.75],
        }
    )
    cache_df.to_parquet(cache_path, index=False)

    report = HillslopeWatbalReport(run_dir)
    rows = list(report.avg_annual_iter())
    assert len(rows) == 1
    assert rows[0].row["TopazID"] == 301


def test_hillslope_watbal_rebuilds_when_source_is_newer_than_cache(tmp_path, monkeypatch):
    from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport

    run_dir = tmp_path / "run"
    cache_dir = run_dir / "wepp" / "reports" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "hillslope_watbal_summary.parquet"
    meta_path = cache_dir / "hillslope_watbal_summary.meta.json"
    cache_df = pd.DataFrame(
        {
            "TopazID": [301],
            "WaterYear": [1999],
            "Area_m2": [500.0],
            "Precipitation (mm)": [2.0],
            "Percolation (mm)": [1.0],
            "Surface Runoff (mm)": [0.5],
            "Lateral Flow (mm)": [0.25],
            "Transpiration + Evaporation (mm)": [0.75],
        }
    )
    cache_df.to_parquet(cache_path, index=False)
    meta_path.write_text(json.dumps({"version": "1"}))
    os.utime(cache_path, (1, 1))
    os.utime(meta_path, (1, 1))

    source_path = run_dir / "wepp" / "output" / "interchange" / "H.wat.parquet"
    _write_h_wat_parquet(source_path)
    os.utime(source_path, (2, 2))

    report = HillslopeWatbalReport(run_dir)
    rows = list(report.avg_annual_iter())
    assert len(rows) == 2
    assert rows[0].row["TopazID"] == 101

    refreshed_cache = pd.read_parquet(cache_path)
    assert len(refreshed_cache) == 4
    assert refreshed_cache["TopazID"].tolist() == [101, 101, 202, 202]


def test_hillslope_watbal_uses_roads_output_scope_with_isolated_cache(tmp_path, monkeypatch):
    from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport

    run_dir = tmp_path / "run"
    baseline_path = run_dir / "wepp" / "output" / "interchange" / "H.wat.parquet"
    _write_h_wat_parquet(baseline_path)

    roads_path = run_dir / "wepp" / "roads" / "output" / "interchange" / "H.wat.parquet"
    roads_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(baseline_path, roads_path)

    roads_frame = pd.read_parquet(roads_path)
    roads_frame["P"] = roads_frame["P"].astype(float) + 10.0
    roads_frame.to_parquet(roads_path, index=False)

    baseline = HillslopeWatbalReport(run_dir, output_scope="baseline")
    roads = HillslopeWatbalReport(run_dir, output_scope="roads")

    baseline_rows = [row.row for row in baseline.avg_annual_iter()]
    roads_rows = [row.row for row in roads.avg_annual_iter()]
    assert roads_rows[0]["Precipitation (mm)"] > baseline_rows[0]["Precipitation (mm)"]

    cache_dir = run_dir / "wepp" / "reports" / "cache"
    assert (cache_dir / "hillslope_watbal_summary.parquet").exists()
    assert (cache_dir / "hillslope_watbal_summary_roads.parquet").exists()


def test_hillslope_watbal_roads_maps_segment_run_ids_from_manifest(tmp_path, monkeypatch):
    from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport

    run_dir = tmp_path / "run"
    roads_path = run_dir / "wepp" / "roads" / "output" / "interchange" / "H.wat.parquet"
    _write_h_wat_parquet(roads_path)

    roads_frame = pd.read_parquet(roads_path)
    roads_frame.loc[roads_frame["wepp_id"] == 1, "wepp_id"] = 900001
    roads_frame.to_parquet(roads_path, index=False)

    manifest_path = run_dir / "wepp" / "roads" / "segments" / "roads.segment.pass.manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            [
                {
                    "segment_run_id": 900001,
                    "target_hillslope_wepp_id": 1,
                }
            ]
        ),
        encoding="utf-8",
    )

    report = HillslopeWatbalReport(run_dir, output_scope="roads")
    avg_rows = [row.row for row in report.avg_annual_iter()]
    topaz_ids = sorted(int(row["TopazID"]) for row in avg_rows)
    assert topaz_ids == [101, 202]


def test_hillslope_watbal_roads_preserves_unknown_ids_without_crashing(tmp_path, monkeypatch):
    from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport

    run_dir = tmp_path / "run"
    roads_path = run_dir / "wepp" / "roads" / "output" / "interchange" / "H.wat.parquet"
    _write_h_wat_parquet(roads_path)

    roads_frame = pd.read_parquet(roads_path)
    roads_frame.loc[roads_frame["wepp_id"] == 1, "wepp_id"] = 900001
    roads_frame.to_parquet(roads_path, index=False)

    report = HillslopeWatbalReport(run_dir, output_scope="roads")
    avg_rows = [row.row for row in report.avg_annual_iter()]
    topaz_ids = sorted(int(row["TopazID"]) for row in avg_rows)
    assert topaz_ids == [202, 900001]


def test_hillslope_watbal_rejects_invalid_output_scope(tmp_path, monkeypatch):
    from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport

    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(ValueError, match="Invalid output_scope"):
        HillslopeWatbalReport(run_dir, output_scope="invalid")
