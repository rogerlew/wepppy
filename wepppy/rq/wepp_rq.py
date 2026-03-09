from __future__ import annotations
from typing import Any, Iterable

"""
RQ task entry points for orchestrating WEPP model runs and post-processing steps.

The helpers enqueue work onto Redis-backed queues, orchestrate NoDb controller prep,
and publish progress updates so the UI can reflect job status in real time.
"""

import inspect
import socket
import sys
from glob import glob
from os.path import exists as _exists
from os.path import join as _join
from subprocess import call

import redis
from rq import Queue, get_current_job
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
from wepppy.export.prep_details import (
    export_channels_prep_details,
    export_hillslopes_prep_details,
)
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
        run_flowpath,
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
    run_flowpath = _missing_runner  # type: ignore[assignment]
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

_cleanup_dss_export_dir = _dss_helpers._cleanup_dss_export_dir
_copy_dss_readme = _dss_helpers._copy_dss_readme
_resolve_downstream_channel_ids = _dss_helpers._resolve_downstream_channel_ids
_extract_channel_topaz_id = _dss_helpers._extract_channel_topaz_id
_write_dss_channel_geojson = _dss_helpers._write_dss_channel_geojson


_SINGLE_STORM_DEPRECATED_MESSAGE = _stage_helpers.SINGLE_STORM_DEPRECATED_MESSAGE
_NODIR_RECOVERY_ROOTS = _stage_helpers.NODIR_RECOVERY_ROOTS


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
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        runs_dir = _join(wd, 'wepp/runs')
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id})')
        status, _, duration = run_ss_batch_hillslope(wepp_id, runs_dir, wepp_bin=wepp_bin, ss_batch_id=ss_batch_id, status_channel=status_channel)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id}) -> ({status}, {duration})')
        return status, duration
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq.py:242", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id})')
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
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        runs_dir = _join(wd, 'wepp/runs')
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin})')
        status, _, duration = run_hillslope(wepp_id, runs_dir, wepp_bin=wepp_bin, status_channel=status_channel)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin}) -> ({status}, {duration})')
        return status, duration
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq.py:271", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin})')
        raise

@with_exception_logging
def run_flowpath_rq(runid: str, flowpath: str, wepp_bin: str | None = None) -> tuple[bool, float]:
    """Run a flowpath WEPP simulation within an RQ worker.

    Args:
        runid: Identifier used to locate the working directory.
        flowpath: Flowpath identifier that maps to prepared input artifacts.
        wepp_bin: Optional override for the WEPP executable name.

    Returns:
        Tuple with the runner success flag and the runtime in seconds.

    Raises:
        Exception: Propagates any failure produced by the underlying WEPP runner.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        runs_dir = _join(wd, 'wepp/runs')
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid}, flowpath={flowpath}, wepp_bin={wepp_bin})')
        status, _, duration = run_flowpath(flowpath, runs_dir, wepp_bin=wepp_bin, status_channel=status_channel)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid}, flowpath={flowpath}, wepp_bin={wepp_bin}) -> ({status}, {duration})')
        return status, duration
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq.py:300", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid}, flowpath={flowpath}, wepp_bin={wepp_bin})')
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
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        runs_dir = _join(wd, 'wepp/runs')
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid}, wepp_bin={wepp_bin})')
        status, duration = run_watershed(runs_dir, wepp_bin=wepp_bin, status_channel=status_channel)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid}, wepp_bin={wepp_bin}) -> ({status}, {duration})')
        return status, duration
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq.py:328", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid}, wepp_bin={wepp_bin})')
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
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        runs_dir = _join(wd, 'wepp/runs')
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id})')
        status, duration = run_ss_batch_watershed(runs_dir, wepp_bin=wepp_bin, ss_batch_id=ss_batch_id, status_channel=status_channel)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id}) -> ({status}, {duration})')
        return status, duration
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq.py:361", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id})')
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
        wepp = Wepp.getInstance(wd)

        if not wepp.bootstrap_enabled:
            wepp.init_bootstrap()

        StatusMessenger.publish(status_channel, f"rq:{job_id} COMPLETED bootstrap_enable_rq({runid})")
        return {"enabled": True, "runid": runid}
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq.py:385", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f"rq:{job_id} EXCEPTION bootstrap_enable_rq({runid})")
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
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)

        recovered_roots = _recover_mixed_nodir_roots(wd)
        if recovered_roots:
            recovered_txt = ", ".join(recovered_roots)
            recovery_msg = f"Recovered mixed NoDir roots before WEPP run: {recovered_txt}"
            wepp.logger.warning(recovery_msg)
            StatusMessenger.publish(status_channel, recovery_msg)

        if wepp.islocked():
            raise Exception(f'{runid} is locked')

        wepp.ensure_bootstrap_main()

        # send feedback to user
        wepp.logger.info('Running Wepp\n')

        wepp.clean()
        
        # quick prep operations that require locking
        wepp._check_and_set_baseflow_map()
        wepp._check_and_set_phosphorus_map()

        climate = Climate.getInstance(wd)
        _assert_supported_climate(climate)

        wepp.logger.info('    wepp_bin:{}'.format(wepp.wepp_bin))
        if not wepp.run_wepp_watershed:
            wepp.logger.info('Skipping WEPP watershed run (wepp.run_wepp_watershed=False)')

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
            f'rq:{job.id} ENQUEUED {func_name}({runid}) -> awaiting final job {job6_finalfinal.id}',
        )

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq.py:473", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

    return job6_finalfinal


@with_exception_logging
def run_wepp_noprep_rq(runid: str) -> Job:
    """Enqueue WEPP execution using existing inputs (no prep)."""
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)

        recovered_roots = _recover_mixed_nodir_roots(wd, roots=("watershed",))
        if recovered_roots:
            recovered_txt = ", ".join(recovered_roots)
            recovery_msg = f"Recovered mixed NoDir roots before {func_name}({runid}): {recovered_txt}"
            wepp.logger.warning(recovery_msg)
            StatusMessenger.publish(status_channel, recovery_msg)

        if wepp.islocked():
            raise Exception(f'{runid} is locked')

        wepp.logger.info('Running Wepp (no-prep)\n')

        climate = Climate.getInstance(wd)
        _assert_supported_climate(climate)
        if not wepp.run_wepp_watershed:
            wepp.logger.info('Skipping WEPP watershed run (wepp.run_wepp_watershed=False)')

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
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
            f'rq:{job.id} ENQUEUED {func_name}({runid}) -> awaiting final job {job6_finalfinal.id}',
        )

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq.py:527", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
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
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)

        recovered_roots = _recover_mixed_nodir_roots(wd, roots=("watershed",))
        if recovered_roots:
            recovered_txt = ", ".join(recovered_roots)
            recovery_msg = f"Recovered mixed NoDir roots before {func_name}({runid}): {recovered_txt}"
            wepp.logger.warning(recovery_msg)
            StatusMessenger.publish(status_channel, recovery_msg)

        if wepp.islocked():
            raise Exception(f'{runid} is locked')

        wepp.ensure_bootstrap_main()

        if not wepp.run_wepp_watershed:
            wepp.logger.info('Skipping WEPP watershed run (wepp.run_wepp_watershed=False)')
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
        wepp.logger.info('Running Wepp Watershed\n')

        # quick prep operations that require locking
        wepp._check_and_set_baseflow_map()
        wepp._check_and_set_phosphorus_map()

        climate = Climate.getInstance(wd)
        _assert_supported_climate(climate)
        wepp.logger.info('    wepp_bin:{}'.format(wepp.wepp_bin))

        # everything below here is asynchronous, performed by workers
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            wepp.logger.info(f'Running Watershed wepp_bin:{wepp.wepp_bin}... ')
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
            f'rq:{job.id} ENQUEUED {func_name}({runid}) -> awaiting final job {job6_finalfinal.id}',
        )

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq.py:624", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

    return job6_finalfinal


@with_exception_logging
def prep_wepp_watershed_rq(runid: str) -> Job:
    """Enqueue prep-only WEPP input generation for hillslopes + watershed."""
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)

        recovered_roots = _recover_mixed_nodir_roots(wd)
        if recovered_roots:
            recovered_txt = ", ".join(recovered_roots)
            recovery_msg = f"Recovered mixed NoDir roots before {func_name}({runid}): {recovered_txt}"
            wepp.logger.warning(recovery_msg)
            StatusMessenger.publish(status_channel, recovery_msg)

        if wepp.islocked():
            raise Exception(f'{runid} is locked')

        wepp.ensure_bootstrap_main()

        wepp.logger.info('Preparing WEPP inputs only\n')

        # quick prep operations that require locking
        wepp._check_and_set_baseflow_map()
        wepp._check_and_set_phosphorus_map()

        climate = Climate.getInstance(wd)
        _assert_supported_climate(climate)

        wepp.logger.info('    wepp_bin:{}'.format(wepp.wepp_bin))

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
            f'rq:{job.id} ENQUEUED {func_name}({runid}) -> awaiting final job {job6_finalfinal.id}',
        )

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq.py:744", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

    return job6_finalfinal


@with_exception_logging
def run_wepp_watershed_noprep_rq(runid: str) -> Job:
    """Enqueue watershed-only WEPP execution using existing inputs (no prep)."""
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)

        if wepp.islocked():
            raise Exception(f'{runid} is locked')

        if not wepp.run_wepp_watershed:
            wepp.logger.info('Skipping WEPP watershed run (wepp.run_wepp_watershed=False)')
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

        wepp.logger.info('Running Wepp Watershed (no-prep)\n')

        climate = Climate.getInstance(wd)
        _assert_supported_climate(climate)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            has_hillslope_outputs = bool(glob(_join(wepp.output_dir, "H*")))
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
            f'rq:{job.id} ENQUEUED {func_name}({runid}) -> awaiting final job {job6_finalfinal.id}',
        )

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq.py:685", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
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
def _run_flowpaths_rq(runid: str) -> None:
    _sync_stage_prep_compat()
    return _stage_prep._run_flowpaths_rq(runid)


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
