from __future__ import annotations

from pathlib import Path
from typing import Any

TC_OUT_FILENAME: str
TC_OUT_PARQUET: str
CHUNK_SIZE: int
SCHEMA: Any

def run_wepp_watershed_tc_out_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: int | None = ...,
    delete_after_interchange: bool = ...,
) -> Path | None: ...
