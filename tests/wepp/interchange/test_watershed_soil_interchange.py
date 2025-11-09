from __future__ import annotations

import shutil
from pathlib import Path
from typing import Set

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
_write_soil_parquet = _watershed_soil._write_soil_parquet
_SCHEMA = _watershed_soil.SCHEMA
_MEASUREMENT_COLUMNS = _watershed_soil.MEASUREMENT_COLUMNS

PROFILE_DATA_ROOT = Path("/workdir/wepppy-test-engine-data/profiles")


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


@pytest.mark.integration
@pytest.mark.parametrize(
    ("profile", "missing_columns"),
    [
        ("legacy-palouse", {"Saturation", "TSW"}),
        ("us-small-wbt-daymet-rap-wepp", set()),
    ],
    ids=["legacy-layout", "modern-layout"],
)
def test_watershed_soil_interchange_supports_multiple_layouts(tmp_path: Path, profile: str, missing_columns: Set[str]) -> None:
    source = PROFILE_DATA_ROOT / profile / "run/wepp/output" / "soil_pw0.txt"
    if not source.exists():
        pytest.skip(f"profile dataset missing: {source}")

    tmp_source = tmp_path / "soil_pw0.txt"
    tmp_source.write_bytes(source.read_bytes())
    target = tmp_path / "soil.parquet"

    _write_soil_parquet(tmp_source, target)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == _SCHEMA
    assert table.num_rows > 0

    for column in _MEASUREMENT_COLUMNS:
        arr = table.column(column)
        if column in missing_columns:
            assert arr.null_count == table.num_rows
        else:
            assert arr.null_count < table.num_rows
