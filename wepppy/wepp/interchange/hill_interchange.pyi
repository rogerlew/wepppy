from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

LOGGER: logging.Logger
_update_catalog_entry: Optional[object]

def cleanup_hillslope_sources_for_completed_interchange(
    wepp_output_dir: Path | str,
    *,
    run_loss_interchange: bool = ...,
    run_soil_interchange: bool = ...,
    run_wat_interchange: bool = ...,
) -> list[str]: ...

def run_wepp_hillslope_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: Optional[int] = ...,
    run_loss_interchange: bool = ...,
    run_soil_interchange: bool = ...,
    run_wat_interchange: bool = ...,
    delete_after_interchange: bool = ...,
) -> Path: ...
