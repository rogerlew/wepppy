from __future__ import annotations

from pathlib import Path
from typing import Union

from .quality import SoilQualityContext, SoilQualityResult

class ESDACSoilQualityReportError(RuntimeError):
    report_path: str
    code: str
    topaz_id: str | int | None
    detail: str | None

class ESDACDisturbedSoilBuildError(RuntimeError):
    result: SoilQualityResult
    artifact_path: str
    quality_report_path: str

def load_soil_quality_report(
    report_path: Union[str, Path],
) -> dict[str, SoilQualityResult]: ...

def validate_disturbed_soil_artifact(
    soil_path: Union[str, Path],
    *,
    context: SoilQualityContext,
    expected_datver: int | float | None = ...,
    expected_luse: str | None = ...,
    expected_stext: str | None = ...,
    base_quality: SoilQualityResult | None = ...,
) -> SoilQualityResult: ...
