from __future__ import annotations

from pathlib import Path
import shutil

import pyarrow.parquet as pq

from .module_loader import PROJECT_OUTPUT, cleanup_import_state, load_module


load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")

_watershed_chan = load_module(
    "wepppy.wepp.interchange.watershed_chan_interchange",
    "wepppy/wepp/interchange/watershed_chan_interchange.py",
)
cleanup_import_state()

run_wepp_watershed_chan_interchange = _watershed_chan.run_wepp_watershed_chan_interchange
CHAN_PARQUET = _watershed_chan.CHAN_PARQUET
MEASUREMENTS = [col for col, *_ in _watershed_chan.MEASUREMENT_COLUMNS]


def test_watershed_chan_interchange_writes_parquet(tmp_path: Path) -> None:
    src = PROJECT_OUTPUT
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    start_year = 2000
    target = run_wepp_watershed_chan_interchange(workdir, start_year=start_year)
    assert target == workdir / "interchange" / CHAN_PARQUET
    assert target.exists()

    table = pq.read_table(target)
    schema = table.schema
    expected_columns = [
        "year",
        "simulation_year",
        "julian",
        "month",
        "day_of_month",
        "water_year",
        "Elmt_ID",
        "Chan_ID",
    ] + MEASUREMENTS
    assert schema.names == expected_columns

    inflow_field = schema.field(schema.get_field_index("Inflow (m^3)"))
    assert inflow_field.metadata.get(b"units") == b"m^3"
    assert b"description" in inflow_field.metadata

    df = table.to_pandas()
    assert not df.empty
    assert df["year"].min() == start_year
    assert df["year"].max() == start_year + df["simulation_year"].max() - 2000
    first_row = df.iloc[0]
    assert first_row["Elmt_ID"] == 4
    assert first_row["Chan_ID"] == 1
    assert first_row["julian"] == df.iloc[0]["julian"]
    assert 1 <= first_row["month"] <= 12
    assert 1 <= first_row["day_of_month"] <= 31
    assert first_row["Inflow (m^3)"] >= 0.0
