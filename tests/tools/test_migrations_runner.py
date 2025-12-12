from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.query_engine import activate_query_engine
from wepppy.tools.migrations.runner import refresh_query_catalog


def _write_parquet(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({"id": [1]}), path)


def test_refresh_query_catalog_forces_rebuild(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    first = run_dir / "wepp" / "output" / "interchange" / "a.parquet"
    second = run_dir / "wepp" / "output" / "interchange" / "b.parquet"

    _write_parquet(first)

    activate_query_engine(run_dir, run_interchange=False, force_refresh=True)
    catalog_path = run_dir / "_query_engine" / "catalog.json"
    original = json.loads(catalog_path.read_text())
    assert any(entry["path"] == "wepp/output/interchange/a.parquet" for entry in original["files"])

    _write_parquet(second)

    refresh_query_catalog(str(run_dir), dry_run=False)

    updated = json.loads(catalog_path.read_text())
    assert any(entry["path"] == "wepp/output/interchange/b.parquet" for entry in updated["files"])
    assert len(updated["files"]) >= 2
