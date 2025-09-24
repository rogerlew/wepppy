"""Routes for map blueprint extracted from app.py."""

from ._common import *  # noqa: F401,F403

from wepppy.nodb import Baer, Disturbed, Landuse, Ron, Soils


map_bp = Blueprint('map', __name__)


@map_bp.route('/runs/<string:runid>/<config>/resources/legends/slope_aspect')
@map_bp.route('/runs/<string:runid>/<config>/resources/legends/slope_aspect/')
def resources_slope_aspect_legend(runid, config):
    wd = get_wd(runid)

    return render_template('legends/slope_aspect.htm')


@map_bp.route('/runs/<string:runid>/<config>/resources/legends/landuse')
@map_bp.route('/runs/<string:runid>/<config>/resources/legends/landuse/')
def resources_landuse_legend(runid, config):
    wd = get_wd(runid)

    return render_template('legends/landuse.htm',
                           legend=Landuse.getInstance(wd).legend)


@map_bp.route('/runs/<string:runid>/<config>/resources/legends/soils')
@map_bp.route('/runs/<string:runid>/<config>/resources/legends/soils/')
def resources_soil_legend(runid, config):
    wd = get_wd(runid)

    return render_template('legends/soil.htm',
                           legend=Soils.getInstance(wd).legend)


@map_bp.route('/runs/<string:runid>/<config>/resources/legends/sbs')
@map_bp.route('/runs/<string:runid>/<config>/resources/legends/sbs/')
def resources_sbs_legend(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    if 'baer' in ron.mods:
        baer = Baer.getInstance(wd)
    else:
        baer = Disturbed.getInstance(wd)

    return render_template('legends/landuse.htm',
                           legend=baer.legend)
