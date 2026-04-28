"""RQ task wrappers for Roads prepare/run workflows."""

from __future__ import annotations

import inspect
import logging
from typing import Any, Dict, Optional

import redis
from rq import get_current_job
from rq.exceptions import NoSuchJobError
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.base import clear_nodb_file_cache
from wepppy.nodb.core import Ron
from wepppy.nodb.mods.roads import Roads
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.exception_logging import with_exception_logging
from wepppy.weppcloud.utils.helpers import get_wd

TIMEOUT: int = 43_200
ROADS_RQ_JOB_KEYS: tuple[str, str] = ("run_roads_prepare_rq", "run_roads_rq")
ACTIVE_RQ_JOB_STATUSES: frozenset[str] = frozenset({"queued", "started", "deferred", "scheduled"})
ROADS_SUBMIT_LOCK_TTL_SECONDS: int = 30
ROADS_RUNTIME_LOCK_TTL_SECONDS: int = max(TIMEOUT, 600)

logger = logging.getLogger(__name__)


class RoadsSingleFlightConflict(RuntimeError):
    """Raised when another Roads task is already active for the run."""


def _roads_lock_key(runid: str, *, domain: str) -> str:
    return f"roads:{domain}:{runid}"


def _normalize_redis_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _acquire_lock(key: str, owner: str, *, ttl_seconds: int) -> bool:
    with redis.Redis(**redis_connection_kwargs(RedisDB.LOCK)) as redis_conn:
        return bool(redis_conn.set(key, owner, nx=True, ex=ttl_seconds))


def _release_lock(key: str, owner: str) -> None:
    with redis.Redis(**redis_connection_kwargs(RedisDB.LOCK)) as redis_conn:
        existing_owner = _normalize_redis_value(redis_conn.get(key))
        if existing_owner is None:
            return
        if existing_owner != owner:
            return
        redis_conn.delete(key)


def acquire_roads_submit_lock(runid: str, owner: str) -> bool:
    return _acquire_lock(
        _roads_lock_key(runid, domain="submit_lock"),
        owner,
        ttl_seconds=ROADS_SUBMIT_LOCK_TTL_SECONDS,
    )


def release_roads_submit_lock(runid: str, owner: str) -> None:
    _release_lock(_roads_lock_key(runid, domain="submit_lock"), owner)


def acquire_roads_runtime_lock(runid: str, owner: str) -> bool:
    return _acquire_lock(
        _roads_lock_key(runid, domain="runtime_lock"),
        owner,
        ttl_seconds=ROADS_RUNTIME_LOCK_TTL_SECONDS,
    )


def release_roads_runtime_lock(runid: str, owner: str) -> None:
    _release_lock(_roads_lock_key(runid, domain="runtime_lock"), owner)


def get_active_roads_job(prep: Optional[RedisPrep], redis_conn: redis.Redis) -> Optional[Dict[str, str]]:
    if prep is None:
        return None
    for key in ROADS_RQ_JOB_KEYS:
        job_id = prep.get_rq_job_id(key)
        if not job_id:
            continue
        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except NoSuchJobError:
            continue
        status = str(job.get_status(refresh=False) or "").lower()
        if status in ACTIVE_RQ_JOB_STATUSES:
            return {
                "key": key,
                "job_id": str(job_id),
                "status": status,
            }
    return None


def ensure_no_active_roads_job(runid: str, prep: Optional[RedisPrep], redis_conn: redis.Redis) -> None:
    active_job = get_active_roads_job(prep, redis_conn)
    if active_job is None:
        return
    raise RoadsSingleFlightConflict(
        "Roads job already active for this run "
        f"(key={active_job['key']}, job_id={active_job['job_id']}, status={active_job['status']})."
    )


def _ensure_roads_controller(wd: str, cfg_fn: str) -> Roads:
    roads = Roads.tryGetInstance(wd)
    if roads is None:
        roads = Roads(wd, cfg_fn)
    return roads


def _sync_roads_enabled_state(wd: str) -> Roads:
    ron = Ron.getInstance(wd)
    roads = _ensure_roads_controller(wd, f"{ron.config_stem}.cfg")
    should_enable = "roads" in (ron.mods or [])
    if roads.enabled != should_enable:
        roads.set_enabled(should_enable)
    return roads


@with_exception_logging
def run_roads_prepare_rq(runid: str) -> Dict[str, Any]:
    """Queue worker entrypoint for Roads segment preparation."""

    job = get_current_job()
    job_id = str(getattr(job, "id", "unknown"))
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:roads"
    StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {func_name}({runid})")

    lock_owner = f"{func_name}:{job_id}"
    lock_acquired = False

    wd = get_wd(runid)
    prep = RedisPrep.tryGetInstance(wd)
    if prep is not None:
        try:
            prep.remove_timestamp(TaskEnum.run_roads)
        except Exception as exc:  # boundary: prep metadata persistence should not mask worker execution
            logger.warning("roads prepare: failed to clear run_roads timestamp (%s): %s", runid, exc)

    try:
        lock_acquired = acquire_roads_runtime_lock(runid, lock_owner)
        if not lock_acquired:
            raise RoadsSingleFlightConflict("Roads job already running for this run.")

        clear_nodb_file_cache(runid, pup_relpath="roads.nodb")
        roads = _sync_roads_enabled_state(wd)
        if not roads.enabled:
            raise ValueError("Roads module is not enabled for this run.")

        result = roads.prepare_segments()
        StatusMessenger.publish(status_channel, f"rq:{job_id} COMPLETED {func_name}({runid})")
        StatusMessenger.publish(status_channel, f"rq:{job_id} TRIGGER roads ROADS_PREPARE_TASK_COMPLETED")
        return result
    except Exception:
        # Boundary catch: preserve queue contract while surfacing the original exception.
        logger.exception("roads prepare worker failed", extra={"runid": runid, "job_id": job_id})
        StatusMessenger.publish(status_channel, f"rq:{job_id} EXCEPTION {func_name}({runid})")
        raise
    finally:
        try:
            release_roads_runtime_lock(runid, lock_owner)
        except Exception as exc:  # boundary: cleanup failure should not mask worker result
            logger.warning("roads prepare: failed to release runtime lock (%s): %s", runid, exc)


@with_exception_logging
def run_roads_rq(runid: str) -> Dict[str, Any]:
    """Queue worker entrypoint for full Roads run orchestration."""

    job = get_current_job()
    job_id = str(getattr(job, "id", "unknown"))
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:roads"
    StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {func_name}({runid})")

    lock_owner = f"{func_name}:{job_id}"
    lock_acquired = False

    wd = get_wd(runid)
    prep = RedisPrep.tryGetInstance(wd)
    if prep is not None:
        try:
            prep.remove_timestamp(TaskEnum.run_roads)
        except Exception as exc:  # boundary: prep metadata persistence should not mask worker execution
            logger.warning("roads run: failed to clear run_roads timestamp (%s): %s", runid, exc)

    try:
        lock_acquired = acquire_roads_runtime_lock(runid, lock_owner)
        if not lock_acquired:
            raise RoadsSingleFlightConflict("Roads job already running for this run.")

        clear_nodb_file_cache(runid, pup_relpath="roads.nodb")
        roads = _sync_roads_enabled_state(wd)
        if not roads.enabled:
            raise ValueError("Roads module is not enabled for this run.")

        result = roads.run_roads_wepp()

        if prep is not None:
            try:
                prep.timestamp(TaskEnum.run_roads)
            except Exception as exc:  # boundary: prep metadata persistence should not mask worker completion
                logger.warning("roads run: failed to set run_roads timestamp (%s): %s", runid, exc)

        StatusMessenger.publish(status_channel, f"rq:{job_id} COMPLETED {func_name}({runid})")
        StatusMessenger.publish(status_channel, f"rq:{job_id} TRIGGER roads ROADS_RUN_TASK_COMPLETED")
        return result
    except Exception:
        # Boundary catch: preserve queue contract while surfacing the original exception.
        logger.exception("roads run worker failed", extra={"runid": runid, "job_id": job_id})
        StatusMessenger.publish(status_channel, f"rq:{job_id} EXCEPTION {func_name}({runid})")
        raise
    finally:
        try:
            release_roads_runtime_lock(runid, lock_owner)
        except Exception as exc:  # boundary: cleanup failure should not mask worker result
            logger.warning("roads run: failed to release runtime lock (%s): %s", runid, exc)
