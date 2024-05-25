import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from flask import abort, Blueprint, request, render_template
from utils.helpers import get_wd, exception_factory

rq_job_dashboard_bp = Blueprint('rq_job_dashboard', __name__, template_folder='templates')

@rq_job_dashboard_bp.route('/rq/job-dashboard/<string:job_id>')
def job_dashboard_route(job_id):
    # Assuming you have a function to get job details
    return render_template('dashboard.html', job_id=job_id)

