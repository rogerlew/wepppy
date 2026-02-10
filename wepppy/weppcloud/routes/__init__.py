from __future__ import annotations

import importlib
import sys
from typing import Any, List

# Keep this import eager: many routes assume the all_your_base package is present
# (and tests stub it defensively). Avoid importing the entire routes tree here.
if "wepppy.all_your_base" not in sys.modules:
    importlib.import_module("wepppy.all_your_base")

from ._run_context import register_run_context_preprocessor

_BLUEPRINT_CACHE: dict[str, Any] = {}

_BLUEPRINT_IMPORTS: dict[str, tuple[str, str]] = {
    # nodb_api blueprints (optional)
    "climate_bp": (".nodb_api.climate_bp", "climate_bp"),
    "debris_flow_bp": (".nodb_api.debris_flow_bp", "debris_flow_bp"),
    "disturbed_bp": (".nodb_api.disturbed_bp", "disturbed_bp"),
    "landuse_bp": (".nodb_api.landuse_bp", "landuse_bp"),
    "interchange_bp": (".nodb_api.interchange_bp", "interchange_bp"),
    "observed_bp": (".nodb_api.observed_bp", "observed_bp"),
    "omni_bp": (".nodb_api.omni_bp", "omni_bp"),
    "path_ce_bp": (".nodb_api.path_ce_bp", "path_ce_bp"),
    "project_bp": (".nodb_api.project_bp", "project_bp"),
    "rangeland_bp": (".nodb_api.rangeland_bp", "rangeland_bp"),
    "rangeland_cover_bp": (".nodb_api.rangeland_cover_bp", "rangeland_cover_bp"),
    "rhem_bp": (".nodb_api.rhem_bp", "rhem_bp"),
    "soils_bp": (".nodb_api.soils_bp", "soils_bp"),
    "treatments_bp": (".nodb_api.treatments_bp", "treatments_bp"),
    "unitizer_bp": (".nodb_api.unitizer_bp", "unitizer_bp"),
    "watar_bp": (".nodb_api.watar_bp", "watar_bp"),
    "watershed_bp": (".nodb_api.watershed_bp", "watershed_bp"),
    "wepp_bp": (".nodb_api.wepp_bp", "wepp_bp"),
    # top-level / misc blueprints
    "weppcloud_site_bp": (".weppcloud_site", "weppcloud_site_bp"),
    "admin_bp": (".admin", "admin_bp"),
    "archive_bp": (".archive_dashboard", "archive_bp"),
    "combined_watershed_viewer_bp": (".combined_watershed_viewer", "combined_watershed_viewer_bp"),
    "command_bar_bp": (".command_bar", "command_bar_bp"),
    "agent_bp": (".agent", "agent_bp"),
    "fork_bp": (".fork_console", "fork_bp"),
    "diff_bp": (".diff", "diff_bp"),
    "geodata_bp": (".geodata", "geodata_bp"),
    "gl_dashboard_bp": (".gl_dashboard", "gl_dashboard_bp"),
    "storm_event_analyzer_bp": (".storm_event_analyzer", "storm_event_analyzer_bp"),
    "huc_fire_bp": (".huc_fire", "huc_fire_bp"),
    "pivottable_bp": (".pivottable", "pivottable_bp"),
    "jsoncrack_bp": (".jsoncrack", "jsoncrack_bp"),
    "readme_bp": (".readme_md", "readme_bp"),
    "usersum_bp": (".usersum", "usersum_bp"),
    "batch_runner_bp": (".batch_runner", "batch_runner_bp"),
    "user_bp": (".user", "user_bp"),
    "run_sync_dashboard_bp": (".run_sync_dashboard", "run_sync_dashboard_bp"),
    "locations_bp": (".locations", "locations_bp"),
    "weppcloudr_bp": (".weppcloudr", "weppcloudr_bp"),
    "rq_job_dashboard_bp": (".rq.job_dashboard.routes", "rq_job_dashboard_bp"),
    "stats_bp": (".stats", "stats_bp"),
    "run_0_bp": (".run_0", "run_0_bp"),
    "security_logging_bp": ("._security", "security_logging_bp"),
    "security_ui_bp": ("._security", "security_ui_bp"),
    "security_oauth_bp": ("._security", "security_oauth_bp"),
    "ui_showcase_bp": (".ui_showcase", "ui_showcase_bp"),
    "recorder_bp": (".recorder_bp", "recorder_bp"),
    "bootstrap_bp": (".bootstrap", "bootstrap_bp"),
    # Test support blueprint (optional)
    "test_bp": (".test_bp", "test_bp"),
}

_OPTIONAL_BLUEPRINT_ATTRS = {
    "climate_bp",
    "debris_flow_bp",
    "disturbed_bp",
    "landuse_bp",
    "interchange_bp",
    "observed_bp",
    "omni_bp",
    "path_ce_bp",
    "project_bp",
    "rangeland_bp",
    "rangeland_cover_bp",
    "rhem_bp",
    "soils_bp",
    "treatments_bp",
    "unitizer_bp",
    "watar_bp",
    "watershed_bp",
    "wepp_bp",
    "test_bp",
}

_RUN_CONTEXT_BLUEPRINT_ATTRS = {
    "admin_bp",
    "archive_bp",
    "climate_bp",
    "command_bar_bp",
    "agent_bp",
    "interchange_bp",
    "debris_flow_bp",
    "diff_bp",
    "disturbed_bp",
    "gl_dashboard_bp",
    "storm_event_analyzer_bp",
    "geodata_bp",
    "huc_fire_bp",
    "jsoncrack_bp",
    "landuse_bp",
    "observed_bp",
    "omni_bp",
    "path_ce_bp",
    "pivottable_bp",
    "project_bp",
    "rangeland_bp",
    "rangeland_cover_bp",
    "readme_bp",
    "rhem_bp",
    "run_0_bp",
    "bootstrap_bp",
    "soils_bp",
    "stats_bp",
    "treatments_bp",
    "unitizer_bp",
    "watar_bp",
    "watershed_bp",
    "wepp_bp",
    "weppcloudr_bp",
    "rq_job_dashboard_bp",
}


def _load_blueprint(name: str) -> Any:
    module_name, attr_name = _BLUEPRINT_IMPORTS[name]
    module = importlib.import_module(module_name, __name__)
    bp = getattr(module, attr_name)
    if bp is not None and name in _RUN_CONTEXT_BLUEPRINT_ATTRS:
        register_run_context_preprocessor(bp)
    return bp


def __getattr__(name: str) -> Any:
    if name in _BLUEPRINT_IMPORTS:
        if name in _BLUEPRINT_CACHE:
            value = _BLUEPRINT_CACHE[name]
            globals()[name] = value
            return value
        try:
            value = _load_blueprint(name)
        except ImportError:
            if name in _OPTIONAL_BLUEPRINT_ATTRS:
                value = None
            else:
                raise
        _BLUEPRINT_CACHE[name] = value
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def resolve_blueprint(name: str) -> Any:
    """Resolve a blueprint export by attribute name.

    Prefer this over ``getattr(routes, name)`` because importing submodules like
    ``wepppy.weppcloud.routes.recorder_bp`` can overwrite the package attribute
    with the submodule object, masking the blueprint variable.
    """
    if name not in _BLUEPRINT_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return __getattr__(name)


def __dir__() -> List[str]:
    return sorted(set(globals()) | set(__all__))


__all__ = [
    'weppcloud_site_bp', 
    'admin_bp',
    'archive_bp',
    'climate_bp',
    'combined_watershed_viewer_bp',
    'command_bar_bp',
    'agent_bp',
    'debris_flow_bp',
    'disturbed_bp',
    'interchange_bp',
    'fork_bp',
    'diff_bp',
    'gl_dashboard_bp',
    'storm_event_analyzer_bp',
    'geodata_bp',
    'huc_fire_bp',
    'landuse_bp',
    'observed_bp',
    'omni_bp',
    'path_ce_bp',
    'pivottable_bp',
    'project_bp',
    'jsoncrack_bp',
    'rangeland_bp',
    'rangeland_cover_bp',
    'readme_bp',
    'usersum_bp',
    'batch_runner_bp',
    'rhem_bp',
    'soils_bp',
    'treatments_bp',
    'unitizer_bp',
    'user_bp',
    'run_sync_dashboard_bp',
    'watar_bp',
    'watershed_bp',
    'wepp_bp',
    'locations_bp',
    'weppcloudr_bp',
    'rq_job_dashboard_bp',
    'stats_bp',
    'run_0_bp',
    'security_logging_bp',
    'security_ui_bp',
    'security_oauth_bp',
    'recorder_bp',
    'ui_showcase_bp',
    'bootstrap_bp',
    'test_bp',
]
