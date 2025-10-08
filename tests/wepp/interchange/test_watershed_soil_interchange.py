from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
import shutil

import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(full_name: str, relative_path: str):
    parts = full_name.split(".")
    for idx in range(1, len(parts)):
        pkg = ".".join(parts[:idx])
        if pkg not in sys.modules:
            module = types.ModuleType(pkg)
            module.__path__ = []
            sys.modules[pkg] = module

    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(full_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
_load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")

_watershed_soil = _load_module(
    "wepppy.wepp.interchange.watershed_soil_interchange",
    "wepppy/wepp/interchange/watershed_soil_interchange.py",
)

run_wepp_watershed_soil_interchange = _watershed_soil.run_wepp_watershed_soil_interchange
SOIL_PARQUET = _watershed_soil.SOIL_PARQUET


def test_watershed_soil_interchange_writes_parquet(tmp_path: Path) -> None:
    src = Path("tests/wepp/interchange/test_project/output")
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
