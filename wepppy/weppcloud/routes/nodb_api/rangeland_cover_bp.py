"""Routes for rangeland_cover blueprint extracted from app.py."""

from .._common import *  # noqa: F401,F403

from wepppy.nodb.mods.rangeland_cover import RangelandCover, RangelandCoverMode


rangeland_cover_bp = Blueprint('rangeland_cover', __name__)

@rangeland_cover_bp.route('/runs/<string:runid>/<config>/query/rangeland_cover/current_cover_summary/', methods=['POST'])
def query_rangeland_cover_current(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    topaz_ids = request.json.get('topaz_ids', None)
    topaz_ids = [x for x in topaz_ids if x != '']

    return jsonify(RangelandCover.getInstance(wd).current_cover_summary(topaz_ids))


@rangeland_cover_bp.route('/runs/<string:runid>/<config>/tasks/set_rangeland_cover_mode/', methods=['POST'])
def set_rangeland_cover_mode(runid, config):

    mode = None
    rap_year = None
    try:
        mode = int(request.form.get('mode', None))
        rap_year = int(request.form.get('rap_year', None))
    except Exception:
        exception_factory('mode and rap_year must be provided', runid=runid)

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    rangeland_cover = RangelandCover.getInstance(wd)

    try:
        rangeland_cover.mode = RangelandCoverMode(mode)
        rangeland_cover.rap_year = rap_year
    except Exception:
        exception_factory('error setting mode or rap_year', runid=runid)

    return success_factory()
