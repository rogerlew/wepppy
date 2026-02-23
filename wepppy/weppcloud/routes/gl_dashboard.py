"""Run-scoped deck.gl dashboard stub."""

from __future__ import annotations

import logging
import os
from flask import current_app

from ._common import *  # noqa: F401,F403
from wepppy.nodb.core import Ron, Climate
from wepppy.nodb.mods.omni import Omni
from wepppy.weppcloud.utils.helpers import is_omni_child_run


gl_dashboard_bp = Blueprint("gl_dashboard", __name__)
logger = logging.getLogger(__name__)


def _coerce_bool_setting(value: object, *, default: bool = False) -> bool:
    """Normalize config booleans that may arrive as strings from env-backed settings."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in {"1", "true", "yes", "on"}:
            return True
        if token in {"0", "false", "no", "off"}:
            return False
    return default


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


def _get_omni_contrasts(wd: str):
    """Get list of omni contrasts if the project has the omni mod.

    Returns a list of contrast dicts with 'id', 'name', and 'path' keys, or None if not omni-enabled.
    """
    omni_nodb_path = os.path.join(wd, 'omni.nodb')
    if not os.path.exists(omni_nodb_path):
        return None

    contrasts_dir = os.path.join(wd, '_pups', 'omni', 'contrasts')
    if not os.path.isdir(contrasts_dir):
        return None

    try:
        omni = Omni.getInstance(wd)
        contrast_names = omni.contrast_names or []
    except (OSError, RuntimeError, ValueError):
        logger.warning("gl_dashboard: failed to load omni contrasts for %s", wd, exc_info=True)
        return None

    if not contrast_names:
        return None

    contrasts = []
    for contrast_id, contrast_name in enumerate(contrast_names, start=1):
        if not contrast_name:
            continue
        contrast_path = os.path.join(contrasts_dir, str(contrast_id))
        if not os.path.isdir(contrast_path):
            continue
        marker = os.path.join(contrast_path, 'wepp', 'output', 'interchange', 'README.md')
        if not os.path.exists(marker):
            continue
        contrasts.append({
            'id': contrast_id,
            'name': contrast_name,
            'path': f'_pups/omni/contrasts/{contrast_id}'
        })

    return contrasts if contrasts else None


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
    batch_mode_enabled = _coerce_bool_setting(
        current_app.config.get("GL_DASHBOARD_BATCH_ENABLED", False),
        default=False,
    )
    
    # Check for omni scenarios (skip when viewing omni child runs).
    is_omni_child = is_omni_child_run(runid, wd=wd, pup_relpath=ctx.pup_relpath)
    omni_scenarios = None if is_omni_child else _get_omni_scenarios(wd)
    omni_contrasts = None if is_omni_child else _get_omni_contrasts(wd)

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
    except (OSError, RuntimeError, ValueError):
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
    except (OSError, RuntimeError, TypeError, ValueError):
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
        omni_contrasts=omni_contrasts,
        is_omni_child=is_omni_child,
        mode="run",
        batch=None,
        batch_mode_enabled=batch_mode_enabled,
    )
