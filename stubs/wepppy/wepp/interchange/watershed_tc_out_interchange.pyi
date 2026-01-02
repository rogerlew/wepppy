from __future__ import annotations

from pathlib import Path

def run_wepp_watershed_tc_out_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: int | None = ...,
) -> Path | None: ...
