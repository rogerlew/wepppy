import importlib
import sys


def _ensure_package(name: str) -> None:
    module = sys.modules.get(name)
    if module is not None and not hasattr(module, "__path__"):
        sys.modules.pop(name, None)
    if name not in sys.modules:
        importlib.import_module(name)


_ensure_package("wepppy.all_your_base")

_LAZY_EXPORTS = {
    "generate_interchange_documentation": (".interchange_documentation", "generate_interchange_documentation"),
    "run_wepp_hillslope_interchange": (".hill_interchange", "run_wepp_hillslope_interchange"),
    "cleanup_hillslope_sources_for_completed_interchange": (
        ".hill_interchange",
        "cleanup_hillslope_sources_for_completed_interchange",
    ),
    "run_wepp_hillslope_ebe_interchange": (".hill_ebe_interchange", "run_wepp_hillslope_ebe_interchange"),
    "run_wepp_hillslope_element_interchange": (
        ".hill_element_interchange",
        "run_wepp_hillslope_element_interchange",
    ),
    "run_wepp_hillslope_loss_interchange": (".hill_loss_interchange", "run_wepp_hillslope_loss_interchange"),
    "run_wepp_hillslope_pass_interchange": (".hill_pass_interchange", "run_wepp_hillslope_pass_interchange"),
    "run_wepp_hillslope_soil_interchange": (".hill_soil_interchange", "run_wepp_hillslope_soil_interchange"),
    "run_wepp_hillslope_wat_interchange": (".hill_wat_interchange", "run_wepp_hillslope_wat_interchange"),
    "run_wepp_watershed_pass_interchange": (".watershed_pass_interchange", "run_wepp_watershed_pass_interchange"),
    "run_wepp_watershed_soil_interchange": (".watershed_soil_interchange", "run_wepp_watershed_soil_interchange"),
    "run_wepp_watershed_ebe_interchange": (".watershed_ebe_interchange", "run_wepp_watershed_ebe_interchange"),
    "run_wepp_watershed_chnwb_interchange": (".watershed_chnwb_interchange", "run_wepp_watershed_chnwb_interchange"),
    "run_wepp_watershed_chanwb_interchange": (".watershed_chanwb_interchange", "run_wepp_watershed_chanwb_interchange"),
    "run_wepp_watershed_chan_interchange": (".watershed_chan_interchange", "run_wepp_watershed_chan_interchange"),
    "run_wepp_watershed_chan_peak_interchange": (
        ".watershed_chan_peak_interchange",
        "run_wepp_watershed_chan_peak_interchange",
    ),
    "chanout_dss_export": (".watershed_chan_peak_interchange", "chanout_dss_export"),
    "run_wepp_watershed_tc_out_interchange": (
        ".watershed_tc_out_interchange",
        "run_wepp_watershed_tc_out_interchange",
    ),
    "totalwatsed_partitioned_dss_export": (
        ".watershed_totalwatsed_export",
        "totalwatsed_partitioned_dss_export",
    ),
    "archive_dss_export_zip": (".watershed_totalwatsed_export", "archive_dss_export_zip"),
    "run_wepp_watershed_loss_interchange": (".watershed_loss_interchange", "run_wepp_watershed_loss_interchange"),
    "run_wepp_watershed_interchange": (".watershed_interchange", "run_wepp_watershed_interchange"),
    "run_totalwatsed3": (".totalwatsed3", "run_totalwatsed3"),
    "INTERCHANGE_VERSION": (".versioning", "INTERCHANGE_VERSION"),
    "schema_with_version": (".versioning", "schema_with_version"),
    "write_version_manifest": (".versioning", "write_version_manifest"),
    "read_version_manifest": (".versioning", "read_version_manifest"),
    "needs_major_refresh": (".versioning", "needs_major_refresh"),
    "remove_incompatible_interchange": (".versioning", "remove_incompatible_interchange"),
}


def __getattr__(name: str):
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    module = importlib.import_module(module_name, __name__)
    value = getattr(module, attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))

__all__ = [
    "generate_interchange_documentation",
    "run_wepp_hillslope_interchange",
    "cleanup_hillslope_sources_for_completed_interchange",
    "run_wepp_hillslope_ebe_interchange",
    "run_wepp_hillslope_element_interchange",
    "run_wepp_hillslope_loss_interchange",
    "run_wepp_hillslope_pass_interchange",
    "run_wepp_hillslope_soil_interchange",
    "run_wepp_hillslope_wat_interchange",
    "run_wepp_watershed_pass_interchange",
    "run_wepp_watershed_soil_interchange",
    "run_wepp_watershed_ebe_interchange",
    "run_wepp_watershed_chnwb_interchange",
    "run_wepp_watershed_chanwb_interchange",
    "run_wepp_watershed_chan_interchange",
    "run_wepp_watershed_chan_peak_interchange",
    "run_wepp_watershed_tc_out_interchange",
    "chanout_dss_export",
    "totalwatsed_partitioned_dss_export",
    "archive_dss_export_zip",
    "run_wepp_watershed_loss_interchange",
    "run_wepp_watershed_interchange",
    "run_totalwatsed3",
    "INTERCHANGE_VERSION",
    "schema_with_version",
    "write_version_manifest",
    "read_version_manifest",
    "needs_major_refresh",
    "remove_incompatible_interchange",
]
