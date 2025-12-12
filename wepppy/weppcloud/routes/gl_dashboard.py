"""Run-scoped deck.gl dashboard stub."""

from __future__ import annotations

import os
from flask import current_app

from ._common import *  # noqa: F401,F403
from wepppy.nodb.core import Ron, Climate


gl_dashboard_bp = Blueprint("gl_dashboard", __name__)


def _get_omni_scenarios(wd: str):
    """Get list of omni scenarios if the project has the omni mod.
    
    Returns a list of scenario dicts with 'name' and 'path' keys, or None if not omni-enabled.
    """
    omni_nodb_path = os.path.join(wd, 'omni.nodb')
    if not os.path.exists(omni_nodb_path):
        return None
    
    scenarios_dir = os.path.join(wd, '_pups', 'omni', 'scenarios')
    if not os.path.isdir(scenarios_dir):
        return None
    
    scenarios = []
    for name in sorted(os.listdir(scenarios_dir)):
        scenario_path = os.path.join(scenarios_dir, name)
        if os.path.isdir(scenario_path):
            # Check for valid scenario by presence of wepp.nodb
            if os.path.exists(os.path.join(scenario_path, 'wepp.nodb')):
                scenarios.append({
                    'name': name,
                    'path': f'_pups/omni/scenarios/{name}'
                })
    
    return scenarios if scenarios else None


@gl_dashboard_bp.route(
    "/runs/<string:runid>/<config>/gl-dashboard", strict_slashes=False
)
def gl_dashboard(runid: str, config: str):
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    site_prefix = current_app.config.get("SITE_PREFIX", "/weppcloud")
    tile_url = current_app.config.get(
        "GL_DASHBOARD_BASE_TILE_URL", "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png"
    )
    
    # Check for omni scenarios
    omni_scenarios = _get_omni_scenarios(wd)

    # Get map extent/center/zoom from Ron if available
    map_extent = None
    map_center = None
    map_zoom = None
    try:
        ron = Ron.getInstance(wd)
        if ron.map is not None:
            map_extent = ron.map.extent  # [west, south, east, north]
            map_center = ron.map.center  # [longitude, latitude]
            map_zoom = ron.map.zoom
    except Exception:
        pass

    # Get climate context for year slider
    climate_context = None
    try:
        climate = Climate.getInstance(wd)
        has_observed = climate.has_observed
        if has_observed:
            # Observed climate: use calendar years
            start_year = climate.observed_start_year
            end_year = climate.observed_end_year
            # Normalize to int if valid
            if isinstance(start_year, str) and start_year.strip() == '':
                start_year = None
            if isinstance(end_year, str) and end_year.strip() == '':
                end_year = None
            if start_year is not None:
                start_year = int(start_year)
            if end_year is not None:
                end_year = int(end_year)
        else:
            # CLIGEN/stochastic: years start at 1
            input_years = climate.input_years
            start_year = 1
            end_year = input_years if input_years else 100
        
        climate_context = {
            'hasObserved': bool(has_observed),
            'startYear': start_year,
            'endYear': end_year,
        }
    except Exception:
        pass

    return render_template(
        "gl_dashboard.htm",
        runid=runid,
        config=config,
        site_prefix=site_prefix,
        tile_url=tile_url,
        map_extent=map_extent,
        map_center=map_center,
        map_zoom=map_zoom,
        climate_context=climate_context,
        omni_scenarios=omni_scenarios,
    )
