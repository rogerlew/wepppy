from __future__ import annotations
import json
from typing import Any, Dict, Iterable, Optional
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
import time
from glob import glob
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from subprocess import call

from datetime import datetime

import redis
from rq import Queue, get_current_job
from rq.job import Job
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

from wepppy.wepp.interchange import (
    run_wepp_hillslope_interchange, 
    run_wepp_watershed_interchange, 
    generate_interchange_documentation
)
from wepppy.wepp.interchange.dss_dates import parse_dss_date
from wepppy.wepp.interchange.hec_ras_boundary import build_boundary_condition_features
from wepppy.wepp.interchange.hec_ras_buffer import write_hec_buffer_gml
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

from wepppy.export.prep_details import (
    export_channels_prep_details,
    export_hillslopes_prep_details
)
from wepppy.rq.exception_logging import with_exception_logging

try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except:
    send_discord_message = None


_hostname = socket.gethostname()

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)

TIMEOUT: int = 43_200


_DSS_CHANNELS_RELATIVE_PATH = ("export", "dss", "dss_channels.geojson")
_FEATURE_TOPAZ_KEYS = ("TopazID", "topaz_id", "topazId", "topaz", "id", "ID")
_BOUNDARY_CONDITION_WIDTH_M = 100.0



def _safe_int(value: Any) -> int | None:
    try:
        candidate = int(str(value))
    except (TypeError, ValueError):
        return None
    return candidate


def _safe_relpath(base: str, target: str | os.PathLike[str]) -> str:
    try:
        return os.path.relpath(str(target), base)
    except (ValueError, TypeError):
        return str(target)


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

        if wepp.islocked():
            raise Exception(f'{runid} is locked')

        # send feedback to user
        wepp.logger.info('Running Wepp\n')

        wepp.clean()
        
        # quick prep operations that require locking
        wepp._check_and_set_baseflow_map()
        wepp._check_and_set_phosphorus_map()

        #
        # Run Hillslopes
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        climate = Climate.getInstance(wd)
        runs_dir = os.path.abspath(wepp.runs_dir)
        wepp_bin = wepp.wepp_bin

        wepp.logger.info('    wepp_bin:{}'.format(wepp_bin))

        # everything below here is asynchronous, performed by workers
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)

            # jobs:0
            jobs0_hillslopes_prep: list[Job] = []

            if wepp.multi_ofe:
                job_prep_soils = q.enqueue_call(_prep_multi_ofe_rq, (runid,), timeout='4h')
                job.meta['jobs:0,func:_prep_multi_ofe_rq'] = job_prep_soils.id
                jobs0_hillslopes_prep.append(job_prep_soils)
                job.save()
            else:
                _job = q.enqueue_call(_prep_slopes_rq, (runid,), timeout='4h')
                job.meta['jobs:0,func:_prep_slopes_rq'] = _job.id
                jobs0_hillslopes_prep.append(_job)
                job.save()

                _job = q.enqueue_call(_prep_managements_rq, (runid,), timeout='4h')
                job.meta['jobs:0,func:_prep_managements_rq'] = _job.id
                jobs0_hillslopes_prep.append(_job)
                job.save()

                job_prep_soils = q.enqueue_call(_prep_soils_rq, (runid,), timeout='4h')
                job.meta['jobs:0,func:_prep_soils_rq'] = job_prep_soils.id
                jobs0_hillslopes_prep.append(job_prep_soils)
                job.save()

            _job = q.enqueue_call(_prep_climates_rq, (runid,), timeout='4h')
            job.meta['jobs:0,func:_prep_climates_rq'] = _job.id
            jobs0_hillslopes_prep.append(_job)
            job.save()

            job_prep_remaining = q.enqueue_call(_prep_remaining_rq, (runid,), timeout='4h', depends_on=jobs0_hillslopes_prep)
            job.meta['jobs:0,func:_prep_remaining_rq'] = job_prep_remaining.id
            job.save()

            # jobs:1

            jobs1_hillslopes = q.enqueue_call(_run_hillslopes_rq, (runid,), timeout=TIMEOUT, depends_on=job_prep_remaining)
            job.meta['jobs:1,func:run_hillslopes_rq'] = jobs1_hillslopes.id
            job.save()

            #
            # Prep Watershed
            job2_watershed_prep = q.enqueue_call(_prep_watershed_rq, (runid,),
                                  timeout=TIMEOUT,
                                  depends_on=jobs1_hillslopes)
            job.meta[f'jobs:2,func:_prep_watershed_rq'] = job2_watershed_prep.id

            job2_totalwatsed2: Job | None = None
            job2_hillslope_interchange: Job | None = None
            job2_post_dss_export: Job | None = None

            job2_hillslope_interchange = q.enqueue_call(
                _build_hillslope_interchange_rq,
                (runid,),
                timeout=TIMEOUT,
                depends_on=jobs1_hillslopes,
            )
            job.meta['jobs:2,func:_build_hillslope_interchange_rq'] = job2_hillslope_interchange.id
            job.save()

            if not climate.is_single_storm:
                job2_totalwatsed2 = q.enqueue_call(_build_totalwatsed3_rq, (runid,),  timeout=TIMEOUT, depends_on=job2_hillslope_interchange)
                job.meta['jobs:2,func:_build_totalwatsed3_rq'] = job2_totalwatsed2.id
                job.save()

                if wepp.dss_export_on_run_completion:
                    job2_post_dss_export = q.enqueue_call(post_dss_export_rq, (runid,),  timeout=TIMEOUT, depends_on=job2_hillslope_interchange)
                    job.meta['jobs:2,func:_post_dss_export_rq'] = job2_post_dss_export.id
                    job.save()


            jobs2_flowpaths: Job | None = None
            if wepp.run_flowpaths:
                jobs2_flowpaths = q.enqueue_call(_run_flowpaths_rq, (runid,), timeout=TIMEOUT, depends_on=job_prep_remaining)
                job.meta['jobs:2,func:run_flowpaths_rq'] = jobs2_flowpaths.id
                job.save()

            #
            # Run Watershed
            wepp.logger.info(f'Running Watershed wepp_bin:{wepp_bin}... ')

            # jobs:3
            jobs3_watersheds: list[Job] = []
            if climate.climate_mode == ClimateMode.SingleStormBatch:

                for d in climate.ss_batch_storms:
                    ss_batch_key = d['ss_batch_key']
                    ss_batch_id = d['ss_batch_id']

                    _job = q.enqueue_call(
                            func=run_ss_batch_watershed_rq,
                            args=[runid],
                            kwargs=dict(wepp_bin=wepp_bin, ss_batch_id=ss_batch_id),
                            timeout=TIMEOUT,
                            depends_on=job2_watershed_prep)
                    job.meta[f'jobs:3,func:run_ss_batch_watershed_rq,ss_batch_id:{ss_batch_id}'] = _job.id
                    jobs3_watersheds.append(_job)
                    job.save()

            else:
                _job = q.enqueue_call(
                        func=run_watershed_rq,
                        args=[runid],
                        kwargs=dict(wepp_bin=wepp_bin),
                        timeout=TIMEOUT,
                        depends_on=job2_watershed_prep)
                job.meta[f'jobs:3,func:run_watershed_rq'] = _job.id
                jobs3_watersheds.append(_job)
                job.save()

            post_dependencies = jobs3_watersheds or [job2_watershed_prep]

            # jobs:4
            jobs4_post: list[Job] = []

            _job = q.enqueue_call(_post_run_cleanup_out_rq, (runid,),  timeout=TIMEOUT, depends_on=post_dependencies)
            job.meta['jobs:4,func:_post_run_cleanup_out_rq'] = _job.id
            jobs4_post.append(_job)
            job.save()

            if wepp.prep_details_on_run_completion:
                _job = q.enqueue_call(_post_prep_details_rq, (runid,),  timeout=TIMEOUT, depends_on=post_dependencies)
                job.meta['jobs:4,func:_post_prep_details_rq'] = _job.id
                jobs4_post.append(_job)
                job.save()

            if not climate.is_single_storm:
                _job = q.enqueue_call(_run_hillslope_watbal_rq, (runid,),  timeout=TIMEOUT, depends_on=post_dependencies)
                job.meta['jobs:4,func:_run_hillslope_watbal_rq'] = _job.id
                jobs4_post.append(_job)
                job.save()

            if not wepp.multi_ofe:
                _job = q.enqueue_call(_post_make_loss_grid_rq, (runid,),  timeout=TIMEOUT, depends_on=post_dependencies)
                job.meta['jobs:4,func:_post_make_loss_grid_rq'] = _job.id
                jobs4_post.append(_job)
                job.save()

            job_post_watershed_interchange = q.enqueue_call(
                _post_watershed_interchange_rq,
                (runid,),
                timeout=TIMEOUT,
                depends_on=post_dependencies,
            )
            job.meta['jobs:4,func:_post_watershed_interchange_rq'] = job_post_watershed_interchange.id
            jobs4_post.append(job_post_watershed_interchange)
            job.save()

            if not climate.is_single_storm:
                _job = q.enqueue_call(
                    _analyze_return_periods_rq,
                    (runid,),
                    timeout=TIMEOUT,
                    depends_on=job_post_watershed_interchange,
                )
                job.meta['jobs:4,func:_analyze_return_periods_rq'] = _job.id
                jobs4_post.append(_job)
                job.save()

            jobs5_post: list[Job] = []
            if wepp.legacy_arc_export_on_run_completion:
                _job = q.enqueue_call(_post_legacy_arc_export_rq, (runid,), timeout=TIMEOUT, depends_on=jobs4_post)
                job.meta['jobs:5,func:_post_legacy_arc_export_rq'] = _job.id
                jobs5_post.append(_job)
                job.save()

            # if wepp.arc_export_on_run_completion:
            #     _job = q.enqueue_call(_post_gpkg_export_rq, (runid,),  timeout=TIMEOUT, depends_on=jobs4_post)
            #     job.meta['jobs:5,func:_post_gpkg_export_rq'] = _job.id
            #     jobs5_post.append(_job)
            #     job.save()

            if job2_hillslope_interchange is not None:
                jobs5_post.append(job2_hillslope_interchange)

            if job2_totalwatsed2 is not None:
                jobs5_post.append(job2_totalwatsed2)

            if job2_post_dss_export is not None:
                jobs5_post.append(job2_post_dss_export)

            if jobs2_flowpaths is not None:
                jobs5_post.append(jobs2_flowpaths)

            # jobs:6
            job6_finalfinal: Job
            final_dependencies = jobs4_post + jobs5_post
            job6_finalfinal = q.enqueue_call(_log_complete_rq, (runid,), depends_on=final_dependencies)
                
            job.meta['jobs:6,func:_log_complete_rq'] = job6_finalfinal.id
            job.save()
         
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

        reveg = False
        disturbed = Disturbed.getInstance(wepp.wd, allow_nonexistent=True)
        if disturbed is not None:
            if disturbed.sol_ver == 9005.0:
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
        start_year = climate.calendar_start_year
        run_wepp_hillslope_interchange(_join(wd, 'wepp/output'), start_year=start_year)
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
        from wepppy.wepp.interchange._utils import _wait_for_path
        wat_file = _join(wd, 'wepp/output/interchange/H.wat.parquet')
        _wait_for_path(wat_file)
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
        start_year = climate.calendar_start_year
        run_soil_interchange = not climate.is_single_storm
        run_chnwb_interchange = not climate.is_single_storm
        run_wepp_watershed_interchange(
            _join(wd, 'wepp/output'),
            start_year=start_year,
            run_soil_interchange=run_soil_interchange,
            run_chnwb_interchange=run_chnwb_interchange,
        )
        generate_interchange_documentation(_join(wd, 'wepp/output/interchange'))
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


def _cleanup_dss_export_dir(wd: str) -> None:
    dss_export_dir = _join(wd, "export", "dss")
    if _exists(dss_export_dir):
        with contextlib.suppress(OSError):
            shutil.rmtree(dss_export_dir, ignore_errors=False)


def _copy_dss_readme(wd: str, status_channel: Optional[str] = None) -> None:
    """Copy the DSS export README alongside generated artifacts."""
    source = Path(__file__).resolve().parent.parent / "wepp" / "interchange" / "README.dss_export.md"
    if not source.exists():
        return
    dest_dir = Path(wd) / "export" / "dss"
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest_dir / "README.dss_export.md")
        if status_channel is not None:
            StatusMessenger.publish(status_channel, "copied DSS export README\n")
    except OSError:
        # Non-fatal; leave a breadcrumb if the status channel is available.
        if status_channel is not None:
            StatusMessenger.publish(status_channel, "warning: unable to write DSS README\n")
            


def _resolve_downstream_channel_ids(network: Any, seeds: Iterable[int]) -> set[int]:
    resolved: set[int] = set()
    for seed in seeds:
        numeric = _safe_int(seed)
        if numeric is None or numeric <= 0:
            continue
        resolved.add(numeric)
    if not isinstance(network, dict):
        return resolved

    downstream_map: dict[int, set[int]] = {}
    for downstream_raw, upstream_values in network.items():
        downstream_id = _safe_int(downstream_raw)
        if downstream_id is None or downstream_id <= 0:
            continue
        for upstream_raw in upstream_values or []:
            upstream_id = _safe_int(upstream_raw)
            if (
                upstream_id is None
                or upstream_id <= 0
                or upstream_id == downstream_id
            ):
                continue
            downstream_map.setdefault(upstream_id, set()).add(downstream_id)

    stack = list(resolved)
    while stack:
        current = stack.pop()
        for downstream_id in downstream_map.get(current, ()):
            if downstream_id not in resolved:
                resolved.add(downstream_id)
                stack.append(downstream_id)

    return resolved


def _extract_channel_topaz_id(feature: Dict[str, Any]) -> int | None:
    props = feature.get("properties")
    if not isinstance(props, dict):
        return None
    for key in _FEATURE_TOPAZ_KEYS:
        topaz_id = _safe_int(props.get(key))
        if topaz_id is not None:
            return topaz_id
    return None


def _write_dss_channel_geojson(
    wd: str,
    channel_ids: Optional[list[int]],
    *,
    boundary_width_m: float = _BOUNDARY_CONDITION_WIDTH_M,
) -> None:
    dest_path = _join(wd, *_DSS_CHANNELS_RELATIVE_PATH)

    if channel_ids is not None and not channel_ids:
        with contextlib.suppress(OSError):
            os.remove(dest_path)
        return

    try:
        watershed = Watershed.getInstance(wd)
    except Exception:
        return

    channels_geojson = getattr(watershed, "channels_shp", None)
    if not channels_geojson or not _exists(channels_geojson):
        return

    try:
        with open(channels_geojson, "r", encoding="utf-8") as source_fp:
            source_geojson = json.load(source_fp)
    except (OSError, json.JSONDecodeError):
        return

    try:
        network = watershed.network
    except Exception:
        network = None

    include_ids: set[int]
    downstream_ids: Iterable[int]
    if channel_ids is None:
        include_ids = set()
    else:
        downstream_ids = _resolve_downstream_channel_ids(network, channel_ids)
        include_ids = set(downstream_ids)

    source_features = source_geojson.get("features", [])
    filtered_features = []
    selected_topaz_ids: set[int] = set()
    for feature in source_features:
        topaz_id = _extract_channel_topaz_id(feature)
        if topaz_id is None:
            continue
        if channel_ids is None:
            filtered_features.append(feature)
            include_ids.add(topaz_id)
            selected_topaz_ids.add(topaz_id)
        elif topaz_id in include_ids:
            filtered_features.append(feature)
            selected_topaz_ids.add(topaz_id)

    if not filtered_features:
        with contextlib.suppress(OSError):
            os.remove(dest_path)
        return

    boundary_dir = _join(wd, "export", "dss", "boundaries")
    target_boundary_ids = sorted(include_ids) if include_ids else sorted(selected_topaz_ids)

    boundary_features = build_boundary_condition_features(
        watershed,
        target_boundary_ids,
        boundary_dir,
        boundary_width_m=boundary_width_m,
    )
    boundary_shapefiles: list[str] = []
    if boundary_features:
        pattern = os.path.join(boundary_dir, "bc_*.shp")
        for shp_path in sorted(glob(pattern)):
            boundary_shapefiles.append(_safe_relpath(wd, shp_path))
    buffer_info = None
    if target_boundary_ids:
        boundary_filter = set(channel_ids or []) or None
        buffer_info = write_hec_buffer_gml(
            watershed,
            target_boundary_ids,
            _join(wd, "export", "dss"),
            boundary_channel_ids=boundary_filter,
        )

    output_geojson = dict(source_geojson)
    output_geojson["features"] = filtered_features + boundary_features
    metadata = output_geojson.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    metadata.update(
        {
            "selected_topaz_ids": None if channel_ids is None else sorted(set(channel_ids)),
            "downstream_topaz_ids": sorted(include_ids),
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "boundary_condition_width_m": boundary_width_m,
            "boundary_feature_count": len(boundary_features),
        }
    )
    if boundary_shapefiles:
        metadata["boundary_shapefiles"] = boundary_shapefiles
    if buffer_info:
        metadata["channel_buffer"] = buffer_info
        metadata["floodplain_polygon"] = buffer_info.get("buffer_gml")
        if buffer_info.get("buffer_shapefile"):
            metadata["floodplain_polygon_shp"] = buffer_info["buffer_shapefile"]
    output_geojson["metadata"] = metadata

    dest_dir = os.path.dirname(dest_path)
    os.makedirs(dest_dir, exist_ok=True)
    tmp_path = dest_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as dest_fp:
            json.dump(output_geojson, dest_fp)
        os.replace(tmp_path, dest_path)
    except OSError:
        with contextlib.suppress(OSError):
            os.remove(tmp_path)


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

        StatusMessenger.publish(status_channel, 'cleaning up previous DSS export directory...')
        _cleanup_dss_export_dir(wd)
        dss_export_zip = _join(wd, 'export/dss.zip')
        if _exists(dss_export_zip):
            if status_channel is not None:
                StatusMessenger.publish(status_channel, 'removing export/dss.zip\n')
            os.remove(dss_export_zip)
                
        StatusMessenger.publish(status_channel, 'writing DSS channel geojson + boundary GMLs...')
        _write_dss_channel_geojson(wd, channel_filter)

        time.sleep(1)
        StatusMessenger.publish(status_channel, 'generating partitioned DSS export...')
        totalwatsed_partitioned_dss_export(
            wd,
            channel_filter,
            status_channel=status_channel,
            start_date=start_date,
            end_date=end_date,
        )
        time.sleep(1)
        StatusMessenger.publish(status_channel, 'generating channel outlet DSS export...')
        chanout_dss_export(
            wd,
            status_channel=status_channel,
            start_date=start_date,
            end_date=end_date,
        )
        time.sleep(1)
        _copy_dss_readme(wd, status_channel=status_channel)
        time.sleep(0.5)
        StatusMessenger.publish(status_channel, 'archiving DSS export zip...')
        archive_dss_export_zip(wd, status_channel=status_channel)

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
def _log_complete_rq(runid: str) -> None:
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
