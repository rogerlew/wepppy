"""Routes for combined_watershed_viewer blueprint extracted from app.py."""

from ._common import *  # noqa: F401,F403
from wepppy.nodb.core import Ron


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

    for runid in runids:
        try:
            wd = get_wd(runid, prefer_active=False)
        except ValueError as exc:
            raise _InvalidRunInputError('invalid run identifier') from exc

        if not Ron.ispublic(wd):
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


@combined_watershed_viewer_bp.route('/combined_ws_viewer')
@combined_watershed_viewer_bp.route('/combined_ws_viewer/')
def combined_ws_viewer():
    validation_error = _validate_ws_query_public_runs()
    if validation_error is not None:
        return validation_error
    return render_template('combined_ws_viewer.htm')


@combined_watershed_viewer_bp.route('/combined_ws_viewer2')
@combined_watershed_viewer_bp.route('/combined_ws_viewer2/')
def combined_ws_viewer2():
    validation_error = _validate_ws_query_public_runs()
    if validation_error is not None:
        return validation_error
    return render_template('combined_ws_viewer2.htm')


@combined_watershed_viewer_bp.route('/bounds_ws_viewer')
@combined_watershed_viewer_bp.route('/bounds_ws_viewer/')
def bounds_ws_viewer():
    validation_error = _validate_ws_query_public_runs()
    if validation_error is not None:
        return validation_error
    return render_template('bounds_ws_viewer.htm')


@combined_watershed_viewer_bp.route('/combined_ws_viewer/url_generator', methods=['GET', 'POST'])
@combined_watershed_viewer_bp.route('/combined_ws_viewer/url_generator/', methods=['GET', 'POST'])
def combined_ws_viewer_url_gen():
    if current_user.is_authenticated:
        if not current_user.roles:
            from wepppy.weppcloud.app import user_datastore  # lazy import to avoid circular

            user_datastore.add_role_to_user(current_user.email, 'User')

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
        return exception_factory('Error processing request')
