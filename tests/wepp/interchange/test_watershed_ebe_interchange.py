from __future__ import annotations

import importlib.util
import sys
import types
from functools import partial
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

_watershed_ebe = _load_module(
    "wepppy.wepp.interchange.watershed_ebe_interchange",
    "wepppy/wepp/interchange/watershed_ebe_interchange.py",
)

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

    expected_measurements = [
        "Precip Depth (mm)",
        "Runoff Volume (m^3)",
        "Peak Runoff (m^3/s)",
        "Sediment Yield (kg)",
        "Solub. React. Phosphorus (kg)",
        "Particulate Phosphorus (kg)",
        "Total Phosphorus (kg)",
    ]

    for column, units in [
        ("Precip Depth (mm)", b"mm"),
        ("Runoff Volume (m^3)", b"m^3"),
        ("Peak Runoff (m^3/s)", b"m^3/s"),
        ("Sediment Yield (kg)", b"kg"),
    ]:
        field = schema.field(schema.get_field_index(column))
        assert field.metadata.get(b"units") == units

    df = table.to_pandas()
    assert not df.empty
    assert df["year"].min() == start_year
    assert df["year"].max() == start_year + 6 - 1
    assert set(df["Elmt ID"].unique()) == {4}
    assert set(df.columns) == {
        "year",
        "simulation_year",
        "month",
        "day_of_month",
        "julian",
        "water_year",
        "Precip Depth (mm)",
        "Runoff Volume (m^3)",
        "Peak Runoff (m^3/s)",
        "Sediment Yield (kg)",
        "Solub. React. Phosphorus (kg)",
        "Particulate Phosphorus (kg)",
        "Total Phosphorus (kg)",
        "Elmt ID",
    }

    first_row = df.iloc[0]
    assert first_row["simulation_year"] == 1
    assert first_row["year"] == start_year
    assert first_row["julian"] == 1

