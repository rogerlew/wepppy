"""Independent real Redis/flock checks; temporary identities, no project data."""
from contextvars import copy_context
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import redis

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq import submission_recovery as admission


def expect_conflict(action):
    try:
        action()
    except admission.RqSubmissionConflict:
        return
    raise AssertionError("Expected admission conflict before the protected operation")


with TemporaryDirectory(prefix="sbs-security-admission-") as lock_dir:
    admission._LIFECYCLE_LOCK_DIR = lock_dir
    runid = "security-admission-" + uuid4().hex
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
        connection.ping()

        def request(*, fresh=False):
            with admission.rq_submission_lock(
                connection, runid + ":request", lifecycle_key=runid,
                blocking_timeout=0, inherit_lifecycle=not fresh,
            ):
                admission.checkpoint_run_lifecycle(runid)
                with admission.rq_submission_lock(
                    connection, runid + ":model", lifecycle_key=runid,
                    blocking_timeout=0,
                ):
                    admission.checkpoint_run_lifecycle(runid)

        with admission.rq_submission_lock(connection, runid + ":request", lifecycle_key=runid):
            copied = copy_context()
        expect_conflict(lambda: copied.run(request))
        copied.run(request, fresh=True)
        copied.run(request, fresh=True)

        with admission.rq_submission_lock(
            connection, runid + ":request", lifecycle_key=runid, inherit_lifecycle=False,
        ) as outer:
            expect_conflict(lambda: request(fresh=True))
            outer.checkpoint()

        with admission.rq_submission_lock(
            connection, runid + ":request", lifecycle_key=runid, inherit_lifecycle=False,
        ) as outer:
            lifecycle_name = outer._locks[0].name
            assert "rq:submission-lifecycle:" in lifecycle_name
            # Remove only this probe's own Redis lease to simulate owner loss.
            assert connection.delete(lifecycle_name) == 1

            def nested():
                with admission.rq_submission_lock(
                    connection, runid + ":model", lifecycle_key=runid, blocking_timeout=0,
                ):
                    raise AssertionError("Lost parent granted nested authority")
            expect_conflict(nested)

            def fresh_file_conflict():
                # The Redis lifecycle key is gone, but the outer flock still exists.
                with admission.rq_submission_lock(
                    connection, runid + ":other", lifecycle_key=runid,
                    blocking_timeout=0, inherit_lifecycle=False,
                ):
                    raise AssertionError("Fresh lease bypassed the live file fence")
            expect_conflict(fresh_file_conflict)

        for name in (runid + ":request", runid + ":model", runid + ":other"):
            assert not connection.exists("rq:submission:" + name)
        assert not connection.exists(lifecycle_name)
        request(fresh=True)

    print(json.dumps({
        "passed": True,
        "real_redis": True,
        "real_flock": True,
        "copied_closed_context_reproduced": True,
        "fresh_requests_reacquired_twice": True,
        "active_owner_rejected": True,
        "nested_lost_parent_rejected": True,
        "file_fence_after_redis_loss_rejected": True,
        "cleanup_and_recovery_passed": True,
        "submission_recovery_sha256": hashlib.sha256(Path(admission.__file__).read_bytes()).hexdigest(),
    }, indent=2))
