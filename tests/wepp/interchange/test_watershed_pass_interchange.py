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

_watershed_pass = _load_module(
    "wepppy.wepp.interchange.watershed_pass_interchange",
    "wepppy/wepp/interchange/watershed_pass_interchange.py",
)

run_wepp_watershed_pass_interchange = _watershed_pass.run_wepp_watershed_pass_interchange
EVENTS_PARQUET = _watershed_pass.EVENTS_PARQUET
METADATA_PARQUET = _watershed_pass.METADATA_PARQUET


def test_watershed_pass_interchange_writes_parquet(tmp_path: Path) -> None:
    src = Path("tests/wepp/interchange/test_project/output")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    result = run_wepp_watershed_pass_interchange(workdir)
    events_path = result["events"]
    metadata_path = result["metadata"]

    assert events_path == workdir / "interchange" / EVENTS_PARQUET
    assert metadata_path == workdir / "interchange" / METADATA_PARQUET
    assert events_path.exists()
    assert metadata_path.exists()

    events_table = pq.read_table(events_path)
    metadata_table = pq.read_table(metadata_path)

    # Verify basic schema expectations
    assert {"event", "year", "julian", "wepp_id", "runoff", "gwbfv"}.issubset(events_table.schema.names)
    assert metadata_table.schema.names[0] == "wepp_id"
    assert metadata_table.num_rows == 3

    events_df = events_table.to_pandas()

    assert not events_df.empty
    events_present = set(events_df["event"].unique())
    assert {"SUBEVENT", "NO EVENT"}.issubset(events_present)
    assert set(events_df["wepp_id"].unique()) == {1, 2, 3}

    sedcon_cols = [col for col in events_df.columns if col.startswith("sedcon_")]
    assert sedcon_cols
    if "EVENT" in events_present:
        event_rows = events_df[events_df["event"] == "EVENT"]
        assert not event_rows.empty
        assert (event_rows["runoff"] > 0).any()
    else:
        subevent_rows = events_df[events_df["event"] == "SUBEVENT"]
        assert (subevent_rows["sbrunf"] > 0).any()

    # Metadata should carry climate file mappings
    metadata_df = metadata_table.to_pandas()
    assert metadata_df.set_index("wepp_id")["climate_file"].to_dict() == {1: "p1.cli", 2: "p2.cli", 3: "p3.cli"}
    area_field = metadata_table.schema.field(metadata_table.schema.get_field_index("area"))
    assert area_field.metadata.get(b"units") == b"m^2"
    srp_field = metadata_table.schema.field(metadata_table.schema.get_field_index("srp"))
    assert srp_field.metadata.get(b"units") == b"mg/L"
