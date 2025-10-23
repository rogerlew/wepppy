"""Routes for rangeland_cover blueprint extracted from app.py."""

from .._common import *  # noqa: F401,F403

from wepppy.nodb.mods.rangeland_cover import RangelandCover, RangelandCoverMode


def _normalize_topaz_ids(raw):
    if raw is None:
        return []

    if isinstance(raw, (list, tuple, set)):
        items = list(raw)
    else:
        items = [raw]

    parsed = []
    for item in items:
        if item is None:
            continue
        if isinstance(item, str):
            tokens = [token.strip() for token in item.split(',')]
        else:
            tokens = [item]

        for token in tokens:
            if token is None:
                continue
            if isinstance(token, str):
                value = token.strip()
            else:
                value = str(token).strip()
            if not value:
                continue
            if value.isdigit():
                value = str(int(value))
            else:
                try:
                    value = str(int(float(value)))
                except (TypeError, ValueError):
                    value = value
            parsed.append(value)

    result = []
    seen = set()
    for value in parsed:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


rangeland_cover_bp = Blueprint('rangeland_cover', __name__)

@rangeland_cover_bp.route('/runs/<string:runid>/<config>/query/rangeland_cover/current_cover_summary/', methods=['POST'])
def query_rangeland_cover_current(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    payload = parse_request_payload(request)
    topaz_ids = _normalize_topaz_ids(payload.get('topaz_ids'))

    return jsonify(RangelandCover.getInstance(wd).current_cover_summary(topaz_ids))


@rangeland_cover_bp.route('/runs/<string:runid>/<config>/tasks/set_rangeland_cover_mode/', methods=['POST'])
def set_rangeland_cover_mode(runid, config):
    payload = parse_request_payload(request)

    mode_raw = payload.get('mode')
    rap_year_raw = payload.get('rap_year')

    if rap_year_raw in (None, ''):
        return exception_factory('mode and rap_year must be provided', runid=runid)

    try:
        mode = int(mode_raw)
        rap_year = int(rap_year_raw)
    except (TypeError, ValueError):
        return exception_factory('mode and rap_year must be provided', runid=runid)

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    rangeland_cover = RangelandCover.getInstance(wd)

    try:
        rangeland_cover.mode = RangelandCoverMode(mode)
        rangeland_cover.rap_year = rap_year
    except Exception:
        return exception_factory('error setting mode or rap_year', runid=runid)

    return success_factory()
