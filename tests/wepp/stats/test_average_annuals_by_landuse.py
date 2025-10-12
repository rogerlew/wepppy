from __future__ import annotations

import contextlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

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

    class _Env(contextlib.AbstractContextManager):
        def __exit__(self, exc_type, exc_val, exc_tb):  # pragma: no cover - stub
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

if "geopandas" not in sys.modules:
    geopandas_module = types.ModuleType("geopandas")
    geopandas_module.GeoDataFrame = object  # pragma: no cover - stub
    sys.modules["geopandas"] = geopandas_module

from wepppy.query_engine.formatter import QueryResult
from wepppy.wepp.stats.average_annuals_by_landuse import AverageAnnualsByLanduse


def test_average_annuals_by_landuse_builds_dataframe(monkeypatch, tmp_path):
    run_dir = tmp_path / "example_run"
    cache_dir = run_dir / "wepp" / "output" / "interchange"
    cache_dir.mkdir(parents=True, exist_ok=True)

    records = [
        {
            "landuse_id": 101,
            "management_description": "Forest",
            "sum_runoff_m3": 100.0,
            "sum_subrunoff_m3": 200.0,
            "sum_baseflow_m3": 50.0,
            "sum_soil_loss": 5.0,
            "sum_sediment_yield": 4.0,
            "sum_sediment_deposition": 1.5,
            "sum_area_m2": 5_000.0,
        },
        {
            "landuse_id": 202,
            "management_description": "Pasture",
            "sum_runoff_m3": 20.0,
            "sum_subrunoff_m3": 40.0,
            "sum_baseflow_m3": 10.0,
            "sum_soil_loss": 2.5,
            "sum_sediment_yield": 1.5,
            "sum_sediment_deposition": 0.2,
            "sum_area_m2": 20_000.0,
        },
    ]

    def fake_activate(wd, run_interchange=False):
        assert Path(wd) == run_dir

    def fake_resolve(wd, auto_activate=False):
        assert wd == str(run_dir)
        required = {
            "wepp/output/interchange/loss_pw0.hill.parquet",
            "watershed/hillslopes.parquet",
            "landuse/landuse.parquet",
        }

        def _has(path: str) -> bool:
            return path in required

        catalog = SimpleNamespace(has=_has)
        return SimpleNamespace(base_dir=run_dir, catalog=catalog)

    def fake_run_query(context, payload):
        return QueryResult(records=records, schema=None, row_count=len(records))

    monkeypatch.setattr(
        "wepppy.wepp.stats.average_annuals_by_landuse.activate_query_engine",
        fake_activate,
    )
    monkeypatch.setattr(
        "wepppy.wepp.stats.average_annuals_by_landuse.resolve_run_context",
        fake_resolve,
    )
    monkeypatch.setattr(
        "wepppy.wepp.stats.average_annuals_by_landuse.run_query",
        fake_run_query,
    )

    report = AverageAnnualsByLanduse(run_dir)
    cache_path = run_dir / "wepp" / "output" / "interchange" / "average_annuals_by_landuse.parquet"
    assert cache_path.exists()

    df = pd.read_parquet(cache_path)
    assert not df.empty
    assert list(report.header) == list(df.columns)

    first_row = df.iloc[0]
    assert first_row["Landuse ID"] == 202
    assert first_row["Management Description"] == "Pasture"
    # Landuse area = 20,000 m^2 = 2 ha
    assert first_row["Landuse Area (ha)"] == 2.0
    # Runoff depth = 20 m^3 * 1000 / 20,000 m^2 = 1 mm
    assert first_row["Avg Runoff Depth (mm/yr)"] == 1.0
    assert first_row["Avg Lateral Flow Depth (mm/yr)"] == 2.0
    assert first_row["Avg Baseflow Depth (mm/yr)"] == 0.5
    assert first_row["Avg Soil Loss (kg/yr)"] == 2.5

    # Verify iteration yields RowData objects with matching keys
    rows = list(report)
    assert len(rows) == len(df)
    row0_pairs = list(rows[0])
    assert len(row0_pairs) == len(report.header)
