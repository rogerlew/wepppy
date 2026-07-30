from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.nodb.mods.omni.omni_documentation import (
    generate_omni_contrasts_documentation,
    generate_omni_scenarios_documentation,
)


pytestmark = pytest.mark.unit


def test_generate_omni_scenarios_documentation_uses_present_parquet_schemas(tmp_path: Path) -> None:
    pq.write_table(
        pa.table(
            {
                "key": ["Avg. Ann. sediment discharge from outlet"],
                "value": [12.5],
                "units": ["tonne/yr"],
                "scenario": ["uniform_high"],
                "new_optional_column": [7],
            }
        ),
        tmp_path / "scenarios.out.parquet",
    )

    markdown = generate_omni_scenarios_documentation(tmp_path)

    assert "## `scenarios.out.parquet`" in markdown
    assert "`new_optional_column`" in markdown
    assert "Mean annual sediment mass leaving the watershed" in markdown
    assert "## `scenarios.hillslope_summaries.parquet`" not in markdown
    assert (tmp_path / "README.scenarios.md").read_text(encoding="utf-8") == markdown


def test_generate_omni_contrasts_documentation_explains_difference_sign(tmp_path: Path) -> None:
    pq.write_table(
        pa.table(
            {
                "key": ["Avg. Ann. water discharge from outlet"],
                "v": [8.0],
                "units": ["m^3/yr"],
                "control_v": [10.0],
                "control_units": ["m^3/yr"],
                "control-contrast_v": [2.0],
                "contrast_id": [1],
            }
        ),
        tmp_path / "contrasts.out.parquet",
    )

    markdown = generate_omni_contrasts_documentation(tmp_path)

    assert "`control-contrast_v = control_v - v`; positive means a reduction" in markdown
    assert "`control-contrast_v`" in markdown
    assert "Mean annual water volume discharged" in markdown
    assert (tmp_path / "README.contrasts.md").read_text(encoding="utf-8") == markdown


def test_generate_omni_documentation_can_render_without_writing(tmp_path: Path) -> None:
    markdown = generate_omni_scenarios_documentation(tmp_path, to_readme_md=False)

    assert "No matching Omni Parquet artifacts" in markdown
    assert not (tmp_path / "README.scenarios.md").exists()
