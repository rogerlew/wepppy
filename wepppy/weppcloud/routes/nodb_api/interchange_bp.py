"""Routes for launching interchange migrations."""

from __future__ import annotations

from typing import Any, MutableMapping, Optional

import redis
from flask import Response
from rq import Queue

from .._common import Blueprint, error_factory, jsonify, load_run_context, request
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.interchange_rq import TIMEOUT, run_interchange_migration
from wepppy.weppcloud.utils.helpers import authorize_and_handle_with_exception_factory

interchange_bp = Blueprint('interchange', __name__)


def _sanitize_subpath(value: Optional[str]) -> Optional[str]:
    """Normalize and validate an optional WEPP output subpath.

    Raises:
        ValueError: If the proposed path tries directory traversal or is absolute.
    """
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if ".." in cleaned or cleaned.startswith(("/", "\\")):
        raise ValueError("Invalid subpath")
    return cleaned


def _enqueue_interchange_job(runid: str, config: str, wepp_output_subpath: Optional[str]) -> Response:
    """Queue an RQ job that runs the interchange migration workflow.

    Args:
        runid: Unique identifier for the active run.
        config: Configuration profile name (needed for context loading).
        wepp_output_subpath: Optional path under ``wepp/`` whose output directory should be migrated.

    Returns:
        Response: JSON payload with the enqueued job identifier.
    """
    load_run_context(runid, config)
    subpath = _sanitize_subpath(wepp_output_subpath)

    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
        queue = Queue(connection=redis_conn)
        job = queue.enqueue_call(
            func=run_interchange_migration,
            args=(runid, subpath),
            timeout=TIMEOUT,
        )

    return jsonify({'Success': True, 'job_id': job.id})


@interchange_bp.route('/runs/<string:runid>/<config>/tasks/interchange/migrate', methods=['POST'])
@authorize_and_handle_with_exception_factory
def migrate_default_interchange(runid: str, config: str) -> Response | tuple[Response, int]:
    """Trigger the interchange migration RQ job for the active run.

    Returns:
        A JSON success payload when the job is enqueued, or a tuple containing
        an error response and HTTP status when validation fails.
    """
    payload: MutableMapping[str, Any] = request.get_json(silent=True) or {}
    subpath = payload.get('wepp_output_subpath')
    if subpath is None:
        subpath = request.form.get('wepp_output_subpath')
    try:
        return _enqueue_interchange_job(runid, config, subpath)
    except ValueError as exc:
        return error_factory(str(exc)), 400
