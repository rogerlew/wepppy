"""Routes for debris_flow blueprint extracted from app.py."""

import wepppy

from ._common import *  # noqa: F401,F403

from wepppy.nodb import DebrisFlow, Ron, Unitizer


debris_flow_bp = Blueprint('debris_flow', __name__)


@debris_flow_bp.route('/runs/<string:runid>/<config>/report/debris_flow')
@debris_flow_bp.route('/runs/<string:runid>/<config>/report/debris_flow/')
def report_debris_flow(runid, config):
    wd = get_wd(runid)

    ron = Ron.getInstance(wd)
    debris_flow = DebrisFlow.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/debris_flow.htm', runid=runid, config=config,
                           unitizer_nodb=unitizer,
                           precisions=wepppy.nodb.unitizer.precisions,
                           debris_flow=debris_flow,
                           ron=ron,
                           user=current_user)
