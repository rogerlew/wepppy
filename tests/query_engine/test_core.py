from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.query_engine.catalog import DatasetCatalog
from wepppy.query_engine.context import RunContext
from wepppy.query_engine.core import run_query
from wepppy.query_engine.payload import QueryRequest


def _write_parquet(path: Path) -> None:
    table = pa.table({"id": [1, 2, 3], "value": ["a", "b", "c"]})
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)


def _write_catalog(root: Path, rel_path: str) -> None:
    catalog = {
        "version": 1,
        "generated_at": "2024-01-01T00:00:00Z",
        "root": str(root),
        "files": [
            {
                "path": rel_path,
                "extension": ".parquet",
                "size_bytes": (root / rel_path).stat().st_size,
                "modified": "2024-01-01T00:00:00Z",
            }
        ],
    }
    out_dir = root / "_query_engine"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")


def test_run_query_basic(tmp_path: Path) -> None:
    rel = "data/sample.parquet"
    parquet_path = tmp_path / rel
    _write_parquet(parquet_path)
    _write_catalog(tmp_path, rel)

    catalog = DatasetCatalog.load(tmp_path / "_query_engine" / "catalog.json")
    run_context = RunContext(runid=str(tmp_path), base_dir=tmp_path, scenario=None, catalog=catalog)

    payload = QueryRequest(datasets=[rel], columns=["id", "value"], limit=2)
    result = run_query(run_context, payload)

    assert result.row_count == 2
    assert result.records == [{"id": 1, "value": "a"}, {"id": 2, "value": "b"}]
    assert result.schema is None


def test_run_query_include_schema(tmp_path: Path) -> None:
    rel = "data/sample.parquet"
    parquet_path = tmp_path / rel
    _write_parquet(parquet_path)
    _write_catalog(tmp_path, rel)

    catalog = DatasetCatalog.load(tmp_path / "_query_engine" / "catalog.json")
    run_context = RunContext(runid=str(tmp_path), base_dir=tmp_path, scenario=None, catalog=catalog)

    payload = QueryRequest(datasets=[rel], include_schema=True)
    result = run_query(run_context, payload)

    assert result.row_count == 3
    assert len(result.records) == 3
    assert result.schema is not None
    assert any(field["name"] == "id" for field in result.schema)
