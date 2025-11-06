"""Routes for rangeland blueprint extracted from app.py."""

from .._common import *  # noqa: F401,F403

from wepppy.nodb.core import Ron
from wepppy.nodb.mods.rangeland_cover import RangelandCover

from wepppy.weppcloud.utils.helpers import handle_with_exception_factory


_COVER_MEASURES = (
    'bunchgrass',
    'forbs',
    'sodgrass',
    'shrub',
    'basal',
    'rock',
    'litter',
    'cryptogams',
)

_COVER_KEY_VARIANTS = {
    measure: (
        measure,
        f'{measure}_cover',
        f'input_{measure}_cover',
    )
    for measure in _COVER_MEASURES
}


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


def _extract_cover_value(measure, *sources):
    variants = _COVER_KEY_VARIANTS[measure]
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in variants:
            if key in source:
                candidate = source[key]
                if candidate is None or candidate == '':
                    continue
                return candidate
    return None


def _coerce_cover_values(payload):
    covers_section = payload.get('covers') if isinstance(payload.get('covers'), dict) else {}
    sources = (covers_section, payload)

    covers = {}
    for measure in _COVER_MEASURES:
        raw_value = _extract_cover_value(measure, *sources)
        if raw_value in (None, ''):
            raise ValueError(f'{measure} cover value is required.')
        try:
            numeric = float(raw_value)
        except (TypeError, ValueError):
            raise ValueError(f'{measure} cover must be numeric.')
        if numeric < 0.0 or numeric > 100.0:
            raise ValueError(f'{measure} cover must be between 0 and 100.')
        covers[measure] = float(numeric)
    return covers


rangeland_bp = Blueprint('rangeland', __name__)

@rangeland_bp.route('/runs/<string:runid>/<config>/tasks/modify_rangeland_cover/', methods=['POST'])
@handle_with_exception_factory
def task_modify_rangeland_cover(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    payload = parse_request_payload(request)
    topaz_ids = _normalize_topaz_ids(payload.get('topaz_ids'))
    if not topaz_ids:
        return exception_factory('Modify Rangeland Cover failed: provide at least one Topaz ID.', runid=runid)

    try:
        covers = _coerce_cover_values(payload)
    except ValueError as exc:
        message = str(exc) or 'Invalid cover values supplied.'
        return exception_factory(message, runid=runid)

    rangeland_cover = RangelandCover.getInstance(wd)
    try:
        rangeland_cover.modify_covers(topaz_ids, covers)
    except AssertionError as exc:
        invalid_id = None
        if exc.args:
            if isinstance(exc.args[0], tuple):
                invalid_id = exc.args[0][0]
            else:
                invalid_id = exc.args[0]
        message = 'One or more Topaz IDs are invalid.'
        if invalid_id:
            message = f'Topaz ID {invalid_id} is not available.'
        return exception_factory(message, runid=runid)
    except Exception:
        return exception_factory('Failed to modify rangeland cover.', runid=runid)

    return success_factory()


@rangeland_bp.route('/runs/<string:runid>/<config>/query/rangeland_cover/subcatchments')
@rangeland_bp.route('/runs/<string:runid>/<config>/query/rangeland_cover/subcatchments/')
@handle_with_exception_factory
def query_rangeland_cover_subcatchments(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(RangelandCover.getInstance(wd).subs_summary)


@rangeland_bp.route('/runs/<string:runid>/<config>/report/rangeland_cover')
@rangeland_bp.route('/runs/<string:runid>/<config>/report/rangeland_cover/')
@handle_with_exception_factory
def report_rangeland_cover(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)
    rangeland_cover = RangelandCover.getInstance(wd)

    return render_template('reports/rangeland_cover.htm', runid=runid, config=config,
                           rangeland_cover=rangeland_cover)


@rangeland_bp.route('/runs/<string:runid>/<config>/tasks/build_rangeland_cover/', methods=['POST'])
@handle_with_exception_factory
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
