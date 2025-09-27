"""Routes for rangeland blueprint extracted from app.py."""

from ._common import *  # noqa: F401,F403

from wepppy.nodb import RangelandCover, Ron


rangeland_bp = Blueprint('rangeland', __name__)

@rangeland_bp.route('/runs/<string:runid>/<config>/tasks/modify_rangeland_cover/', methods=['POST'])
def task_modify_rangeland_cover(runid, config):
    wd = get_wd(runid)

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
    wd = get_wd(runid)
    return jsonify(RangelandCover.getInstance(wd).subs_summary)


@rangeland_bp.route('/runs/<string:runid>/<config>/report/rangeland_cover')
@rangeland_bp.route('/runs/<string:runid>/<config>/report/rangeland_cover/')
def report_rangeland_cover(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    rangeland_cover = RangelandCover.getInstance(wd)

    return render_template('reports/rangeland_cover.htm', runid=runid, config=config,
                           rangeland_cover=rangeland_cover)


@rangeland_bp.route('/runs/<string:runid>/<config>/tasks/build_rangeland_cover/', methods=['POST'])
def task_build_rangeland_cover(runid, config):
    wd = get_wd(runid)
    rangeland_cover = RangelandCover.getInstance(wd)

    rap_year = request.form.get('rap_year')

    default_covers = dict(
        bunchgrass=request.form.get('bunchgrass_cover'),
        forbs=request.form.get('forbs_cover'),
        sodgrass=request.form.get('sodgrass_cover'),
        shrub=request.form.get('shrub_cover'),
        basal=request.form.get('basal_cover'),
        rock=request.form.get('rock_cover'),
        litter=request.form.get('litter_cover'),
        cryptogams=request.form.get('cryptogams_cover'))

    try:
        rangeland_cover.build(rap_year=rap_year, default_covers=default_covers)
    except Exception:
        return exception_factory('Building RangelandCover Failed')

    return success_factory()
