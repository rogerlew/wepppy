from __future__ import annotations

from pathlib import Path
from typing import Any, List

EBE_FILENAME: str
EBE_PARQUET: str
CHUNK_SIZE: int
SCHEMA: Any
MEASUREMENT_COLUMNS: List[str]

def run_wepp_watershed_ebe_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: int | None = ...,
) -> Path: ...
