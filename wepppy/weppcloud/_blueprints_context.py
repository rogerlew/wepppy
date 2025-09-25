from flask import jsonify
from wepppy.weppcloud.routes.browse import browse_bp
from wepppy.weppcloud.routes.weppcloud_site import weppcloud_site_bp
from wepppy.weppcloud.routes.admin import admin_bp
from wepppy.weppcloud.routes.archive import archive_bp
from wepppy.weppcloud.routes.climate import climate_bp
from wepppy.weppcloud.routes.combined_watershed_viewer import combined_watershed_viewer_bp
from wepppy.weppcloud.routes.command_bar import command_bar_bp
from wepppy.weppcloud.routes.debris_flow import debris_flow_bp
from wepppy.weppcloud.routes.disturbed import disturbed_bp
from wepppy.weppcloud.routes.download import download_bp
from wepppy.weppcloud.routes.export import export_bp
from wepppy.weppcloud.routes.fork import fork_bp
from wepppy.weppcloud.routes.wepprepr import repr_bp
from wepppy.weppcloud.routes.diff import diff_bp
from wepppy.weppcloud.routes.gdalinfo import gdalinfo_bp
from wepppy.weppcloud.routes.geodata import geodata_bp
from wepppy.weppcloud.routes.landuse import landuse_bp
from wepppy.weppcloud.routes.map import map_bp
from wepppy.weppcloud.routes.observed import observed_bp
from wepppy.weppcloud.routes.omni import omni_bp
from wepppy.weppcloud.routes.pivottable import pivottable_bp
from wepppy.weppcloud.routes.project import project_bp
from wepppy.weppcloud.routes.jsoncrack import jsoncrack_bp
from wepppy.weppcloud.routes.rangeland import rangeland_bp
from wepppy.weppcloud.routes.rangeland_cover import rangeland_cover_bp
from wepppy.weppcloud.routes.readme import readme_bp
from wepppy.weppcloud.routes.rhem import rhem_bp
from wepppy.weppcloud.routes.soils import soils_bp
from wepppy.weppcloud.routes.treatments import treatments_bp
from wepppy.weppcloud.routes.unitizer import unitizer_bp
from wepppy.weppcloud.routes.user import user_bp
from wepppy.weppcloud.routes.watar import watar_bp
from wepppy.weppcloud.routes.watershed import watershed_bp
from wepppy.weppcloud.routes.wepp import wepp_bp
from wepppy.weppcloud.routes.locations import locations_bp
from wepppy.weppcloud.routes.weppcloudr import weppcloudr_bp
from wepppy.weppcloud.routes.rq.api.jobinfo import rq_jobinfo_bp
from wepppy.weppcloud.routes.rq.api.api import rq_api_bp
from wepppy.weppcloud.routes.rq.job_dashboard.routes import rq_job_dashboard_bp
from wepppy.weppcloud.routes.stats import stats_bp
from wepppy.weppcloud.routes.run_0 import run_0_bp
from wepppy.weppcloud.routes._security import security_logging_bp, security_ui_bp

def register_blueprints(app):

    @app.route('/health')
    def health():
        return jsonify('OK')

    app.register_blueprint(rq_api_bp)
    app.register_blueprint(download_bp)
    app.register_blueprint(browse_bp)
    app.register_blueprint(rq_jobinfo_bp)
    app.register_blueprint(security_logging_bp)
    app.register_blueprint(security_ui_bp)
    app.register_blueprint(unitizer_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(landuse_bp)
    app.register_blueprint(soils_bp)
    app.register_blueprint(climate_bp)
    app.register_blueprint(rhem_bp)
    app.register_blueprint(treatments_bp)
    app.register_blueprint(watar_bp)
    app.register_blueprint(watershed_bp)
    app.register_blueprint(wepp_bp)
    app.register_blueprint(run_0_bp)
    app.register_blueprint(weppcloud_site_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(archive_bp)
    app.register_blueprint(command_bar_bp)
    app.register_blueprint(debris_flow_bp)
    app.register_blueprint(disturbed_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(gdalinfo_bp)
    app.register_blueprint(geodata_bp)
    app.register_blueprint(repr_bp)
    app.register_blueprint(diff_bp)
    app.register_blueprint(fork_bp)
    app.register_blueprint(observed_bp)
    app.register_blueprint(omni_bp)
    app.register_blueprint(pivottable_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(jsoncrack_bp)
    app.register_blueprint(rangeland_bp)
    app.register_blueprint(rangeland_cover_bp)
    app.register_blueprint(weppcloudr_bp)
    app.register_blueprint(locations_bp)
    app.register_blueprint(rq_job_dashboard_bp)
    app.register_blueprint(readme_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(combined_watershed_viewer_bp)
