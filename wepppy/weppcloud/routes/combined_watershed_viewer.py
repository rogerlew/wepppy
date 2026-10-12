"""Routes for combined_watershed_viewer blueprint extracted from app.py."""

from ._common import *  # noqa: F401,F403
from wepppy.nodb.core import Ron
import math
from wepppy.weppcloud.utils.portland_collections import can_read_collection_run


combined_watershed_viewer_bp = Blueprint('combined_watershed_viewer', __name__)


class _InvalidRunInputError(ValueError):
    """Raised when combined watershed run input cannot be parsed safely."""


class _NonPublicRunError(PermissionError):
    """Raised when a run in the request is not publicly accessible."""


def _normalize_runid(raw_runid) -> str:
    if not isinstance(raw_runid, str):
        raise _InvalidRunInputError('invalid run identifier')

    runid = raw_runid.strip().rstrip('/')
    if not runid:
        raise _InvalidRunInputError('invalid run identifier')

    return runid


def _parse_and_validate_public_runids(
    *,
    runids_input: str | None = None,
    ws_input: str | None = None,
    required: bool = False,
) -> list[str]:
    if (runids_input is None) == (ws_input is None):
        raise _InvalidRunInputError('invalid run input source')

    runids: list[str]
    if runids_input is not None:
        runids = [_normalize_runid(item) for item in runids_input.replace(',', ' ').split()]
        if required and not runids:
            raise _InvalidRunInputError('missing run identifiers')
    else:
        assert ws_input is not None
        if ws_input == '':
            raise _InvalidRunInputError('invalid ws payload')

        try:
            ws_payload = json.loads(ws_input)
        except json.JSONDecodeError as exc:
            raise _InvalidRunInputError('invalid ws payload') from exc

        if not isinstance(ws_payload, list):
            raise _InvalidRunInputError('invalid ws payload')

        runids = []
        for ws_entry in ws_payload:
            if not isinstance(ws_entry, dict) or 'runid' not in ws_entry:
                raise _InvalidRunInputError('invalid ws payload')
            runids.append(_normalize_runid(ws_entry['runid']))

    runids = list(dict.fromkeys(runids))
    if len(runids) > 100:
        raise _InvalidRunInputError('Too many runs')
    for runid in runids:
        try:
            wd = get_wd(runid, prefer_active=False)
        except ValueError as exc:
            raise _InvalidRunInputError('invalid run identifier') from exc

        if not can_read_collection_run(runid, current_user, public=Ron.ispublic(wd)):
            raise _NonPublicRunError('run is not public')

    return runids


def _validate_ws_query_public_runs():
    ws_input = request.args.get('ws')
    if ws_input is None:
        return None

    try:
        _parse_and_validate_public_runids(ws_input=ws_input)
    except _InvalidRunInputError:
        return error_factory('Invalid request', status_code=400)
    except _NonPublicRunError:
        return error_factory('Forbidden', status_code=403)

    return None


def _viewer_options():
    from wepppy.weppcloud.combined_watershed_viewer_generator import VARIABLES
    options = {'title': request.args.get('title', 'Combined watersheds'),
               'units': request.args.get('units', 'SI'),
               'varname': request.args.get('varname', 'loss')}
    if options['units'] not in ('SI', 'English') or options['varname'] not in VARIABLES:
        raise ValueError('Invalid units or variable')
    for name in ('center', 'varopts'):
        if name in request.args:
            options[name] = json.loads(request.args[name])
    center = options.get('center')
    if 'center' in options and (not isinstance(center, list) or len(center) != 2
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in center)
            or not -90 <= center[0] <= 90 or not -180 <= center[1] <= 180):
        raise ValueError('Invalid center')
    ranges = options.setdefault('varopts', {})
    if not isinstance(ranges, dict) or any(
            key not in VARIABLES or type(value) not in (int, float)
            or not math.isfinite(value) or value <= 0 for key, value in ranges.items()):
        raise ValueError('Invalid ranges')
    if 'zoom' in request.args:
        options['zoom'] = float(request.args['zoom'])
        if not math.isfinite(options['zoom']) or not 0 <= options['zoom'] <= 22:
            raise ValueError('Invalid zoom')
    return options


def _render_collection(template="combined_ws_viewer.htm", include_ids=True):
    if "data_uri" in request.args:
        return error_factory("Use an explicit ws collection", status_code=400)
    validation_error = _validate_ws_query_public_runs()
    if validation_error is not None:
        return validation_error
    try:
        options = _viewer_options()
    except (ValueError, TypeError):
        return error_factory('Invalid display settings', status_code=400)
    runids = list(dict.fromkeys(item['runid'].strip().rstrip('/')
                               for item in json.loads(request.args.get('ws', '[]'))))
    try:
        from wepppy.weppcloud.combined_watershed_viewer_generator import collection_metadata
        metadata = collection_metadata(runids, include_ids=include_ids) if runids else {'ws': []}
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        current_app.logger.warning('Combined viewer metadata unavailable: %s', exc)
        return error_factory('Collection metadata is not ready. Contact the project maintainer.', status_code=409)
    context = {'center': [39, -99], 'zoom': 5, **metadata, **options, 'sitePrefix': current_app.config.get('SITE_PREFIX', '/weppcloud')}
    return render_template(template, collection=context)


@combined_watershed_viewer_bp.route('/combined_ws_viewer')
@combined_watershed_viewer_bp.route('/combined_ws_viewer/')
def combined_ws_viewer():
    return _render_collection()


@combined_watershed_viewer_bp.route('/combined_ws_viewer2')
@combined_watershed_viewer_bp.route('/combined_ws_viewer2/')
def combined_ws_viewer2():
    return _render_collection()


@combined_watershed_viewer_bp.route('/bounds_ws_viewer')
@combined_watershed_viewer_bp.route('/bounds_ws_viewer/')
def bounds_ws_viewer():
    return _render_collection('bounds_ws_viewer.htm', include_ids=False)


@combined_watershed_viewer_bp.route('/combined_ws_viewer/url_generator', methods=['GET', 'POST'])
@combined_watershed_viewer_bp.route('/combined_ws_viewer/url_generator/', methods=['GET', 'POST'])
def combined_ws_viewer_url_gen():
    if request.method == 'GET' and not request.args.get('runids'):
        return render_template('combined_ws_viewer_url_gen.htm', url=None, user=current_user,
                               title=request.args.get('title', ''), runids='')

    try:
        title = request.values.get('title', '')
        runids = _parse_and_validate_public_runids(
            runids_input=request.values.get('runids', ''),
            required=True,
        )
    except _InvalidRunInputError:
        return error_factory('Invalid request', status_code=400)
    except _NonPublicRunError:
        return error_factory('Forbidden', status_code=403)

    try:
        from wepppy.weppcloud.combined_watershed_viewer_generator import combined_watershed_viewer_generator
        url = combined_watershed_viewer_generator(runids, title)

        return render_template('combined_ws_viewer_url_gen.htm',
            url=url, user=current_user, title=title, runids=', '.join(runids))
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        current_app.logger.exception("combined_ws_viewer_url_gen failed")
        return error_factory('Collection metadata is not ready. Contact the project maintainer.', status_code=409)
