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
loss_module = _load_module("wepppy.wepp.interchange.hill_loss_interchange", "wepppy/wepp/interchange/hill_loss_interchange.py")


def test_loss_interchange_writes_parquet(tmp_path, monkeypatch):
    src = Path("tests/wepp/interchange/test_project/output")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    calls = []

    def _wrapper(files, parser, schema, target_path, **kwargs):
        file_list = [Path(p) for p in files]
        calls.append({"files": file_list, "schema": schema})
        return concurrency_module.write_parquet_with_pool(file_list, parser, schema, target_path, **kwargs)

    monkeypatch.setattr(loss_module, "write_parquet_with_pool", _wrapper)

    target = loss_module.run_wepp_hillslope_loss_interchange(workdir)
    assert target.exists()
    assert calls
    assert all(p.name.lower().endswith(".loss.dat") for p in calls[0]["files"])

    table = pq.read_table(target)
    assert table.schema == loss_module.SCHEMA
    assert table.num_rows > 0

    df = table.to_pandas()
    assert set(df["wepp_id"].unique()) == {1, 2, 3}
    assert (df.groupby("wepp_id")["Class"].nunique() == 5).all()

    first = df.sort_values(["wepp_id", "Class"]).iloc[0]
    assert first["Diameter (mm)"] == pytest.approx(0.002)
    assert first["Sediment Fraction"] == pytest.approx(0.010)
    assert first["In Flow Exiting"] == pytest.approx(0.0)


def test_loss_interchange_handles_missing_files(tmp_path):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = loss_module.run_wepp_hillslope_loss_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == loss_module.SCHEMA
    assert table.num_rows == 0
