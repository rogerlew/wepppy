"""Run-scoped deck.gl dashboard stub."""

from __future__ import annotations

from flask import current_app

from ._common import *  # noqa: F401,F403


gl_dashboard_bp = Blueprint("gl_dashboard", __name__)


@gl_dashboard_bp.route(
    "/runs/<string:runid>/<config>/gl-dashboard", strict_slashes=False
)
def gl_dashboard(runid: str, config: str):
    authorize(runid, config)
    load_run_context(runid, config)

    site_prefix = current_app.config.get("SITE_PREFIX", "/weppcloud")
    tile_url = current_app.config.get(
        "GL_DASHBOARD_BASE_TILE_URL", "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png"
    )

    return render_template(
        "gl_dashboard.htm",
        runid=runid,
        config=config,
        site_prefix=site_prefix,
        tile_url=tile_url,
    )
