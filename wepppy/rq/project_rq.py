from __future__ import annotations

"""
RQ tasks that manage project-level preparation, execution, and archival flows.

Each helper wraps a discrete step in the WEPP project lifecycle - from DEM
ingest and landuse building through run forking and archive restoration -
emitting status updates for the front-end while coordinating NoDb controllers.
"""

import errno
import base64
import copy
from contextlib import ExitStack, contextmanager
import fcntl
import hashlib
import inspect
import logging
import json
import os
import re
import shutil
import socket
import time
import uuid
import zipfile
from glob import glob
from subprocess import call
from typing import Any, Mapping, Optional, Sequence

from os.path import exists as _exists
from os.path import join as _join

import redis
from rq import Queue, get_current_job
from rq.exceptions import InvalidJobOperation, NoSuchJobError
from rq.job import Dependency, Job, JobStatus
from rq.registry import DeferredJobRegistry, StartedJobRegistry
from redis.exceptions import WatchError
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)
from wepppy.rq.job_id import new_rq_job_id
from wepppy.rq.submission_recovery import RqEnqueueVerificationError
from wepppy.weppcloud.utils.helpers import get_wd, get_primary_wd
from wepppy.weppcloud.user_preferences import (
    WBT_BOUNDARY_POLICY_SNAPSHOT_KEY,
    WbtBoundaryPolicyApplyError,
    WbtBoundaryPolicySnapshotError,
    validate_wbt_boundary_policy_snapshot,
)
from wepppy.topo.wbt.wbt_topaz_emulator import (
    WbtConditioningDiagnosticsError,
    summarize_conditioning_diagnostics,
)

from wepppy.nodb.base import clear_locks, clear_nodb_file_cache, lock_statuses
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as nodir_resolve
from wepppy.runtime_paths.thaw_freeze import maintenance_lock as nodir_maintenance_lock
from wepppy.nodb.core import (
    Climate,
    Landuse,
    Ron,
    Soils,
    Watershed,
    WatershedCentroidStateError,
    Wepp,
)
from wepppy.nodb.core.climate import ClimateMultipleBuildSupersededError
from wepppy.nodb.core.watershed_errors import (
    WATERSHED_BOUNDARY_TOUCH_MESSAGE,
    WatershedBoundaryTouchesEdgeError,
)
from wepppy.topo.wbt import (
    WBT_UNRESOLVED_DEPRESSION_MESSAGE,
    WbtUnresolvedDepressionsError,
)
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.omni import Omni
from wepppy.nodb.mods.ash_transport import Ash
from wepppy.nodb.mods.debris_flow import DebrisFlow
from wepppy.nodb.mods.rangeland_cover import RangelandCover
from wepppy.nodb.mods.rhem import Rhem
from wepppy.nodb.mods.openet import OpenET_TS
from wepppy.nodb.mods.polaris import Polaris
from wepppy.nodb.mods.rap import RAP_TS
from wepppy.nodb.mods.rusle import Rusle
from wepppy.nodb.mods.treatments import Treatments

from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.wepp.interchange import run_totalwatsed3
from wepppy.io_wait import wait_for_path, wait_for_paths
from wepppy.rq.exception_logging import with_exception_logging
from . import project_rq_archive as _archive_helpers
from . import project_rq_delete as _delete_helpers
from . import project_rq_fork as _fork_helpers
from .wepp_rq import run_wepp_rq
from wepppy.rq.job_dependencies import (
    failure_tolerant_depends_on,
    release_deferred_job_if_ready,
)

_hostname = socket.gethostname()
_logger = logging.getLogger(__name__)

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)

TIMEOUT: int = 43_200
FETCH_DEM_AND_BUILD_CHANNELS_CHILD_TIMEOUT: int = int(
    os.getenv("RQ_ENGINE_FETCH_DEM_BUILD_CHANNELS_TIMEOUT", "600")
)
TOPAZ_BUILD_CHANNELS_CHILD_TIMEOUT_MINIMUM: int = 600
DEFAULT_ZOOM: int = 12
DIRECTORY_ROOT_LOCK_RETRY_ATTEMPTS: int = 5
DIRECTORY_ROOT_LOCK_RETRY_SECONDS: float = 1.0
LANDUSE_MAPPING_BATCH_MAX_EDITS: int = 500
LANDUSE_MAPPING_MAX_KEY_LENGTH: int = 128
LANDUSE_MAPPING_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
WBT_BOUNDARY_POLICY_SNAPSHOT_INVALID_MESSAGE = (
    "The WBT boundary policy snapshot is invalid. Submit delineation again."
)
WBT_BOUNDARY_POLICY_APPLY_FAILED_MESSAGE = (
    "The WBT boundary policy could not be applied. Submit delineation again."
)
WBT_SUBCATCHMENT_TREE_LOCK_TTL_SECONDS = TIMEOUT + 300
WBT_SUBCATCHMENT_ADMISSION_RETRY_ATTEMPTS = 5
_WBT_BUILD_LINK_KEY = "jobs:0,func:build_subcatchments_rq"
_WBT_RECEIPT_LINK_KEY = "jobs:1,func:abstract_watershed_rq"
_WBT_ADMISSION_FINGERPRINT_KEY = "wbt_subcatchment_admission_fingerprint"
_WBT_ADMISSION_ROOT_KEY = "wbt_subcatchment_admission_root"
_WBT_ADMISSION_BUILD_KEY = "wbt_subcatchment_admission_build"
_WBT_ADMISSION_RECEIPT_KEY = "wbt_subcatchment_admission_receipt"
_WBT_ADMISSION_PREVIOUS_KEY = "wbt_subcatchment_admission_previous"
_COMPARE_AND_DELETE_TAIL_SCRIPT = """
local current = redis.call('GET', KEYS[1])
if current == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
""".strip()

_clean_env_for_system_tools = _fork_helpers._clean_env_for_system_tools
_build_fork_rsync_cmd = _fork_helpers._build_fork_rsync_cmd

_normalize_relpath = _archive_helpers._normalize_relpath
_is_archive_excluded_relpath = _archive_helpers._is_archive_excluded_relpath
_estimate_archive_required_bytes = _archive_helpers._estimate_archive_required_bytes
_assert_sufficient_disk_space = _archive_helpers._assert_sufficient_disk_space
_calculate_run_payload_bytes = _archive_helpers._calculate_run_payload_bytes
_collect_restore_members = _archive_helpers._collect_restore_members


def _build_channels_child_timeout(
    watershed: Watershed,
    requested_fill_or_breach: Optional[str],
) -> int:
    """Return a child timeout that preserves the Topaz cleanup margin."""
    effective_fill_or_breach = requested_fill_or_breach
    if effective_fill_or_breach is None:
        effective_fill_or_breach = getattr(watershed, "wbt_fill_or_breach", None)
    if effective_fill_or_breach == "topaz":
        return max(
            FETCH_DEM_AND_BUILD_CHANNELS_CHILD_TIMEOUT,
            TOPAZ_BUILD_CHANNELS_CHILD_TIMEOUT_MINIMUM,
        )
    return FETCH_DEM_AND_BUILD_CHANNELS_CHILD_TIMEOUT


def _delete_runtime() -> _delete_helpers.DeleteRuntime:
    return _delete_helpers.DeleteRuntime(
        get_current_job=get_current_job,
        get_wd=get_wd,
        publish_status=StatusMessenger.publish,
        clear_nodb_file_cache=clear_nodb_file_cache,
        clear_locks=clear_locks,
        rmtree=shutil.rmtree,
        sleep=time.sleep,
        logger=_logger,
    )


def _archive_runtime() -> _archive_helpers.ArchiveRuntime:
    return _archive_helpers.ArchiveRuntime(
        get_current_job=get_current_job,
        get_wd=get_wd,
        get_prep_from_runid=RedisPrep.getInstanceFromRunID,
        lock_statuses=lock_statuses,
        clear_nodb_file_cache=clear_nodb_file_cache,
        publish_status=StatusMessenger.publish,
        disk_usage=shutil.disk_usage,
        zip_file_cls=zipfile.ZipFile,
    )


def _require_directory_root(wd: str, root: str) -> None:
    resolved = nodir_resolve(wd, root, view="effective")
    if resolved is not None and getattr(resolved, "form", "dir") != "dir":
        raise NoDirError(
            http_status=409,
            code="NODIR_ARCHIVE_ACTIVE",
            message=f"{root} root is archive-backed; directory root required",
        )


def _require_directory_roots(wd: str, roots: Sequence[str]) -> None:
    for root in roots:
        _require_directory_root(wd, root)


def _run_with_directory_root_lock(
    wd: str,
    root: str,
    callback,
    *,
    purpose: str,
    lock_ttl_seconds: int | None = None,
):
    retry_attempts = max(1, int(DIRECTORY_ROOT_LOCK_RETRY_ATTEMPTS))
    retry_delay_seconds = max(0.0, float(DIRECTORY_ROOT_LOCK_RETRY_SECONDS))

    for attempt in range(1, retry_attempts + 1):
        _require_directory_root(wd, root)
        try:
            lock_kwargs = (
                {}
                if lock_ttl_seconds is None
                else {"ttl_seconds": lock_ttl_seconds}
            )
            with nodir_maintenance_lock(
                wd,
                root,
                purpose=purpose,
                **lock_kwargs,
            ):
                _require_directory_root(wd, root)
                return callback()
        except NoDirError as exc:
            if exc.code != "NODIR_LOCKED" or attempt >= retry_attempts:
                raise
            _logger.warning(
                "Directory lock busy for root=%s purpose=%s; retrying (%d/%d)",
                root,
                purpose,
                attempt,
                retry_attempts,
            )
            if retry_delay_seconds > 0:
                time.sleep(retry_delay_seconds)


def _cancel_deferred_job(job: Job) -> None:
    """Atomically cancel a deferred job and detach its dependency membership."""
    dependency_keys = job.connection.smembers(job.dependencies_key)
    with job.connection.pipeline() as pipeline:
        DeferredJobRegistry(
            job.origin,
            connection=job.connection,
            job_class=job.__class__,
            serializer=job.serializer,
        ).remove(job, pipeline=pipeline)
        for dependency_id in dependency_keys:
            if isinstance(dependency_id, bytes):
                dependency_id = dependency_id.decode("utf-8")
            pipeline.srem(job.dependents_key_for(dependency_id), job.id)
        pipeline.delete(job.dependencies_key)
        job.cancel(pipeline=pipeline)
        pipeline.execute()


def _cancel_policy_dependents(job: Job) -> None:
    for dependent_id in sorted(job.dependent_ids):
        try:
            dependent = Job.fetch(dependent_id, connection=job.connection)
            if dependent.meta.get("wbt_completion_receipt_for") != job.id:
                continue
            _cancel_deferred_job(dependent)
        except (InvalidJobOperation, NoSuchJobError):
            _logger.warning(
                "WBT policy dependent disappeared "
                "(job_id=%s dependent_id=%s)",
                job.id,
                dependent_id,
            )


def _record_wbt_policy_failure(
    job: Job,
    *,
    runid: str,
    code: str,
    message: str,
    cancel_dependents: bool,
) -> str:
    error_id = __import__("uuid").uuid4().hex
    job.meta["error"] = {"code": code, "message": message}
    job.meta["error_id"] = error_id
    job.meta.pop("exc_string", None)
    job.save_meta()
    if cancel_dependents:
        _cancel_policy_dependents(job)
    _logger.error(
        "Controlled WBT policy failure "
        "[error_id=%s runid=%s code=%s job_id=%s]",
        error_id,
        runid,
        code,
        job.id,
        extra={
            "error_id": error_id,
            "runid": runid,
            "error_code": code,
            "job_id": job.id,
        },
    )
    return error_id


def _validate_optional_wbt_policy(
    job: Job,
    runid: str,
    boundary_policy: dict[str, Any] | None,
):
    job_meta = getattr(job, "meta", None)
    raw_snapshot = (
        job_meta.get(WBT_BOUNDARY_POLICY_SNAPSHOT_KEY)
        if isinstance(job_meta, dict)
        else None
    )
    if boundary_policy is None and raw_snapshot is None:
        return None
    if boundary_policy is None or raw_snapshot is None:
        raise WbtBoundaryPolicySnapshotError(
            "WBT boundary snapshot metadata and argument must both be present."
        )
    return validate_wbt_boundary_policy_snapshot(
        raw_snapshot,
        boundary_policy,
        expected_runid=runid,
    )


def _subcatchment_tail_key(runid: str) -> str:
    return f"rq:subcatchment-mutation-tail:{runid}"


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
        if receipt_dependencies:
            raise RuntimeError(
                "WBT completion receipt retains a stale dependency."
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
        if build_dependencies:
            raise RuntimeError("WBT build retains a stale prior dependency.")
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


def _register_deferred_job(job: Job, pipeline) -> None:
    job.set_status(JobStatus.DEFERRED, pipeline=pipeline)
    job.register_dependency(pipeline=pipeline)
    job.save(pipeline=pipeline)
    job.cleanup(ttl=job.ttl, pipeline=pipeline)


def _enqueue_serial_subcatchment_tree(
    redis_conn,
    queue: Queue,
    *,
    runid: str,
    updates: dict[str, Any],
    boundary_policy: dict[str, Any] | None,
    child_meta: dict[str, Any] | None,
    receipt_meta: dict[str, Any],
    parent_job: Job,
) -> tuple[Job, Job]:
    """Atomically admit one serialized mutation and its completion receipt."""
    tail_key = _subcatchment_tail_key(runid)
    fingerprint = _subcatchment_admission_fingerprint(
        parent_job_id=parent_job.id,
        queue_name=queue.name,
        runid=runid,
        updates=updates,
        boundary_policy=boundary_policy,
    )
    existing = _load_exact_subcatchment_tree(
        redis_conn,
        queue,
        parent_job=parent_job,
        fingerprint=fingerprint,
        tail_key=tail_key,
        require_current_tail=False,
    )
    if existing is not None:
        return existing

    child_id = new_rq_job_id()
    receipt_id = new_rq_job_id()
    original_parent_meta = dict(parent_job.meta)

    for attempt in range(WBT_SUBCATCHMENT_ADMISSION_RETRY_ATTEMPTS):
        pipeline = redis_conn.pipeline()
        try:
            pipeline.watch(tail_key, parent_job.key)
            previous_tail_id = _decode_redis_text(pipeline.get(tail_key))
            previous_tail = _fetch_job_or_none(previous_tail_id, redis_conn)
            if previous_tail is not None:
                pipeline.watch(previous_tail.key)
                previous_tail.refresh()
                if _is_terminal_job(previous_tail):
                    previous_tail_id = None
                    previous_tail = None
                else:
                    location_keys = _active_job_location_keys(previous_tail)
                    if location_keys:
                        pipeline.watch(*location_keys)
                if (
                    previous_tail is not None
                    and not _active_job_has_execution_location(previous_tail)
                ):
                    # Validate that the watched tail/job remained unchanged
                    # before diagnosing an orphan instead of a live transition.
                    pipeline.multi()
                    pipeline.exists(previous_tail.key)
                    pipeline.execute()
                    raise RuntimeError(
                        "WBT subcatchment admission found a nonterminal "
                        "tail outside every valid execution registry."
                    )
            else:
                previous_tail_id = None

            dependency = (
                None
                if previous_tail_id is None
                else Dependency(
                    jobs=[previous_tail_id],
                    allow_failure=True,
                )
            )
            registered_child_meta = dict(child_meta or {})
            registered_child_meta.update(
                {
                    _WBT_ADMISSION_FINGERPRINT_KEY: fingerprint,
                    _WBT_ADMISSION_ROOT_KEY: parent_job.id,
                    _WBT_ADMISSION_RECEIPT_KEY: receipt_id,
                    _WBT_ADMISSION_PREVIOUS_KEY: previous_tail_id,
                }
            )
            registered_receipt_meta = dict(receipt_meta)
            registered_receipt_meta.update(
                {
                    "wbt_completion_receipt_for": child_id,
                    _WBT_ADMISSION_FINGERPRINT_KEY: fingerprint,
                    _WBT_ADMISSION_ROOT_KEY: parent_job.id,
                    _WBT_ADMISSION_BUILD_KEY: child_id,
                }
            )
            child = queue.create_job(
                build_subcatchments_rq,
                args=(runid, updates, boundary_policy, True),
                timeout=TIMEOUT,
                depends_on=dependency,
                job_id=child_id,
                meta=registered_child_meta,
            )
            receipt = queue.create_job(
                abstract_watershed_rq,
                args=(runid, True),
                timeout=TIMEOUT,
                # Failure tolerant so a failed build still releases the receipt.
                # No release_deferred_job_if_ready here: this runs inside the
                # admission WATCH/MULTI, which registers deferral explicitly.
                depends_on=failure_tolerant_depends_on(child),
                job_id=receipt_id,
                meta=registered_receipt_meta,
            )

            # Prime version caches before MULTI so every subsequent operation
            # contributes only commands to the one admission transaction.
            queue.get_redis_server_version()
            child.get_redis_server_version()
            receipt.get_redis_server_version()

            parent_job.meta[_WBT_BUILD_LINK_KEY] = child.id
            parent_job.meta[_WBT_RECEIPT_LINK_KEY] = receipt.id
            parent_job.meta[_WBT_ADMISSION_FINGERPRINT_KEY] = fingerprint

            pipeline.multi()
            if dependency is None:
                queue._enqueue_job(child, pipeline=pipeline)
            else:
                _register_deferred_job(child, pipeline)
            _register_deferred_job(receipt, pipeline)
            parent_job.save(pipeline=pipeline)
            pipeline.set(tail_key, child.id)
            pipeline.execute()
            return child, receipt
        except WatchError:
            parent_job.meta = dict(original_parent_meta)
            parent_job.refresh()
            exact = _load_exact_subcatchment_tree(
                redis_conn,
                queue,
                parent_job=parent_job,
                fingerprint=fingerprint,
                tail_key=tail_key,
                require_current_tail=False,
            )
            if exact is not None:
                return exact
            original_parent_meta = dict(parent_job.meta)
            if attempt + 1 >= WBT_SUBCATCHMENT_ADMISSION_RETRY_ATTEMPTS:
                raise RuntimeError(
                    "WBT subcatchment admission conflicted five times; "
                    "no work was created."
                )
        except redis.RedisError:
            try:
                exact = _load_exact_subcatchment_tree(
                    redis_conn,
                    queue,
                    parent_job=parent_job,
                    fingerprint=fingerprint,
                    tail_key=tail_key,
                    require_current_tail=True,
                )
            except (NoSuchJobError, redis.RedisError, RuntimeError):
                parent_job.meta = dict(original_parent_meta)
                raise RuntimeError(
                    "WBT subcatchment admission result is ambiguous and "
                    "could not be reconciled exactly."
                )
            if exact is None:
                parent_job.meta = dict(original_parent_meta)
                raise RuntimeError(
                    "WBT subcatchment admission failed before commit."
                )
            return exact
        finally:
            pipeline.reset()

    raise AssertionError("unreachable WBT subcatchment admission state")


def _release_subcatchment_tail(
    redis_conn,
    runid: str,
    expected_job_id: str,
) -> None:
    redis_conn.eval(
        _COMPARE_AND_DELETE_TAIL_SCRIPT,
        1,
        _subcatchment_tail_key(runid),
        expected_job_id,
    )


def _run_with_directory_roots_lock(
    wd: str,
    roots: Sequence[str],
    callback,
    *,
    purpose: str,
):
    lock_roots = tuple(sorted({str(root) for root in roots}))
    retry_attempts = max(1, int(DIRECTORY_ROOT_LOCK_RETRY_ATTEMPTS))
    retry_delay_seconds = max(0.0, float(DIRECTORY_ROOT_LOCK_RETRY_SECONDS))

    for attempt in range(1, retry_attempts + 1):
        _require_directory_roots(wd, lock_roots)
        try:
            with ExitStack() as stack:
                for root in lock_roots:
                    stack.enter_context(nodir_maintenance_lock(wd, root, purpose=f"{purpose}/{root}"))
                _require_directory_roots(wd, lock_roots)
                return callback()
        except NoDirError as exc:
            if exc.code != "NODIR_LOCKED" or attempt >= retry_attempts:
                raise
            _logger.warning(
                "Directory locks busy for roots=%s purpose=%s; retrying (%d/%d)",
                ",".join(lock_roots),
                purpose,
                attempt,
                retry_attempts,
            )
            if retry_delay_seconds > 0:
                time.sleep(retry_delay_seconds)


@with_exception_logging
def test_run_rq(runid: str) -> tuple[str, ...]:
    """Execute the full preparation pipeline inline as a smoke-test.

    This helper clones a base project into a `-latest` working directory,
    clears locks, and runs through DEM/landuse/climate prep before invoking
    the WEPP runners. It mirrors the asynchronous orchestration but keeps the
    work local so developers can validate pipelines without RQ dependencies.

    Args:
        runid: The project identifier already provisioned on disk.

    Returns:
        Tuple of cleared lock identifiers from `clear_locks`. Empty when no
        locks were cleared.

    Raises:
        Exception: Any failure in controller prep or WEPP execution is surfaced.
    """
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        class TaskStub:
            @classmethod
            def is_task_enabled(cls, task: TaskEnum) -> bool:
                return True
            
        base_wd = get_wd(runid)

        new_runid = f'{runid}-latest'
        runid_wd = get_primary_wd(new_runid)

        StatusMessenger.publish(status_channel, f'base_wd: {base_wd}')
        init_required = False
        if os.path.exists(runid_wd) and TaskStub.is_task_enabled(TaskEnum.fetch_dem):
            StatusMessenger.publish(status_channel, f'removing existing runid_wd: {runid_wd}')
            shutil.rmtree(runid_wd)
            init_required = True

        if not os.path.exists(runid_wd):
            init_required = True
        
        StatusMessenger.publish(status_channel, f'init_required: {init_required}')
        prep: RedisPrep | None = None
        locks_cleared: list[str] | None = None
        if init_required:
            StatusMessenger.publish(status_channel, f'copying base project to runid_wd: {runid_wd}')
            shutil.copytree(base_wd, runid_wd)

            for nodb_fn in glob(_join(runid_wd, '*.nodb')):
                with open(nodb_fn, 'r') as fp:
                    state = json.load(fp)
                state.setdefault('py/state', {})['wd'] = runid_wd
                with open(nodb_fn, 'w') as fp:
                    json.dump(state, fp)
                    fp.flush()
                    os.fsync(fp.fileno())
            clear_nodb_file_cache(runid)
            StatusMessenger.publish(status_channel, 'cleared NoDb file cache')
            try:
                locks_cleared = clear_locks(runid)
                StatusMessenger.publish(status_channel, f'cleared NoDb locks: {locks_cleared}')
            except RuntimeError:
                pass

        StatusMessenger.publish(status_channel, 'getting RedisPrep instance')
        prep = RedisPrep.getInstance(runid_wd)
        StatusMessenger.publish(status_channel, prep.timestamps_report())

        if init_required:
            StatusMessenger.publish(status_channel, f'init_required: {init_required} removing all RedisPrep timestamps')
            prep.remove_all_timestamp()
            StatusMessenger.publish(status_channel, prep.timestamps_report())

        StatusMessenger.publish(status_channel, 'getting NoDb instances')
        ron = Ron.getInstance(runid_wd)
        watershed = Watershed.getInstance(runid_wd)
        landuse = Landuse.getInstance(runid_wd)
        soils = Soils.getInstance(runid_wd)
        climate = Climate.getInstance(runid_wd)
        wepp = Wepp.getInstance(runid_wd)
        
        if TaskStub.is_task_enabled(TaskEnum.fetch_dem) and prep[str(TaskEnum.fetch_dem)] is None:
            StatusMessenger.publish(status_channel, 'fetching DEM')
            ron.fetch_dem()

        if TaskStub.is_task_enabled(TaskEnum.build_channels) and prep[str(TaskEnum.build_channels)] is None:
            StatusMessenger.publish(status_channel, f'building channels')
            _run_with_directory_root_lock(
                runid_wd,
                "watershed",
                lambda: watershed.build_channels(),
                purpose="test-run-build-channels",
            )

        if TaskStub.is_task_enabled(TaskEnum.find_outlet) and prep[str(TaskEnum.find_outlet)] is None:
            StatusMessenger.publish(status_channel, f'setting outlet')
            _run_with_directory_root_lock(
                runid_wd,
                "watershed",
                lambda: watershed.set_outlet(
                    lng=watershed.outlet.requested_loc.lng,
                    lat=watershed.outlet.requested_loc.lat,
                ),
                purpose="test-run-set-outlet",
            )

        if TaskStub.is_task_enabled(TaskEnum.build_subcatchments) and prep[str(TaskEnum.build_subcatchments)] is None:
            StatusMessenger.publish(status_channel, f'building subcatchments')
            _run_with_directory_root_lock(
                runid_wd,
                "watershed",
                lambda: watershed.build_subcatchments(),
                purpose="test-run-build-subcatchments",
            )

        if TaskStub.is_task_enabled(TaskEnum.abstract_watershed) and prep[str(TaskEnum.abstract_watershed)] is None:
            StatusMessenger.publish(status_channel, f'abstracting watershed')
            _run_with_directory_root_lock(
                runid_wd,
                "watershed",
                lambda: watershed.abstract_watershed(),
                purpose="test-run-abstract-watershed",
            )

        if TaskStub.is_task_enabled(TaskEnum.build_landuse) and prep[str(TaskEnum.build_landuse)] is None:
            StatusMessenger.publish(status_channel, f'building landuse')
            _run_with_directory_root_lock(
                runid_wd,
                "landuse",
                lambda: landuse.build(),
                purpose="test-run-build-landuse",
            )

        if TaskStub.is_task_enabled(TaskEnum.build_soils) and prep[str(TaskEnum.build_soils)] is None:
            StatusMessenger.publish(status_channel, f'building soils')
            _run_with_directory_root_lock(
                runid_wd,
                "soils",
                lambda: soils.build(),
                purpose="test-run-build-soils",
            )

        if TaskStub.is_task_enabled(TaskEnum.build_climate) and prep[str(TaskEnum.build_climate)] is None:
            StatusMessenger.publish(status_channel, f'building climate')
            _run_with_directory_root_lock(
                runid_wd,
                "climate",
                lambda: climate.build(),
                purpose="test-run-build-climate",
            )

        rap_ts = RAP_TS.tryGetInstance(runid_wd)
        StatusMessenger.publish(status_channel, f'rap_ts: {rap_ts}')
        if rap_ts and TaskStub.is_task_enabled(TaskEnum.fetch_rap_ts) \
            and prep[str(TaskEnum.fetch_rap_ts)] is None:
            StatusMessenger.publish(status_channel, f'fetching RAP TS')
            rap_ts.acquire_rasters(
                start_year=climate.observed_start_year,
                end_year=climate.observed_end_year,
            )
            StatusMessenger.publish(status_channel, f'analyzing RAP TS')
            rap_ts.analyze()

        run_hillslopes = TaskStub.is_task_enabled(TaskEnum.run_wepp_hillslopes) \
            and prep[str(TaskEnum.run_wepp_hillslopes)] is None
        run_watershed = TaskStub.is_task_enabled(TaskEnum.run_wepp_watershed) \
            and prep[str(TaskEnum.run_wepp_watershed)] is None

        StatusMessenger.publish(status_channel, f'run_hillslopes: {run_hillslopes}')
        StatusMessenger.publish(status_channel, f'run_watershed: {run_watershed}')

        if run_hillslopes:
            StatusMessenger.publish(status_channel, 'calling wepp.clean()')
            wepp.clean()

        if run_hillslopes or run_watershed:
            StatusMessenger.publish(status_channel, 'calling wepp._check_and_set_baseflow_map()')
            wepp._check_and_set_baseflow_map()
            StatusMessenger.publish(status_channel, 'calling wepp._check_and_set_phosphorus_map()')
            wepp._check_and_set_phosphorus_map()

        if run_hillslopes:
            StatusMessenger.publish(status_channel, 'calling wepp.prep_hillslopes()')
            wepp.prep_hillslopes()
            StatusMessenger.publish(status_channel, 'calling wepp.run_hillslopes()')
            wepp.run_hillslopes()

        if run_watershed:
            StatusMessenger.publish(status_channel, 'calling wepp.prep_watershed()')
            wepp.prep_watershed()
            StatusMessenger.publish(status_channel, 'calling wepp.run_watershed()')
            wepp.run_watershed()  # also triggers post wepp processing

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')

        return tuple(locks_cleared) if locks_cleared else ()

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:272", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def set_run_readonly_rq(runid: str, readonly: bool) -> None:
    """Toggle read-only state for a run and manage browse manifests.

    Args:
        runid: Identifier used to locate the working directory.
        readonly: Flag indicating whether the run should become read-only.

    Raises:
        Exception: Any error during manifest creation/removal or NoDb updates.
    """
    from wepppy.microservices.browse import create_manifest, remove_manifest, MANIFEST_FILENAME

    job = get_current_job()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid}, readonly={readonly})')

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    previous_state = ron.readonly
    prep = RedisPrep.tryGetInstance(wd)

    try:
        if prep is not None:
            try:
                prep.set_rq_job_id('set_readonly', job.id)
                prep.remove_timestamp(TaskEnum.set_readonly)
            except (redis.exceptions.RedisError, OSError, json.JSONDecodeError, ValueError, TypeError):
                pass

        if readonly:
            if not previous_state:
                ron.readonly = True

            if ron.is_child_run:
                StatusMessenger.publish_command(
                    runid,
                    f'rq:{job.id} {MANIFEST_FILENAME} skipped (child run)'
                )
            else:
                StatusMessenger.publish(
                    status_channel,
                    f'rq:{job.id} STATUS {MANIFEST_FILENAME} creation started'
                )
                with ron.timed('Create manifest'):
                    create_manifest(wd)
                    if not _exists(_join(wd, MANIFEST_FILENAME)):
                        raise RuntimeError(f'{MANIFEST_FILENAME} was not created')
                StatusMessenger.publish_command(
                    runid,
                    f'rq:{job.id} {MANIFEST_FILENAME} creation finished'
                )
        else:
            if previous_state:
                ron.readonly = False

            remove_manifest(wd)
            if _exists(_join(wd, MANIFEST_FILENAME)):
                raise RuntimeError(f'Unable to remove {MANIFEST_FILENAME}')
            StatusMessenger.publish_command(
                runid,
                f'rq:{job.id} {MANIFEST_FILENAME} removed'
            )

        try:
            from wepppy.weppcloud.utils.run_ttl import sync_ttl_policy

            sync_ttl_policy(wd, touched_by="readonly")
        except Exception as exc:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:346", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            StatusMessenger.publish(
                status_channel,
                f'rq:{job.id} STATUS TTL sync failed ({exc})',
            )

        if prep is not None:
            try:
                prep.timestamp(TaskEnum.set_readonly)
            except (redis.exceptions.RedisError, OSError, json.JSONDecodeError, ValueError, TypeError):
                pass

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid}, readonly={readonly})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:359", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        try:
            if ron.readonly != previous_state:
                ron.readonly = previous_state
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:363", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            pass

        failure_suffix = 'creation failed' if readonly else 'removal failed'
        StatusMessenger.publish_command(
            runid,
            f'rq:{job.id} {MANIFEST_FILENAME} {failure_suffix}'
        )
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid}, readonly={readonly})')
        raise


@with_exception_logging
def delete_run_rq(runid: str, wd: Optional[str] = None, *, delete_files: bool = False) -> None:
    _delete_helpers.delete_run_rq(
        runid,
        wd=wd,
        delete_files=delete_files,
        runtime=_delete_runtime(),
    )


@with_exception_logging
def gc_runs_rq(
    root: str = "/wc1/runs",
    limit: int = 200,
    dry_run: bool = False,
) -> Mapping[str, Any]:
    return _delete_helpers.gc_runs_rq(
        root=root,
        limit=limit,
        dry_run=dry_run,
        runtime=_delete_runtime(),
    )


@with_exception_logging
def compile_dot_logs_rq(
    *,
    access_log_path: Optional[str] = None,
    run_locations_path: Optional[str] = None,
    run_roots: Optional[list[str]] = None,
    legacy_roots: Optional[list[str]] = None,
) -> Mapping[str, Any]:
    return _delete_helpers.compile_dot_logs_rq(
        access_log_path=access_log_path,
        run_locations_path=run_locations_path,
        run_roots=list(run_roots) if run_roots is not None else None,
        legacy_roots=list(legacy_roots) if legacy_roots is not None else None,
        runtime=_delete_runtime(),
    )


@with_exception_logging
def index_usersum_docs_rq(
    *,
    usersum_base_dir: Optional[str] = None,
    repo_root: Optional[str] = None,
    write_index: bool = True,
    require_vendor_files: bool = False,
    sync_postgres: bool = True,
    db_url: Optional[str] = None,
) -> Mapping[str, Any]:
    return _delete_helpers.index_usersum_docs_rq(
        usersum_base_dir=usersum_base_dir,
        repo_root=repo_root,
        write_index=write_index,
        require_vendor_files=require_vendor_files,
        sync_postgres=sync_postgres,
        db_url=db_url,
        runtime=_delete_runtime(),
    )


@with_exception_logging
def init_sbs_map_rq(runid: str, sbs_map: str) -> None:
    """Persist an SBS map selection and timestamp the prep step.

    Args:
        runid: Identifier used to locate the working directory.
        sbs_map: Serialized SBS map payload selected by the user.

    Raises:
        Exception: Propagates failures while mutating NoDb state.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:watershed'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
            
        ron = Ron.getInstance(wd)
        sbs_scope = "baer.nodb" if "baer" in (ron.mods or ()) else "disturbed.nodb"
        clear_nodb_file_cache(runid, pup_relpath=sbs_scope)
        ron.init_sbs_map(sbs_map, ron.disturbed)
        
        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.init_sbs_map)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:440", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def fetch_dem_rq(
    runid: str,
    extent: Sequence[float],
    center: Optional[Sequence[float]],
    zoom: Optional[int],
    map_object: Any | None = None,
) -> None:
    """Fetch a DEM for the current map extent.

    Args:
        runid: Identifier used to locate the working directory.
        extent: Bounding box `[minx, miny, maxx, maxy]` in projected coords.
        center: Optional map center override; derived from extent when omitted.
        zoom: Optional zoom level; falls back to `DEFAULT_ZOOM` when missing.
        map_object: Optional hydrated Map object to reuse exact map geometry.

    Raises:
        Exception: Propagates size validation and DEM acquisition failures.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:channel_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        clear_nodb_file_cache(runid, pup_relpath="ron.nodb")
        ron = Ron.getInstance(wd)
        if map_object is not None:
            ron.set_map_object(map_object)
            extent = ron.map.extent  # type: ignore[assignment]
            center = ron.map.center  # type: ignore[assignment]
            zoom = ron.map.zoom      # type: ignore[assignment]
        else:
            if center is None:
                center = [(extent[0]+extent[2])/2, (extent[1]+extent[3])/2]
            
            if zoom is None:
                zoom = DEFAULT_ZOOM
            ron.set_map(extent, center, zoom)

        if ron.map.num_cols > ron.max_map_dimension_px or ron.map.num_rows > ron.max_map_dimension_px:
            raise Exception(f'Map size too large: {ron.map.num_cols}x{ron.map.num_rows}. Maximum is {ron.max_map_dimension_px}x{ron.max_map_dimension_px}.')
        
        ron.fetch_dem()
        
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:492", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

@with_exception_logging
def build_channels_rq(
    runid: str,
    csa: float,
    mcl: float,
    stream_pruning_method: Optional[str],
    wbt_fill_or_breach: Optional[str],
    wbt_blc_dist: Optional[int],
    root_job_id: Optional[str] = None,
) -> None:
    """Delineate channels for the watershed using configured thresholds.

    Args:
        runid: Identifier used to locate the working directory.
        csa: Contributing source area threshold.
        mcl: Minimum channel length threshold.
        stream_pruning_method: Optional stream-pruning selection (`ifolp` or `remove_short_streams`).
        wbt_fill_or_breach: Optional override for Whitebox fill/breach strategy.
        wbt_blc_dist: Optional breaching distance when Whitebox backend is used.
        root_job_id: Aggregate submission job used to correlate diagnostics.

    Raises:
        Exception: Propagates errors from watershed delineation.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:channel_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        watershed_holder: dict[str, Any] = {}
        def _mutate_watershed() -> None:
            clear_nodb_file_cache(runid, pup_relpath="watershed.nodb")
            watershed = Watershed.getInstance(wd)
            watershed_holder["value"] = watershed
            if watershed.delineation_backend_is_topaz:
                clear_nodb_file_cache(runid, pup_relpath="topaz.nodb")
            has_wbt_diagnostics = (
                watershed.delineation_backend_is_wbt and hasattr(watershed, "wbt_wd")
            )
            if has_wbt_diagnostics:
                job.meta["conditioning_diagnostics_required"] = True
                job.save_meta()
            if watershed.delineation_backend_is_wbt:
                if stream_pruning_method is not None:
                    StatusMessenger.publish(
                        status_channel,
                        f"Setting stream_pruning_method to {stream_pruning_method}",
                    )
                    watershed.stream_pruning_method = stream_pruning_method
                if wbt_fill_or_breach is not None:
                    StatusMessenger.publish(status_channel, f'Setting wbt_fill_or_breach to {wbt_fill_or_breach}')
                    watershed.wbt_fill_or_breach = wbt_fill_or_breach
                if wbt_blc_dist is not None:
                    StatusMessenger.publish(status_channel, f'Setting wbt_blc_dist to {wbt_blc_dist}')
                    watershed.wbt_blc_dist = wbt_blc_dist
            StatusMessenger.publish(status_channel, f'Building channels with csa={csa}, mcl={mcl}')
            watershed.build_channels(csa, mcl)
            if has_wbt_diagnostics:
                method = watershed.wbt_fill_or_breach
                diagnostics = getattr(
                    getattr(watershed, "_wbt", None),
                    "_conditioning_diagnostics_payload",
                    None,
                )
                if not isinstance(diagnostics, dict):
                    raise WbtConditioningDiagnosticsError("missing")
                watershed_holder["diagnostics"] = (method, diagnostics)

        _run_with_directory_root_lock(
            wd,
            "watershed",
            _mutate_watershed,
            purpose="build-channels-rq",
        )
        watershed = watershed_holder["value"]
        has_wbt_diagnostics = "diagnostics" in watershed_holder
        if has_wbt_diagnostics:
            method, diagnostics = watershed_holder["diagnostics"]
            diagnostics_root_job_id = str(root_job_id or job.meta.get("root_job_id") or job.id)
            reduced = {
                "schema_version": 1,
                "root_job_id": diagnostics_root_job_id,
                "producer_job_id": job.id,
                "operation_id": diagnostics["operation_id"],
                "method": method,
                "elevation_unit": "m",
                "maximum_raise": diagnostics["terrain_change"]["maximum_raise"],
                "maximum_cut": diagnostics["terrain_change"]["maximum_cut"],
                "summary": summarize_conditioning_diagnostics(diagnostics, method),
            }
            job.meta["conditioning_diagnostics"] = reduced
            job.save_meta()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        trigger_payload = ""
        if has_wbt_diagnostics:
            encoded = base64.urlsafe_b64encode(
                json.dumps(reduced, separators=(",", ":"), sort_keys=True).encode("utf-8")
            ).decode("ascii").rstrip("=")
            trigger_payload = f" DIAGNOSTICS_V1:{encoded}"
        StatusMessenger.publish(
            status_channel,
            f'rq:{job.id} TRIGGER{trigger_payload} channel_delineation BUILD_CHANNELS_TASK_COMPLETED',
        )
        
        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_channels)
    except WbtUnresolvedDepressionsError as exc:
        error_id = __import__("uuid").uuid4().hex
        job.meta["error"] = {
            "code": exc.code,
            "message": WBT_UNRESOLVED_DEPRESSION_MESSAGE,
            "details": {
                "unresolved_depression_count": exc.unresolved_depression_count,
                "search_distance_m": exc.search_distance_m,
                "search_distance_cells": exc.search_distance_cells,
            },
        }
        job.meta["error_id"] = error_id
        job.meta.pop("exc_string", None)
        job.save_meta()
        __import__("logging").getLogger(__name__).error(
            "Controlled WBT unresolved-depression failure "
            "[error_id=%s runid=%s unresolved_depression_count=%s "
            "search_distance_m=%s search_distance_cells=%s]",
            error_id,
            runid,
            exc.unresolved_depression_count,
            exc.search_distance_m,
            exc.search_distance_cells,
            extra={
                "error_id": error_id,
                "runid": runid,
                "unresolved_depression_count": exc.unresolved_depression_count,
                "search_distance_m": exc.search_distance_m,
                "search_distance_cells": exc.search_distance_cells,
            },
        )
        StatusMessenger.publish(
            status_channel,
            f"rq:{job.id} FAILED {func_name}({runid}) "
            f"{WBT_UNRESOLVED_DEPRESSION_MESSAGE}",
        )
        raise
    except WbtConditioningDiagnosticsError as exc:
        error_id = uuid.uuid4().hex
        job.meta["error"] = {
            "code": exc.code,
            "message": exc.public_message,
            "details": {"reason": exc.reason},
        }
        job.meta["error_id"] = error_id
        job.meta.pop("exc_string", None)
        job.save_meta()
        __import__("logging").getLogger(__name__).error(
            "Controlled WBT conditioning diagnostics failure "
            "[error_id=%s runid=%s reason=%s]",
            error_id,
            runid,
            exc.reason,
        )
        raise
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:540", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def fetch_dem_and_build_channels_rq(
    runid: str,
    extent: Optional[Sequence[float]],
    center: Optional[Sequence[float]],
    zoom: Optional[int],
    csa: float,
    mcl: float,
    stream_pruning_method: Optional[str],
    wbt_fill_or_breach: Optional[str],
    wbt_blc_dist: Optional[int],
    set_extent_mode: int,
    map_bounds_text: str,
    map_object: Any | None = None,
) -> None:
    """Chain DEM acquisition and channel building via dependent RQ jobs.

    Args:
        runid: Identifier used to locate the working directory.
        extent: Bounding box `[minx, miny, maxx, maxy]` in projected coords.
            Optional when `set_extent_mode` is 3 (Upload DEM).
        center: Optional map center override.
        zoom: Optional zoom level.
        csa: Contributing source area threshold.
        mcl: Minimum channel length threshold.
        stream_pruning_method: Optional stream-pruning selection (`ifolp` or `remove_short_streams`).
        wbt_fill_or_breach: Optional Whitebox fill/breach directive.
        wbt_blc_dist: Optional breaching distance for Whitebox runs.
        set_extent_mode: Serialized extent mode persisted on the watershed.
        map_bounds_text: User-facing bounds description stored with the run.
        map_object: Optional hydrated Map object to preserve exact map geometry.

    Raises:
        Exception: Propagates errors from job enqueueing or delineation.
    """
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:channel_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        wd = get_wd(runid)
        clear_nodb_file_cache(runid, pup_relpath="watershed.nodb")
        watershed = Watershed.getInstance(wd)
        watershed.set_extent_mode = int(set_extent_mode)
        watershed.map_bounds_text = map_bounds_text
        if int(set_extent_mode) != 3:
            watershed.uploaded_dem_filename = None

        build_channels_timeout = _build_channels_child_timeout(
            watershed,
            wbt_fill_or_breach,
        )
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            if int(set_extent_mode) == 3:
                bjob = q.enqueue_call(
                    build_channels_rq,
                    (
                        runid,
                        csa,
                        mcl,
                        stream_pruning_method,
                        wbt_fill_or_breach,
                        wbt_blc_dist,
                        job.id,
                    ),
                    timeout=build_channels_timeout,
                )
                job.meta['jobs:0,func:build_channels_rq'] = bjob.id
                job.save()
            else:
                ajob = q.enqueue_call(
                    fetch_dem_rq,
                    (runid, extent, center, zoom, map_object),
                    timeout=FETCH_DEM_AND_BUILD_CHANNELS_CHILD_TIMEOUT,
                )
                job.meta['jobs:0,func:fetch_dem_rq'] = ajob.id
                job.save()

                bjob = q.enqueue_call(
                    build_channels_rq,
                    (
                        runid,
                        csa,
                        mcl,
                        stream_pruning_method,
                        wbt_fill_or_breach,
                        wbt_blc_dist,
                        job.id,
                    ),
                    timeout=build_channels_timeout,
                    depends_on=failure_tolerant_depends_on(ajob),
                )
                release_deferred_job_if_ready(q, bjob)
                job.meta['jobs:1,func:build_channels_rq'] = bjob.id
                job.save()
        
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:612", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def set_outlet_rq(runid: str, outlet_lng: float, outlet_lat: float) -> None:
    """Persist the watershed outlet coordinates.

    Args:
        runid: Identifier used to locate the working directory.
        outlet_lng: Longitude of the outlet point.
        outlet_lat: Latitude of the outlet point.

    Raises:
        Exception: Propagates failures from watershed controller updates.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:outlet'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        def _set_outlet() -> None:
            clear_nodb_file_cache(runid, pup_relpath="watershed.nodb")
            watershed = Watershed.getInstance(wd)
            if watershed.delineation_backend_is_topaz:
                clear_nodb_file_cache(runid, pup_relpath="topaz.nodb")
            watershed.set_outlet(outlet_lng, outlet_lat)

        _run_with_directory_root_lock(
            wd,
            "watershed",
            _set_outlet,
            purpose="set-outlet-rq",
        )
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   outlet SET_OUTLET_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.set_outlet)

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:647", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

def _abstract_watershed_locked(
    runid: str,
    wd: str,
    watershed: Watershed | None = None,
) -> None:
    if watershed is None:
        clear_nodb_file_cache(runid, pup_relpath="watershed.nodb")
        watershed = Watershed.getInstance(wd)
        wait_for_path(watershed.subwta, logger=watershed.logger)

    watershed.abstract_watershed()

    persisted = Watershed.load_detached(wd, allow_nonexistent=True)
    persisted_centroid = (
        None
        if persisted is None
        else Watershed._coerce_centroid(getattr(persisted, "centroid", None))
    )
    if persisted_centroid is not None:
        return

    watershed.logger.warning(
        "Watershed centroid durability check failed after abstraction for runid=%s; "
        "attempting one bounded repair",
        runid,
    )
    watershed.require_centroid()

    repaired = Watershed.load_detached(wd, allow_nonexistent=True)
    repaired_centroid = (
        None
        if repaired is None
        else Watershed._coerce_centroid(getattr(repaired, "centroid", None))
    )
    if repaired_centroid is None:
        raise WatershedCentroidStateError(
            runid=runid,
            wd=wd,
            detail=(
                "post-abstraction durability verification failed after one repair attempt; "
                "persisted centroid remains unavailable"
            ),
        )


def build_subcatchments_rq(
    runid: str,
    updates: dict[str, Any] | None = None,
    boundary_policy: dict[str, Any] | None = None,
    abstract_after_build: bool = False,
) -> None:
    """Delineate subcatchments after channel extraction is complete.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates failures from watershed delineation.
    """
    phase = {"wbt_started": False}
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:subcatchment_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        def _mutate_watershed() -> None:
            try:
                clear_nodb_file_cache(runid, pup_relpath="watershed.nodb")
                watershed = Watershed.getInstance(wd)
            except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
                raise WbtBoundaryPolicyApplyError(
                    "Could not hydrate Watershed for WBT policy application."
                ) from exc

            snapshot = _validate_optional_wbt_policy(
                job,
                runid,
                boundary_policy,
            )
            execution_policy = (
                snapshot.effective_policy if snapshot is not None else None
            )
            if watershed.delineation_backend_is_topaz:
                clear_nodb_file_cache(runid, pup_relpath="topaz.nodb")
            if updates:
                try:
                    with watershed.locked():
                        if 'clip_hillslopes' in updates:
                            watershed._clip_hillslopes = bool(updates['clip_hillslopes'])  # type: ignore[attr-defined]
                        if 'walk_flowpaths' in updates:
                            watershed._walk_flowpaths = bool(updates['walk_flowpaths'])  # type: ignore[attr-defined]
                        if 'clip_hillslope_length' in updates:
                            watershed._clip_hillslope_length = float(updates['clip_hillslope_length'])  # type: ignore[attr-defined]
                        if 'mofe_target_length' in updates:
                            watershed._mofe_target_length = float(updates['mofe_target_length'])  # type: ignore[attr-defined]
                        if 'mofe_buffer' in updates:
                            watershed._mofe_buffer = bool(updates['mofe_buffer'])  # type: ignore[attr-defined]
                        if 'mofe_buffer_length' in updates:
                            watershed._mofe_buffer_length = float(updates['mofe_buffer_length'])  # type: ignore[attr-defined]
                        if 'bieger2015_widths' in updates:
                            watershed._bieger2015_widths = bool(updates['bieger2015_widths'])  # type: ignore[attr-defined]
                except (OSError, RuntimeError, ValueError) as exc:
                    raise WbtBoundaryPolicyApplyError(
                        "Could not apply subcatchment execution settings."
                    ) from exc
            phase["wbt_started"] = True
            watershed.build_subcatchments(
                boundary_touch_behavior=execution_policy,
            )
            wait_for_path(watershed.subwta, logger=watershed.logger)
            effective_policy = (
                execution_policy
                if execution_policy is not None
                else watershed.wbt_boundary_touch_behavior
            )
            if (
                watershed.delineation_backend_is_wbt
                and watershed.edge_hillslopes
                and effective_policy == "warn"
            ):
                warning = (
                    f"{WATERSHED_BOUNDARY_TOUCH_MESSAGE} "
                    f"Edge hillslope IDs: {watershed.edge_hillslopes}."
                )
                StatusMessenger.publish(
                    status_channel,
                    f'rq:{job.id} WARNING {func_name}({runid}) {warning}',
                )
            if abstract_after_build:
                _abstract_watershed_locked(runid, wd, watershed)

        _run_with_directory_root_lock(
            wd,
            "watershed",
            _mutate_watershed,
            purpose="build-subcatchments-rq",
            lock_ttl_seconds=(
                WBT_SUBCATCHMENT_TREE_LOCK_TTL_SECONDS
                if abstract_after_build
                else None
            ),
        )
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   subcatchment_delineation BUILD_SUBCATCHMENTS_TASK_COMPLETED')
        if abstract_after_build:
            StatusMessenger.publish(
                status_channel,
                f'rq:{job.id} TRIGGER   subcatchment_delineation '
                "WATERSHED_ABSTRACTION_TASK_COMPLETED",
            )
    except WbtBoundaryPolicySnapshotError:
        _record_wbt_policy_failure(
            job,
            runid=runid,
            code="wbt_boundary_policy_snapshot_invalid",
            message=WBT_BOUNDARY_POLICY_SNAPSHOT_INVALID_MESSAGE,
            cancel_dependents=True,
        )
        StatusMessenger.publish(
            status_channel,
            f'rq:{job.id} EXCEPTION {func_name}({runid}) '
            f'{WBT_BOUNDARY_POLICY_SNAPSHOT_INVALID_MESSAGE}',
        )
        raise
    except WbtBoundaryPolicyApplyError:
        _record_wbt_policy_failure(
            job,
            runid=runid,
            code="wbt_boundary_policy_apply_failed",
            message=WBT_BOUNDARY_POLICY_APPLY_FAILED_MESSAGE,
            cancel_dependents=True,
        )
        StatusMessenger.publish(
            status_channel,
            f'rq:{job.id} EXCEPTION {func_name}({runid}) '
            f'{WBT_BOUNDARY_POLICY_APPLY_FAILED_MESSAGE}',
        )
        raise
    except WatershedBoundaryTouchesEdgeError as exc:
        error_id = __import__("uuid").uuid4().hex
        job.meta["error"] = {
            "code": exc.code,
            "message": WATERSHED_BOUNDARY_TOUCH_MESSAGE,
            "details": {"edge_hillslope_ids": exc.edge_hillslope_ids},
        }
        job.meta["error_id"] = error_id
        job.meta.pop("exc_string", None)
        job.save_meta()
        _cancel_policy_dependents(job)
        _logger.error(
            "Controlled WBT boundary failure "
            "[error_id=%s runid=%s edge_hillslope_ids=%s]",
            error_id,
            runid,
            exc.edge_hillslope_ids,
            extra={
                "error_id": error_id,
                "runid": runid,
                "edge_hillslope_ids": exc.edge_hillslope_ids,
            },
        )
        StatusMessenger.publish(
            status_channel,
            f'rq:{job.id} EXCEPTION {func_name}({runid}) '
            f'{WATERSHED_BOUNDARY_TOUCH_MESSAGE}',
        )
        raise
    except Exception as exc:
        if boundary_policy is not None and not phase["wbt_started"]:
            apply_exc = WbtBoundaryPolicyApplyError(
                "WBT policy application failed before delineation."
            )
            _record_wbt_policy_failure(
                job,
                runid=runid,
                code="wbt_boundary_policy_apply_failed",
                message=WBT_BOUNDARY_POLICY_APPLY_FAILED_MESSAGE,
                cancel_dependents=True,
            )
            StatusMessenger.publish(
                status_channel,
                f'rq:{job.id} EXCEPTION {func_name}({runid}) '
                f'{WBT_BOUNDARY_POLICY_APPLY_FAILED_MESSAGE}',
            )
            raise apply_exc from exc
        if abstract_after_build:
            _cancel_policy_dependents(job)
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:691", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise
@with_exception_logging
def abstract_watershed_rq(
    runid: str,
    mutation_already_completed: bool = False,
) -> None:
    """Run the watershed abstraction step after subcatchments exist.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates failures from watershed abstraction routines.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:subcatchment_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        if not mutation_already_completed:
            _run_with_directory_root_lock(
                wd,
                "watershed",
                lambda: _abstract_watershed_locked(runid, wd),
                purpose="abstract-watershed-rq",
            )
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        if not mutation_already_completed:
            StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   subcatchment_delineation WATERSHED_ABSTRACTION_TASK_COMPLETED')
            prep = RedisPrep.getInstance(wd)
            prep.timestamp(TaskEnum.abstract_watershed)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:723", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise
    finally:
        if mutation_already_completed and "job" in locals():
            build_job_id = job.meta.get(_WBT_ADMISSION_BUILD_KEY)
            if isinstance(build_job_id, str):
                try:
                    _release_subcatchment_tail(
                        job.connection,
                        runid,
                        build_job_id,
                    )
                except redis.RedisError:
                    _logger.exception(
                        "Could not release subcatchment mutation tail "
                        "(runid=%s build_job_id=%s receipt_job_id=%s)",
                        runid,
                        build_job_id,
                        job.id,
                    )


@with_exception_logging
def build_subcatchments_and_abstract_watershed_rq(
    runid: str,
    updates: dict[str, Any] | None = None,
    boundary_policy: dict[str, Any] | None = None,
) -> None:
    """Enqueue subcatchment building followed by watershed abstraction.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates errors while enqueueing dependent jobs.
    """
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:subcatchment_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        snapshot = _validate_optional_wbt_policy(job, runid, boundary_policy)
        child_meta: dict[str, Any] = {}
        if snapshot is not None:
            child_meta[WBT_BOUNDARY_POLICY_SNAPSHOT_KEY] = snapshot.to_meta()
        auth_actor = job.meta.get("auth_actor")
        if isinstance(auth_actor, dict):
            child_meta["auth_actor"] = dict(auth_actor)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            receipt_meta: dict[str, Any] = {}
            if isinstance(auth_actor, dict):
                receipt_meta["auth_actor"] = dict(auth_actor)
            _enqueue_serial_subcatchment_tree(
                redis_conn,
                q,
                runid=runid,
                updates=updates or {},
                boundary_policy=boundary_policy,
                child_meta=child_meta or None,
                receipt_meta=receipt_meta,
                parent_job=job,
            )

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except WbtBoundaryPolicySnapshotError:
        _record_wbt_policy_failure(
            job,
            runid=runid,
            code="wbt_boundary_policy_snapshot_invalid",
            message=WBT_BOUNDARY_POLICY_SNAPSHOT_INVALID_MESSAGE,
            cancel_dependents=False,
        )
        StatusMessenger.publish(
            status_channel,
            f'rq:{job.id} EXCEPTION {func_name}({runid}) '
            f'{WBT_BOUNDARY_POLICY_SNAPSHOT_INVALID_MESSAGE}',
        )
        raise
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:764", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def build_rangeland_cover_rq(
    runid: str,
    rap_year: Optional[int] = None,
    default_covers: Optional[Mapping[str, float]] = None,
) -> None:
    """Construct rangeland cover layers for the watershed asynchronously."""

    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:rangeland_cover'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        clear_nodb_file_cache(runid, pup_relpath="rangeland_cover.nodb")
        rangeland_cover = RangelandCover.getInstance(wd)
        rangeland_cover.build(rap_year=rap_year, default_covers=default_covers)

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   rangeland_cover RANGELAND_COVER_BUILD_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_rangeland_cover)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:792", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def build_landuse_rq(runid: str) -> None:
    """Construct landuse layers for the watershed.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates errors from landuse controller build routines.
    """
    job_id = "unknown-job"
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{runid}:landuse'
    try:
        job = get_current_job()
        if job is not None and getattr(job, "id", None):
            job_id = str(job.id)

        wd = get_wd(runid)
        StatusMessenger.publish(status_channel, f'rq:{job_id} STARTED {func_name}({runid})')

        def _build_landuse() -> None:
            clear_nodb_file_cache(runid, pup_relpath="landuse.nodb")
            Landuse.getInstance(wd).build()

        _run_with_directory_root_lock(
            wd,
            "landuse",
            _build_landuse,
            purpose="build-landuse-rq",
        )
        StatusMessenger.publish(status_channel, f'rq:{job_id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job_id} TRIGGER   landuse LANDUSE_BUILD_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_landuse)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:824", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        try:
            StatusMessenger.publish(status_channel, f'rq:{job_id} EXCEPTION {func_name}({runid})')
        except Exception:
            # Best-effort telemetry boundary: never mask the original task failure
            # when status publish infrastructure is unavailable.
            _logger.exception(
                "Failed to publish landuse exception status update",
                extra={"runid": runid, "job_id": job_id},
            )
        raise


def _normalize_landuse_mapping_batch(
    mapping_edits: Sequence[Mapping[str, Any]] | Mapping[str, Any] | str,
    *,
    newdom: str | None = None,
) -> list[dict[str, str]]:
    if isinstance(mapping_edits, str):
        if newdom is None:
            raise ValueError("newdom must be provided when mapping_edits is a dom string")
        raw_edits: list[Mapping[str, Any]] = [{"dom": mapping_edits, "newdom": newdom}]
    elif isinstance(mapping_edits, Mapping):
        raw_edits = [mapping_edits]
    elif isinstance(mapping_edits, Sequence):
        raw_edits = list(mapping_edits)
    else:
        raise ValueError("mapping_edits must be a sequence of mapping objects")

    if len(raw_edits) == 0:
        raise ValueError("mapping_edits must include at least one edit")
    if len(raw_edits) > LANDUSE_MAPPING_BATCH_MAX_EDITS:
        raise ValueError(f"mapping_edits exceeds {LANDUSE_MAPPING_BATCH_MAX_EDITS} edits")

    collapsed: dict[str, dict[str, str]] = {}
    order: list[str] = []
    for idx, edit in enumerate(raw_edits):
        if not isinstance(edit, Mapping):
            raise ValueError(f"mapping_edits[{idx}] must be an object")
        dom_raw = edit.get("dom")
        newdom_raw = edit.get("newdom")
        if dom_raw is None or newdom_raw is None:
            raise ValueError(f"mapping_edits[{idx}] must include dom and newdom")

        dom_value = str(dom_raw).strip()
        newdom_value = str(newdom_raw).strip()
        if not dom_value or not newdom_value:
            raise ValueError(f"mapping_edits[{idx}] contains a blank dom or newdom")
        if len(dom_value) > LANDUSE_MAPPING_MAX_KEY_LENGTH:
            raise ValueError(f"mapping_edits[{idx}].dom exceeds {LANDUSE_MAPPING_MAX_KEY_LENGTH} characters")
        if len(newdom_value) > LANDUSE_MAPPING_MAX_KEY_LENGTH:
            raise ValueError(f"mapping_edits[{idx}].newdom exceeds {LANDUSE_MAPPING_MAX_KEY_LENGTH} characters")
        if LANDUSE_MAPPING_CONTROL_CHAR_RE.search(dom_value):
            raise ValueError(f"mapping_edits[{idx}].dom contains unsupported control characters")
        if LANDUSE_MAPPING_CONTROL_CHAR_RE.search(newdom_value):
            raise ValueError(f"mapping_edits[{idx}].newdom contains unsupported control characters")

        if dom_value not in collapsed:
            order.append(dom_value)
        collapsed[dom_value] = {"dom": dom_value, "newdom": newdom_value}

    return [collapsed[dom] for dom in order]


@with_exception_logging
def modify_landuse_mapping_rq(
    runid: str,
    mapping_edits: Sequence[Mapping[str, Any]] | Mapping[str, Any] | str,
    newdom: str | None = None,
) -> None:
    """Remap one or more landuse domain assignments asynchronously and rebuild managements."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f"{runid}:landuse"
        StatusMessenger.publish(status_channel, f"rq:{job.id} STARTED {func_name}({runid})")

        normalized_edits = _normalize_landuse_mapping_batch(mapping_edits, newdom=newdom)

        prep = RedisPrep.getInstance(wd)
        latest_mapping_job_id = prep.get_rq_job_id("modify_landuse_mapping_rq")
        if latest_mapping_job_id and latest_mapping_job_id != job.id:
            StatusMessenger.publish(
                status_channel,
                f"rq:{job.id} SKIPPED {func_name}({runid}) stale job superseded by rq:{latest_mapping_job_id}",
            )
            return

        def _modify_mapping_batch() -> bool:
            latest_mapping_job_id_locked = prep.get_rq_job_id("modify_landuse_mapping_rq")
            if latest_mapping_job_id_locked and latest_mapping_job_id_locked != job.id:
                StatusMessenger.publish(
                    status_channel,
                    (
                        f"rq:{job.id} SKIPPED {func_name}({runid}) "
                        f"stale job superseded by rq:{latest_mapping_job_id_locked} (lock gate)"
                    ),
                )
                return False

            # Mutation jobs must not hydrate from the detached Redis cache:
            # cached payloads preserve the controller's pre-write file signature,
            # which makes the subsequent dump fail the stale-write guard.
            clear_nodb_file_cache(runid, pup_relpath="landuse.nodb")
            landuse = Landuse.getInstance(wd, ignore_lock=True)
            original_domlc_d = dict(landuse.domlc_d)
            domlc_mofe_d = getattr(landuse, "domlc_mofe_d", None)
            original_domlc_mofe_d = copy.deepcopy(domlc_mofe_d) if isinstance(domlc_mofe_d, dict) else None
            try:
                original_managements = copy.deepcopy(landuse.managements)
            except Exception:  # broad-except: optional RQ option-logging boundary
                original_managements = None

            with landuse.locked():
                missing_sources = sorted({
                    edit["dom"] for edit in normalized_edits if edit["dom"] not in landuse.managements
                })
                if missing_sources:
                    missing_csv = ", ".join(missing_sources)
                    raise ValueError(f"Unknown mapping dom value(s): {missing_csv}")

                updated_domlc_d = dict(landuse.domlc_d)
                updated_domlc_mofe_d = copy.deepcopy(domlc_mofe_d) if isinstance(domlc_mofe_d, dict) else None

                for edit in normalized_edits:
                    source_dom = edit["dom"]
                    target_dom = edit["newdom"]
                    for topazid, current_dom in updated_domlc_d.items():
                        if str(current_dom) == source_dom:
                            updated_domlc_d[topazid] = target_dom

                    if isinstance(updated_domlc_mofe_d, dict):
                        for _topaz_id, ofe_map in updated_domlc_mofe_d.items():
                            if not isinstance(ofe_map, dict):
                                continue
                            for ofe_id, current_dom in ofe_map.items():
                                if str(current_dom) == source_dom:
                                    ofe_map[ofe_id] = target_dom

                landuse.domlc_d = updated_domlc_d
                if updated_domlc_mofe_d is not None:
                    landuse.domlc_mofe_d = updated_domlc_mofe_d

            try:
                landuse.build_managements()
            except Exception:
                with landuse.locked():
                    landuse.domlc_d = original_domlc_d
                    if original_domlc_mofe_d is not None:
                        landuse.domlc_mofe_d = original_domlc_mofe_d
                    if original_managements is not None:
                        landuse.managements = original_managements
                raise
            return True

        did_apply = _run_with_directory_root_lock(
            wd,
            "landuse",
            _modify_mapping_batch,
            purpose="modify-landuse-mapping-rq",
        )
        if did_apply is False:
            return

        StatusMessenger.publish(status_channel, f"rq:{job.id} COMPLETED {func_name}({runid})")
        StatusMessenger.publish(
            status_channel,
            f"rq:{job.id} TRIGGER   landuse LANDUSE_MODIFY_MAPPING_TASK_COMPLETED",
        )
    except Exception:  # broad-except: RQ task boundary preserves terminal status contract
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:859", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f"rq:{job.id} EXCEPTION {func_name}({runid})")
        raise


@with_exception_logging
def build_treatments_rq(runid: str) -> None:
    """Apply treatments to landuse and soils."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:treatments'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        def _build_treatments() -> None:
            clear_nodb_file_cache(runid, pup_relpath="landuse.nodb")
            clear_nodb_file_cache(runid, pup_relpath="soils.nodb")
            Treatments.getInstance(wd).build_treatments()

        _run_with_directory_roots_lock(
            wd,
            ("landuse", "soils"),
            _build_treatments,
            purpose="build-treatments-rq",
        )
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(
            status_channel,
            f'rq:{job.id} TRIGGER   treatments TREATMENTS_BUILD_TASK_COMPLETED',
        )

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_treatments)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:852", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def build_soils_rq(runid: str) -> None:
    """Build soil layers for the watershed.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates errors from soil controller build routines.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:soils'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        def _build_soils() -> None:
            clear_nodb_file_cache(runid, pup_relpath="soils.nodb")
            Soils.getInstance(wd).build()

        _run_with_directory_root_lock(
            wd,
            "soils",
            _build_soils,
            purpose="build-soils-rq",
        )
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   soils SOILS_BUILD_TASK_COMPLETED')
        
        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_soils)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:884", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

    
@with_exception_logging
def build_climate_rq(runid: str) -> None:
    """Generate climate inputs for the watershed.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates errors from climate controller build routines.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:climate'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        payload_for_build: Optional[dict[str, Any]] = None
        if isinstance(getattr(job, "meta", None), Mapping):
            raw_payload = job.meta.get("build_payload")
            if isinstance(raw_payload, Mapping):
                payload_for_build = copy.deepcopy(dict(raw_payload))

        def _build_climate() -> None:
            clear_nodb_file_cache(runid, pup_relpath="climate.nodb")
            climate = Climate.getInstance(wd)
            if payload_for_build is not None:
                # Re-apply the enqueue-time payload so late state writes cannot
                # clobber the exact climate configuration this job was created for.
                climate.parse_inputs(payload_for_build)
                payload_observed_start_year = payload_for_build.get("observed_start_year")
                climate_observed_start_year = getattr(climate, "_observed_start_year", None)
                if payload_observed_start_year not in (None, "") and climate_observed_start_year == "":
                    _logger.warning(
                        "build_climate_rq: observed_start_year emptied after payload replay",
                        extra={
                            "runid": runid,
                            "job_id": job.id,
                            "payload_observed_start_year": payload_observed_start_year,
                            "climate_observed_start_year": climate_observed_start_year,
                            "climate_mode": getattr(climate, "_climate_mode", None),
                        },
                    )
            climate.build()

        _run_with_directory_root_lock(
            wd,
            "climate",
            _build_climate,
            purpose="build-climate-rq",
        )
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   climate CLIMATE_BUILD_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_climate)
    except ClimateMultipleBuildSupersededError as exc:
        _logger.warning(
            "Climate build superseded before finalization",
            extra={"runid": runid, "job_id": getattr(job, "id", None)},
        )
        StatusMessenger.publish(
            status_channel,
            f'rq:{job.id} SUPERSEDED {func_name}({runid}): {exc}',
        )
        raise
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:916", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def upload_cli_rq(runid: str, cli_filename: str) -> None:
    """Apply a user-uploaded CLI file to the run climate state."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:climate'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        def _set_user_defined_cli() -> None:
            clear_nodb_file_cache(runid, pup_relpath="climate.nodb")
            Climate.getInstance(wd).set_user_defined_cli(cli_filename)

        _run_with_directory_root_lock(
            wd,
            "climate",
            _set_user_defined_cli,
            purpose="upload-cli-rq",
        )
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   climate CLIMATE_BUILD_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_climate)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:941", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def run_ash_rq(
    runid: str,
    fire_date: str,
    ini_white_ash_depth_mm: float,
    ini_black_ash_depth_mm: float,
) -> None:
    """Execute the ash transport model for the given scenario parameters.

    Args:
        runid: Identifier used to locate the working directory.
        fire_date: ISO date string representing the fire event.
        ini_white_ash_depth_mm: Initial white ash depth in millimeters.
        ini_black_ash_depth_mm: Initial black ash depth in millimeters.

    Raises:
        Exception: Propagates errors from ash model execution.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:ash'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        def _run_ash() -> None:
            clear_nodb_file_cache(runid, pup_relpath="ash.nodb")
            ash = Ash.getInstance(wd)
            ash.run_ash(fire_date, ini_white_ash_depth_mm, ini_black_ash_depth_mm)

        _run_with_directory_roots_lock(
            wd,
            ("climate", "watershed", "landuse"),
            _run_ash,
            purpose="run-ash-rq",
        )

        wepp = Wepp.getInstance(wd)
        run_totalwatsed3(
            wepp.wepp_interchange_dir,
            baseflow_opts=wepp.baseflow_opts,
        )

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   ash ASH_RUN_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.run_watar)


    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:990", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def run_debris_flow_rq(runid: str, *, payload: Optional[Mapping[str, Any]] = None) -> None:
    """Run the debris flow model for the current watershed configuration.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates errors from debris flow computations.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:debris_flow'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        options = payload or {}
        cc = options.get("clay_pct")
        ll = options.get("liquid_limit")
        req_datasource = options.get("datasource")

        def _run_debris_flow() -> None:
            clear_nodb_file_cache(runid, pup_relpath="debris_flow.nodb")
            debris = DebrisFlow.getInstance(wd)
            debris.run_debris_flow(cc=cc, ll=ll, req_datasource=req_datasource)

        _run_with_directory_roots_lock(
            wd,
            ("watershed", "soils"),
            _run_debris_flow,
            purpose="run-debris-flow-rq",
        )

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   debris_flow DEBRIS_FLOW_RUN_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.run_watar)

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:1030", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def run_rhem_rq(runid: str, *, payload: Optional[Mapping[str, Any]] = None) -> None:
    """Execute the rangeland hydrology and erosion model (RHEM).

    Args:
        runid: Identifier used to locate the working directory.
        payload: Optional controller-supplied overrides that adjust which stages
            execute (``clean``, ``prep``, ``run`` booleans). Defaults run every
            stage to preserve legacy behavior.

    Raises:
        Exception: Propagates errors from RHEM preprocessing or execution.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:rhem'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        rhem = Rhem.getInstance(wd)
        options = payload or {}

        should_clean = options.get("clean")
        if should_clean is None:
            should_clean = options.get("clean_hillslopes", True)
        if should_clean is None:
            should_clean = True

        should_prep = options.get("prep")
        if should_prep is None:
            should_prep = options.get("prep_hillslopes", True)
        if should_prep is None:
            should_prep = True

        should_run = options.get("run")
        if should_run is None:
            should_run = options.get("run_hillslopes", True)
        if should_run is None:
            should_run = True

        if should_clean:
            rhem.clean()
        else:
            StatusMessenger.publish(status_channel, "Skipping RHEM clean step (payload clean=False).")
        if should_prep:
            rhem.prep_hillslopes()
        else:
            StatusMessenger.publish(status_channel, "Skipping RHEM hillslope prep (payload prep=False).")
        if should_run:
            rhem.run_hillslopes()
        else:
            StatusMessenger.publish(status_channel, "Skipping RHEM hillslope run (payload run=False).")

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   rhem RHEM_RUN_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.run_rhem)

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:1095", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

# Fork Functions
# see docs/ui-docs/weppcloud-project-forking.md for fork console + backend architecture

def _set_fork_destination_outcome(
    connection: Any,
    source_runid: str,
    target_runid: str,
    expected_root_job_id: str,
    state: str,
) -> None:
    planned_key = f"rq:fork:planned:{target_runid}"
    connection.eval(
        """
        if redis.call('HGET', KEYS[1], 'job_id') ~= ARGV[1]
           or redis.call('HGET', KEYS[1], 'source_runid') ~= ARGV[2]
           or redis.call('HGET', KEYS[1], 'target_runid') ~= ARGV[3] then
            return 0
        end
        local current = redis.call('HGET', KEYS[1], 'state') or 'planned'
        local desired = ARGV[4]
        if current == 'succeeded' then return 0 end
        if desired == 'enqueued' and current ~= 'planned' then return 0 end
        if desired == 'running'
           and current ~= 'planned' and current ~= 'enqueued' then return 0 end
        if desired == 'waiting_finalizer'
           and current ~= 'planned' and current ~= 'enqueued'
           and current ~= 'running' then return 0 end
        redis.call('HSET', KEYS[1], 'state', ARGV[4])
        return 1
        """,
        1,
        planned_key,
        str(expected_root_job_id),
        source_runid,
        target_runid,
        state,
    )

@with_exception_logging
def _finish_fork_rq(
    runid: str,
    fork_target_runid: str | None = None,
    dependency_job_id: str | None = None,
    root_fork_job_id: str | None = None,
) -> None:
    """Emit fork completion messages once dependent jobs finish."""
    func_name = "_finish_fork_rq"
    status_channel = f'{runid}:fork'
    try:
        job = get_current_job()
        wd = get_wd(runid)
        if fork_target_runid:
            target_wd = _resolve_fork_destination_wd(fork_target_runid)
            _verify_profile_fork_claim(fork_target_runid, target_wd, job.id)
        if dependency_job_id:
            dependency_job = Job.fetch(dependency_job_id, connection=job.connection)
            dependency_status = dependency_job.get_status(refresh=True)
            if dependency_status not in {JobStatus.FINISHED, JobStatus.FINISHED.value}:
                raise RuntimeError(
                    f"Fork WEPP dependency {dependency_job_id} ended as {dependency_status}"
                )
        StatusMessenger.publish(status_channel, 'Running WEPP... done\n')
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   fork FORK_COMPLETE')
        if fork_target_runid:
            _set_fork_destination_outcome(
                job.connection,
                runid,
                fork_target_runid,
                str(root_fork_job_id or job.id),
                "succeeded",
            )
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:1113", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   fork FORK_FAILED')
        if fork_target_runid:
            _set_fork_destination_outcome(
                job.connection,
                runid,
                fork_target_runid,
                str(root_fork_job_id or job.id),
                "failed",
            )
        raise
    finally:
        if fork_target_runid:
            target_wd = _resolve_fork_destination_wd(fork_target_runid)
            _release_profile_fork_claim(
                fork_target_runid,
                target_wd,
                job.id,
            )


def _reset_forked_run_job_markers(
    new_runid: str,
    new_wd: str,
    status_channel: str,
    *,
    reset_redisprep: bool = True,
) -> None:
    """Clear inherited async job markers from a newly forked run."""
    StatusMessenger.publish(status_channel, "Clearing inherited job markers...\n")

    clear_nodb_file_cache(new_runid, pup_relpath="wepp.nodb", wd_override=new_wd)
    clear_locks(new_runid, pup_relpath="wepp.nodb")
    wepp = Wepp.tryGetInstance(new_wd)
    if wepp is not None:
        wepp.persist_job_hint(job_id=None, job_key=None)

    prep = RedisPrep.tryGetInstance(new_wd) if reset_redisprep else None
    if prep is not None:
        queued_job_keys = tuple(prep.get_rq_job_ids().keys())
        for key in queued_job_keys:
            prep.redis.hdel(prep.run_id, f"rq:{key}")
        if queued_job_keys:
            prep.dump()

        if prep.get_archive_job_id():
            prep.clear_archive_job_id()

    StatusMessenger.publish(status_channel, "Clearing inherited job markers... done.\n")


def _reset_forked_omni(new_runid: str, new_wd: str, status_channel: str) -> None:
    """Reset destination-only Omni controller and lifecycle metadata."""
    StatusMessenger.publish(status_channel, "Resetting forked Omni state...\n")
    clear_nodb_file_cache(new_runid, pup_relpath="omni.nodb", wd_override=new_wd)
    omni = Omni.getInstance(new_wd)
    omni.reset_for_fork()
    clear_nodb_file_cache(new_runid, pup_relpath="omni.nodb", wd_override=new_wd)
    Omni.load_detached(new_wd)

    redisprep_payload = _fork_helpers._rewrite_fork_redisprep_dump(new_wd)
    prep = RedisPrep(new_wd)
    prep.redis.delete(prep.run_id)
    for key, value in redisprep_payload.items():
        prep.redis.hset(prep.run_id, key, value)

    _fork_helpers._reset_fork_omni_directories(new_wd)
    _fork_helpers._clear_query_engine_catalog_cache(
        new_wd,
        status_channel=status_channel,
        publish_status=StatusMessenger.publish,
    )
    StatusMessenger.publish(status_channel, "Resetting forked Omni state... done.\n")


def _resolve_fork_destination_wd(target_runid: str) -> str:
    if target_runid.startswith("profile;;"):
        parts = target_runid.split(";;")
        if len(parts) != 3 or parts[:2] != ["profile", "fork"] or not parts[2]:
            raise ValueError(f"Invalid profile fork target: {target_runid}")
        target_wd = get_wd(target_runid, prefer_active=False)
        profile_root = os.path.realpath(
            os.path.dirname(get_wd("profile;;fork;;__root_probe__", prefer_active=False))
        )
        resolved_target = os.path.realpath(target_wd)
        if os.path.dirname(resolved_target) != profile_root:
            raise ValueError(f"Profile fork target escaped its root: {target_runid}")
        return resolved_target
    return get_primary_wd(target_runid)


def _profile_fork_claim_path(target_wd: str) -> str:
    target = target_wd.rstrip("/")
    return os.path.join(os.path.dirname(target), f".{os.path.basename(target)}.fork-claim")


@contextmanager
def _profile_fork_claim_lock(target_wd: str):
    lock_path = f"{_profile_fork_claim_path(target_wd)}.lock"
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def _verify_profile_fork_claim(target_runid: str, target_wd: str, job_id: str) -> None:
    if not target_runid.startswith("profile;;"):
        return
    with _profile_fork_claim_lock(target_wd):
        with open(_profile_fork_claim_path(target_wd), encoding="utf-8") as claim_file:
            if claim_file.read().strip() != job_id:
                raise RuntimeError(f"Fork destination is not owned by job {job_id}")


def _release_profile_fork_claim(target_runid: str, target_wd: str, job_id: str) -> None:
    if not target_runid.startswith("profile;;"):
        return
    with _profile_fork_claim_lock(target_wd):
        claim_path = _profile_fork_claim_path(target_wd)
        try:
            with open(claim_path, encoding="utf-8") as claim_file:
                if claim_file.read().strip() != job_id:
                    return
            os.unlink(claim_path)
        except FileNotFoundError:
            return


def _transfer_profile_fork_claim(
    target_runid: str,
    target_wd: str,
    current_job_id: str,
    next_job_id: str,
) -> None:
    if not target_runid.startswith("profile;;"):
        return
    with _profile_fork_claim_lock(target_wd):
        claim_path = _profile_fork_claim_path(target_wd)
        with open(claim_path, encoding="utf-8") as claim_file:
            if claim_file.read().strip() != current_job_id:
                raise RuntimeError(f"Fork destination is not owned by job {current_job_id}")
        temp_path = os.path.join(
            os.path.dirname(claim_path),
            f".{os.path.basename(claim_path)}.{os.getpid()}.tmp",
        )
        temp_fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            payload = next_job_id.encode("utf-8")
            written = 0
            while written < len(payload):
                count = os.write(temp_fd, payload[written:])
                if count <= 0:
                    raise OSError("Short write while transferring fork claim")
                written += count
            os.fsync(temp_fd)
        finally:
            os.close(temp_fd)
        try:
            os.replace(temp_path, claim_path)
        finally:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass


def _release_failure_tolerant_fork_finalizer(queue: Queue, finalizer_job: Job) -> None:
    if finalizer_job.get_status(refresh=True) != JobStatus.DEFERRED:
        return
    if not finalizer_job.dependencies_are_met():
        return
    DeferredJobRegistry(queue=queue).remove(finalizer_job)
    queue._enqueue_job(finalizer_job)


@with_exception_logging
def fork_rq(
    runid: str,
    new_runid: str,
    undisturbify: bool = False,
    skip_wepp_runs_output: bool = False,
    skip_omni_scenarios_contrasts: bool = False,
) -> None:
    job = get_current_job()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{runid}:fork'

    new_wd = ""
    profile_claim_deferred = False
    try:
        new_wd = _resolve_fork_destination_wd(new_runid)
        _verify_profile_fork_claim(new_runid, new_wd, job.id)
        try:
            _set_fork_destination_outcome(
                job.connection, runid, new_runid, str(job.id), "running"
            )
        except redis.RedisError:
            logging.getLogger(__name__).warning(
                "Could not update fork destination outcome at worker start",
                exc_info=True,
            )
        StatusMessenger.publish(
            status_channel, f'rq:{job.id} STARTED {func_name}({runid})'
        )
        StatusMessenger.publish(status_channel, f'undisturbify: {undisturbify}')
        StatusMessenger.publish(status_channel, f'skip_wepp_runs_output: {skip_wepp_runs_output}')
        if skip_omni_scenarios_contrasts:
            StatusMessenger.publish(status_channel, 'skip_omni_scenarios_contrasts: True')

        def _initialize_ttl(wd: str) -> None:
            from wepppy.weppcloud.utils.run_ttl import initialize_ttl
            initialize_ttl(wd)

        def _fork_rsync_command(
            run_right: str,
            fork_undisturbify: bool,
            fork_skip_wepp: bool,
            fork_skip_omni: bool = False,
        ) -> list[str]:
            kwargs = {
                "undisturbify": fork_undisturbify,
                "skip_wepp_runs_output": fork_skip_wepp,
            }
            if fork_skip_omni:
                kwargs["skip_omni_scenarios_contrasts"] = True
            return _build_fork_rsync_cmd(run_right, **kwargs)

        new_wd = _fork_helpers.prepare_fork_run(
            runid,
            new_runid,
            undisturbify=undisturbify,
            skip_wepp_runs_output=skip_wepp_runs_output,
            skip_omni_scenarios_contrasts=skip_omni_scenarios_contrasts,
            status_channel=status_channel,
            publish_status=StatusMessenger.publish,
            get_wd=get_wd,
            get_primary_wd=_resolve_fork_destination_wd,
            wait_for_paths=wait_for_paths,
            ron_cls=Ron,
            disturbed_cls=Disturbed,
            landuse_cls=Landuse,
            soils_cls=Soils,
            initialize_ttl=_initialize_ttl,
            format_ttl_failure=lambda exc: f'rq:{job.id} STATUS TTL initialization failed ({exc})',
            build_rsync_cmd=_fork_rsync_command,
            clean_env_for_system_tools=_clean_env_for_system_tools,
        )
        if skip_omni_scenarios_contrasts:
            _reset_forked_omni(new_runid, new_wd, status_channel)
            _reset_forked_run_job_markers(
                new_runid,
                new_wd,
                status_channel,
                reset_redisprep=False,
            )
        else:
            _reset_forked_run_job_markers(new_runid, new_wd, status_channel)

        if undisturbify:
            StatusMessenger.publish(status_channel, 'Rerunning WEPP...\n')
            final_wepp_job = run_wepp_rq(new_runid)

            conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
            with redis.Redis(**conn_kwargs) as redis_conn:
                q = Queue(connection=redis_conn)
                finalizer_job_id = new_rq_job_id()
                _transfer_profile_fork_claim(
                    new_runid,
                    new_wd,
                    job.id,
                    finalizer_job_id,
                )
                finalizer_enqueued = False
                finalizer_commit_unknown = False
                try:
                    try:
                        finalizer_job = q.enqueue(
                            _finish_fork_rq,
                            args=[runid, new_runid, final_wepp_job.id, job.id],
                            depends_on=Dependency(
                                jobs=[final_wepp_job.id],
                                allow_failure=True,
                            ),
                            job_id=finalizer_job_id,
                            meta={"fork_source_runid": runid},
                        )
                    except RqEnqueueVerificationError:
                        finalizer_commit_unknown = True
                        profile_claim_deferred = new_runid.startswith("profile;;")
                        raise
                    finalizer_enqueued = True
                    job.meta["jobs:0,func:run_wepp_rq"] = final_wepp_job.id
                    job.meta["jobs:1,func:_finish_fork_rq"] = finalizer_job.id
                    job.save()
                    profile_claim_deferred = new_runid.startswith("profile;;")
                    try:
                        _release_failure_tolerant_fork_finalizer(q, finalizer_job)
                    except (redis.RedisError, InvalidJobOperation, NoSuchJobError):
                        logging.getLogger(__name__).warning(
                            "Could not eagerly release fork finalizer %s; stale-claim recovery remains active",
                            finalizer_job_id,
                            exc_info=True,
                        )
                finally:
                    if not finalizer_enqueued and not finalizer_commit_unknown:
                        _release_profile_fork_claim(
                            new_runid,
                            new_wd,
                            finalizer_job_id,
                        )
        else:
            StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
            StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   fork FORK_COMPLETE')
            _set_fork_destination_outcome(
                job.connection, runid, new_runid, str(job.id), "succeeded"
            )

        if undisturbify:
            _set_fork_destination_outcome(
                job.connection,
                runid,
                new_runid,
                str(job.id),
                "waiting_finalizer",
            )

    except Exception:  # broad-except: worker boundary contract
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:1173", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   fork FORK_FAILED')
        _set_fork_destination_outcome(
            job.connection, runid, new_runid, str(job.id), "failed"
        )
        raise
    finally:
        if new_wd and not profile_claim_deferred:
            _release_profile_fork_claim(new_runid, new_wd, job.id)


@with_exception_logging
def archive_rq(runid: str, comment: Optional[str] = None) -> None:
    _archive_helpers.archive_rq(runid, comment, runtime=_archive_runtime())


@with_exception_logging
def restore_archive_rq(runid: str, archive_name: str) -> None:
    _archive_helpers.restore_archive_rq(runid, archive_name, runtime=_archive_runtime())

# RAP_TS Functions

@with_exception_logging
def fetch_and_analyze_rap_ts_rq(runid: str, payload: Mapping[str, Any] | None = None) -> None:
    """Download and analyze RAP time series rasters for the scenario.

    Args:
        runid: Identifier used to locate the working directory.
        payload: Optional scheduling or dataset metadata supplied by the controller.

    Raises:
        Exception: Propagates RAP acquisition or analysis errors.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:rap_ts'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        options = dict(payload) if payload else {}

        climate = Climate.getInstance(wd)
        assert climate.observed_start_year is not None
        assert climate.observed_end_year is not None

        clear_nodb_file_cache(runid, pup_relpath="rap_ts.nodb")
        rap_ts = RAP_TS.getInstance(wd)
        if options:
            try:
                rap_ts.logger.info('RAP_TS job options: %s', json.dumps(options, sort_keys=True))
            except Exception:  # broad-except: optional RQ option-logging boundary
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:1218", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                rap_ts.logger.info('RAP_TS job options provided (%d keys)', len(options))

        rap_ts.acquire_rasters(start_year=climate.observed_start_year,
                               end_year=climate.observed_end_year)
        rap_ts.analyze()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   rap_ts RAP_TS_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.run_rhem)

    except Exception:  # broad-except: RQ task boundary preserves terminal status contract
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:1230", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


# OpenET_TS Functions

@with_exception_logging
def fetch_and_analyze_openet_ts_rq(runid: str, payload: Mapping[str, Any] | None = None) -> None:
    """Download and analyze OpenET time series data for the scenario."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:openet_ts'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        options = dict(payload) if payload else {}

        climate = Climate.getInstance(wd)
        assert climate.observed_start_year is not None
        assert climate.observed_end_year is not None

        clear_nodb_file_cache(runid, pup_relpath="openet_ts.nodb")
        openet_ts = OpenET_TS.getInstance(wd)
        if options:
            try:
                openet_ts.logger.info('OpenET_TS job options: %s', json.dumps(options, sort_keys=True))
            except Exception:  # broad-except: optional RQ option-logging boundary
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:1257", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                openet_ts.logger.info('OpenET_TS job options provided (%d keys)', len(options))

        force_refresh = bool(options.get("force_refresh")) if options else False
        openet_ts.acquire_timeseries(
            start_year=climate.observed_start_year,
            end_year=climate.observed_end_year,
            force_refresh=force_refresh,
        )
        openet_ts.analyze()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   openet_ts OPENET_TS_TASK_COMPLETED')

    except (
        AssertionError,
        FileNotFoundError,
        PermissionError,
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        KeyError,
        AttributeError,
        redis.RedisError,
        NoDirError,
    ):
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:1270", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


# POLARIS Functions

@with_exception_logging
def fetch_and_align_polaris_rq(runid: str, payload: Mapping[str, Any] | None = None) -> None:
    """Fetch and align POLARIS rasters for the scenario."""
    job = get_current_job()
    wd = get_wd(runid)
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{runid}:polaris'
    StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

    options = dict(payload) if payload else {}

    clear_nodb_file_cache(runid, pup_relpath="polaris.nodb")
    polaris = Polaris.getInstance(wd)
    if options:
        try:
            polaris.logger.info('POLARIS job options: %s', json.dumps(options, sort_keys=True))
        except (TypeError, ValueError):
            polaris.logger.info('POLARIS job options provided (%d keys)', len(options))

    summary = polaris.acquire_and_align(payload=options)
    StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   polaris POLARIS_TASK_COMPLETED')
    StatusMessenger.publish(status_channel, json.dumps(summary, sort_keys=True))

    prep = RedisPrep.getInstance(wd)
    prep.timestamp(TaskEnum.fetch_polaris)


@with_exception_logging
def build_rusle_rq(runid: str, payload: Mapping[str, Any] | None = None) -> None:
    """Build RUSLE factors and final mode-specific A output."""
    job = get_current_job()
    wd = get_wd(runid)
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:rusle"
    StatusMessenger.publish(status_channel, f"rq:{job.id} STARTED {func_name}({runid})")

    options = dict(payload) if payload else {}
    clear_nodb_file_cache(runid, pup_relpath="rusle.nodb")
    rusle = Rusle.getInstance(wd)
    if options:
        try:
            rusle.logger.info("RUSLE job options: %s", json.dumps(options, sort_keys=True))
        except (TypeError, ValueError):
            rusle.logger.info("RUSLE job options provided (%d keys)", len(options))

    summary = rusle.build(payload=options)
    StatusMessenger.publish(status_channel, f"rq:{job.id} COMPLETED {func_name}({runid})")
    StatusMessenger.publish(status_channel, "rq:{job.id} TRIGGER   rusle RUSLE_BUILD_TASK_COMPLETED".format(job=job))
    StatusMessenger.publish(status_channel, json.dumps(summary, sort_keys=True))

    prep = RedisPrep.getInstance(wd)
    prep.timestamp(TaskEnum.build_rusle)
