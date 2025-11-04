from flask import jsonify
from wepppy.weppcloud.routes import *


def _register(app, blueprint):
    if blueprint is not None:
        app.register_blueprint(blueprint)


def register_blueprints(app):

    if hasattr(app, "route"):
        @app.route('/health')
        def health():
            return jsonify('OK')

    _register(app, rq_api_bp)
    _register(app, rq_jobinfo_bp)
    _register(app, security_logging_bp)
    _register(app, security_oauth_bp)
    _register(app, security_ui_bp)
    _register(app, unitizer_bp)
    _register(app, map_bp)
    _register(app, user_bp)
    _register(app, landuse_bp)
    _register(app, soils_bp)
    _register(app, climate_bp)
    _register(app, rhem_bp)
    _register(app, treatments_bp)
    _register(app, watar_bp)
    _register(app, watershed_bp)
    _register(app, wepp_bp)
    _register(app, run_0_bp)
    _register(app, weppcloud_site_bp)
    _register(app, admin_bp)
    _register(app, archive_bp)
    _register(app, command_bar_bp)
    _register(app, agent_bp)
    _register(app, debris_flow_bp)
    _register(app, disturbed_bp)
    _register(app, export_bp)
    _register(app, geodata_bp)
    _register(app, huc_fire_bp)
    _register(app, diff_bp)
    _register(app, fork_bp)
    _register(app, observed_bp)
    _register(app, omni_bp)
    _register(app, pivottable_bp)
    _register(app, project_bp)
    _register(app, jsoncrack_bp)
    _register(app, rangeland_bp)
    _register(app, rangeland_cover_bp)
    _register(app, weppcloudr_bp)
    _register(app, path_ce_bp)
    _register(app, recorder_bp)
    _register(app, locations_bp)
    _register(app, rq_job_dashboard_bp)
    _register(app, readme_bp)
    _register(app, usersum_bp)
    _register(app, stats_bp)
    _register(app, combined_watershed_viewer_bp)
    _register(app, batch_runner_bp)
    _register(app, interchange_bp)
    _register(app, ui_showcase_bp)
    if app.config.get("TEST_SUPPORT_ENABLED") and 'test_bp' in globals():
        if test_bp is not None:
            app.register_blueprint(test_bp)
