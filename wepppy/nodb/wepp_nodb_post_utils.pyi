from __future__ import annotations

import logging
from typing import Optional

from wepppy.nodb.core import Climate, Wepp

__all__ = [
    "activate_query_engine_for_run",
    "ensure_hillslope_interchange",
    "ensure_totalwatsed3",
    "ensure_watershed_interchange",
]

def ensure_hillslope_interchange(
    wepp: Wepp,
    climate: Climate,
    logger: Optional[logging.Logger] = ...,
    *,
    watershed_pending: bool = ...,
) -> None: ...
def ensure_totalwatsed3(
    wepp: Wepp, climate: Climate, logger: Optional[logging.Logger] = ...
) -> None: ...
def ensure_watershed_interchange(
    wepp: Wepp,
    climate: Climate,
    logger: Optional[logging.Logger] = ...,
    *,
    cleanup_deferred_hillslope_sources: bool = ...,
) -> None: ...
def activate_query_engine_for_run(
    wepp: Wepp, logger: Optional[logging.Logger] = ...
) -> None: ...
