from __future__ import annotations

from pathlib import Path
from typing import Any

CHANWB_FILENAME: str
CHANWB_PARQUET: str
SCHEMA: Any
MEASUREMENT_COLUMNS: Any

def run_wepp_watershed_chnwb_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: int | None = ...,
) -> Path: ...
