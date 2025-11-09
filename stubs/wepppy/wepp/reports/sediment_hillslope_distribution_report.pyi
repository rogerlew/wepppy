from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable

from .report_base import ReportBase
from .row_data import RowData

__all__ = [
    "HillslopeClassFractionReport",
    "HillslopeParticleDistributionReport",
    "HillslopeSedimentDistribution",
]


class HillslopeClassFractionReport(ReportBase):
    def __init__(self, rows: Iterable[OrderedDict[str, float]]) -> None: ...

    def __iter__(self) -> Iterable[RowData]: ...


class HillslopeParticleDistributionReport(ReportBase):
    def __init__(self, rows: Iterable[OrderedDict[str, float]]) -> None: ...

    def __iter__(self) -> Iterable[RowData]: ...


class HillslopeSedimentDistribution:
    total_delivery_tonne: float
    class_fraction_report: HillslopeClassFractionReport
    particle_distribution_report: HillslopeParticleDistributionReport
