from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from wepppy.climates.cligen import ClimateFile

pytestmark = pytest.mark.unit


def _load_test_climate(tmp_path: Path) -> ClimateFile:
    src = Path(__file__).resolve().parent / "test.cli"
    dst = tmp_path / "test.cli"
    dst.write_text(src.read_text(encoding="ascii"), encoding="ascii")
    return ClimateFile(str(dst))


def test_replace_var_rejects_nan_values_without_mutating_lines(tmp_path: Path) -> None:
    climate = _load_test_climate(tmp_path)
    original_lines = list(climate.lines)

    with pytest.raises(ValueError, match="NaN value"):
        climate.replace_var("tdew", [(2023, 1, 1)], [np.nan])

    assert climate.lines == original_lines


def test_replace_var_updates_numeric_values_when_no_nan_present(tmp_path: Path) -> None:
    climate = _load_test_climate(tmp_path)

    climate.replace_var("tdew", [(2023, 1, 1)], [5.25])
    updated = climate.as_dataframe()

    first_row = updated.iloc[0]
    assert int(first_row["year"]) == 2023
    assert int(first_row["mo"]) == 1
    assert int(first_row["da"]) == 1
    assert float(first_row["tdew"]) == pytest.approx(5.2, abs=0.05)
