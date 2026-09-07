"""Publish fork prerequisite failures without unblocking strict dependencies."""
from __future__ import annotations

import logging
from typing import Any

from rq.exceptions import NoSuchJobError
from rq.job import Job

_LOG = logging.getLogger(__name__)

# Redis pub/sub is server-wide, independent of the selected DB. Publishing in
# the receipt transaction prevents a rejected/stale callback from signaling a
# different fork, and cannot race a receipt replacement after the state check.
_RECORD_FAILURE = """
if redis.call('GET', KEYS[1]) ~= ARGV[1]
   or redis.call('HGET', KEYS[2], 'job_id') ~= ARGV[1]
   or redis.call('HGET', KEYS[2], 'source_runid') ~= ARGV[2]
   or redis.call('HGET', KEYS[2], 'target_runid') ~= ARGV[3] then
    return 0
end
local state = redis.call('HGET', KEYS[2], 'state')
if state == 'succeeded' or state == 'failed' then return 0 end
redis.call('HSET', KEYS[2], 'state', 'failed', 'failed_job_id', ARGV[4])
redis.call('PUBLISH', ARGV[2] .. ':fork',
    'rq:' .. ARGV[4] .. ' STATUS Fork WEPP prerequisite failed; inspect job ' .. ARGV[4])
redis.call('PUBLISH', ARGV[2] .. ':fork',
    'rq:' .. ARGV[4] .. ' TRIGGER   fork FORK_FAILED')
return 1
"""


def _report_failure(job: Job, connection: Any) -> None:
    lineage = job.meta.get("fork_failure")
    if not isinstance(lineage, dict):
        return
    root_id = lineage.get("root_job_id")
    source = lineage.get("source_runid")
    target = lineage.get("target_runid")
    if not all(isinstance(value, str) and value for value in (root_id, source, target)):
        return
    if not job.args or job.args[0] != target:
        return
    try:
        root = Job.fetch(root_id, connection=connection)
    except NoSuchJobError:
        return
    if (
        root.func_name != "wepppy.rq.project_rq.fork_rq"
        or root.origin != "fork-archive"
        or len(root.args) < 3
        or root.args[0] != source
        or root.args[1] != target
        or root.args[2] is not True
        or not any(
            isinstance(key, str) and key.startswith("jobs:") and value == job.id
            for key, value in root.meta.items()
        )
    ):
        return
    connection.eval(
        _RECORD_FAILURE, 2,
        f"rq:fork:destination:{target}", f"rq:fork:planned:{target}",
        root_id, source, target, job.id,
    )


def report_fork_failure(job: Job, connection: Any, exc_type: Any, exc_value: Any, traceback: Any) -> None:
    """RQ failure callback; reporting must never replace the task's exception."""
    try:
        _report_failure(job, connection)
    except Exception:  # broad-except: RQ callback boundary preserves original task failure
        _LOG.exception("Could not report fork prerequisite failure job_id=%s", job.id)
