"""Routes for launching interchange migrations."""

import redis
from rq import Queue

from .._common import *  # noqa: F401,F403
from wepppy.weppcloud.utils.helpers import authorize_and_handle_with_exception_factory
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.interchange_rq import run_interchange_migration, TIMEOUT

interchange_bp = Blueprint('interchange', __name__)


def _sanitize_subpath(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if ".." in cleaned or cleaned.startswith(("/", "\\")):
        raise ValueError("Invalid subpath")
    return cleaned


def _enqueue_interchange_job(runid: str, config: str, wepp_output_subpath: str | None):
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
def migrate_default_interchange(runid, config):
    payload = request.get_json(silent=True) or {}
    subpath = payload.get('wepp_output_subpath')
    if subpath is None:
        subpath = request.form.get('wepp_output_subpath')
    try:
        return _enqueue_interchange_job(runid, config, subpath)
    except ValueError as exc:
        return error_factory(str(exc)), 400
