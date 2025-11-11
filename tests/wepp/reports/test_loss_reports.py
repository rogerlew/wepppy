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



from wepppy.wepp.reports.loss_channel_report import ChannelSummaryReport
from wepppy.wepp.reports.loss_hill_report import HillSummaryReport
from wepppy.wepp.reports.loss_outlet_report import OutletSummaryReport



def _configure_query_engine_stubs(monkeypatch, tmp_path: Path, dataset_paths: set[str], records_map: dict[str, list[dict]]):
    captured_payloads = []

    class StubQueryContext:
        def __init__(self, run_directory, *, run_interchange=False, auto_activate=True):
            assert Path(run_directory) == tmp_path
            self.run_directory = Path(run_directory)
            self.catalog = SimpleNamespace(has=lambda path: path in dataset_paths)

        def ensure_datasets(self, *paths: str) -> None:
            missing = [path for path in paths if path not in dataset_paths]
            if missing:
                raise FileNotFoundError(', '.join(sorted(missing)))

        def query(self, payload):
            captured_payloads.append(payload)
            if isinstance(payload, dict):
                path = next(item['path'] for item in payload["datasets"])
            else:
                path = payload.datasets[0]["path"]
            records = records_map.get(path, [])
            return SimpleNamespace(records=records, schema=None, row_count=len(records))

    monkeypatch.setattr(
        "wepppy.wepp.reports.loss_hill_report.ReportQueryContext",
        StubQueryContext,
    )
    monkeypatch.setattr(
        "wepppy.wepp.reports.loss_channel_report.ReportQueryContext",
        StubQueryContext,
    )
    monkeypatch.setattr(
        "wepppy.wepp.reports.loss_outlet_report.ReportQueryContext",
        StubQueryContext,
    )

    return captured_payloads


def test_hill_summary_builds_rows(monkeypatch, tmp_path):
    dataset_paths = {
        "wepp/output/interchange/loss_pw0.hill.parquet",
        "watershed/hillslopes.parquet",
        "landuse/landuse.parquet",
        "soils/soils.parquet",
    }
    records_map = {
        "wepp/output/interchange/loss_pw0.hill.parquet": [
            {
                "wepp_id": 1,
                "topaz_id": 101,
                "length_m": 120.0,
                "width_m": 25.0,
                "slope": 0.12,
                "area_ha": 2.0,
                "runoff_m3": 10.0,
                "lateral_m3": 6.0,
                "baseflow_m3": 4.0,
                "soil_loss_kg": 200.0,
                "sediment_dep_kg": 50.0,
                "sediment_yield_kg": 25.0,
                "solub_react_kg": 1.5,
                "particulate_kg": 0.8,
                "total_kg": 2.3,
                "landuse_key": 105,
                "landuse_desc": "Forest",
                "soil_key": "S1",
                "soil_desc": "Soil One",
            }
        ],
        "watershed/hillslopes.parquet": [],
        "landuse/landuse.parquet": [],
        "soils/soils.parquet": [],
    }

    _ = _configure_query_engine_stubs(monkeypatch, tmp_path, dataset_paths, records_map)

    report = HillSummaryReport(tmp_path)
    df = pd.DataFrame([dict(row.row) for row in report])

    assert "Runoff Depth (mm/yr)" in df.columns
    assert abs(df.loc[0, "Runoff Depth (mm/yr)"] - 0.5) < 1e-6  # 10 m3 over 2 ha
    assert abs(df.loc[0, "Soil Loss Density (kg/ha/yr)"] - 100.0) < 1e-6
    assert df.loc[0, "Landuse Description"] == "Forest"
    assert report.header[0] == "Wepp ID"


def test_channel_summary_builds_rows(monkeypatch, tmp_path):
    dataset_paths = {
        "wepp/output/interchange/loss_pw0.chn.parquet",
        "watershed/channels.parquet",
    }
    records_map = {
        "wepp/output/interchange/loss_pw0.chn.parquet": [
            {
                "loss_channel_id": 1,
                "channel_wepp_id": 10,
                "channel_enum": 10,
                "topaz_id": 501,
                "length_m": 300.0,
                "width_m": 15.0,
                "channel_order": 2,
                "slope": 0.02,
                "channel_area_m2": 5000.0,
                "contributing_area_ha": 50.0,
                "discharge_m3": 1000.0,
                "lateral_m3": 500.0,
                "upland_m3": 100.0,
                "sediment_yield_tonne": 2.0,
                "soil_loss_kg": 600.0,
                "solub_react_kg": 0.0,
                "particulate_kg": 0.0,
                "total_kg": 0.0,
            }
        ],
    }

    payloads = _configure_query_engine_stubs(monkeypatch, tmp_path, dataset_paths, records_map)

    report = ChannelSummaryReport(tmp_path)
    df = pd.DataFrame([dict(row.row) for row in report])
    assert "Discharge Depth (mm/yr)" in df.columns
    expected_depth = 1000.0 * 1000.0 / (50.0 * 10000.0)
    assert abs(df.loc[0, "Discharge Depth (mm/yr)"] - expected_depth) < 1e-6
    assert abs(df.loc[0, "Channel Erosion Density (kg/ha/yr)"] - (600.0 / (5000.0 / 10000.0))) < 1e-6

    payload = payloads[-1]
    assert payload.columns[0] == "loss.chn_enum AS loss_channel_id"
    assert payload.joins[0]["left_on"] == ["chn_enum"]
    assert payload.joins[0]["right_on"] == ["chn_enum"]


def test_outlet_summary_rows(monkeypatch, tmp_path):
    dataset_paths = {"wepp/output/interchange/loss_pw0.out.parquet"}
    records_map = {
        "wepp/output/interchange/loss_pw0.out.parquet": [
            {"key": "Total contributing area to outlet", "value": 100.0, "units": "ha"},
            {"key": "Avg. Ann. Precipitation volume in contributing area", "value": 500000.0, "units": "m^3/yr"},
            {"key": "Avg. Ann. water discharge from outlet", "value": 200000.0, "units": "m^3/yr"},
            {"key": "Avg. Ann. total hillslope soil loss", "value": 5.0, "units": "tonne/yr"},
            {"key": "Avg. Ann. total channel soil loss", "value": 2.0, "units": "tonne/yr"},
            {"key": "Avg. Ann. sediment discharge from outlet", "value": 2.5, "units": "tonne/yr"},
            {"key": "Sediment Delivery Ratio for Watershed", "value": 0.5, "units": ""},
            {"key": "Avg. Ann. Phosphorus discharge from outlet", "value": 30.0, "units": "kg/yr"},
        ]
    }

    _ = _configure_query_engine_stubs(monkeypatch, tmp_path, dataset_paths, records_map)

    report = OutletSummaryReport(tmp_path)
    rows = report.rows()
    assert rows[0].label == "Total contributing area to outlet"
    precipitation_row = next(row for row in rows if row.label == "Precipitation")
    assert abs(precipitation_row.per_area_value - 500000.0 * 1000.0 / (100.0 * 10000.0)) < 1e-6


def test_outlet_summary_accepts_loss_instance(monkeypatch, tmp_path):
    def _raise_context(*args, **kwargs):
        raise AssertionError("Query context should not be constructed for Loss inputs")

    monkeypatch.setattr(
        "wepppy.wepp.reports.loss_outlet_report.ReportQueryContext",
        _raise_context,
    )

    loss_file = tmp_path / "run" / "wepp" / "output" / "loss_pw0.txt"
    loss_file.parent.mkdir(parents=True, exist_ok=True)
    loss_file.touch()

    class StubLoss:
        def __init__(self, fn, records):
            self.fn = str(fn)
            self._records = records

        @property
        def out_tbl(self):
            return list(self._records)

    records = [
        {"key": "Total contributing area to outlet", "value": 100.0, "units": "ha"},
        {"key": "Avg. Ann. Precipitation volume in contributing area", "value": 500000.0, "units": "m^3/yr"},
        {"key": "Avg. Ann. water discharge from outlet", "value": 200000.0, "units": "m^3/yr"},
        {"key": "Avg. Ann. total hillslope soil loss", "value": 5.0, "units": "tonne/yr"},
        {"key": "Avg. Ann. sediment discharge from outlet", "value": 2.5, "units": "tonne/yr"},
        ]

    report = OutletSummaryReport(StubLoss(loss_file, records))
    rows = report.rows()

    assert any(row.label == "Stream discharge" for row in rows)
    precipitation_row = next(row for row in rows if row.label == "Precipitation")
    assert abs(precipitation_row.per_area_value - 500000.0 * 1000.0 / (100.0 * 10000.0)) < 1e-6


def test_hill_summary_accepts_loss_instance(monkeypatch, tmp_path):
    dataset_paths = {
        "wepp/output/interchange/loss_pw0.hill.parquet",
        "watershed/hillslopes.parquet",
        "landuse/landuse.parquet",
        "soils/soils.parquet",
    }
    records_map = {
        "wepp/output/interchange/loss_pw0.hill.parquet": [
            {
                "wepp_id": 1,
                "topaz_id": 101,
                "length_m": 120.0,
                "width_m": 25.0,
                "slope": 0.12,
                "area_ha": 2.0,
                "runoff_m3": 10.0,
                "lateral_m3": 6.0,
                "baseflow_m3": 4.0,
                "soil_loss_kg": 200.0,
                "sediment_dep_kg": 50.0,
                "sediment_yield_kg": 25.0,
                "solub_react_kg": 1.5,
                "particulate_kg": 0.8,
                "total_kg": 2.3,
                "landuse_key": 105,
                "landuse_desc": "Forest",
                "soil_key": "S1",
                "soil_desc": "Soil One",
            }
        ],
        "watershed/hillslopes.parquet": [],
        "landuse/landuse.parquet": [],
        "soils/soils.parquet": [],
    }

    _ = _configure_query_engine_stubs(monkeypatch, tmp_path, dataset_paths, records_map)

    loss_file = tmp_path / "wepp" / "output" / "interchange" / "loss_pw0.hill.parquet"
    loss_file.parent.mkdir(parents=True, exist_ok=True)
    loss_file.touch()

    class StubLoss:
        def __init__(self, fn):
            self.fn = str(fn)

        @property
        def hill_tbl(self):
            return []

    report = HillSummaryReport(StubLoss(loss_file), fraction_under=0.2)
    df = pd.DataFrame([dict(row.row) for row in report])

    assert "Runoff Depth (mm/yr)" in df.columns
    assert abs(df.loc[0, "Runoff Depth (mm/yr)"] - 0.5) < 1e-6


def test_channel_summary_accepts_loss_instance(monkeypatch, tmp_path):
    dataset_paths = {
        "wepp/output/interchange/loss_pw0.chn.parquet",
        "watershed/channels.parquet",
    }
    records_map = {
        "wepp/output/interchange/loss_pw0.chn.parquet": [
            {
                "loss_channel_id": 1,
                "channel_wepp_id": 10,
                "channel_enum": 10,
                "topaz_id": 501,
                "length_m": 300.0,
                "width_m": 15.0,
                "channel_order": 2,
                "slope": 0.02,
                "channel_area_m2": 5000.0,
                "contributing_area_ha": 50.0,
                "discharge_m3": 1000.0,
                "lateral_m3": 500.0,
                "upland_m3": 100.0,
                "sediment_yield_tonne": 2.0,
                "soil_loss_kg": 600.0,
                "solub_react_kg": 0.0,
                "particulate_kg": 0.0,
                "total_kg": 0.0,
            }
        ],
    }

    _ = _configure_query_engine_stubs(monkeypatch, tmp_path, dataset_paths, records_map)

    loss_file = tmp_path / "wepp" / "output" / "interchange" / "loss_pw0.chn.parquet"
    loss_file.parent.mkdir(parents=True, exist_ok=True)
    loss_file.touch()

    class StubLoss:
        def __init__(self, fn):
            self.fn = str(fn)

        @property
        def chn_tbl(self):
            return []

    report = ChannelSummaryReport(StubLoss(loss_file))
    df = pd.DataFrame([dict(row.row) for row in report])
    assert "Discharge Depth (mm/yr)" in df.columns
