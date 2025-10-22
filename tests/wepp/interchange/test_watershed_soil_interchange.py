from __future__ import annotations

import shutil
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from .module_loader import PROJECT_OUTPUT, cleanup_import_state, load_module


load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")

_watershed_soil = load_module(
    "wepppy.wepp.interchange.watershed_soil_interchange",
    "wepppy/wepp/interchange/watershed_soil_interchange.py",
)
cleanup_import_state()

run_wepp_watershed_soil_interchange = _watershed_soil.run_wepp_watershed_soil_interchange
SOIL_PARQUET = _watershed_soil.SOIL_PARQUET


def test_watershed_soil_interchange_writes_parquet(tmp_path: Path) -> None:
    src = PROJECT_OUTPUT
    if not any((src / name).exists() for name in ("soil_pw0.txt", "soil_pw0.txt.gz")):
        pytest.skip("soil_pw0 dataset not available in test fixture")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    target = run_wepp_watershed_soil_interchange(workdir)
    assert target == workdir / "interchange" / SOIL_PARQUET
    assert target.exists()

    table = pq.read_table(target)
    schema = table.schema

    expected_columns = [
        "wepp_id",
        "ofe_id",
        "year",
        "day",
        "julian",
        "month",
        "day_of_month",
        "water_year",
        "OFE",
        "Poros",
        "Keff",
        "Suct",
        "FC",
        "WP",
        "Rough",
        "Ki",
        "Kr",
        "Tauc",
        "Saturation",
        "TSW",
    ]
    assert schema.names == expected_columns

    poros_field = schema.field(schema.get_field_index("Poros"))
    assert poros_field.metadata.get(b"units") == b"%"
    keff_field = schema.field(schema.get_field_index("Keff"))
    assert keff_field.metadata.get(b"units") == b"mm/hr"
    tsw_field = schema.field(schema.get_field_index("TSW"))
    assert tsw_field.metadata.get(b"units") == b"mm"

    df = table.to_pandas()
    assert not df.empty
    assert set(df["wepp_id"].unique()) == {1}
    assert (df["wepp_id"] == df["ofe_id"]).all()
    assert (df["wepp_id"] == df["OFE"]).all()
    assert (df["day"] == df["julian"]).all()
    first_row = df.iloc[0]
    assert 1 <= first_row["month"] <= 12
    assert 1 <= first_row["day_of_month"] <= 31
