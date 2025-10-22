from __future__ import annotations

from functools import partial
from pathlib import Path
import shutil

import pyarrow.parquet as pq

from .module_loader import cleanup_import_state, load_module


load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")

_watershed_ebe = load_module(
    "wepppy.wepp.interchange.watershed_ebe_interchange",
    "wepppy/wepp/interchange/watershed_ebe_interchange.py",
)
cleanup_import_state()

run_wepp_watershed_ebe_interchange = _watershed_ebe.run_wepp_watershed_ebe_interchange
EBE_PARQUET = _watershed_ebe.EBE_PARQUET


def test_watershed_ebe_interchange_writes_parquet(tmp_path: Path) -> None:
    src = Path("tests/wepp/interchange/test_project/output")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    start_year = 2000
    target = run_wepp_watershed_ebe_interchange(workdir, start_year=start_year)
    assert target == workdir / "interchange" / EBE_PARQUET
    assert target.exists()

    table = pq.read_table(target)
    schema = table.schema

    expected_measurements = {
        "precip": b"mm",
        "runoff_volume": b"m^3",
        "peak_runoff": b"m^3/s",
        "sediment_yield": b"kg",
        "soluble_pollutant": b"kg",
        "particulate_pollutant": b"kg",
        "total_pollutant": b"kg",
    }

    for column, units in expected_measurements.items():
        field = schema.field(schema.get_field_index(column))
        assert field.metadata.get(b"units") == units

    df = table.to_pandas()
    assert not df.empty
    assert df["year"].min() == start_year
    assert df["year"].max() == start_year + 6 - 1
    assert set(df["element_id"].unique()) == {4}
    assert set(df.columns) == {
        "year",
        "simulation_year",
        "month",
        "day_of_month",
        "julian",
        "water_year",
        "precip",
        "runoff_volume",
        "peak_runoff",
        "sediment_yield",
        "soluble_pollutant",
        "particulate_pollutant",
        "total_pollutant",
        "element_id",
    }

    first_row = df.iloc[0]
    assert first_row["simulation_year"] == 1
    assert first_row["year"] == start_year
    assert first_row["julian"] == 1
