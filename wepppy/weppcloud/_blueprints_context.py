from flask import jsonify
import wepppy.weppcloud.routes as routes


_BLUEPRINT_ATTRS = [
    "rq_api_bp",
    "rq_jobinfo_bp",
    "security_logging_bp",
    "security_oauth_bp",
    "security_ui_bp",
    "unitizer_bp",
    "map_bp",
    "user_bp",
    "landuse_bp",
    "soils_bp",
    "climate_bp",
    "rhem_bp",
    "treatments_bp",
    "watar_bp",
    "watershed_bp",
    "wepp_bp",
    "run_0_bp",
    "weppcloud_site_bp",
    "admin_bp",
    "archive_bp",
    "command_bar_bp",
    "agent_bp",
    "run_sync_dashboard_bp",
    "debris_flow_bp",
    "disturbed_bp",
    "export_bp",
    "geodata_bp",
    "huc_fire_bp",
    "diff_bp",
    "fork_bp",
    "observed_bp",
    "omni_bp",
    "gl_dashboard_bp",
    "pivottable_bp",
    "project_bp",
    "jsoncrack_bp",
    "rangeland_bp",
    "rangeland_cover_bp",
    "weppcloudr_bp",
    "path_ce_bp",
    "recorder_bp",
    "locations_bp",
    "rq_job_dashboard_bp",
    "readme_bp",
    "usersum_bp",
    "stats_bp",
    "combined_watershed_viewer_bp",
    "batch_runner_bp",
    "interchange_bp",
    "ui_showcase_bp",
]


def _register(app, blueprint):
    if blueprint is not None:
        app.register_blueprint(blueprint)


def _register_from_routes(app, name: str):
    _register(app, getattr(routes, name, None))


def register_blueprints(app):

    if hasattr(app, "route"):
        @app.route('/health')
        def health():
            return jsonify('OK')

    for attr in _BLUEPRINT_ATTRS:
        _register_from_routes(app, attr)

    if app.config.get("TEST_SUPPORT_ENABLED"):
        _register_from_routes(app, "test_bp")
