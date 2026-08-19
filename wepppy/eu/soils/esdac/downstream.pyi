from __future__ import annotations

from pathlib import Path
from typing import Union

from .quality import SoilQualityContext, SoilQualityResult

def validate_disturbed_soil_artifact(
    soil_path: Union[str, Path],
    *,
    context: SoilQualityContext,
    expected_datver: int | float | None = ...,
    expected_luse: str | None = ...,
    expected_stext: str | None = ...,
    base_quality: SoilQualityResult | None = ...,
) -> SoilQualityResult: ...
