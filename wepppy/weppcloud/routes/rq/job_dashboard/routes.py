import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from flask import abort, Blueprint, request, render_template
from wepppy.weppcloud.utils.helpers import get_wd, exception_factory
from wepppy.weppcloud.utils.cap_guard import requires_cap

rq_job_dashboard_bp = Blueprint('rq_job_dashboard', __name__, template_folder='templates')

@rq_job_dashboard_bp.route('/rq/job-dashboard/<string:job_id>')
@requires_cap(gate_reason="Complete verification to view the RQ job dashboard.")
def job_dashboard_route(job_id):
    # Preserve the exact Redis/RQ identifier so legacy bare-hex jobs remain
    # inspectable. RQ job IDs are opaque at lookup boundaries.
    return render_template('dashboard_pure.htm', job_id=job_id)
