from __future__ import annotations

import importlib
import sys
import warnings

from wepppy.wepp.reports import *  # noqa: F401,F403

_DEPRECATED_MODULES = {
    "wepppy.wepp.stats.average_annuals_by_landuse": "wepppy.wepp.reports.average_annuals_by_landuse",
    "wepppy.wepp.stats.channel_watbal": "wepppy.wepp.reports.channel_watbal",
    "wepppy.wepp.stats.frq_flood": "wepppy.wepp.reports.frq_flood",
    "wepppy.wepp.stats.hillslope_watbal": "wepppy.wepp.reports.hillslope_watbal",
    "wepppy.wepp.stats.loss_channel_report": "wepppy.wepp.reports.loss_channel_report",
    "wepppy.wepp.stats.loss_hill_report": "wepppy.wepp.reports.loss_hill_report",
    "wepppy.wepp.stats.loss_outlet_report": "wepppy.wepp.reports.loss_outlet_report",
    "wepppy.wepp.stats.report_base": "wepppy.wepp.reports.report_base",
    "wepppy.wepp.stats.return_periods": "wepppy.wepp.reports.return_periods",
    "wepppy.wepp.stats.row_data": "wepppy.wepp.reports.row_data",
    "wepppy.wepp.stats.sediment_channel_distribution_report": "wepppy.wepp.reports.sediment_channel_distribution_report",
    "wepppy.wepp.stats.sediment_characteristics": "wepppy.wepp.reports.sediment_characteristics",
    "wepppy.wepp.stats.sediment_class_info_report": "wepppy.wepp.reports.sediment_class_info_report",
    "wepppy.wepp.stats.sediment_hillslope_distribution_report": "wepppy.wepp.reports.sediment_hillslope_distribution_report",
    "wepppy.wepp.stats.summary": "wepppy.wepp.reports.summary",
    "wepppy.wepp.stats.total_watbal": "wepppy.wepp.reports.total_watbal",
}


def _install_redirects() -> None:
    for old, new in _DEPRECATED_MODULES.items():
        if old in sys.modules:
            continue
        module = importlib.import_module(new)
        sys.modules[old] = module

        # Provide legacy attribute names when available.
        legacy_name = old.rsplit(".", 1)[-1]
        candidate = None
        camel_name = ''.join(part.capitalize() for part in legacy_name.split('_')) + "Report"
        if hasattr(module, camel_name):
            candidate = getattr(module, camel_name)
        elif hasattr(module, f"{legacy_name}Report"):
            candidate = getattr(module, f"{legacy_name}Report")
        if candidate is not None and not hasattr(module, legacy_name):
            setattr(module, legacy_name, candidate)


_install_redirects()

warnings.warn(
    "wepppy.wepp.stats is deprecated; import from wepppy.wepp.reports instead",
    DeprecationWarning,
    stacklevel=2,
)
