from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Iterable, Sequence

from wepppy.wepp.stats.report_base import ReportBase
from wepppy.wepp.stats.row_data import RowData


class HillslopeClassFractionReport(ReportBase):
    """Distribution of hillslope sediment delivery by particle class."""

    def __init__(self, rows: Iterable[OrderedDict[str, float]]):
        self._rows = list(rows)
        self.header = ["Class", "Fraction (ratio)", "Sediment Delivery (tonne/yr)"]

    def __iter__(self) -> Iterable[RowData]:
        for row in self._rows:
            yield RowData(row)


class HillslopeParticleDistributionReport(ReportBase):
    """Distribution of hillslope sediment delivery by particle type."""

    def __init__(self, rows: Iterable[OrderedDict[str, float]]):
        self._rows = list(rows)
        self.header = ["Particle Type", "Fraction (ratio)", "Sediment Delivery (tonne/yr)"]

    def __iter__(self) -> Iterable[RowData]:
        for row in self._rows:
            yield RowData(row)


@dataclass(slots=True)
class HillslopeSedimentDistribution:
    total_delivery_tonne: float
    class_fraction_report: HillslopeClassFractionReport
    particle_distribution_report: HillslopeParticleDistributionReport


__all__: Sequence[str] = [
    "HillslopeClassFractionReport",
    "HillslopeParticleDistributionReport",
    "HillslopeSedimentDistribution",
]
