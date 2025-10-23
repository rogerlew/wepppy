"""Routes for rangeland blueprint extracted from app.py."""

from .._common import *  # noqa: F401,F403

from wepppy.nodb.core import Ron
from wepppy.nodb.mods.rangeland_cover import RangelandCover


rangeland_bp = Blueprint('rangeland', __name__)

@rangeland_bp.route('/runs/<string:runid>/<config>/tasks/modify_rangeland_cover/', methods=['POST'])
def task_modify_rangeland_cover(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    topaz_ids = request.json.get('topaz_ids', None)
    covers = request.json.get('covers', None)

    assert topaz_ids is not None
    assert covers is not None

    for measure, value in covers.items():
        value = float(value)
        covers[measure] = float(value)
        if value < 0.0 or value > 100.0:
            return Exception('covers must be between 0 and 100')

    rangeland_cover = RangelandCover.getInstance(wd)
    rangeland_cover.modify_covers(topaz_ids, covers)

    return success_factory()


@rangeland_bp.route('/runs/<string:runid>/<config>/query/rangeland_cover/subcatchments')
@rangeland_bp.route('/runs/<string:runid>/<config>/query/rangeland_cover/subcatchments/')
def query_rangeland_cover_subcatchments(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(RangelandCover.getInstance(wd).subs_summary)


@rangeland_bp.route('/runs/<string:runid>/<config>/report/rangeland_cover')
@rangeland_bp.route('/runs/<string:runid>/<config>/report/rangeland_cover/')
def report_rangeland_cover(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)
    rangeland_cover = RangelandCover.getInstance(wd)

    return render_template('reports/rangeland_cover.htm', runid=runid, config=config,
                           rangeland_cover=rangeland_cover)


@rangeland_bp.route('/runs/<string:runid>/<config>/tasks/build_rangeland_cover/', methods=['POST'])
def task_build_rangeland_cover(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    rangeland_cover = RangelandCover.getInstance(wd)

    payload = parse_request_payload(request)

    rap_year_raw = payload.get('rap_year')
    if rap_year_raw in (None, ''):
        rap_year = None
    else:
        try:
            rap_year = int(rap_year_raw)
        except (TypeError, ValueError):
            return exception_factory('Building RangelandCover Failed', runid=runid)

    defaults_payload = payload.get('defaults')
    if not isinstance(defaults_payload, dict):
        defaults_payload = {
            'bunchgrass': payload.get('bunchgrass_cover'),
            'forbs': payload.get('forbs_cover'),
            'sodgrass': payload.get('sodgrass_cover'),
            'shrub': payload.get('shrub_cover'),
            'basal': payload.get('basal_cover'),
            'rock': payload.get('rock_cover'),
            'litter': payload.get('litter_cover'),
            'cryptogams': payload.get('cryptogams_cover'),
        }

    try:
        default_covers = dict(
            bunchgrass=float(defaults_payload.get('bunchgrass')),
            forbs=float(defaults_payload.get('forbs')),
            sodgrass=float(defaults_payload.get('sodgrass')),
            shrub=float(defaults_payload.get('shrub')),
            basal=float(defaults_payload.get('basal')),
            rock=float(defaults_payload.get('rock')),
            litter=float(defaults_payload.get('litter')),
            cryptogams=float(defaults_payload.get('cryptogams')),
        )
        rangeland_cover.build(rap_year=rap_year, default_covers=default_covers)
    except Exception:
        return exception_factory('Building RangelandCover Failed', runid=runid)

    return success_factory()
