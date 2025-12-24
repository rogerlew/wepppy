from flask import Blueprint, request, jsonify
from wepppy.weppcloud.utils.helpers import exception_factory, success_factory
from wepppy.rq.jobinfo_payloads import extract_job_ids

from wepppy.rq.job_info import (
    get_wepppy_rq_job_info,
    get_wepppy_rq_job_status,
    get_wepppy_rq_jobs_info,
)
from wepppy.rq.cancel_job import cancel_jobs


rq_jobinfo_bp = Blueprint('rq_jobinfo', __name__)


def _extract_job_ids_from_request():
    payload = request.get_json(silent=True)
    return extract_job_ids(payload=payload, query_args=request.args)

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



@rq_jobinfo_bp.route('/rq/api/jobstatus/<string:job_id>')
def jobstatus_route(job_id):
    # NOTE: Read-only polling endpoint; rq-engine provides the preferred FastAPI offload, keep this as fallback.
    try:
        job_status = get_wepppy_rq_job_status(job_id)
        return jsonify(job_status)
    except Exception:
        return exception_factory()


@rq_jobinfo_bp.route('/rq/api/jobinfo/<string:job_id>')
def jobinfo_route(job_id):
    try:
        job_info = get_wepppy_rq_job_info(job_id)
        return jsonify(job_info)
    except Exception:
        return exception_factory()


@rq_jobinfo_bp.route('/rq/api/jobinfo', methods=['POST'])
def jobinfo_batch_route():
    try:
        job_ids = _extract_job_ids_from_request()
        if not job_ids:
            return jsonify({'jobs': {}, 'job_ids': []})

        job_info_map = get_wepppy_rq_jobs_info(job_ids)
        ordered_ids = [job_id for job_id in job_ids if job_id in job_info_map]

        return jsonify({'jobs': job_info_map, 'job_ids': ordered_ids})
    except Exception:
        return exception_factory('Failed to retrieve batch job info')


@rq_jobinfo_bp.route('/rq/api/canceljob/<string:job_id>')
def canceljob_route(job_id):
    try:
        cancel_jobs(job_id)
        return success_factory()
    except Exception:
        return exception_factory()
