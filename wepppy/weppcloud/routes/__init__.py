
from ._run_context import register_run_context_preprocessor

from .nodb_api.climate_bp import climate_bp
from .nodb_api.debris_flow_bp import debris_flow_bp
from .nodb_api.disturbed_bp import disturbed_bp
from .nodb_api.landuse_bp import landuse_bp
from .nodb_api.observed_bp import observed_bp
from .nodb_api.omni_bp import omni_bp
from .nodb_api.rangeland_bp import rangeland_bp
from .nodb_api.rangeland_cover_bp import rangeland_cover_bp
from .nodb_api.rhem_bp import rhem_bp
from .nodb_api.treatments_bp import treatments_bp
from .nodb_api.unitizer_bp import unitizer_bp
from .nodb_api.watar_bp import watar_bp
from .nodb_api.watershed_bp import watershed_bp
from .nodb_api.wepp_bp import wepp_bp

from .weppcloud_site import weppcloud_site_bp
from .admin import admin_bp
from .archive_dashboard import archive_bp
from .combined_watershed_viewer import combined_watershed_viewer_bp
from .command_bar import command_bar_bp
from .export import export_bp
from .fork_console import fork_bp
from .diff import diff_bp
from .geodata import geodata_bp
from .huc_fire import huc_fire_bp
from .map import map_bp
from .pivottable import pivottable_bp
from .project import project_bp
from .jsoncrack import jsoncrack_bp
from .readme_md import readme_bp
from .usersum import usersum_bp
from .soils import soils_bp
from .user import user_bp
from .locations import locations_bp
from .weppcloudr import weppcloudr_bp
from .rq.api.jobinfo import rq_jobinfo_bp
from .rq.api.api import rq_api_bp
from .rq.job_dashboard.routes import rq_job_dashboard_bp
from .stats import stats_bp
from .run_0 import run_0_bp
from ._security import security_logging_bp, security_ui_bp

_RUN_CONTEXT_BLUEPRINTS = dict.fromkeys([
    admin_bp,
    archive_bp,
    climate_bp,
    command_bar_bp,
    debris_flow_bp,
    diff_bp,
    disturbed_bp,
    export_bp,
    geodata_bp,
    huc_fire_bp,
    jsoncrack_bp,
    landuse_bp,
    map_bp,
    observed_bp,
    omni_bp,
    pivottable_bp,
    project_bp,
    rangeland_bp,
    rangeland_cover_bp,
    readme_bp,
    rhem_bp,
    run_0_bp,
    soils_bp,
    stats_bp,
    treatments_bp,
    unitizer_bp,
    watar_bp,
    watershed_bp,
    wepp_bp,
    weppcloudr_bp,
    rq_api_bp,
    rq_jobinfo_bp,
    rq_job_dashboard_bp,
])

for _bp in _RUN_CONTEXT_BLUEPRINTS:
    register_run_context_preprocessor(_bp)


__all__ = [
    'weppcloud_site_bp', 
    'admin_bp',
    'archive_bp',
    'climate_bp',
    'combined_watershed_viewer_bp',
    'command_bar_bp',
    'debris_flow_bp',
    'disturbed_bp',
    'export_bp',
    'fork_bp',
    'diff_bp',
    'geodata_bp',
    'landuse_bp',
    'map_bp',
    'observed_bp',
    'omni_bp',
    'pivottable_bp',
    'project_bp',
    'jsoncrack_bp',
    'rangeland_bp',
    'rangeland_cover_bp',
    'readme_bp',
    'usersum_bp',
    'rhem_bp',
    'soils_bp',
    'treatments_bp',
    'unitizer_bp',
    'user_bp',
    'watar_bp',
    'watershed_bp',
    'wepp_bp',
    'locations_bp',
    'weppcloudr_bp',
    'rq_jobinfo_bp',
    'rq_api_bp',
    'rq_job_dashboard_bp',
    'stats_bp',
    'run_0_bp',
    'security_logging_bp',
    'security_ui_bp'
]
