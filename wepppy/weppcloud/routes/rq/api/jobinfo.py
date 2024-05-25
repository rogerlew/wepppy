import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from flask import abort, Blueprint, request, jsonify
from utils.helpers import get_wd, exception_factory

from wepppy.rq.job_info import get_run_wepp_rq_job_info


rq_jobinfo_bp = Blueprint('rq_jobinfo', __name__)


@rq_jobinfo_bp.route('/rq/jobinfo/<string:job_id>')
def jobinfo_tree(job_id):
    try:
        job_info = get_run_wepp_rq_job_info(job_id)
        return jsonify(job_info)
    except Exception:
        return exception_factory()

