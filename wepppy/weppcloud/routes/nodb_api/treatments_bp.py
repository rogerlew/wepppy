"""Routes for treatments blueprint extracted from app.py."""

from ._common import *  # noqa: F401,F403

from wepppy.nodb.mods.treatments import Treatments, TreatmentsMode


treatments_bp = Blueprint('treatments', __name__)

@treatments_bp.route('/runs/<string:runid>/<config>/tasks/set_treatments_mode/', methods=['POST'])
def set_treatments_mode(runid, config):

    mode = None
    single_selection = None
    try:
        mode = int(request.form.get('treatments_mode', None))
    except Exception:
        exception_factory('mode and landuse_single_selection must be provided', runid=runid)

    wd = get_wd(runid)
    treatments = Treatments.getInstance(wd)

    try:
        treatments.mode = TreatmentsMode(mode)
    except Exception:
        exception_factory('error setting landuse mode', runid=runid)

    return success_factory()
