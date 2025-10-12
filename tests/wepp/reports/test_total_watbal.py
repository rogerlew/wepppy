from __future__ import annotations

import contextlib
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

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

sys.modules.setdefault("geopandas", types.ModuleType("geopandas"))

from wepppy.wepp.reports.total_watbal import TotalWatbalReport


def _write_totalwatsed3(path: Path) -> None:
    records = [
        {"water_year": 2000, "Precipitation": 2.0, "Rain+Melt": 3.0, "Lateral Flow": 1.0, "ET": 0.6, "Percolation": 0.4, "tdet": 5.0},
        {"water_year": 2000, "Precipitation": 1.0, "Rain+Melt": 0.5, "Lateral Flow": 0.3, "ET": 0.2, "Percolation": 0.1, "tdet": 2.0},
        {"water_year": 2001, "Precipitation": 4.0, "Rain+Melt": 2.0, "Lateral Flow": 1.5, "ET": 1.0, "Percolation": 0.8, "tdet": 3.0},
        {"water_year": 2001, "Precipitation": 2.0, "Rain+Melt": 1.0, "Lateral Flow": 0.8, "ET": 0.5, "Percolation": 0.3, "tdet": 1.5},
    ]
    df = pd.DataFrame.from_records(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def test_total_watbal_summarises_water_years(tmp_path):
    run_dir = tmp_path / "run"
    dataset_path = run_dir / "wepp" / "output" / "interchange" / "totalwatsed3.parquet"
    _write_totalwatsed3(dataset_path)

    report = TotalWatbalReport(run_dir, exclude_yr_indxs=[])

    rows = list(report)
    assert len(rows) == 2

    first = dict(rows[0].row)
    assert first["WaterYear"] == 2000
    assert first["Precipitation (mm)"] == pytest.approx(3.0)
    assert first["Rain + Melt (mm)"] == pytest.approx(3.5)
    assert first["Sed Del (kg)"] == pytest.approx(7.0)

    second = dict(rows[1].row)
    assert second["WaterYear"] == 2001
    assert second["Precipitation (mm)"] == pytest.approx(6.0)

    means = dict(report.means.row)
    assert means["Precipitation (mm)"] == pytest.approx(4.5)

    ratios = dict(report.pratios.row)
    assert ratios["Rain + Melt (%)"] == pytest.approx((3.5 + 3.0) / 9.0 * 100.0)


def test_total_watbal_excludes_year_indices(tmp_path):
    run_dir = tmp_path / "run"
    dataset_path = run_dir / "wepp" / "output" / "interchange" / "totalwatsed3.parquet"
    _write_totalwatsed3(dataset_path)

    report = TotalWatbalReport(run_dir, exclude_yr_indxs=[0])
    rows = list(report)
    assert len(rows) == 1
    assert rows[0].row["WaterYear"] == 2001
