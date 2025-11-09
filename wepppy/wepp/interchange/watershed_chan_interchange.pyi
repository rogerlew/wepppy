from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .watershed_chanwb_interchange import MEASUREMENT_COLUMNS as MEASUREMENT_COLUMNS

CHAN_PARQUET: str

def run_wepp_watershed_chan_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: Optional[int] = ...,
    **kwargs: Any,
) -> Path: ...

__all__ = ["CHAN_PARQUET", "MEASUREMENT_COLUMNS", "run_wepp_watershed_chan_interchange"]
