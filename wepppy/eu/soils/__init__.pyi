from __future__ import annotations

from collections.abc import Sequence

from wepppy.soils.ssurgo import SoilSummary

__all__ = ["build_esdac_soils"]

def build_esdac_soils(
    orders: Sequence[tuple[int | str, tuple[float, float]]],
    soils_dir: str,
    res_lyr_ksat_threshold: float = ...,
    status_channel: str | None = ...,
) -> tuple[dict[str, SoilSummary], dict[str, str]]: ...
