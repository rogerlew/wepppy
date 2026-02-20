from __future__ import annotations
from typing import Any, Iterable, Optional
from pathlib import Path

"""
RQ task entry points for orchestrating WEPP model runs and post-processing steps.

The helpers enqueue work onto Redis-backed queues, orchestrate NoDb controller prep,
and publish progress updates so the UI can reflect job status in real time.
"""

import contextlib
import inspect
import os
import shutil
import socket
import sys
import time
from glob import glob
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from subprocess import call

import redis
from rq import Queue, get_current_job
from rq.job import Job
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

from wepppy.wepp.interchange import (
    generate_interchange_documentation,
    run_wepp_hillslope_interchange,
    run_wepp_watershed_interchange,
    run_wepp_watershed_tc_out_interchange,
)
from wepppy.wepp.interchange.dss_dates import parse_dss_date
from wepppy.weppcloud.utils.helpers import get_wd

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
from wepppy.io_wait import wait_for_path, wait_for_paths

from wepppy.nodir.errors import nodir_mixed_state
from wepppy.nodir.fs import resolve
from wepppy.nodir.projections import with_root_projection

from wepppy.export.prep_details import (
    export_channels_prep_details,
    export_hillslopes_prep_details
)
from wepppy.query_engine.activate import activate_query_engine
from wepppy.rq.exception_logging import with_exception_logging
from . import wepp_rq_dss as _dss_helpers
from . import wepp_rq_pipeline as _pipeline
from wepppy.rq.swat_rq import _build_swat_inputs_rq, _run_swat_rq
from wepppy.weppcloud.bootstrap.git_lock import (
    acquire_bootstrap_git_lock,
    clear_bootstrap_enable_job_id,
    release_bootstrap_git_lock,
)

try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except:
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


_SINGLE_STORM_DEPRECATED_MESSAGE = (
    "Single-storm climate modes are deprecated and unsupported. "
    "Use continuous/multi-year climate datasets for WEPP runs."
)


_NODIR_RECOVERY_ROOTS = ("climate", "landuse", "soils", "watershed")


def _recover_mixed_nodir_roots(
    wd: str,
    *,
    roots: Iterable[str] = _NODIR_RECOVERY_ROOTS,
) -> tuple[str, ...]:
    """Recover mixed NoDir roots by preserving archive form as source of truth."""

    wd_path = Path(wd)
    recovered: list[str] = []
    for root in roots:
        root_dir = wd_path / root
        root_archive = wd_path / f"{root}.nodir"
        if not root_dir.exists() or not root_archive.exists():
            continue

        # Mixed state means both forms exist. Keep the archive and discard the
        # thawed directory-form tree, which may be partially mutated after a
        # failed callback.
        if root_dir.is_dir() and not root_dir.is_symlink():
            shutil.rmtree(root_dir)
        else:
            root_dir.unlink()
        recovered.append(root)

    return tuple(recovered)


def _assert_supported_climate(climate: Climate) -> None:
    if climate.is_single_storm:
        raise ValueError(_SINGLE_STORM_DEPRECATED_MESSAGE)


@contextlib.contextmanager
def _with_stage_read_projections(
    wd: str,
    *,
    roots: tuple[str, ...],
    purpose: str,
):
    with contextlib.ExitStack() as stack:
        for root in roots:
            target = resolve(wd, root, view="archive")
            if target is None:
                continue

            mount_path = Path(wd) / root
            if mount_path.exists() and not mount_path.is_symlink():
                raise nodir_mixed_state(f"{root} is in mixed state (dir + .nodir present)")

            stack.enter_context(with_root_projection(wd, root, mode="read", purpose=purpose))
        yield


def _bootstrap_autocommit_actor(job: Job | None) -> str:
    job_id = str(getattr(job, "id", "") or "").strip()
    if job_id:
        return f"rq:{job_id}:wepp:auto_commit"
    return "rq:unknown:wepp:auto_commit"


def _bootstrap_autocommit_with_lock(runid: str, wepp: Wepp, stage: str, *, actor: str) -> str | None:
    conn_kwargs = redis_connection_kwargs(RedisDB.LOCK)
    with redis.Redis(**conn_kwargs) as redis_conn:
        lock = acquire_bootstrap_git_lock(
            redis_conn,
            runid=runid,
            operation="auto_commit",
            actor=actor,
        )
        if lock is None:
            wepp.logger.warning("Skipped bootstrap auto-commit for %s: bootstrap lock busy", stage)
            return None
        try:
            return wepp.bootstrap_commit_inputs(stage)
        finally:
            release_bootstrap_git_lock(redis_conn, runid=runid, token=lock.token)


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
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

    return job6_finalfinal


@with_exception_logging
def _prep_multi_ofe_rq(runid: str) -> None:
    """Prepare multi-OFE slope inputs prior to hillslope execution.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates controller or filesystem failures encountered during prep.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        with _with_stage_read_projections(
            wd,
            roots=("watershed", "soils", "landuse"),
            purpose=f"{func_name}:{runid}",
        ):
            wepp._prep_multi_ofe(translator)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _prep_slopes_rq(runid: str) -> None:
    """Export slope files for each hillslope in preparation for WEPP runs.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates controller failures encountered during prep.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        with _with_stage_read_projections(
            wd,
            roots=("watershed",),
            purpose=f"{func_name}:{runid}",
        ):
            wepp._prep_slopes(translator, watershed.clip_hillslopes, watershed.clip_hillslope_length)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _run_hillslopes_rq(runid: str) -> None:
    """Execute all queued hillslope WEPP runs for the scenario.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates failures surfaced by the hillslope runner.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        wepp.run_hillslopes()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _run_flowpaths_rq(runid: str) -> None:
    """Prepare inputs and execute flowpath WEPP runs for the scenario.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates failures surfaced by the flowpath runner.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        with _with_stage_read_projections(
            wd,
            roots=("watershed",),
            purpose=f"{func_name}:{runid}",
        ):
            wepp.prep_and_run_flowpaths()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _prep_managements_rq(runid: str) -> None:
    """Export management files required for upcoming hillslope runs.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates controller failures encountered during prep.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        wepp._prep_managements(translator)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _prep_soils_rq(runid: str) -> None:
    """Export soil files required for upcoming hillslope runs.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates controller failures encountered during prep.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        wepp._prep_soils(translator)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _prep_climates_rq(runid: str) -> None:
    """Copy climate artifacts into the run directory for hillslope prep.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates controller failures encountered during prep.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        wepp._prep_climates(translator)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _prep_remaining_rq(runid: str) -> None:
    """Finalize hillslope preparation, including optional frost/baseflow assets.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates controller failures encountered during prep.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()

        def _prep_remaining() -> None:
            reveg = False
            disturbed = Disturbed.getInstance(wepp.wd, allow_nonexistent=True)
            if disturbed is not None and disturbed.sol_ver == 9005.0:
                reveg = True

            wepp._make_hillslope_runs(translator, reveg=reveg)

            if wepp.run_frost:
                wepp._prep_frost()
            else:
                wepp._remove_frost()

            wepp._prep_phosphorus()

            if wepp.run_baseflow:
                wepp._prep_baseflow()
            else:
                wepp._remove_baseflow()

            if wepp.run_wepp_ui:
                wepp._prep_wepp_ui()
            else:
                wepp._remove_wepp_ui()

            if wepp.run_pmet:
                wepp._prep_pmet()
            else:
                wepp._remove_pmet()

            if wepp.run_snow:
                wepp._prep_snow()
            else:
                wepp._remove_snow()

            if reveg:
                wepp._prep_revegetation()

        _prep_remaining()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _prep_watershed_rq(runid: str) -> None:
    """Generate watershed-scale WEPP inputs after hillslopes complete.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates controller failures encountered during prep.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)

        with _with_stage_read_projections(
            wd,
            roots=("watershed",),
            purpose=f"{func_name}:{runid}",
        ):
            wepp.prep_watershed()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

@with_exception_logging
def _post_run_cleanup_out_rq(runid: str) -> None:
    """Move WEPP .out files into output directories once runs finish.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates filesystem errors encountered during cleanup.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        climate = Climate.getInstance(wd)
        wepp = Wepp.getInstance(wd)
        if climate.climate_mode == ClimateMode.SingleStormBatch:
            for d in climate.ss_batch_storms:
                ss_batch_key = d['ss_batch_key']
                ss_batch_id = d['ss_batch_id']

                wepp.logger.info('    moving .out files...')
                for fn in glob(_join(wepp.runs_dir, '*.out')):
                    dst_path = _join(wepp.output_dir, ss_batch_key, _split(fn)[1])
                    shutil.move(fn, dst_path)

        else:
            wepp.logger.info('    moving .out files...')
            for fn in glob(_join(wepp.runs_dir, '*.out')):
                dst_path = _join(wepp.output_dir, _split(fn)[1])
                shutil.move(fn, dst_path)

        tc_src = _join(wepp.runs_dir, 'tc_out.txt')
        if _exists(tc_src):
            tc_dst = _join(wepp.output_dir, 'tc_out.txt')
            wepp.logger.info('    moving tc_out.txt...')
            shutil.move(tc_src, tc_dst)
            if _exists(tc_dst):
                run_wepp_watershed_tc_out_interchange(
                    wepp.output_dir,
                    delete_after_interchange=wepp.delete_after_interchange,
                )

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _analyze_return_periods_rq(runid: str) -> None:
    """Generate return period summaries for the completed hillslope runs.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates controller failures encountered during analysis.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        output_dir = Path(wepp.output_dir)
        interchange_dir = output_dir / "interchange"
        ebe_path = interchange_dir / "ebe_pw0.parquet"
        alt_ebe = output_dir / "ebe_pw0.parquet"
        if not ebe_path.exists() and alt_ebe.exists():
            ebe_path = alt_ebe
        tot_path = interchange_dir / "totalwatsed3.parquet"
        wait_for_paths(
            [ebe_path, tot_path],
            timeout_s=60.0,
            require_stable_size=True,
            logger=wepp.logger,
        )
        wepp.export_return_periods_tsv_summary(meoization=True)
        wepp.export_return_periods_tsv_summary(meoization=True, extraneous=True)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

@with_exception_logging
def _build_hillslope_interchange_rq(runid: str) -> None:
    """Create hillslope interchange parquet artifacts for downstream tools.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates errors from interchange builders.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        climate = Climate.getInstance(wd)
        delete_after_interchange = climate.delete_after_interchange
        start_year = climate.calendar_start_year
        is_single_storm = climate.is_single_storm
        # Single storm runs don't produce .loss.dat, .soil.dat, or .wat.dat files
        run_wepp_hillslope_interchange(
            _join(wd, 'wepp/output'),
            start_year=start_year,
            run_loss_interchange=not is_single_storm,
            run_soil_interchange=not is_single_storm,
            run_wat_interchange=not is_single_storm,
            delete_after_interchange=delete_after_interchange,
        )
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

@with_exception_logging
def _build_totalwatsed3_rq(runid: str) -> None:
    """Generate the aggregate watershed TotWatSed interchange dataset.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates errors from interchange builders.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        interchange_dir = Path(wepp.output_dir) / "interchange"
        wait_for_paths(
            [interchange_dir / "H.pass.parquet", interchange_dir / "H.wat.parquet"],
            timeout_s=60.0,
            require_stable_size=True,
            logger=wepp.logger,
        )
        wepp._build_totalwatsed3()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _run_hillslope_watbal_rq(runid: str) -> None:
    """Compute water balance metrics once hillslope interchange data exists.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates controller failures encountered during analysis.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wat_file = _join(wd, 'wepp/output/interchange/H.wat.parquet')
        wait_for_path(wat_file, timeout_s=60.0, require_stable_size=True)
        wepp = Wepp.getInstance(wd)
        wepp._run_hillslope_watbal()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _post_prep_details_rq(runid: str) -> None:
    """Export prep detail CSVs/Parquets after runs complete.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates export failures.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        export_channels_prep_details(wd)
        export_hillslopes_prep_details(wd)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

@with_exception_logging
def _post_watershed_interchange_rq(runid: str) -> None:
    """Generate watershed interchange artifacts and documentation.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates errors from interchange builders.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        climate = Climate.getInstance(wd)
        delete_after_interchange = climate.delete_after_interchange
        start_year = climate.calendar_start_year
        run_soil_interchange = not climate.is_single_storm
        run_chnwb_interchange = not climate.is_single_storm
        wepp = Wepp.getInstance(wd)
        output_dir = Path(wepp.output_dir)
        timeout_s = 60.0
        poll_s = 0.5

        def _wait_for_output(filename: str, *, allow_gzip: bool = False) -> Path:
            path = output_dir / filename
            gz_path = path.with_suffix(path.suffix + ".gz") if allow_gzip else None
            deadline = time.monotonic() + timeout_s
            while True:
                if path.exists():
                    wait_for_path(
                        path,
                        timeout_s=timeout_s,
                        poll_s=poll_s,
                        require_stable_size=True,
                        logger=wepp.logger,
                    )
                    return path
                if allow_gzip and gz_path is not None and gz_path.exists():
                    wait_for_path(
                        gz_path,
                        timeout_s=timeout_s,
                        poll_s=poll_s,
                        require_stable_size=True,
                        logger=wepp.logger,
                    )
                    return gz_path
                if time.monotonic() >= deadline:
                    if allow_gzip and gz_path is not None:
                        raise FileNotFoundError(
                            f"Expected file {path} (or {gz_path}) to be available within {timeout_s:.2f}s"
                        )
                    raise FileNotFoundError(
                        f"Expected file {path} to be available within {timeout_s:.2f}s"
                    )
                time.sleep(poll_s)

        _wait_for_output("pass_pw0.txt", allow_gzip=True)
        _wait_for_output("ebe_pw0.txt")
        _wait_for_output("loss_pw0.txt")
        _wait_for_output("chan.out")
        _wait_for_output("chanwb.out")
        if run_chnwb_interchange:
            _wait_for_output("chnwb.txt")
        if run_soil_interchange:
            _wait_for_output("soil_pw0.txt", allow_gzip=True)
        run_wepp_watershed_interchange(
            output_dir,
            start_year=start_year,
            run_soil_interchange=run_soil_interchange,
            run_chnwb_interchange=run_chnwb_interchange,
            delete_after_interchange=delete_after_interchange,
        )
        generate_interchange_documentation(_join(wd, 'wepp/output/interchange'))
        activate_query_engine(wd, run_interchange=False, force_refresh=True)
        StatusMessenger.publish(status_channel, f'rq:{job.id} ACTIVATED query_engine({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _post_legacy_arc_export_rq(runid: str) -> None:
    """Rebuild the legacy Arc-compatible export bundle when requested.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates errors from the export pipeline.
    """
    try:
        from wepppy.export import  legacy_arc_export
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        legacy_arc_export(wd)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _post_gpkg_export_rq(runid: str) -> None:
    """Rebuild the GeoPackage export bundle when requested.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates errors from the export pipeline.
    """
    try:
        from wepppy.export.gpkg_export import gpkg_export
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        gpkg_export(wd)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def post_dss_export_rq(runid: str) -> None:
    """Build DSS exports once hillslope interchange data is ready.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates errors from the export pipeline.
    """
    try:
        from wepppy.wepp.interchange import (
            totalwatsed_partitioned_dss_export,
            archive_dss_export_zip,
            chanout_dss_export,
        )
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:dss_export'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        export_channel_ids = wepp.dss_export_channel_ids
        channel_filter: Optional[list[int]] = export_channel_ids if export_channel_ids else None
        start_date = parse_dss_date(wepp.dss_start_date)
        end_date = parse_dss_date(wepp.dss_end_date)
        dss_export_dir = Path(wd) / "export" / "dss"

        StatusMessenger.publish(status_channel, 'cleaning up previous DSS export directory...')
        _cleanup_dss_export_dir(wd)
        dss_export_zip = _join(wd, 'export/dss.zip')
        if _exists(dss_export_zip):
            if status_channel is not None:
                StatusMessenger.publish(status_channel, 'removing export/dss.zip\n')
            os.remove(dss_export_zip)
                
        StatusMessenger.publish(status_channel, 'writing DSS channel geojson + boundary GMLs...')
        _write_dss_channel_geojson(wd, channel_filter)

        dss_channels_path = dss_export_dir / "dss_channels.geojson"
        if dss_channels_path.exists():
            wait_for_path(
                dss_channels_path,
                timeout_s=60.0,
                require_stable_size=True,
                logger=wepp.logger,
            )
        StatusMessenger.publish(status_channel, 'generating partitioned DSS export...')
        totalwatsed_partitioned_dss_export(
            wd,
            channel_filter,
            status_channel=status_channel,
            start_date=start_date,
            end_date=end_date,
        )
        totalwatsed_exports = sorted(dss_export_dir.glob("totalwatsed3_chan_*.dss"))
        if totalwatsed_exports:
            wait_for_paths(
                totalwatsed_exports,
                timeout_s=60.0,
                require_stable_size=True,
                logger=wepp.logger,
            )
        StatusMessenger.publish(status_channel, 'generating channel outlet DSS export...')
        chanout_dss_export(
            wd,
            status_channel=status_channel,
            start_date=start_date,
            end_date=end_date,
        )
        chanout_exports = sorted(dss_export_dir.glob("peak_chan_*.dss"))
        if chanout_exports:
            wait_for_paths(
                chanout_exports,
                timeout_s=60.0,
                require_stable_size=True,
                logger=wepp.logger,
            )
        _copy_dss_readme(wd, status_channel=status_channel)
        readme_path = dss_export_dir / "README.dss_export.md"
        if readme_path.exists():
            wait_for_path(
                readme_path,
                timeout_s=60.0,
                require_stable_size=True,
                logger=wepp.logger,
            )
        StatusMessenger.publish(status_channel, 'archiving DSS export zip...')
        archive_dss_export_zip(wd, status_channel=status_channel)
        dss_export_zip = Path(wd) / "export" / "dss.zip"
        wait_for_path(
            dss_export_zip,
            timeout_s=60.0,
            require_stable_size=True,
            logger=wepp.logger,
        )

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')

        try:
            prep = RedisPrep.getInstance(wd)
            prep.timestamp(TaskEnum.dss_export)
        except FileNotFoundError:
            pass

        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   dss_export DSS_EXPORT_TASK_COMPLETED')
        
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise



@with_exception_logging
def _post_make_loss_grid_rq(runid: str) -> None:
    """Generate raster loss grids once watershed outputs are available.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates raster generation errors.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        wepp.make_loss_grid()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _log_complete_rq(
    runid: str,
    auto_commit_inputs: bool = False,
    commit_stage: str = "WEPP pipeline",
) -> None:
    """Record final completion metadata and emit notifications for the run.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates failures encountered while emitting metadata.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        try:
            prep = RedisPrep.getInstance(wd)
            prep.timestamp(TaskEnum.run_wepp_watershed)
        except FileNotFoundError:
            pass

        if auto_commit_inputs:
            wepp = Wepp.getInstance(wd)
            _bootstrap_autocommit_with_lock(
                runid,
                wepp,
                commit_stage,
                actor=_bootstrap_autocommit_actor(job),
            )

        ron = Ron.getInstance(wd)
        name = ron.name
        scenario = ron.scenario
        config = ron.config_stem

        link = runid
        if name or scenario:
            if name and scenario:
                link = f'{name} - {scenario} _{runid}_'
            elif name:
                link = f'{name} _{runid}_'
            else:
                link = f'{scenario} _{runid}_'

        if send_discord_message is not None:
            send_discord_message(f':fireworks: [{link}](https://wepp.cloud/weppcloud/runs/{runid}/{config}/)')

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   wepp WEPP_RUN_TASK_COMPLETED')

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise
