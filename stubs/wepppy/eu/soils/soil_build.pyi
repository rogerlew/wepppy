from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from wepppy.eu.soils.esdac.esdac import Horizon
from wepppy.soils.ssurgo import SoilSummary

NCPU: int

def _build_esdac_soil(kwargs: dict[str, Any]) -> tuple[str | int, str, Horizon, str]: ...

def build_esdac_soils(
    orders: Sequence[tuple[int | str, tuple[float, float]]],
    soils_dir: str,
    res_lyr_ksat_threshold: float = ...,
    status_channel: str | None = ...,
) -> tuple[dict[str, SoilSummary], dict[str, str]]: ...
