import importlib.util
import sys
import types
from pathlib import Path
import shutil

import pyarrow.parquet as pq
import pytest


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
concurrency_module = _load_module("wepppy.wepp.interchange.concurrency", "wepppy/wepp/interchange/concurrency.py")
ebe_module = _load_module("wepppy.wepp.interchange.hill_ebe_interchange", "wepppy/wepp/interchange/hill_ebe_interchange.py")


def test_ebe_interchange_writes_parquet(tmp_path, monkeypatch):
    src = Path("tests/wepp/interchange/test_project/output")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    for ebe_path in workdir.glob("H*.ebe.dat"):
        if ebe_path.name != "H1.ebe.dat":
            ebe_path.unlink()

    sample_rows = [
        "  29   2     5  10.6     4.1   0.000   0.00   0.00    0.0    0.00    0.00    0.0     0.0  1.00",
        "   1   3     5   0.0     0.0   0.000   0.00   0.00    0.0    0.00    0.00    0.0     0.0  1.00",
    ]

    header = [
        " EVENT OUTPUT",
        "day mo  year Precp  Runoff  IR-det Av-det Mx-det  Point  Av-dep Max-dep  Point Sed.Del    ER",
        "--- --  ----  (mm)    (mm)  kg/m^2 kg/m^2 kg/m^2    (m)  kg/m^2  kg/m^2    (m)  (kg/m)  ----",
    ]

    h1_path = workdir / "H1.ebe.dat"
    h1_path.write_text("\n".join(header + sample_rows) + "\n")

    calls = []

    def _wrapper(files, parser, schema, target_path, **kwargs):
        file_list = [Path(p) for p in files]
        calls.append({"files": file_list, "schema": schema})
        return concurrency_module.write_parquet_with_pool(file_list, parser, schema, target_path, **kwargs)

    monkeypatch.setattr(ebe_module, "write_parquet_with_pool", _wrapper)

    target = ebe_module.run_wepp_hillslope_ebe_interchange(workdir, start_year=2008)
    assert target.exists()
    assert calls
    assert all(p.name.lower().endswith(".ebe.dat") for p in calls[0]["files"])

    table = pq.read_table(target)
    assert table.schema == ebe_module.SCHEMA
    assert table.num_rows == len(sample_rows)

    df = table.to_pandas()
    assert set(df["wepp_id"].unique()) == {1}
    assert set(df["year"].unique()) == {2012}
    assert list(df["Precp (mm)"]) == pytest.approx([10.6, 0.0])
    assert list(df["Point (m)_2"]) == pytest.approx([0.0, 0.0])

    first = df.iloc[0]
    assert first["month"] == 2
    assert first["day_of_month"] == 29
    assert first["julian"] == 60
    assert first["water_year"] == 2012


def test_ebe_interchange_handles_missing_files(tmp_path):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = ebe_module.run_wepp_hillslope_ebe_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == ebe_module.SCHEMA
    assert table.num_rows == 0
