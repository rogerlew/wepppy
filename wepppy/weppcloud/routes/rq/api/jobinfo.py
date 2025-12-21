import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from flask import abort, Blueprint, request, jsonify
from wepppy.weppcloud.utils.helpers import get_wd, exception_factory, success_factory

from wepppy.rq.job_info import (
    get_wepppy_rq_job_info,
    get_wepppy_rq_job_status,
    get_wepppy_rq_jobs_info,
)
from wepppy.rq.cancel_job import cancel_jobs


rq_jobinfo_bp = Blueprint('rq_jobinfo', __name__)


def _normalize_job_id_inputs(raw_values):
    normalized = []
    if raw_values is None:
        return normalized

    seen = set()

    def _consume(value):
        if value is None:
            return
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return
            if ',' in stripped:
                for part in stripped.split(','):
                    _consume(part)
                return
            job_id = stripped
            if job_id in seen:
                return
            seen.add(job_id)
            normalized.append(job_id)
            return
        if isinstance(value, dict):
            for payload in value.values():
                _consume(payload)
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                _consume(item)
            return

        job_id = str(value).strip()
        if not job_id or job_id in seen:
            return
        seen.add(job_id)
        normalized.append(job_id)

    _consume(raw_values)
    return normalized


def _extract_job_ids_from_request():
    job_ids = []

    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        if any(key in payload for key in ('job_ids', 'jobs', 'ids')):
            job_ids = _normalize_job_id_inputs(
                payload.get('job_ids') or payload.get('jobs') or payload.get('ids')
            )
        else:
            job_ids = _normalize_job_id_inputs(payload.values())
    elif payload is not None:
        job_ids = _normalize_job_id_inputs(payload)

    if not job_ids:
        arg_values = request.args.getlist('job_id')
        if not arg_values:
            arg_values = request.args.getlist('job_ids')
        if not arg_values:
            arg_values = request.args.get('job_ids')
        job_ids = _normalize_job_id_inputs(arg_values)

    return job_ids

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
    # NOTE: Read-only polling endpoint; consider implementing fastapi microservice and rate limiting if worker pressure grows.
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
