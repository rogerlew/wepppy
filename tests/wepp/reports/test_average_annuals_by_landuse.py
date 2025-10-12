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
from wepppy.wepp.reports.average_annuals_by_landuse import AverageAnnualsByLanduseReport


def test_average_annuals_by_landuse_builds_dataframe(monkeypatch, tmp_path):
    run_dir = tmp_path / "example_run"
    cache_dir = run_dir / "wepp" / "reports" / "cache"
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

    class StubQueryContext:
        def __init__(self, run_directory, *, run_interchange=False, auto_activate=True):
            assert Path(run_directory) == run_dir
            required = {
                "wepp/output/interchange/loss_pw0.hill.parquet",
                "watershed/hillslopes.parquet",
                "landuse/landuse.parquet",
            }
            self.catalog = SimpleNamespace(has=lambda path: path in required)

        def ensure_datasets(self, *paths: str) -> None:
            missing = [path for path in paths if not self.catalog.has(path)]
            if missing:
                raise FileNotFoundError(', '.join(missing))

        def query(self, payload):
            return QueryResult(records=records, schema=None, row_count=len(records))

    monkeypatch.setattr(
        "wepppy.wepp.reports.average_annuals_by_landuse.ReportQueryContext",
        StubQueryContext,
    )

    report = AverageAnnualsByLanduseReport(run_dir)
    cache_path = run_dir / "wepp" / "reports" / "cache" / "average_annuals_by_landuse.parquet"
    assert cache_path.exists()
    meta_path = cache_path.with_suffix(".meta.json")
    assert meta_path.exists()

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
