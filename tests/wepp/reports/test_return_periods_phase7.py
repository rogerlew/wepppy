from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from wepppy.runtime_paths.errors import NoDirError
from wepppy.wepp.reports.return_periods import _discover_climate_asset

pytestmark = pytest.mark.unit


def test_discover_climate_asset_rejects_retired_root_sidecars(tmp_path: Path) -> None:
    (tmp_path / "climate.wepp_cli.parquet").write_text("retired", encoding="utf-8")

    with pytest.raises(NoDirError, match="NODIR_MIGRATION_REQUIRED"):
        _discover_climate_asset(tmp_path)


def test_discover_climate_asset_returns_canonical_directory_parquet(tmp_path: Path) -> None:
    climate_dir = tmp_path / "climate"
    climate_dir.mkdir(parents=True)
    canonical = climate_dir / "wepp_cli.parquet"
    pd.DataFrame({
        "year": [2020],
        "month": [1],
        "day_of_month": [1],
        "prcp": [1.0],
        "storm_duration_hours": [1.0],
        "peak_intensity_30": [2.0],
    }).to_parquet(canonical, index=False)

    path, mapping = _discover_climate_asset(tmp_path)

    assert path == canonical
    assert mapping["year"] == "year"
