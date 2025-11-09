"""High-level re-exports for report generators exposed throughout WEPPcloud."""

from .average_annuals_by_landuse import AverageAnnualsByLanduseReport
from .channel_watbal import ChannelWatbalReport
from .frq_flood import FrqFloodReport
from .harness import ReportHarness
from .helpers import (
    ReportCacheManager,
    ReportQueryContext,
    extract_units_from_schema,
)
from .hillslope_watbal import HillslopeWatbalReport
from .report_base import ReportBase
from .return_periods import ReturnPeriodDataset, ReturnPeriods, refresh_return_period_events
from .sediment_characteristics import SedimentCharacteristics
from .sediment_channel_distribution_report import (
    ChannelClassFractionReport,
    ChannelParticleDistributionReport,
    ChannelSedimentDistribution,
)
from .sediment_class_info_report import SedimentClassInfoReport
from .sediment_hillslope_distribution_report import (
    HillslopeClassFractionReport,
    HillslopeParticleDistributionReport,
    HillslopeSedimentDistribution,
)
from .summary import ChannelSummaryReport, HillSummaryReport, OutletSummaryReport
from .total_watbal import TotalWatbalReport

__all__ = [
    "AverageAnnualsByLanduseReport",
    "ChannelWatbalReport",
    "FrqFloodReport",
    "HillslopeWatbalReport",
    "ReturnPeriods",
    "ReturnPeriodDataset",
    "refresh_return_period_events",
    "ChannelSummaryReport",
    "HillSummaryReport",
    "OutletSummaryReport",
    "ReportBase",
    "ReportCacheManager",
    "ReportQueryContext",
    "extract_units_from_schema",
    "ReportHarness",
    "TotalWatbalReport",
    "SedimentCharacteristics",
    "SedimentClassInfoReport",
    "ChannelSedimentDistribution",
    "ChannelClassFractionReport",
    "ChannelParticleDistributionReport",
    "HillslopeSedimentDistribution",
    "HillslopeClassFractionReport",
    "HillslopeParticleDistributionReport",
    "SedimentDelivery",
    "AverageAnnualsByLanduse",
    "ChannelWatbal",
    "FrqFlood",
    "HillslopeWatbal",
    "ChannelSummary",
    "HillSummary",
    "OutletSummary",
    "TotalWatbal",
]

# Backwards-compatible aliases for downstream callers that still rely on the
# legacy names. These remain intentionally undocumented and will be removed in
# a future major release.
AverageAnnualsByLanduse = AverageAnnualsByLanduseReport
ChannelWatbal = ChannelWatbalReport
FrqFlood = FrqFloodReport
HillslopeWatbal = HillslopeWatbalReport
ChannelSummary = ChannelSummaryReport
HillSummary = HillSummaryReport
OutletSummary = OutletSummaryReport
TotalWatbal = TotalWatbalReport

# Historically SedimentDelivery re-exported SedimentCharacteristics; keep the
# alias so existing CLI scripts continue to function without modification.
SedimentDelivery = SedimentCharacteristics
