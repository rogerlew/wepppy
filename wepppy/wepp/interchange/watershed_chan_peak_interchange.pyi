from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

CHAN_PEAK_FILENAME: str
CHAN_PEAK_PARQUET: str
CHUNK_SIZE: int
SCHEMA: Any

def run_wepp_watershed_chan_peak_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: int | None = ...,
) -> Path: ...

def chanout_dss_export(
    wd: Path | str,
    status_channel: str | None = ...,
    *,
    start_date: date | None = ...,
    end_date: date | None = ...,
) -> None: ...
