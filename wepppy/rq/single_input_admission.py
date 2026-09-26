"""Admission transaction for opted-in input builds; legacy routes remain unchanged."""
from contextlib import contextmanager
from pathlib import Path

import redis
from rq.exceptions import NoSuchJobError
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Watershed
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.nodb.single_input_policy import require_single_input_policy, single_input_uploads_enabled
from wepppy.nodb.single_input_sources import accept_source, read_source
from wepppy.rq.submission_recovery import RqSubmissionConflict, rq_submission_lock
from wepppy.runtime_paths.thaw_freeze import maintenance_lock
from wepppy.wepp.single_input import MAX_SOURCE_BYTES, SingleInputError


def require_idle(prep, connection):
    """Inspect receipts and descendants without canceling or replacing work."""
    pending = list(prep.get_rq_job_ids().values())
    archive_job = prep.get_archive_job_id()
    if archive_job:
        pending.append(archive_job)
    seen = set()
    while pending:
        job_id = str(pending.pop())
        if not job_id or job_id in seen:
            continue
        seen.add(job_id)
        if len(seen) > 10000:
            raise RqSubmissionConflict("Cannot verify that the project is idle.")
        try:
            job = Job.fetch(job_id, connection=connection)
        except NoSuchJobError:
            continue
        status = job.get_status(refresh=True)
        status = getattr(status, "value", status)
        if status not in {"finished", "failed", "stopped", "canceled"}:
            raise RqSubmissionConflict("Project work is active; retry the input build after it finishes.")
        pending.extend(value for key, value in (job.meta or {}).items() if key.startswith("jobs:"))
        for raw in connection.smembers(job.dependents_key):
            pending.append(raw.decode() if isinstance(raw, bytes) else str(raw))


@contextmanager
def input_submission(controller, kind, runid):
    if not single_input_uploads_enabled(controller):
        yield
        return
    if (Path(controller.wd) / "READONLY").exists():
        raise SingleInputError("This project is read-only.", code="forbidden", status_code=403)
    require_single_input_policy(controller, watershed=Watershed.getInstance(controller.wd))
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
        with rq_submission_lock(connection, f"{runid}:single-inputs:request", lifecycle_key=runid) as lease:
            require_idle(RedisPrep.getInstance(controller.wd), connection)
            with maintenance_lock(controller.wd, kind, purpose="single-input-build"):
                lease.checkpoint()
                yield


async def accept_input(controller, kind, form, mode):
    field = "input_upload_single_landuse" if kind == "landuse" else "input_upload_single_soil"
    upload = form.get(field) if form is not None else None
    if int(mode) != 5:
        if upload is not None:
            raise SingleInputError("Select Single User-Defined to upload this source.")
        return
    require_single_input_policy(controller, require_enabled=True)
    if upload is None:
        read_source(controller, kind)
    else:
        raw = await upload.read(MAX_SOURCE_BYTES + 1)
        accept_source(controller, kind, raw, upload.filename)
