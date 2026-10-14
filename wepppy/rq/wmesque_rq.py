"""Opt-in, coalesced WMesque synchronization on the existing batch queue."""
import hashlib
import logging
import os
from pathlib import Path

from redis.exceptions import WatchError
from rq.exceptions import NoSuchJobError
from rq.job import Job

from wepppy.rq.job_id import new_rq_job_id
from wepppy.webservices.wmesque_catalog import sync_catalog


def sync_wmesque_rq(source=None, destination=None):
    source = source if source is not None else os.environ.get("WMESQUE_SYNC_SOURCE", "").strip()
    if not source:
        raise ValueError("WMESQUE_SYNC_SOURCE is required for synchronization")
    destination = destination if destination is not None else os.environ.get("WMESQUE_SYNC_DESTINATION", "/geodata")
    result = sync_catalog(source, destination)
    logging.getLogger(__name__).info("WMesque sync completed: %s", result)
    return result


def enqueue_sync(queue, *, timeout=3600, result_ttl=86400):
    """Coalesce pending/running work, using the existing catalog-sweep pattern."""
    source = os.environ.get("WMESQUE_SYNC_SOURCE", "").strip()
    if not source:
        raise ValueError("WMESQUE_SYNC_SOURCE is required for synchronization")
    destination = str(Path(os.environ.get("WMESQUE_SYNC_DESTINATION", "/geodata")).resolve())
    key = "wmesque:sync:admission:" + hashlib.sha256(destination.encode()).hexdigest()
    with queue.connection.pipeline() as pipeline:
        try:
            pipeline.watch(key)
            previous = pipeline.get(key)
            if previous:
                previous = previous.decode() if isinstance(previous, bytes) else previous
                pipeline.watch(Job.key_for(previous))
                try:
                    job = Job.fetch(previous, connection=queue.connection)
                    status = job.get_status(refresh=True)
                    status = getattr(status, "value", status)
                except NoSuchJobError:
                    status = None
                if status in {"queued", "started", "deferred", "scheduled"}:
                    return False
            identifier = new_rq_job_id()
            queue.enqueue_call(sync_wmesque_rq, job_id=identifier, description="WMesque catalog synchronization",
                               timeout=timeout, result_ttl=result_ttl, pipeline=pipeline,
                               kwargs={"source": source, "destination": destination})
            pipeline.set(key, identifier)
            pipeline.execute()
            return True
        except WatchError:
            return False
