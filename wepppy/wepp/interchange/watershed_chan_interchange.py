from __future__ import annotations

"""
Backward-compatible shim for legacy imports expecting
``wepppy.wepp.interchange.watershed_chan_interchange``.

The channel water-balance interchange logic now lives in
``watershed_chanwb_interchange``; this module re-exports the public
surface so existing callers keep working without introducing a hard
dependency on the old filename.
"""

from pathlib import Path
from typing import Any

from .watershed_chanwb_interchange import (  # noqa: F401 re-exported surface
    CHAN_PARQUET as _CHANWB_PARQUET,
    MEASUREMENT_COLUMNS,
    run_wepp_watershed_chanwb_interchange as _run_wepp_watershed_chanwb_interchange,
)

CHAN_PARQUET = _CHANWB_PARQUET

__all__ = [
    "CHAN_PARQUET",
    "MEASUREMENT_COLUMNS",
    "run_wepp_watershed_chan_interchange",
]


def run_wepp_watershed_chan_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: int | None = None,
    **kwargs: Any,
) -> Path:
    """
    Delegate to :func:`run_wepp_watershed_chanwb_interchange` while preserving
    the legacy entry point. Additional keyword arguments pass straight through
    to the underlying implementation.
    """

    return _run_wepp_watershed_chanwb_interchange(
        wepp_output_dir,
        start_year=start_year,
        **kwargs,
    )
