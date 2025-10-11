from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.query_engine.activate import activate_query_engine, update_catalog_entry


def _write_parquet(path: Path, table: pa.Table) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)


def test_activate_query_engine_readonly(tmp_path: Path) -> None:
    (tmp_path / "READONLY").write_text("locked", encoding="utf-8")
    with pytest.raises(PermissionError):
        activate_query_engine(tmp_path, run_interchange=False)


def test_update_catalog_entry(tmp_path: Path) -> None:
    table = pa.table({"id": [1, 2], "value": ["a", "b"]})
    rel = "data/sample.parquet"
    file_path = tmp_path / rel
    _write_parquet(file_path, table)

    # initial activation builds catalog
    activate_query_engine(tmp_path, run_interchange=False)

    catalog_path = tmp_path / "_query_engine" / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    assert any(entry["path"] == rel for entry in catalog["files"])

    # modify file and update entry
    table_updated = pa.table({"id": [1, 2, 3], "value": ["a", "b", "c"]})
    _write_parquet(file_path, table_updated)

    entry = update_catalog_entry(tmp_path, rel)
    assert entry is not None
    assert entry["path"] == rel

    catalog = json.loads(catalog_path.read_text())
    updated_entry = next(item for item in catalog["files"] if item["path"] == rel)
    assert updated_entry["size_bytes"] == file_path.stat().st_size

    # remove file and ensure catalog entry removed
    file_path.unlink()
    removed = update_catalog_entry(tmp_path, rel)
    assert removed is None
    catalog = json.loads(catalog_path.read_text())
    assert all(item["path"] != rel for item in catalog["files"])
