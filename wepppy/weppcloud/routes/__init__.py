
import importlib
import sys

if 'wepppy.all_your_base' not in sys.modules:
    importlib.import_module('wepppy.all_your_base')

from ._run_context import register_run_context_preprocessor

try:
    from .nodb_api.climate_bp import climate_bp
except ImportError:
    climate_bp = None  # optional blueprint
try:
    from .nodb_api.debris_flow_bp import debris_flow_bp
except ImportError:
    debris_flow_bp = None  # optional blueprint
try:
    from .nodb_api.disturbed_bp import disturbed_bp
except ImportError:
    disturbed_bp = None  # optional blueprint
try:
    from .nodb_api.landuse_bp import landuse_bp
except ImportError:
    landuse_bp = None  # optional blueprint
try:
    from .nodb_api.interchange_bp import interchange_bp
except ImportError:
    interchange_bp = None  # optional blueprint
try:
    from .nodb_api.observed_bp import observed_bp
except ImportError:
    observed_bp = None  # optional blueprint
try:
    from .nodb_api.omni_bp import omni_bp
except ImportError:
    omni_bp = None  # optional blueprint
try:
    from .nodb_api.path_ce_bp import path_ce_bp
except ImportError:
    path_ce_bp = None  # optional blueprint
try:
    from .nodb_api.project_bp import project_bp
except ImportError:
    project_bp = None  # optional blueprint
try:
    from .nodb_api.rangeland_bp import rangeland_bp
except ImportError:
    rangeland_bp = None  # optional blueprint
try:
    from .nodb_api.rangeland_cover_bp import rangeland_cover_bp
except ImportError:
    rangeland_cover_bp = None  # optional blueprint
try:
    from .nodb_api.rhem_bp import rhem_bp
except ImportError:
    rhem_bp = None  # optional blueprint
try:
    from .nodb_api.soils_bp import soils_bp
except ImportError:
    soils_bp = None  # optional blueprint
try:
    from .nodb_api.treatments_bp import treatments_bp
except ImportError:
    treatments_bp = None  # optional blueprint
try:
    from .nodb_api.unitizer_bp import unitizer_bp
except ImportError:
    unitizer_bp = None  # optional blueprint
try:
    from .nodb_api.watar_bp import watar_bp
except ImportError:
    watar_bp = None  # optional blueprint
try:
    from .nodb_api.watershed_bp import watershed_bp
except ImportError:
    watershed_bp = None  # optional blueprint
try:
    from .nodb_api.wepp_bp import wepp_bp
except ImportError:
    wepp_bp = None  # optional blueprint

from .weppcloud_site import weppcloud_site_bp
from .admin import admin_bp
from .archive_dashboard import archive_bp
from .combined_watershed_viewer import combined_watershed_viewer_bp
from .command_bar import command_bar_bp
from .agent import agent_bp
from .export import export_bp
from .fork_console import fork_bp
from .diff import diff_bp
from .geodata import geodata_bp
from .huc_fire import huc_fire_bp
from .map import map_bp
from .pivottable import pivottable_bp
from .jsoncrack import jsoncrack_bp
from .readme_md import readme_bp
from .usersum import usersum_bp
from .batch_runner import batch_runner_bp
from .user import user_bp
from .locations import locations_bp
from .weppcloudr import weppcloudr_bp
from .rq.api.jobinfo import rq_jobinfo_bp
from .rq.api.api import rq_api_bp
from .rq.job_dashboard.routes import rq_job_dashboard_bp
from .stats import stats_bp
from .run_0 import run_0_bp
from ._security import security_logging_bp, security_oauth_bp, security_ui_bp
from .ui_showcase import ui_showcase_bp
from .recorder import recorder_bp
try:
    from .test_bp import test_bp
except ImportError:
    test_bp = None

_RUN_CONTEXT_BLUEPRINTS = dict.fromkeys([
    admin_bp,
    archive_bp,
    climate_bp,
    command_bar_bp,
    agent_bp,
    interchange_bp,
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
    path_ce_bp,
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
    if _bp is not None:
        register_run_context_preprocessor(_bp)


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
    'export_bp',
    'fork_bp',
    'diff_bp',
    'geodata_bp',
    'huc_fire_bp',
    'landuse_bp',
    'map_bp',
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
    'security_ui_bp',
    'security_oauth_bp',
    'recorder_bp',
    'ui_showcase_bp',
    'test_bp',
]
