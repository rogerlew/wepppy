from __future__ import annotations

from typing import Mapping

def pmetpara_prep(
    runs_dir: str,
    kcb: float | Mapping[str, float],
    rawp: float | Mapping[str, float],
) -> None: ...
