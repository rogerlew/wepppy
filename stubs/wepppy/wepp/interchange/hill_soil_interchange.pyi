from __future__ import annotations

from pathlib import Path
from typing import Any

SCHEMA: Any

def run_wepp_hillslope_soil_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: int | None = ...,
    expected_hillslopes: int | None = ...,
    max_workers: int | None = ...,
) -> Path: ...
