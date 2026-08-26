from __future__ import annotations

from pathlib import Path
from typing import Union

from .esdac import ESDAC, _attr_fmt
from .downstream import (
    ESDACDisturbedSoilBuildError,
    ESDACSoilQualityReportError,
    load_soil_quality_report,
)
from .quality import SoilQualityContext, SoilQualityResult

__all__ = [
    "ESDAC",
    "_attr_fmt",
    "ESDACDisturbedSoilBuildError",
    "ESDACSoilQualityReportError",
    "load_soil_quality_report",
    "validate_disturbed_soil_artifact",
]

def validate_disturbed_soil_artifact(
    soil_path: Union[str, Path],
    *,
    context: SoilQualityContext,
    expected_datver: int | float | None = ...,
    expected_luse: str | None = ...,
    expected_stext: str | None = ...,
    base_quality: SoilQualityResult | None = ...,
) -> SoilQualityResult: ...
