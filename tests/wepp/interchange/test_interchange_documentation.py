from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.wepp.interchange.interchange_documentation import generate_interchange_documentation


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
    assert "## Companion Documentation" in markdown
    assert "`README.totalwatsed3.md`" in markdown
    assert "### `totalwatsed3.parquet`" in markdown
    assert "outlet-facing (last) OFE" in markdown

    readme_text = (interchange_dir / "README.md").read_text(encoding="utf-8")
    assert "## Companion Documentation" in readme_text
    assert "`README.totalwatsed3.md`" in readme_text
    assert "### `totalwatsed3.parquet`" in readme_text
    assert "outlet-facing (last) OFE" in readme_text
