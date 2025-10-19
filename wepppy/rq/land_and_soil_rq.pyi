from __future__ import annotations

from typing import Optional, Sequence, Tuple

TIMEOUT: int

def land_and_soil_rq(
    runid: Optional[str],
    extent: Sequence[float],
    cfg: Optional[str],
    nlcd_db: Optional[str],
    ssurgo_db: Optional[str],
) -> Tuple[str, float]: ...
