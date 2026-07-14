from __future__ import annotations

import importlib.util
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "docs/work-packages/20260713_ag_fields_concept2_watershed_integration"
    / "artifacts/capture_authoritative_inventory.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("ag_fields_authoritative_inventory", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_inventory(path: Path, *, sha256: str) -> None:
    table = pa.Table.from_pylist(
        [
            {
                "tree": "baseline_output",
                "relative_path": "example.txt",
                "size_bytes": 7,
                "sha256": sha256,
            }
        ]
    )
    pq.write_table(table, path)


def test_compare_reads_selected_parquet_columns_and_reports_changes(tmp_path: Path) -> None:
    module = _load_module()
    expected = tmp_path / "expected.parquet"
    identical = tmp_path / "identical.parquet"
    changed = tmp_path / "changed.parquet"
    _write_inventory(expected, sha256="a" * 64)
    _write_inventory(identical, sha256="a" * 64)
    _write_inventory(changed, sha256="b" * 64)

    assert module.compare(expected, identical)["identical"] is True
    result = module.compare(expected, changed)
    assert result["identical"] is False
    assert result["changed_count"] == 1
