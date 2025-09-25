import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from flask import abort, Blueprint, request, jsonify
from wepppy.weppcloud.utils.helpers import get_wd, exception_factory, success_factory

from wepppy.rq.job_info import get_wepppy_rq_job_info, get_wepppy_rq_job_status
from wepppy.rq.cancel_job import cancel_jobs


rq_jobinfo_bp = Blueprint('rq_jobinfo', __name__)

## Job Status
# The status of a job can be one of the following:
#
# queued: 
#   The default status for created jobs, except for those that have dependencies, 
#   which will be created as deferred. These jobs have been placed in a queue and are ready to be executed.

# finished: 
#   The job has finished execution and is available through the finished job registry.
# failed: 
#   Jobs that encountered errors during execution or expired before being executed.
# started: 
#   The job has started execution. This status includes the job execution support mechanisms, such as setting the worker name and setting up heartbeat information.
# deferred: 
#   The job is not ready for execution because its dependencies have not finished successfully yet.
# scheduled: 
#   Jobs created to run at a future date or jobs that are retried after a retry interval.
# stopped: 
#   The job was stopped because the worker was stopped.
# canceled: 
#   The job has been manually canceled and will not be executed, even if it is part of a dependency chain.



@rq_jobinfo_bp.route('/rq/api/jobinfo/<string:job_id>')
@rq_jobinfo_bp.route('/rq/jobinfo/<string:job_id>')
def jobinfo_route(job_id):
    try:
        job_info = get_wepppy_rq_job_info(job_id)
        return jsonify(job_info)
    except Exception:
        return exception_factory()


@rq_jobinfo_bp.route('/rq/api/canceljob/<string:job_id>')
@rq_jobinfo_bp.route('/rq/canceljob/<string:job_id>')
def canceljob_route(job_id):
    try:
        cancel_jobs(job_id)
        return success_factory()
    except Exception:
        return exception_factory()


@rq_jobinfo_bp.route('/rq/api/jobstatus/<string:job_id>')
@rq_jobinfo_bp.route('/rq/jobstatus/<string:job_id>')
def jobstatus_route(job_id):
    try:
        job_status = get_wepppy_rq_job_status(job_id)
        return jsonify(job_status)
    except Exception:
        return exception_factory()
