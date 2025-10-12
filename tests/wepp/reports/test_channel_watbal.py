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

from wepppy.wepp.reports.channel_watbal import ChannelWatbalReport


def _write_sample_channel_parquet(target: Path) -> None:
    field_names = [
        "wepp_id",
        "julian",
        "year",
        "simulation_year",
        "month",
        "day_of_month",
        "water_year",
        "OFE",
        "J",
        "Y",
        "P (mm)",
        "RM (mm)",
        "Q (mm)",
        "Ep (mm)",
        "Es (mm)",
        "Er (mm)",
        "Dp (mm)",
        "UpStrmQ (mm)",
        "SubRIn (mm)",
        "latqcc (mm)",
        "Total Soil Water (mm)",
        "frozwt (mm)",
        "Snow Water (mm)",
        "QOFE (mm)",
        "Tile (mm)",
        "Irr (mm)",
        "Surf (mm)",
        "Base (mm)",
        "Area (m^2)",
    ]
    rows: list[dict[str, object]] = []

    def add_record(
        *,
        wepp_id: int,
        julian: int,
        year: int,
        sim_year: int,
        month: int,
        day: int,
        water_year: int,
        p: float,
        q: float,
        ep: float,
        es: float,
        er: float,
        dp: float,
        soil_water: float,
        base: float,
        area: float,
    ) -> None:
        rows.append(
            {
                "wepp_id": wepp_id,
                "julian": julian,
                "year": year,
                "simulation_year": sim_year,
                "month": month,
                "day_of_month": day,
                "water_year": water_year,
                "OFE": wepp_id,
                "J": julian,
                "Y": sim_year,
                "P (mm)": p,
                "RM (mm)": 0.0,
                "Q (mm)": q,
                "Ep (mm)": ep,
                "Es (mm)": es,
                "Er (mm)": er,
                "Dp (mm)": dp,
                "UpStrmQ (mm)": 0.0,
                "SubRIn (mm)": 0.0,
                "latqcc (mm)": 0.0,
                "Total Soil Water (mm)": soil_water,
                "frozwt (mm)": 0.0,
                "Snow Water (mm)": 0.0,
                "QOFE (mm)": 0.0,
                "Tile (mm)": 0.0,
                "Irr (mm)": 0.0,
                "Surf (mm)": 0.0,
                "Base (mm)": base,
                "Area (m^2)": area,
            }
        )

    # Channel 101 (area 1,000 m^2)
    add_record(
        wepp_id=101,
        julian=1,
        year=2000,
        sim_year=1,
        month=1,
        day=1,
        water_year=2000,
        p=1.0,
        q=0.5,
        ep=0.1,
        es=0.05,
        er=0.05,
        dp=0.2,
        soil_water=0.3,
        base=0.1,
        area=1_000.0,
    )
    add_record(
        wepp_id=101,
        julian=2,
        year=2000,
        sim_year=1,
        month=1,
        day=2,
        water_year=2000,
        p=2.0,
        q=0.7,
        ep=0.15,
        es=0.07,
        er=0.08,
        dp=0.3,
        soil_water=0.2,
        base=0.2,
        area=1_000.0,
    )
    add_record(
        wepp_id=101,
        julian=366,
        year=2001,
        sim_year=2,
        month=12,
        day=31,
        water_year=2001,
        p=0.5,
        q=0.3,
        ep=0.05,
        es=0.02,
        er=0.03,
        dp=0.1,
        soil_water=0.25,
        base=0.05,
        area=1_000.0,
    )
    add_record(
        wepp_id=101,
        julian=367,
        year=2001,
        sim_year=2,
        month=12,
        day=31,
        water_year=2001,
        p=1.5,
        q=0.4,
        ep=0.1,
        es=0.04,
        er=0.06,
        dp=0.15,
        soil_water=0.2,
        base=0.1,
        area=1_000.0,
    )

    # Channel 202 (area 3,000 m^2)
    add_record(
        wepp_id=202,
        julian=1,
        year=2000,
        sim_year=1,
        month=1,
        day=1,
        water_year=2000,
        p=4.0,
        q=2.0,
        ep=0.2,
        es=0.25,
        er=0.15,
        dp=0.8,
        soil_water=0.5,
        base=0.4,
        area=3_000.0,
    )
    add_record(
        wepp_id=202,
        julian=2,
        year=2000,
        sim_year=1,
        month=1,
        day=2,
        water_year=2000,
        p=5.0,
        q=2.2,
        ep=0.25,
        es=0.25,
        er=0.2,
        dp=0.9,
        soil_water=0.6,
        base=0.5,
        area=3_000.0,
    )
    add_record(
        wepp_id=202,
        julian=366,
        year=2001,
        sim_year=2,
        month=12,
        day=31,
        water_year=2001,
        p=3.0,
        q=1.5,
        ep=0.2,
        es=0.2,
        er=0.15,
        dp=0.6,
        soil_water=0.45,
        base=0.35,
        area=3_000.0,
    )
    add_record(
        wepp_id=202,
        julian=367,
        year=2001,
        sim_year=2,
        month=12,
        day=31,
        water_year=2001,
        p=4.5,
        q=1.8,
        ep=0.25,
        es=0.25,
        er=0.15,
        dp=0.7,
        soil_water=0.5,
        base=0.45,
        area=3_000.0,
    )

    data_frame = pd.DataFrame(rows, columns=field_names)
    data_frame.to_parquet(target, engine="pyarrow", index=False)


def test_channel_watbal_aggregates_average_annual_values(tmp_path):
    run_dir = tmp_path / "run"
    dataset_path = run_dir / "wepp" / "output" / "interchange" / "chnwb.parquet"
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    _write_sample_channel_parquet(dataset_path)

    report = ChannelWatbalReport(run_dir)

    assert report.wsarea == pytest.approx(4_000.0)
    assert report.units_d["Precipitation (mm)"] == "mm"

    avg_records = [row.row for row in report.avg_annual_iter()]
    assert len(avg_records) == 2

    first = avg_records[0]
    assert first["TopazID"] == 101
    assert first["Precipitation (mm)"] == pytest.approx(2.5)
    assert first["Streamflow (mm)"] == pytest.approx(0.95)
    assert first["Transpiration + Evaporation (mm)"] == pytest.approx(0.4)

    second = avg_records[1]
    assert second["TopazID"] == 202
    assert second["Precipitation (mm)"] == pytest.approx(8.25)
    assert second["Streamflow (mm)"] == pytest.approx(3.75)

    yearly_records = [row.row for row in report.yearly_iter()]
    assert [record["Year"] for record in yearly_records] == [2000, 2001]
    assert yearly_records[0]["Precipitation (mm)"] == pytest.approx(7.5)
    assert yearly_records[0]["Streamflow (mm)"] == pytest.approx(3.45)
    assert yearly_records[1]["Precipitation (mm)"] == pytest.approx(6.125)
