from __future__ import annotations

from pathlib import Path
from typing import Any

CHAN_FILENAME: str
CHAN_PARQUET: str
SCHEMA: Any
MEASUREMENT_COLUMNS: Any

def run_wepp_watershed_chanwb_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: int | None = ...,
) -> Path: ...
