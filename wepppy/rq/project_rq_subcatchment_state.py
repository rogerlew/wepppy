"""Inspect persisted RQ state for serialized WBT subcatchment jobs."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job, JobStatus
from rq.registry import DeferredJobRegistry, StartedJobRegistry

_WBT_BUILD_LINK_KEY = "jobs:0,func:build_subcatchments_rq"
_WBT_RECEIPT_LINK_KEY = "jobs:1,func:abstract_watershed_rq"
_WBT_ADMISSION_FINGERPRINT_KEY = "wbt_subcatchment_admission_fingerprint"
_WBT_ADMISSION_ROOT_KEY = "wbt_subcatchment_admission_root"
_WBT_ADMISSION_BUILD_KEY = "wbt_subcatchment_admission_build"
_WBT_ADMISSION_RECEIPT_KEY = "wbt_subcatchment_admission_receipt"
_WBT_ADMISSION_PREVIOUS_KEY = "wbt_subcatchment_admission_previous"


def _decode_redis_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _subcatchment_admission_fingerprint(
    *,
    parent_job_id: str,
    queue_name: str,
    runid: str,
    updates: dict[str, Any],
    boundary_policy: dict[str, Any] | None,
) -> str:
    payload = {
        "boundary_policy": boundary_policy,
        "parent_job_id": parent_job_id,
        "queue_name": queue_name,
        "runid": runid,
        "updates": updates,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fetch_job_or_none(job_id: str | None, redis_conn) -> Job | None:
    if not job_id:
        return None
    try:
        return Job.fetch(job_id, connection=redis_conn)
    except NoSuchJobError:
        return None


def _is_terminal_job(job: Job) -> bool:
    return job.get_status(refresh=True) in {
        JobStatus.CANCELED,
        JobStatus.FAILED,
        JobStatus.FINISHED,
        JobStatus.STOPPED,
    }


def _stored_dependency_ids(job: Job) -> set[str]:
    return {
        decoded
        for raw in job.connection.smembers(job.dependencies_key)
        if (decoded := _decode_redis_text(raw)) is not None
    }


def _active_job_has_execution_location(job: Job) -> bool:
    origin = getattr(job, "origin", None)
    if not isinstance(origin, str) or not origin:
        return False
    status = job.get_status(refresh=True)
    if status == JobStatus.QUEUED:
        queue = Queue(
            origin,
            connection=job.connection,
            job_class=job.__class__,
        )
        intermediate_ids = {
            decoded
            for raw in job.connection.lrange(
                queue.intermediate_queue_key,
                0,
                -1,
            )
            if (decoded := _decode_redis_text(raw)) is not None
        }
        return job.id in queue.get_job_ids() or job.id in intermediate_ids
    if status == JobStatus.DEFERRED:
        return job.id in DeferredJobRegistry(
            origin,
            connection=job.connection,
            job_class=job.__class__,
        ).get_job_ids()
    if status == JobStatus.STARTED:
        return job.id in StartedJobRegistry(
            origin,
            connection=job.connection,
            job_class=job.__class__,
        ).get_job_ids()
    return False


def _active_job_location_keys(job: Job) -> tuple[str, ...]:
    origin = getattr(job, "origin", None)
    if not isinstance(origin, str) or not origin:
        return ()
    status = job.get_status(refresh=False)
    if status == JobStatus.QUEUED:
        queue = Queue(
            origin,
            connection=job.connection,
            job_class=job.__class__,
        )
        return (queue.key, queue.intermediate_queue_key)
    if status == JobStatus.DEFERRED:
        return (
            DeferredJobRegistry(
                origin,
                connection=job.connection,
                job_class=job.__class__,
            ).key,
        )
    if status == JobStatus.STARTED:
        return (
            StartedJobRegistry(
                origin,
                connection=job.connection,
                job_class=job.__class__,
            ).key,
        )
    return ()


def _load_exact_subcatchment_tree(
    redis_conn,
    queue: Queue,
    *,
    parent_job: Job,
    fingerprint: str,
    tail_key: str,
    require_current_tail: bool,
) -> tuple[Job, Job] | None:
    """Return an already committed tree only when all bounded links agree."""
    build_id = parent_job.meta.get(_WBT_BUILD_LINK_KEY)
    receipt_id = parent_job.meta.get(_WBT_RECEIPT_LINK_KEY)
    stored_fingerprint = parent_job.meta.get(_WBT_ADMISSION_FINGERPRINT_KEY)
    if build_id is None and receipt_id is None and stored_fingerprint is None:
        return None
    if not (
        isinstance(build_id, str)
        and isinstance(receipt_id, str)
        and stored_fingerprint == fingerprint
    ):
        raise RuntimeError(
            "WBT subcatchment root contains an incomplete or mismatched "
            "admission tree."
        )

    build = _fetch_job_or_none(build_id, redis_conn)
    receipt = _fetch_job_or_none(receipt_id, redis_conn)
    if build is None or receipt is None:
        raise RuntimeError(
            "WBT subcatchment root references a missing admission job."
        )

    expected_common = {
        _WBT_ADMISSION_FINGERPRINT_KEY: fingerprint,
        _WBT_ADMISSION_ROOT_KEY: parent_job.id,
    }
    if any(build.meta.get(key) != value for key, value in expected_common.items()):
        raise RuntimeError("WBT subcatchment build linkage does not match its root.")
    if any(receipt.meta.get(key) != value for key, value in expected_common.items()):
        raise RuntimeError("WBT subcatchment receipt linkage does not match its root.")
    if build.meta.get(_WBT_ADMISSION_RECEIPT_KEY) != receipt.id:
        raise RuntimeError("WBT subcatchment build does not link to its receipt.")
    if receipt.meta.get(_WBT_ADMISSION_BUILD_KEY) != build.id:
        raise RuntimeError("WBT subcatchment receipt does not link to its build.")
    if receipt.meta.get("wbt_completion_receipt_for") != build.id:
        raise RuntimeError("WBT completion receipt identifies the wrong build.")

    deferred_ids = set(
        DeferredJobRegistry(
            queue.name,
            connection=redis_conn,
            job_class=queue.job_class,
            serializer=queue.serializer,
        ).get_job_ids()
    )
    queued_ids = set(queue.get_job_ids())
    intermediate_ids = {
        decoded
        for raw in redis_conn.lrange(queue.intermediate_queue_key, 0, -1)
        if (decoded := _decode_redis_text(raw)) is not None
    }
    started_ids = set(
        StartedJobRegistry(
            queue.name,
            connection=redis_conn,
            job_class=queue.job_class,
            serializer=queue.serializer,
        ).get_job_ids()
    )

    receipt_dependencies = _stored_dependency_ids(receipt)
    receipt_status = receipt.get_status(refresh=True)
    if receipt_status == JobStatus.DEFERRED:
        if receipt_dependencies != {build.id}:
            raise RuntimeError("WBT completion receipt dependency is incomplete.")
        if receipt.id not in deferred_ids or receipt.id not in build.dependent_ids:
            raise RuntimeError(
                "WBT completion receipt registry linkage is incomplete."
            )
    elif (
        receipt_status == JobStatus.QUEUED
        and receipt.id not in queued_ids
        and receipt.id not in intermediate_ids
    ):
        raise RuntimeError("WBT completion receipt is absent from its queue.")
    elif receipt_status == JobStatus.STARTED and receipt.id not in started_ids:
        raise RuntimeError("WBT completion receipt is absent from its started registry.")
    elif receipt_status not in {
        JobStatus.QUEUED,
        JobStatus.STARTED,
        JobStatus.CANCELED,
        JobStatus.FAILED,
        JobStatus.FINISHED,
        JobStatus.STOPPED,
    }:
        raise RuntimeError("WBT completion receipt has an unsupported status.")
    if receipt_status != JobStatus.DEFERRED:
        if receipt_dependencies not in (set(), {build.id}):
            raise RuntimeError(
                "WBT completion receipt has an unexpected dependency."
            )
        if receipt.id in build.dependent_ids:
            raise RuntimeError(
                "WBT build retains a stale completion-receipt link."
            )

    previous_id = build.meta.get(_WBT_ADMISSION_PREVIOUS_KEY)
    build_dependencies = _stored_dependency_ids(build)
    build_status = build.get_status(refresh=True)
    if previous_id is None:
        if build_dependencies:
            raise RuntimeError("WBT build has an unexpected prior dependency.")
    elif build_status == JobStatus.DEFERRED:
        if build_dependencies != {previous_id}:
            raise RuntimeError("WBT build prior dependency is incomplete.")
        previous = _fetch_job_or_none(previous_id, redis_conn)
        if previous is None or build.id not in previous.dependent_ids:
            raise RuntimeError("WBT build reverse dependency is incomplete.")
    elif build_status not in {
        JobStatus.QUEUED,
        JobStatus.STARTED,
        JobStatus.CANCELED,
        JobStatus.FAILED,
        JobStatus.FINISHED,
        JobStatus.STOPPED,
    }:
        raise RuntimeError("WBT build has an unsupported status.")
    if build_status != JobStatus.DEFERRED:
        expected_build_dependencies = set() if previous_id is None else {previous_id}
        if build_dependencies not in (set(), expected_build_dependencies):
            raise RuntimeError("WBT build has an unexpected prior dependency.")
        if previous_id is not None:
            previous = _fetch_job_or_none(previous_id, redis_conn)
            if previous is not None and build.id in previous.dependent_ids:
                raise RuntimeError(
                    "WBT prior build retains a stale dependent link."
                )
    if build_status == JobStatus.DEFERRED and build.id not in deferred_ids:
        raise RuntimeError("WBT build is absent from its deferred registry.")
    if (
        build_status == JobStatus.QUEUED
        and build.id not in queued_ids
        and build.id not in intermediate_ids
    ):
        raise RuntimeError("WBT build is absent from its queue.")
    if build_status == JobStatus.STARTED and build.id not in started_ids:
        raise RuntimeError("WBT build is absent from its started registry.")

    if require_current_tail:
        current_tail = _decode_redis_text(redis_conn.get(tail_key))
        if current_tail != build.id:
            raise RuntimeError("WBT admission tail does not identify the exact tree.")
    return build, receipt
