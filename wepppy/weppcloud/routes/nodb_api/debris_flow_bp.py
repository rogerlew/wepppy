"""Routes for debris_flow blueprint extracted from app.py."""

from __future__ import annotations

from flask import Response

import wepppy

from .._common import *  # noqa: F401,F403

from wepppy.nodb.core.ron import Ron
from wepppy.nodb.mods.debris_flow import DebrisFlow
from wepppy.nodb.unitizer import Unitizer


debris_flow_bp = Blueprint('debris_flow', __name__)


@debris_flow_bp.route('/runs/<string:runid>/<config>/report/debris_flow')
@debris_flow_bp.route('/runs/<string:runid>/<config>/report/debris_flow/')
def report_debris_flow(runid: str, config: str) -> Response:
    """Render the debris flow summary report for the active run.

    Args:
        runid: Identifier that maps to the working directory.
        config: Configuration profile for the active run (used for template context).

    Returns:
        Response: Rendered HTML report response.
    """
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
