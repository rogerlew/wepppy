from __future__ import annotations

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from wepppy.wepp.interchange._utils import _build_cli_calendar_lookup, _julian_to_calendar


def test_calendar_lookup_uses_cli_parquet(tmp_path) -> None:
    climate_dir = tmp_path / "climate"
    climate_dir.mkdir(parents=True)
    output_dir = tmp_path / "wepp" / "output"
    output_dir.mkdir(parents=True)

    # Build a calendar with an explicit leap day for simulation year 1.
    days = [(1, day) for day in range(1, 32)] + [(2, day) for day in range(1, 30)]
    data = {
        "year": [1] * len(days),
        "month": [month for month, _ in days],
        "day_of_month": [day for _, day in days],
    }
    pq.write_table(pa.table(data), climate_dir / "wepp_cli.parquet")

    lookup = _build_cli_calendar_lookup(output_dir)
    assert lookup
    assert len(lookup[1]) == len(days)

    month, day = _julian_to_calendar(1, 60, calendar_lookup=lookup)
    assert (month, day) == (2, 29)
