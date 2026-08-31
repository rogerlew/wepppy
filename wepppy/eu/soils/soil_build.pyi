from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any

from wepppy.eu.soils.esdac.esdac import Horizon
from wepppy.eu.soils.esdac.quality import SoilQualityResult
from wepppy.soils.ssurgo import SoilSummary

NCPU: int
logger: logging.Logger

@dataclass(frozen=True, slots=True)
class SoilBuildWorkerResult:
    topaz_id: str | int
    key: str | None
    horizon: Horizon | None
    description: str | None
    quality: SoilQualityResult


class ESDACSoilBatchError(RuntimeError):
    rejected: tuple[SoilBuildWorkerResult, ...]
    report_path: Path

    def __init__(
        self,
        rejected: Sequence[SoilBuildWorkerResult],
        report_path: Path,
    ) -> None: ...


def _build_esdac_soil(kwargs: dict[str, Any]) -> SoilBuildWorkerResult: ...

def build_esdac_soils(
    orders: Sequence[tuple[int | str, tuple[float, float]]],
    soils_dir: str,
    res_lyr_ksat_threshold: float = ...,
    status_channel: str | None = ...,
) -> tuple[dict[str, SoilSummary], dict[str, str]]: ...
