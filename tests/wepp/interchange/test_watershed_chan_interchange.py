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

_watershed_chan = _load_module(
    "wepppy.wepp.interchange.watershed_chan_interchange",
    "wepppy/wepp/interchange/watershed_chan_interchange.py",
)

run_wepp_watershed_chan_interchange = _watershed_chan.run_wepp_watershed_chan_interchange
CHAN_PARQUET = _watershed_chan.CHAN_PARQUET
MEASUREMENTS = [col for col, *_ in _watershed_chan.MEASUREMENT_COLUMNS]


def test_watershed_chan_interchange_writes_parquet(tmp_path: Path) -> None:
    src = Path("tests/wepp/interchange/test_project/output")
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

