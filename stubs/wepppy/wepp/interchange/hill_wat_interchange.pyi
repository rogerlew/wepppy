from __future__ import annotations

from pathlib import Path
from typing import Any

SCHEMA: Any
WAT_OPTIONAL_COLUMN_NAMES: list[str]

def run_wepp_hillslope_wat_interchange(
    wepp_output_dir: Path | str,
    *,
    expected_hillslopes: int | None = ...,
    max_workers: int | None = ...,
) -> Path: ...

def load_hill_wat_dataframe(
    wepp_output_dir: Path | str,
    wepp_id: int,
    *,
    collapse: str | None = ...,
) -> Any: ...
