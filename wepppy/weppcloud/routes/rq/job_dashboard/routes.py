import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from flask import abort, Blueprint, request, render_template
from wepppy.weppcloud.utils.helpers import get_wd, exception_factory

rq_job_dashboard_bp = Blueprint('rq_job_dashboard', __name__, template_folder='templates')

@rq_job_dashboard_bp.route('/rq/job-dashboard/<string:job_id>')
def job_dashboard_route(job_id):
    # job id is a uuid; if it doesn't contain '-' then insert them
    if len(job_id) == 32:
        job_id = f'{job_id[:8]}-{job_id[8:12]}-{job_id[12:16]}-{job_id[16:20]}-{job_id[20:]}'
        
    # Assuming you have a function to get job details
    return render_template('dashboard.html', job_id=job_id)

