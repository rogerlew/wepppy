import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from flask import abort, Blueprint, request, jsonify
from utils.helpers import get_wd, exception_factory, success_factory

from wepppy.rq.job_info import get_run_wepp_rq_job_info
from wepppy.rq.cancel_job import cancel_jobs


rq_jobinfo_bp = Blueprint('rq_jobinfo', __name__)


@rq_jobinfo_bp.route('/rq/jobinfo/<string:job_id>')
def jobinfo_route(job_id):
    try:
        job_info = get_run_wepp_rq_job_info(job_id)
        return jsonify(job_info)
    except Exception:
        return exception_factory()


@rq_jobinfo_bp.route('/rq/canceljob/<string:job_id>')
def canceljob_route(job_id):
    try:
        cancel_jobs(job_id)
        return success_factory()
    except Exception:
        return exception_factory()

