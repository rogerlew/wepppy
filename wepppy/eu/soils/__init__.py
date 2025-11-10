"""Facade helpers for EU-specific soil datasets."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wepppy.soils.ssurgo import SoilSummary

__all__ = ["build_esdac_soils"]


def build_esdac_soils(
    orders: Sequence[tuple[int | str, tuple[float, float]]],
    soils_dir: str,
    res_lyr_ksat_threshold: float = 2.0,
    status_channel: str | None = None,
) -> tuple[dict[str, SoilSummary], dict[str, str]]:
    """Proxy to :func:`wepppy.eu.soils.soil_build.build_esdac_soils`.

    The import is deferred to keep the module lightweight for callers that only
    need the package namespace.
    """
    from .soil_build import build_esdac_soils as _build_esdac_soils

    return _build_esdac_soils(
        orders,
        soils_dir,
        res_lyr_ksat_threshold=res_lyr_ksat_threshold,
        status_channel=status_channel,
    )
