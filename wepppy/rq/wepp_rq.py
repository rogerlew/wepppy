from __future__ import annotations
from typing import Any, Iterable

"""
RQ task entry points for orchestrating WEPP model runs and post-processing steps.

The helpers enqueue work onto Redis-backed queues, orchestrate NoDb controller prep,
and publish progress updates so the UI can reflect job status in real time.
"""

import inspect
import logging
import socket
import sys
import time
from glob import glob
from os.path import exists as _exists
from os.path import join as _join
from subprocess import call

import redis
from rq import Queue, get_current_job
from rq.exceptions import (
    AbandonedJobError,
    DeserializationError,
    InvalidJobOperationError,
    NoSuchJobError,
    ShutDownImminentException,
    TimeoutFormatError,
)
from rq.job import Job
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.io_wait import wait_for_path, wait_for_paths
from wepppy.runtime_paths.errors import nodir_mixed_state
from wepppy.runtime_paths.fs import resolve
from wepppy.runtime_paths.projections import with_root_projection
from wepppy.nodb.base import clear_nodb_file_cache
from wepppy.query_engine.activate import activate_query_engine
from wepppy.wepp.interchange import (
    cleanup_hillslope_sources_for_completed_interchange,
    generate_interchange_documentation,
    run_wepp_hillslope_interchange,
    run_wepp_watershed_interchange,
    run_wepp_watershed_tc_out_interchange,
)
from wepppy.wepp.interchange.dss_dates import parse_dss_date

try:
    from wepp_runner import (
        run_ss_batch_hillslope,
        run_hillslope,
        run_watershed,
        run_ss_batch_watershed,
    )
except (ModuleNotFoundError, ImportError) as exc:  # pragma: no cover - optional runner dependency
    _WEPP_RUNNER_IMPORT_ERROR = exc

    def _missing_runner(*_args, **_kwargs):
        raise ModuleNotFoundError(
            "wepp_runner is required for WEPP execution tasks. "
            "Install the optional runner dependencies to enable these RQ jobs."
        ) from _WEPP_RUNNER_IMPORT_ERROR

    run_ss_batch_hillslope = _missing_runner  # type: ignore[assignment]
    run_hillslope = _missing_runner  # type: ignore[assignment]
    run_watershed = _missing_runner  # type: ignore[assignment]
    run_ss_batch_watershed = _missing_runner  # type: ignore[assignment]
else:
    _WEPP_RUNNER_IMPORT_ERROR = None

from wepppy.nodb.core import *
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.exception_logging import with_exception_logging
from . import wepp_rq_dss as _dss_helpers
from . import wepp_rq_pipeline as _pipeline
from . import wepp_rq_stage_finalize as _stage_finalize
from . import wepp_rq_stage_helpers as _stage_helpers
from . import wepp_rq_stage_post as _stage_post
from . import wepp_rq_stage_prep as _stage_prep
from wepppy.rq.swat_rq import _build_swat_inputs_rq, _run_swat_rq
from wepppy.weppcloud.bootstrap.git_lock import (
    acquire_bootstrap_git_lock,
    clear_bootstrap_enable_job_id,
    release_bootstrap_git_lock,
)

try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except (ModuleNotFoundError, ImportError):
    send_discord_message = None


_hostname = socket.gethostname()

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)

TIMEOUT: int = 43_200
WEPP_RQ_JOB_KEYS: tuple[str, ...] = (
    "run_wepp_rq",
    "run_wepp_watershed_rq",
    "prep_wepp_watershed_rq",
    "run_wepp_noprep_rq",
    "run_wepp_watershed_noprep_rq",
)
ACTIVE_RQ_JOB_STATUSES: frozenset[str] = frozenset({"queued", "started", "deferred", "scheduled"})
WEPP_SUBMIT_LOCK_TTL_SECONDS: int = 30
WEPP_LOCK_RETRY_ATTEMPTS: int = 25
WEPP_LOCK_RETRY_DELAY_SECONDS: float = 0.2

_cleanup_dss_export_dir = _dss_helpers._cleanup_dss_export_dir
_copy_dss_readme = _dss_helpers._copy_dss_readme
_resolve_downstream_channel_ids = _dss_helpers._resolve_downstream_channel_ids
_extract_channel_topaz_id = _dss_helpers._extract_channel_topaz_id
_write_dss_channel_geojson = _dss_helpers._write_dss_channel_geojson


_SINGLE_STORM_DEPRECATED_MESSAGE = _stage_helpers.SINGLE_STORM_DEPRECATED_MESSAGE
_NODIR_RECOVERY_ROOTS = _stage_helpers.NODIR_RECOVERY_ROOTS


class WeppSingleFlightConflict(RuntimeError):
    """Raised when another WEPP task is already active for the run."""


class _WeppRunLockedError(RuntimeError):
    """Raised when the run lock prevents starting a new WEPP workflow."""


_WEPP_RQ_BOUNDARY_EXCEPTIONS: tuple[type[Exception], ...] = (
    # Deliberate worker boundary catch: all task failures must publish
    # an EXCEPTION status before re-raising.
    Exception,
    AssertionError,
    AttributeError,
    ImportError,
    LookupError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
    redis.exceptions.RedisError,
    AbandonedJobError,
    DeserializationError,
    InvalidJobOperationError,
    NoSuchJobError,
    ShutDownImminentException,
    TimeoutFormatError,
)


def _publish_boundary_exception(
    *,
    runid: str,
    status_channel: str,
    job_id: str,
    operation: str,
) -> None:
    logging.getLogger(__name__).exception(
        "Boundary exception in wepppy.rq.wepp_rq",
        extra={"runid": runid, "job_id": job_id, "operation": operation},
    )
    StatusMessenger.publish(status_channel, f"rq:{job_id} EXCEPTION {operation}")


def _wait_for_wepp_unlock(wepp: Any, *, runid: str) -> None:
    """Wait briefly for transient NoDb locks before failing the run."""
    if not wepp.islocked():
        return

    retry_attempts = max(0, int(WEPP_LOCK_RETRY_ATTEMPTS))
    retry_delay_seconds = max(0.0, float(WEPP_LOCK_RETRY_DELAY_SECONDS))
    for _ in range(retry_attempts):
        if retry_delay_seconds > 0:
            time.sleep(retry_delay_seconds)
        if not wepp.islocked():
            return

    raise _WeppRunLockedError(f"{runid} is locked")


def _wepp_lock_key(runid: str, *, domain: str) -> str:
    return f"wepp:{domain}:{runid}"


def _normalize_redis_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def acquire_wepp_submit_lock(runid: str, owner: str) -> bool:
    with redis.Redis(**redis_connection_kwargs(RedisDB.LOCK)) as redis_conn:
        return bool(
            redis_conn.set(
                _wepp_lock_key(runid, domain="submit_lock"),
                owner,
                nx=True,
                ex=WEPP_SUBMIT_LOCK_TTL_SECONDS,
            )
        )


def release_wepp_submit_lock(runid: str, owner: str) -> None:
    key = _wepp_lock_key(runid, domain="submit_lock")
    with redis.Redis(**redis_connection_kwargs(RedisDB.LOCK)) as redis_conn:
        existing_owner = _normalize_redis_value(redis_conn.get(key))
        if existing_owner is None:
            return
        if existing_owner != owner:
            return
        redis_conn.delete(key)


def get_active_wepp_job(prep: RedisPrep | None, redis_conn: redis.Redis) -> dict[str, str] | None:
    if prep is None:
        return None

    for key in WEPP_RQ_JOB_KEYS:
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


def ensure_no_active_wepp_job(runid: str, prep: RedisPrep | None, redis_conn: redis.Redis) -> None:
    active_job = get_active_wepp_job(prep, redis_conn)
    if active_job is None:
        return
    raise WeppSingleFlightConflict(
        "WEPP job already active for this run "
        f"(key={active_job['key']}, job_id={active_job['job_id']}, status={active_job['status']})."
    )


def _sync_stage_helpers_compat() -> None:
    # Preserve monkeypatch compatibility for legacy tests/callers patching
    # `wepp_rq` internals directly.
    _stage_helpers.nodir_mixed_state = nodir_mixed_state
    _stage_helpers.resolve = resolve
    _stage_helpers.with_root_projection = with_root_projection


def _sync_stage_prep_compat() -> None:
    _sync_stage_helpers_compat()
    _stage_prep.get_current_job = get_current_job
    _stage_prep.get_wd = get_wd
    _stage_prep.StatusMessenger = StatusMessenger
    _stage_prep.Wepp = Wepp
    _stage_prep.Watershed = Watershed
    _stage_prep.Disturbed = Disturbed


def _sync_stage_post_compat() -> None:
    _stage_post.get_current_job = get_current_job
    _stage_post.get_wd = get_wd
    _stage_post.StatusMessenger = StatusMessenger
    _stage_post.wait_for_path = wait_for_path
    _stage_post.wait_for_paths = wait_for_paths
    _stage_post.Climate = Climate
    _stage_post.ClimateMode = ClimateMode
    _stage_post.Wepp = Wepp
    _stage_post.RedisPrep = RedisPrep
    _stage_post.TaskEnum = TaskEnum
    _stage_post.activate_query_engine = activate_query_engine
    _stage_post.generate_interchange_documentation = generate_interchange_documentation
    _stage_post.cleanup_hillslope_sources_for_completed_interchange = (
        cleanup_hillslope_sources_for_completed_interchange
    )
    _stage_post.run_wepp_hillslope_interchange = run_wepp_hillslope_interchange
    _stage_post.run_wepp_watershed_interchange = run_wepp_watershed_interchange
    _stage_post.run_wepp_watershed_tc_out_interchange = run_wepp_watershed_tc_out_interchange
    _stage_post.parse_dss_date = parse_dss_date
    _stage_post._cleanup_dss_export_dir = _cleanup_dss_export_dir
    _stage_post._copy_dss_readme = _copy_dss_readme
    _stage_post._write_dss_channel_geojson = _write_dss_channel_geojson


def _sync_stage_finalize_compat() -> None:
    _stage_finalize.get_current_job = get_current_job
    _stage_finalize.get_wd = get_wd
    _stage_finalize.StatusMessenger = StatusMessenger
    _stage_finalize.RedisPrep = RedisPrep
    _stage_finalize.TaskEnum = TaskEnum
    _stage_finalize.Ron = Ron
    _stage_finalize.Wepp = Wepp
    _stage_finalize.redis_connection_kwargs = redis_connection_kwargs
    _stage_finalize.redis = redis
    _stage_finalize.acquire_bootstrap_git_lock = acquire_bootstrap_git_lock
    _stage_finalize.release_bootstrap_git_lock = release_bootstrap_git_lock


def _recover_mixed_nodir_roots(
    wd: str,
    *,
    roots: Iterable[str] = _NODIR_RECOVERY_ROOTS,
) -> tuple[str, ...]:
    _sync_stage_helpers_compat()
    return _stage_helpers.recover_mixed_nodir_roots(wd, roots=roots)


def _assert_supported_climate(climate: Climate) -> None:
    _sync_stage_helpers_compat()
    _stage_helpers.assert_supported_climate(climate)


def _with_stage_read_projections(
    wd: str,
    *,
    roots: tuple[str, ...],
    purpose: str,
):
    _sync_stage_helpers_compat()
    return _stage_helpers.with_stage_read_projections(
        wd,
        roots=roots,
        purpose=purpose,
    )


def compress_fn(fn: str) -> None:
    """Force gzip compression in place for the provided file path.

    Args:
        fn: Absolute path to the file to compress.

    Raises:
        AssertionError: If gzip does not create the expected `.gz` file.
    """
    if _exists(fn):
        call(f'gzip {fn} -f', shell=True)
        assert _exists(f'{fn}.gz')

# turtles, turtles all the way down...

@with_exception_logging
def run_ss_batch_hillslope_rq(
    runid: str,
    wepp_id: int,
    wepp_bin: str | None = None,
    ss_batch_id: int | None = None,
) -> tuple[bool, float]:
    """Execute a batch single-storm hillslope WEPP run within an RQ worker.

    Args:
        runid: Identifier used to locate the working directory.
        wepp_id: Hillslope identifier corresponding to the prepared input files.
        wepp_bin: Optional override for the WEPP executable name.
        ss_batch_id: Single-storm batch identifier supplied by the climate controller.

    Returns:
        Tuple with the runner success flag and the runtime in seconds.

    Raises:
        Exception: Propagates any failure produced by the underlying WEPP runner.
    """
    job = get_current_job()
    job_id = job.id if job is not None else ""
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:wepp"
    operation = f"{func_name}({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id})"

    try:
        wd = get_wd(runid)
        runs_dir = _join(wd, "wepp/runs")
        StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {operation}")
        status, _, duration = run_ss_batch_hillslope(
            wepp_id,
            runs_dir,
            wepp_bin=wepp_bin,
            ss_batch_id=ss_batch_id,
            status_channel=status_channel,
        )
        StatusMessenger.publish(status_channel, f"rq:{job_id} COMPLETED {operation} -> ({status}, {duration})")
        return status, duration
    except _WEPP_RQ_BOUNDARY_EXCEPTIONS:
        _publish_boundary_exception(
            runid=runid,
            status_channel=status_channel,
            job_id=job_id,
            operation=operation,
        )
        raise

@with_exception_logging
def run_hillslope_rq(runid: str, wepp_id: int, wepp_bin: str | None = None) -> tuple[bool, float]:
    """Execute a continuous hillslope WEPP run within an RQ worker.

    Args:
        runid: Identifier used to locate the working directory.
        wepp_id: Hillslope identifier corresponding to the prepared input files.
        wepp_bin: Optional override for the WEPP executable name.

    Returns:
        Tuple with the runner success flag and the runtime in seconds.

    Raises:
        Exception: Propagates any failure produced by the underlying WEPP runner.
    """
    job = get_current_job()
    job_id = job.id if job is not None else ""
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:wepp"
    operation = f"{func_name}({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin})"

    try:
        wd = get_wd(runid)
        runs_dir = _join(wd, "wepp/runs")
        StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {operation}")
        status, _, duration = run_hillslope(
            wepp_id,
            runs_dir,
            wepp_bin=wepp_bin,
            status_channel=status_channel,
        )
        StatusMessenger.publish(status_channel, f"rq:{job_id} COMPLETED {operation} -> ({status}, {duration})")
        return status, duration
    except _WEPP_RQ_BOUNDARY_EXCEPTIONS:
        _publish_boundary_exception(
            runid=runid,
            status_channel=status_channel,
            job_id=job_id,
            operation=operation,
        )
        raise

@with_exception_logging
def run_watershed_rq(runid: str, wepp_bin: str | None = None) -> tuple[bool, float]:
    """Run a watershed WEPP simulation within an RQ worker.

    Args:
        runid: Identifier used to locate the working directory.
        wepp_bin: Optional override for the WEPP executable name.

    Returns:
        Tuple with the runner success flag and the runtime in seconds.

    Raises:
        Exception: Propagates any failure produced by the underlying WEPP runner.
    """
    job = get_current_job()
    job_id = job.id if job is not None else ""
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:wepp"
    operation = f"{func_name}({runid}, wepp_bin={wepp_bin})"

    try:
        wd = get_wd(runid)
        runs_dir = _join(wd, "wepp/runs")
        StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {operation}")
        status, duration = run_watershed(runs_dir, wepp_bin=wepp_bin, status_channel=status_channel)
        StatusMessenger.publish(status_channel, f"rq:{job_id} COMPLETED {operation} -> ({status}, {duration})")
        return status, duration
    except _WEPP_RQ_BOUNDARY_EXCEPTIONS:
        _publish_boundary_exception(
            runid=runid,
            status_channel=status_channel,
            job_id=job_id,
            operation=operation,
        )
        raise

@with_exception_logging
def run_ss_batch_watershed_rq(
    runid: str,
    wepp_bin: str | None = None,
    ss_batch_id: int | None = None,
) -> tuple[bool, float]:
    """Run a batch single-storm watershed WEPP simulation within an RQ worker.

    Args:
        runid: Identifier used to locate the working directory.
        wepp_bin: Optional override for the WEPP executable name.
        ss_batch_id: Single-storm batch identifier supplied by the climate controller.

    Returns:
        Tuple with the runner success flag and the runtime in seconds.

    Raises:
        Exception: Propagates any failure produced by the underlying WEPP runner.
    """
    job = get_current_job()
    job_id = job.id if job is not None else ""
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:wepp"
    operation = f"{func_name}({runid}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id})"

    try:
        wd = get_wd(runid)
        runs_dir = _join(wd, "wepp/runs")
        StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {operation}")
        status, duration = run_ss_batch_watershed(
            runs_dir,
            wepp_bin=wepp_bin,
            ss_batch_id=ss_batch_id,
            status_channel=status_channel,
        )
        StatusMessenger.publish(status_channel, f"rq:{job_id} COMPLETED {operation} -> ({status}, {duration})")
        return status, duration
    except _WEPP_RQ_BOUNDARY_EXCEPTIONS:
        _publish_boundary_exception(
            runid=runid,
            status_channel=status_channel,
            job_id=job_id,
            operation=operation,
        )
        raise


# the main turtle

@with_exception_logging
def bootstrap_enable_rq(runid: str, actor: str | None = None, lock_token: str | None = None) -> dict[str, Any]:
    """Initialize git bootstrap for a run in a background worker."""
    job = get_current_job()
    job_id = job.id if job is not None else ""
    status_channel = f"{runid}:bootstrap"

    try:
        StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED bootstrap_enable_rq({runid})")
        wd = get_wd(runid)
        clear_nodb_file_cache(runid, pup_relpath="wepp.nodb")
        wepp = Wepp.getInstance(wd)

        if not wepp.bootstrap_enabled:
            wepp.init_bootstrap()

        StatusMessenger.publish(status_channel, f"rq:{job_id} COMPLETED bootstrap_enable_rq({runid})")
        return {"enabled": True, "runid": runid}
    except _WEPP_RQ_BOUNDARY_EXCEPTIONS:
        _publish_boundary_exception(
            runid=runid,
            status_channel=status_channel,
            job_id=job_id,
            operation=f"bootstrap_enable_rq({runid})",
        )
        raise
    finally:
        conn_kwargs = redis_connection_kwargs(RedisDB.LOCK)
        with redis.Redis(**conn_kwargs) as redis_conn:
            if job_id:
                clear_bootstrap_enable_job_id(redis_conn, runid=runid, expected_job_id=job_id)
            else:
                clear_bootstrap_enable_job_id(redis_conn, runid=runid)
            if lock_token:
                release_bootstrap_git_lock(redis_conn, runid=runid, token=lock_token)


@with_exception_logging
def run_wepp_rq(runid: str) -> Job:
    """Enqueue the full multi-stage WEPP workflow for a run directory.

    The orchestrator performs initial synchronous setup (locking checks,
    controller priming), then enqueues the staged RQ tasks that prepare
    inputs, execute WEPP, and fan out the post-processing jobs. Each stage
    updates Redis-backed status channels so the UI can visualize progress.

    Args:
        runid: Identifier used to locate the working directory.

    Returns:
        The final RQ job that logs completion once all dependencies finish.

    Raises:
        Exception: If the run is currently locked or any prep step fails.
    """
    job = get_current_job()
    job_id = job.id if job is not None else ""
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:wepp"
    operation = f"{func_name}({runid})"

    try:
        StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {operation}")

        wd = get_wd(runid)
        clear_nodb_file_cache(runid, pup_relpath="wepp.nodb")
        wepp = Wepp.getInstance(wd)

        recovered_roots = _recover_mixed_nodir_roots(wd)
        if recovered_roots:
            recovered_txt = ", ".join(recovered_roots)
            recovery_msg = f"Recovered mixed NoDir roots before WEPP run: {recovered_txt}"
            wepp.logger.warning(recovery_msg)
            StatusMessenger.publish(status_channel, recovery_msg)

        _wait_for_wepp_unlock(wepp, runid=runid)

        wepp.ensure_bootstrap_main()

        # send feedback to user
        wepp.logger.info("Running Wepp\n")

        wepp.clean()

        # quick prep operations that require locking
        wepp._check_and_set_baseflow_map()
        wepp._check_and_set_phosphorus_map()

        climate = Climate.getInstance(wd)
        _assert_supported_climate(climate)

        wepp.logger.info("    wepp_bin:{}".format(wepp.wepp_bin))
        if not wepp.run_wepp_watershed:
            wepp.logger.info("Skipping WEPP watershed run (wepp.run_wepp_watershed=False)")

        # everything below here is asynchronous, performed by workers
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job6_finalfinal = _pipeline.enqueue_wepp_pipeline(
                q,
                job,
                runid,
                wepp=wepp,
                climate=climate,
                tasks=sys.modules[__name__],
                timeout=TIMEOUT,
            )

        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} ENQUEUED {operation} -> awaiting final job {job6_finalfinal.id}",
        )

    except _WEPP_RQ_BOUNDARY_EXCEPTIONS:
        _publish_boundary_exception(
            runid=runid,
            status_channel=status_channel,
            job_id=job_id,
            operation=operation,
        )
        raise

    return job6_finalfinal


@with_exception_logging
def run_wepp_noprep_rq(runid: str) -> Job:
    """Enqueue WEPP execution using existing inputs (no prep)."""
    job = get_current_job()
    job_id = job.id if job is not None else ""
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:wepp"
    operation = f"{func_name}({runid})"

    try:
        StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {operation}")

        wd = get_wd(runid)
        clear_nodb_file_cache(runid, pup_relpath="wepp.nodb")
        wepp = Wepp.getInstance(wd)

        recovered_roots = _recover_mixed_nodir_roots(wd, roots=("watershed",))
        if recovered_roots:
            recovered_txt = ", ".join(recovered_roots)
            recovery_msg = f"Recovered mixed NoDir roots before {func_name}({runid}): {recovered_txt}"
            wepp.logger.warning(recovery_msg)
            StatusMessenger.publish(status_channel, recovery_msg)

        _wait_for_wepp_unlock(wepp, runid=runid)

        wepp.logger.info("Running Wepp (no-prep)\n")

        climate = Climate.getInstance(wd)
        _assert_supported_climate(climate)
        if not wepp.run_wepp_watershed:
            wepp.logger.info("Skipping WEPP watershed run (wepp.run_wepp_watershed=False)")

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            # Bootstrap no-prep contract: execute exactly the existing checked-out
            # WEPP inputs. This path intentionally avoids prep stages that can
            # regenerate `wepp/runs/`.
            job6_finalfinal = _pipeline.enqueue_wepp_noprep_pipeline(
                q,
                job,
                runid,
                wepp=wepp,
                climate=climate,
                tasks=sys.modules[__name__],
                timeout=TIMEOUT,
            )

        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} ENQUEUED {operation} -> awaiting final job {job6_finalfinal.id}",
        )

    except _WEPP_RQ_BOUNDARY_EXCEPTIONS:
        _publish_boundary_exception(
            runid=runid,
            status_channel=status_channel,
            job_id=job_id,
            operation=operation,
        )
        raise

    return job6_finalfinal


@with_exception_logging
def run_wepp_watershed_rq(runid: str) -> Job:
    """Enqueue the WEPP watershedworkflow for a run directory.

    The orchestrator performs initial synchronous setup (locking checks,
    controller priming), then enqueues the staged RQ tasks that prepare
    inputs, execute WEPP, and fan out the post-processing jobs. Each stage
    updates Redis-backed status channels so the UI can visualize progress.

    Args:
        runid: Identifier used to locate the working directory.

    Returns:
        The final RQ job that logs completion once all dependencies finish.

    Raises:
        Exception: If the run is currently locked or any prep step fails.
    """
    job = get_current_job()
    job_id = job.id if job is not None else ""
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:wepp"
    operation = f"{func_name}({runid})"

    try:
        StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {operation}")

        wd = get_wd(runid)
        clear_nodb_file_cache(runid, pup_relpath="wepp.nodb")
        wepp = Wepp.getInstance(wd)

        recovered_roots = _recover_mixed_nodir_roots(wd, roots=("watershed",))
        if recovered_roots:
            recovered_txt = ", ".join(recovered_roots)
            recovery_msg = f"Recovered mixed NoDir roots before {func_name}({runid}): {recovered_txt}"
            wepp.logger.warning(recovery_msg)
            StatusMessenger.publish(status_channel, recovery_msg)

        _wait_for_wepp_unlock(wepp, runid=runid)

        wepp.ensure_bootstrap_main()

        if not wepp.run_wepp_watershed:
            wepp.logger.info("Skipping WEPP watershed run (wepp.run_wepp_watershed=False)")
            conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
            with redis.Redis(**conn_kwargs) as redis_conn:
                q = Queue(connection=redis_conn)
                job6_finalfinal = _pipeline.enqueue_log_complete(
                    q,
                    job,
                    runid,
                    tasks=sys.modules[__name__],
                    kwargs={
                        "auto_commit_inputs": True,
                        "commit_stage": "WEPP watershed pipeline",
                    },
                )
            return job6_finalfinal

        # send feedback to user
        wepp.logger.info("Running Wepp Watershed\n")

        # quick prep operations that require locking
        wepp._check_and_set_baseflow_map()
        wepp._check_and_set_phosphorus_map()

        climate = Climate.getInstance(wd)
        _assert_supported_climate(climate)
        wepp.logger.info("    wepp_bin:{}".format(wepp.wepp_bin))

        # everything below here is asynchronous, performed by workers
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            wepp.logger.info(f"Running Watershed wepp_bin:{wepp.wepp_bin}... ")
            has_hillslope_outputs = bool(glob(_join(wepp.output_dir, "H*")))
            job6_finalfinal = _pipeline.enqueue_watershed_pipeline(
                q,
                job,
                runid,
                wepp=wepp,
                climate=climate,
                tasks=sys.modules[__name__],
                timeout=TIMEOUT,
                has_hillslope_outputs=has_hillslope_outputs,
                publish_status=lambda message: StatusMessenger.publish(status_channel, message),
            )

        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} ENQUEUED {operation} -> awaiting final job {job6_finalfinal.id}",
        )

    except _WEPP_RQ_BOUNDARY_EXCEPTIONS:
        _publish_boundary_exception(
            runid=runid,
            status_channel=status_channel,
            job_id=job_id,
            operation=operation,
        )
        raise

    return job6_finalfinal


@with_exception_logging
def prep_wepp_watershed_rq(runid: str) -> Job:
    """Enqueue prep-only WEPP input generation for hillslopes + watershed."""
    job = get_current_job()
    job_id = job.id if job is not None else ""
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:wepp"
    operation = f"{func_name}({runid})"

    try:
        StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {operation}")

        wd = get_wd(runid)
        clear_nodb_file_cache(runid, pup_relpath="wepp.nodb")
        wepp = Wepp.getInstance(wd)

        recovered_roots = _recover_mixed_nodir_roots(wd)
        if recovered_roots:
            recovered_txt = ", ".join(recovered_roots)
            recovery_msg = f"Recovered mixed NoDir roots before {func_name}({runid}): {recovered_txt}"
            wepp.logger.warning(recovery_msg)
            StatusMessenger.publish(status_channel, recovery_msg)

        _wait_for_wepp_unlock(wepp, runid=runid)

        wepp.ensure_bootstrap_main()

        wepp.logger.info("Preparing WEPP inputs only\n")

        # quick prep operations that require locking
        wepp._check_and_set_baseflow_map()
        wepp._check_and_set_phosphorus_map()

        climate = Climate.getInstance(wd)
        _assert_supported_climate(climate)

        wepp.logger.info("    wepp_bin:{}".format(wepp.wepp_bin))

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job6_finalfinal = _pipeline.enqueue_wepp_prep_only_pipeline(
                q,
                job,
                runid,
                wepp=wepp,
                tasks=sys.modules[__name__],
                timeout=TIMEOUT,
            )

        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} ENQUEUED {operation} -> awaiting final job {job6_finalfinal.id}",
        )

    except _WEPP_RQ_BOUNDARY_EXCEPTIONS:
        _publish_boundary_exception(
            runid=runid,
            status_channel=status_channel,
            job_id=job_id,
            operation=operation,
        )
        raise

    return job6_finalfinal


@with_exception_logging
def run_wepp_watershed_noprep_rq(runid: str) -> Job:
    """Enqueue watershed-only WEPP execution using existing inputs (no prep)."""
    job = get_current_job()
    job_id = job.id if job is not None else ""
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:wepp"
    operation = f"{func_name}({runid})"

    try:
        StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {operation}")

        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)

        _wait_for_wepp_unlock(wepp, runid=runid)

        if not wepp.run_wepp_watershed:
            wepp.logger.info("Skipping WEPP watershed run (wepp.run_wepp_watershed=False)")
            conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
            with redis.Redis(**conn_kwargs) as redis_conn:
                q = Queue(connection=redis_conn)
                job6_finalfinal = _pipeline.enqueue_log_complete(
                    q,
                    job,
                    runid,
                    tasks=sys.modules[__name__],
                )
            return job6_finalfinal

        wepp.logger.info("Running Wepp Watershed (no-prep)\n")

        climate = Climate.getInstance(wd)
        _assert_supported_climate(climate)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            has_hillslope_outputs = bool(glob(_join(wepp.output_dir, "H*")))
            # Bootstrap no-prep contract: execute watershed using current checked-out
            # inputs only; no watershed prep task should run in this pipeline.
            job6_finalfinal = _pipeline.enqueue_watershed_noprep_pipeline(
                q,
                job,
                runid,
                wepp=wepp,
                climate=climate,
                tasks=sys.modules[__name__],
                timeout=TIMEOUT,
                has_hillslope_outputs=has_hillslope_outputs,
                publish_status=lambda message: StatusMessenger.publish(status_channel, message),
            )

        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} ENQUEUED {operation} -> awaiting final job {job6_finalfinal.id}",
        )

    except _WEPP_RQ_BOUNDARY_EXCEPTIONS:
        _publish_boundary_exception(
            runid=runid,
            status_channel=status_channel,
            job_id=job_id,
            operation=operation,
        )
        raise

    return job6_finalfinal


@with_exception_logging
def _prep_multi_ofe_rq(runid: str) -> None:
    _sync_stage_prep_compat()
    return _stage_prep._prep_multi_ofe_rq(runid)


@with_exception_logging
def _prep_slopes_rq(runid: str) -> None:
    _sync_stage_prep_compat()
    return _stage_prep._prep_slopes_rq(runid)


@with_exception_logging
def _run_hillslopes_rq(runid: str) -> None:
    _sync_stage_prep_compat()
    return _stage_prep._run_hillslopes_rq(runid)


@with_exception_logging
def _prep_managements_rq(runid: str) -> None:
    _sync_stage_prep_compat()
    return _stage_prep._prep_managements_rq(runid)


@with_exception_logging
def _prep_soils_rq(runid: str) -> None:
    _sync_stage_prep_compat()
    return _stage_prep._prep_soils_rq(runid)


@with_exception_logging
def _prep_climates_rq(runid: str) -> None:
    _sync_stage_prep_compat()
    return _stage_prep._prep_climates_rq(runid)


@with_exception_logging
def _prep_remaining_rq(runid: str) -> None:
    _sync_stage_prep_compat()
    return _stage_prep._prep_remaining_rq(runid)


@with_exception_logging
def _prep_watershed_rq(runid: str) -> None:
    _sync_stage_prep_compat()
    return _stage_prep._prep_watershed_rq(runid)

@with_exception_logging
def _post_run_cleanup_out_rq(runid: str) -> None:
    _sync_stage_post_compat()
    return _stage_post._post_run_cleanup_out_rq(runid)


@with_exception_logging
def _analyze_return_periods_rq(runid: str) -> None:
    _sync_stage_post_compat()
    return _stage_post._analyze_return_periods_rq(runid)

@with_exception_logging
def _build_hillslope_interchange_rq(runid: str) -> None:
    _sync_stage_post_compat()
    return _stage_post._build_hillslope_interchange_rq(runid)

@with_exception_logging
def _build_totalwatsed3_rq(runid: str) -> None:
    _sync_stage_post_compat()
    return _stage_post._build_totalwatsed3_rq(runid)


@with_exception_logging
def _run_hillslope_watbal_rq(runid: str) -> None:
    _sync_stage_post_compat()
    return _stage_post._run_hillslope_watbal_rq(runid)


@with_exception_logging
def _post_prep_details_rq(runid: str) -> None:
    _sync_stage_post_compat()
    return _stage_post._post_prep_details_rq(runid)

@with_exception_logging
def _post_watershed_interchange_rq(runid: str) -> None:
    _sync_stage_post_compat()
    return _stage_post._post_watershed_interchange_rq(runid)


@with_exception_logging
def _post_legacy_arc_export_rq(runid: str) -> None:
    _sync_stage_post_compat()
    return _stage_post._post_legacy_arc_export_rq(runid)


@with_exception_logging
def _post_gpkg_export_rq(runid: str) -> None:
    _sync_stage_post_compat()
    return _stage_post._post_gpkg_export_rq(runid)


@with_exception_logging
def post_dss_export_rq(runid: str) -> None:
    _sync_stage_post_compat()
    return _stage_post.post_dss_export_rq(runid)



@with_exception_logging
def _post_make_loss_grid_rq(runid: str) -> None:
    _sync_stage_post_compat()
    return _stage_post._post_make_loss_grid_rq(runid)


@with_exception_logging
def _log_complete_rq(
    runid: str,
    auto_commit_inputs: bool = False,
    commit_stage: str = "WEPP pipeline",
) -> None:
    _sync_stage_finalize_compat()
    return _stage_finalize._log_complete_rq(
        runid,
        auto_commit_inputs=auto_commit_inputs,
        commit_stage=commit_stage,
        send_message=send_discord_message,
    )


@with_exception_logging
def _log_prep_complete_rq(
    runid: str,
    auto_commit_inputs: bool = False,
    commit_stage: str = "WEPP prep-only pipeline",
) -> None:
    _sync_stage_finalize_compat()
    return _stage_finalize._log_prep_complete_rq(
        runid,
        auto_commit_inputs=auto_commit_inputs,
        commit_stage=commit_stage,
        send_message=None,
    )
