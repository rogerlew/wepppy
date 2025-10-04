"""Routes for map blueprint extracted from app.py."""

from ._common import *  # noqa: F401,F403

from wepppy.nodb.core import Landuse, Ron, Soils
from wepppy.nodb.mods.baer import Baer
from wepppy.nodb.mods.disturbed import Disturbed

map_bp = Blueprint('map', __name__)


@map_bp.route('/runs/<string:runid>/<config>/resources/legends/slope_aspect')
@map_bp.route('/runs/<string:runid>/<config>/resources/legends/slope_aspect/')
def resources_slope_aspect_legend(runid, config):
    load_run_context(runid, config)

    return render_template('legends/slope_aspect.htm')


@map_bp.route('/runs/<string:runid>/<config>/resources/legends/landuse')
@map_bp.route('/runs/<string:runid>/<config>/resources/legends/landuse/')
def resources_landuse_legend(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    return render_template('legends/landuse.htm',
                           legend=Landuse.getInstance(wd).legend)


@map_bp.route('/runs/<string:runid>/<config>/resources/legends/soils')
@map_bp.route('/runs/<string:runid>/<config>/resources/legends/soils/')
def resources_soil_legend(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    return render_template('legends/soil.htm',
                           legend=Soils.getInstance(wd).legend)


@map_bp.route('/runs/<string:runid>/<config>/resources/legends/sbs')
@map_bp.route('/runs/<string:runid>/<config>/resources/legends/sbs/')
def resources_sbs_legend(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)
    if 'baer' in ron.mods:
        baer = Baer.getInstance(wd)
    else:
        baer = Disturbed.getInstance(wd)

    return render_template('legends/landuse.htm',
                           legend=baer.legend)
