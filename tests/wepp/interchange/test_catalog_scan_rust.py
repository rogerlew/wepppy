from __future__ import annotations

import importlib
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from .module_loader import cleanup_import_state, load_module

pytestmark = pytest.mark.integration

try:
    rust_interchange = importlib.import_module("wepppyo3.wepp_interchange")
except Exception:
    pytest.skip("wepppyo3.wepp_interchange not available in this environment.", allow_module_level=True)

activate_module = load_module("wepppy.query_engine.activate", "wepppy/query_engine/activate.py")
build_entry = activate_module._build_entry
cleanup_import_state()


def test_catalog_scan_schema_key_parity(tmp_path: Path) -> None:
    base = tmp_path / "catalog"
    base.mkdir()

    parquet_path = base / "sample.parquet"
    csv_path = base / "notes.csv"

    table = pa.table({"a": [1, 2]})
    pq.write_table(table, parquet_path)
    csv_path.write_text("a,b\n1,2\n")

    rust_entries = rust_interchange.catalog_scan(str(base))
    entries_by_path = {entry["path"]: entry for entry in rust_entries}

    py_parquet = build_entry(base, parquet_path, base_len=None, catalog_path=None)
    py_csv = build_entry(base, csv_path, base_len=None, catalog_path=None)

    assert py_parquet is not None
    assert py_csv is not None
    assert "schema" in py_parquet
    assert "schema" not in py_csv

    rust_parquet = entries_by_path[py_parquet["path"]]
    rust_csv = entries_by_path[py_csv["path"]]

    assert "schema" in rust_parquet
    assert "schema" not in rust_csv
