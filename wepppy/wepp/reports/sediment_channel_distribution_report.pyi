from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable

from .report_base import ReportBase
from .row_data import RowData

__all__ = [
    "ChannelClassFractionReport",
    "ChannelParticleDistributionReport",
    "ChannelSedimentDistribution",
]


class ChannelClassFractionReport(ReportBase):
    def __init__(self, rows: Iterable[OrderedDict[str, float]]) -> None: ...

    def __iter__(self) -> Iterable[RowData]: ...


class ChannelParticleDistributionReport(ReportBase):
    def __init__(self, rows: Iterable[OrderedDict[str, float]]) -> None: ...

    def __iter__(self) -> Iterable[RowData]: ...


class ChannelSedimentDistribution:
    total_discharge_tonne: float
    class_fraction_report: ChannelClassFractionReport
    particle_distribution_report: ChannelParticleDistributionReport
