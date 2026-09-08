from __future__ import annotations

from pathlib import Path

import pytest

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.wepp.interchange.interchange_documentation import generate_interchange_documentation

pytestmark = pytest.mark.integration


def test_generate_interchange_documentation_includes_totalwatsed3_mofe_latqcc_note(tmp_path: Path) -> None:
    interchange_dir = tmp_path / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)

    table = pa.table(
        {
            "year": pa.array([2000], type=pa.int16()),
            "julian": pa.array([1], type=pa.int16()),
            "latqcc": pa.array([2.0], type=pa.float64()),
            "Lateral Flow": pa.array([10.0], type=pa.float64()),
        }
    )
    pq.write_table(table, interchange_dir / "totalwatsed3.parquet")

    markdown = generate_interchange_documentation(interchange_dir, to_readme_md=True)
    assert "## Companion Documentation" not in markdown
    assert "`README.totalwatsed3.md`" not in markdown
    assert "### `totalwatsed3.parquet`" in markdown
    assert "outlet-facing (last) OFE" in markdown

    readme_text = (interchange_dir / "README.md").read_text(encoding="utf-8")
    assert "## Companion Documentation" not in readme_text
    assert "`README.totalwatsed3.md`" not in readme_text
    assert "### `totalwatsed3.parquet`" in readme_text
    assert "outlet-facing (last) OFE" in readme_text


def test_generate_interchange_documentation_lists_existing_companion_docs(tmp_path: Path) -> None:
    interchange_dir = tmp_path / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    (interchange_dir / "README.totalwatsed3.md").write_text("Companion", encoding="utf-8")

    markdown = generate_interchange_documentation(interchange_dir, to_readme_md=True)
    assert "## Companion Documentation" in markdown
    assert "`README.totalwatsed3.md`" in markdown


@pytest.mark.parametrize("rows", [0, 1, 5])
def test_documentation_reads_only_first_preview_batch(tmp_path, monkeypatch, rows):
    table = pa.table({"year": list(range(2000, 2000 + rows))})
    pq.write_table(table, tmp_path / "H.wat.parquet", row_group_size=1)
    original_batches = pq.ParquetFile.iter_batches
    observed = []

    def bounded_batches(self, *args, **kwargs):
        assert kwargs["batch_size"] == 3
        for batch in original_batches(self, *args, **kwargs):
            observed.append(batch.num_rows)
            assert len(observed) == 1, "documentation read beyond its preview"
            yield batch

    def forbidden_full_read(*args, **kwargs):
        raise AssertionError("documentation must not load the full Parquet table")

    monkeypatch.setattr(pq, "read_table", forbidden_full_read)
    monkeypatch.setattr(pq.ParquetFile, "iter_batches", bounded_batches)
    markdown = generate_interchange_documentation(tmp_path)
    assert observed == ([min(rows, 3)] if rows else [])
    if rows:
        assert "2000" in markdown
        assert "2003" not in markdown
    else:
        assert "_No rows_" in markdown
