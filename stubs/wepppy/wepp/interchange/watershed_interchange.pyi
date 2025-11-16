from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

LOGGER: logging.Logger
_update_catalog_entry: Optional[object]

def run_wepp_watershed_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: Optional[int] = ...,
    run_soil_interchange: bool = ...,
    run_chnwb_interchange: bool = ...,
) -> Path: ...
