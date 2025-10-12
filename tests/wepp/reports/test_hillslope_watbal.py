from __future__ import annotations

import contextlib
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
