"""Routes for treatments blueprint extracted from app.py."""

from .._common import *  # noqa: F401,F403

from wepppy.nodb.mods.treatments import Treatments, TreatmentsMode


treatments_bp = Blueprint('treatments', __name__)

@treatments_bp.route('/runs/<string:runid>/<config>/tasks/set_treatments_mode/', methods=['POST'])
def set_treatments_mode(runid: str, config: str):
    payload = parse_request_payload(request)

    raw_mode = payload.get('mode')
    if isinstance(raw_mode, list):
        raw_mode = raw_mode[0]
    if raw_mode is None:
        legacy_mode = payload.get('treatments_mode')
        if isinstance(legacy_mode, list):
            legacy_mode = legacy_mode[0]
        raw_mode = legacy_mode

    if raw_mode is None:
        return error_factory('mode must be provided')

    try:
        mode_value = int(raw_mode)
    except (TypeError, ValueError):
        return error_factory('mode must be an integer')

    wd = get_wd(runid)
    treatments = Treatments.getInstance(wd)

    try:
        treatments.mode = TreatmentsMode(mode_value)
    except Exception:
        return exception_factory('error setting treatments mode', runid=runid)

    return success_factory()
