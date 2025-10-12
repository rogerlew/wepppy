from __future__ import annotations

import contextlib
import math
import sys
import types
from pathlib import Path

import numpy as np
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


def _write_ebe_parquet(path: Path) -> None:
    records = []
    base_values = [
        (1, 10.0, 100.0, 4.0, 1.0, 0.1, 0.2, 0.3),
        (2, 20.0, 200.0, 6.0, 2.0, 0.2, 0.3, 0.5),
        (3, 30.0, 300.0, 8.0, 3.0, 0.3, 0.4, 0.7),
    ]
    for sim_year, precip, runoff, peak, sediment, sol, part, total in base_values:
        records.append(
            {
                "simulation_year": sim_year,
                "precip": precip,
                "runoff_volume": runoff,
                "peak_runoff": peak,
                "sediment_yield": sediment,
                "soluble_pollutant": sol,
                "particulate_pollutant": part,
                "total_pollutant": total,
            }
        )
    frame = pd.DataFrame.from_records(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def _write_totalwatsed3(path: Path, area_m2: float) -> None:
    df = pd.DataFrame({"Area": [area_m2, area_m2]})
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def _expected_value(values: list[float], T: int) -> float:
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=0))
    kfactor = -1.0 * (0.45005 + 0.7797 * math.log(math.log(T / (T - 1.0))))
    return mean + std * kfactor


def test_frq_flood_uses_interchange(tmp_path):
    from wepppy.wepp.reports.frq_flood import FrqFloodReport

    run_dir = tmp_path / "run"
    interchange_dir = run_dir / "wepp" / "output" / "interchange"
    _write_ebe_parquet(interchange_dir / "ebe_pw0.parquet")
    _write_totalwatsed3(interchange_dir / "totalwatsed3.parquet", area_m2=100_000.0)  # 10 ha

    report = FrqFloodReport(run_dir, recurrence=[2, 5])

    assert report.years == 3
    assert report.num_events == 3
    assert report.has_phosphorus is True
    assert report.wsarea == pytest.approx(10.0)
    assert "Runoff (mm)" in report.header

    rows = list(report)
    assert rows[0].row["Recurrence"] == 2

    expected_precip = _expected_value([10.0, 20.0, 30.0], 2)
    assert rows[0].row["Precipitation Depth (mm)"] == pytest.approx(expected_precip)

    expected_runoff = _expected_value([100.0, 200.0, 300.0], 2)
    expected_runoff_mm = expected_runoff / (10.0 * 10000.0) * 1000.0
    assert rows[0].row["Runoff Volume (m^3)"] == pytest.approx(expected_runoff)
    assert rows[0].row["Runoff (mm)"] == pytest.approx(expected_runoff_mm)

    mean_row = rows[-2]
    assert mean_row.row["Recurrence"] == "Mean"
    assert mean_row.row["Sediment Yield (kg)"] == pytest.approx(2.0)

    std_row = rows[-1]
    assert std_row.row["Recurrence"] == "StdDev"
    assert std_row.row["Peak Runoff (m^3/s)"] == pytest.approx(np.std([4.0, 6.0, 8.0], ddof=0))
