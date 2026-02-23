from __future__ import annotations

"""
RQ tasks that manage project-level preparation, execution, and archival flows.

Each helper wraps a discrete step in the WEPP project lifecycle - from DEM
ingest and landuse building through run forking and archive restoration -
emitting status updates for the front-end while coordinating NoDb controllers.
"""

import errno
import inspect
import logging
import json
import os
import shutil
import socket
import time
import zipfile
from glob import glob
from subprocess import call
from typing import Any, Mapping, Optional, Sequence

from os.path import exists as _exists
from os.path import join as _join

import redis
from rq import Queue, get_current_job
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

from wepppy.weppcloud.utils.helpers import get_wd, get_primary_wd

from wepppy.nodb.base import clear_locks, clear_nodb_file_cache, lock_statuses
from wepppy.nodir.mutations import mutate_root, mutate_roots
from wepppy.nodir.fs import resolve as nodir_resolve
from wepppy.nodb.core import *
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.ash_transport import Ash
from wepppy.nodb.mods.debris_flow import DebrisFlow
from wepppy.nodb.mods.rangeland_cover import RangelandCover
from wepppy.nodb.mods.rhem import Rhem
from wepppy.nodb.mods.openet import OpenET_TS
from wepppy.nodb.mods.rap import RAP_TS
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

_hostname = socket.gethostname()
_logger = logging.getLogger(__name__)

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)

TIMEOUT: int = 43_200
DEFAULT_ZOOM: int = 12

_clean_env_for_system_tools = _fork_helpers._clean_env_for_system_tools
_build_fork_rsync_cmd = _fork_helpers._build_fork_rsync_cmd

_normalize_relpath = _archive_helpers._normalize_relpath
_is_archive_excluded_relpath = _archive_helpers._is_archive_excluded_relpath
_estimate_archive_required_bytes = _archive_helpers._estimate_archive_required_bytes
_assert_sufficient_disk_space = _archive_helpers._assert_sufficient_disk_space
_calculate_run_payload_bytes = _archive_helpers._calculate_run_payload_bytes
_collect_restore_members = _archive_helpers._collect_restore_members


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
            watershed.build_channels()

        if TaskStub.is_task_enabled(TaskEnum.find_outlet) and prep[str(TaskEnum.find_outlet)] is None:
            StatusMessenger.publish(status_channel, f'setting outlet')
            watershed.set_outlet(
                lng=watershed.outlet.requested_loc.lng, 
                lat=watershed.outlet.requested_loc.lat
            )

        if TaskStub.is_task_enabled(TaskEnum.build_subcatchments) and prep[str(TaskEnum.build_subcatchments)] is None:
            StatusMessenger.publish(status_channel, f'building subcatchments')
            watershed.build_subcatchments()

        if TaskStub.is_task_enabled(TaskEnum.abstract_watershed) and prep[str(TaskEnum.abstract_watershed)] is None:
            StatusMessenger.publish(status_channel, f'abstracting watershed')
            watershed.abstract_watershed()

        if TaskStub.is_task_enabled(TaskEnum.build_landuse) and prep[str(TaskEnum.build_landuse)] is None:
            StatusMessenger.publish(status_channel, f'building landuse')
            landuse.build()

        if TaskStub.is_task_enabled(TaskEnum.build_soils) and prep[str(TaskEnum.build_soils)] is None:
            StatusMessenger.publish(status_channel, f'building soils')
            soils.build()

        if TaskStub.is_task_enabled(TaskEnum.build_climate) and prep[str(TaskEnum.build_climate)] is None:
            StatusMessenger.publish(status_channel, f'building climate')
            climate.build()

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
    wbt_fill_or_breach: Optional[str],
    wbt_blc_dist: Optional[int],
) -> None:
    """Delineate channels for the watershed using configured thresholds.

    Args:
        runid: Identifier used to locate the working directory.
        csa: Contributing source area threshold.
        mcl: Minimum channel length threshold.
        wbt_fill_or_breach: Optional override for Whitebox fill/breach strategy.
        wbt_blc_dist: Optional breaching distance when Whitebox backend is used.

    Raises:
        Exception: Propagates errors from watershed delineation.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:channel_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        def _mutate_watershed() -> None:
            watershed = Watershed.getInstance(wd)
            if watershed.delineation_backend_is_wbt:
                if wbt_fill_or_breach is not None:
                    StatusMessenger.publish(status_channel, f'Setting wbt_fill_or_breach to {wbt_fill_or_breach}')
                    watershed.wbt_fill_or_breach = wbt_fill_or_breach
                if wbt_blc_dist is not None:
                    StatusMessenger.publish(status_channel, f'Setting wbt_blc_dist to {wbt_blc_dist}')
                    watershed.wbt_blc_dist = wbt_blc_dist
            StatusMessenger.publish(status_channel, f'Building channels with csa={csa}, mcl={mcl}')
            watershed.build_channels(csa, mcl)

        mutate_root(wd, "watershed", _mutate_watershed, purpose="build-channels-rq")
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   channel_delineation BUILD_CHANNELS_TASK_COMPLETED')
        
        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_channels)
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

        watershed = Watershed.getInstance(get_wd(runid))
        watershed.set_extent_mode = int(set_extent_mode)
        watershed.map_bounds_text = map_bounds_text

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            if int(set_extent_mode) == 3:
                bjob = q.enqueue_call(
                    build_channels_rq,
                    (runid, csa, mcl, wbt_fill_or_breach, wbt_blc_dist),
                )
                job.meta['jobs:0,func:build_channels_rq'] = bjob.id
                job.save()
            else:
                ajob = q.enqueue_call(fetch_dem_rq, (runid, extent, center, zoom, map_object))
                job.meta['jobs:0,func:fetch_dem_rq'] = ajob.id
                job.save()

                bjob = q.enqueue_call(
                    build_channels_rq,
                    (runid, csa, mcl, wbt_fill_or_breach, wbt_blc_dist),
                    depends_on=ajob,
                )
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
        mutate_root(
            wd,
            "watershed",
            lambda: Watershed.getInstance(wd).set_outlet(outlet_lng, outlet_lat),
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

@with_exception_logging
def build_subcatchments_rq(runid: str, updates: dict[str, Any] | None = None) -> None:
    """Delineate subcatchments after channel extraction is complete.

    Args:
        runid: Identifier used to locate the working directory.

    Raises:
        Exception: Propagates failures from watershed delineation.
    """
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:subcatchment_delineation'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        def _mutate_watershed() -> None:
            watershed = Watershed.getInstance(wd)
            if updates:
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
            watershed.build_subcatchments()
            wait_for_path(watershed.subwta, logger=watershed.logger)

        mutate_root(wd, "watershed", _mutate_watershed, purpose="build-subcatchments-rq")
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   subcatchment_delineation BUILD_SUBCATCHMENTS_TASK_COMPLETED')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:691", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def abstract_watershed_rq(runid: str) -> None:
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
        def _mutate_watershed() -> None:
            watershed = Watershed.getInstance(wd)
            wait_for_path(watershed.subwta, logger=watershed.logger)
            watershed.abstract_watershed()

        mutate_root(wd, "watershed", _mutate_watershed, purpose="abstract-watershed-rq")
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   subcatchment_delineation WATERSHED_ABSTRACTION_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.abstract_watershed)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:723", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def build_subcatchments_and_abstract_watershed_rq(
    runid: str,
    updates: dict[str, Any] | None = None,
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

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            
            ajob = q.enqueue_call(
                build_subcatchments_rq,
                (runid, updates or {}),
                timeout=TIMEOUT,
            )
            job.meta['jobs:0,func:build_subcatchments_rq'] = ajob.id
            job.save()

            bjob = q.enqueue_call(abstract_watershed_rq, (runid,), timeout=TIMEOUT, depends_on=ajob)
            job.meta['jobs:1,func:abstract_watershed_rq'] = bjob.id
            job.save()
        
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
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
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:landuse'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        mutate_root(
            wd,
            "landuse",
            lambda: Landuse.getInstance(wd).build(),
            purpose="build-landuse-rq",
        )
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   landuse LANDUSE_BUILD_TASK_COMPLETED')
        
        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_landuse)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:824", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
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
        mutate_roots(
            wd,
            ("landuse", "soils"),
            lambda: Treatments.getInstance(wd).build_treatments(),
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
        mutate_root(
            wd,
            "soils",
            lambda: Soils.getInstance(wd).build(),
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
        mutate_root(
            wd,
            "climate",
            lambda: Climate.getInstance(wd).build(),
            purpose="build-climate-rq",
        )
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   climate CLIMATE_BUILD_TASK_COMPLETED')

        prep = RedisPrep.getInstance(wd)
        prep.timestamp(TaskEnum.build_climate)
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
        mutate_root(
            wd,
            "climate",
            lambda: Climate.getInstance(wd).set_user_defined_cli(cli_filename),
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

        for root in ("climate", "watershed", "landuse"):
            nodir_resolve(wd, root, view="effective")

        ash = Ash.getInstance(wd)
        ash.run_ash(fire_date, ini_white_ash_depth_mm, ini_black_ash_depth_mm)

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

        for root in ("watershed", "soils"):
            nodir_resolve(wd, root, view="effective")

        debris = DebrisFlow.getInstance(wd)

        options = payload or {}
        cc = options.get("clay_pct")
        ll = options.get("liquid_limit")
        req_datasource = options.get("datasource")

        debris.run_debris_flow(cc=cc, ll=ll, req_datasource=req_datasource)

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

@with_exception_logging
def _finish_fork_rq(runid: str) -> None:
    """Emit fork completion messages once dependent jobs finish."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:fork'
        StatusMessenger.publish(status_channel, 'Running WEPP... done\n')
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   fork FORK_COMPLETE')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:1113", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   fork FORK_FAILED')
        raise


@with_exception_logging
def fork_rq(runid: str, new_runid: str, undisturbify: bool = False) -> None:
    job = get_current_job()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{runid}:fork'

    try:
        StatusMessenger.publish(
            status_channel, f'rq:{job.id} STARTED {func_name}({runid})'
        )
        StatusMessenger.publish(status_channel, f'undisturbify: {undisturbify}')

        def _initialize_ttl(wd: str) -> None:
            from wepppy.weppcloud.utils.run_ttl import initialize_ttl
            initialize_ttl(wd)

        _fork_helpers.prepare_fork_run(
            runid,
            new_runid,
            undisturbify=undisturbify,
            status_channel=status_channel,
            publish_status=StatusMessenger.publish,
            get_wd=get_wd,
            get_primary_wd=get_primary_wd,
            wait_for_paths=wait_for_paths,
            ron_cls=Ron,
            disturbed_cls=Disturbed,
            landuse_cls=Landuse,
            soils_cls=Soils,
            initialize_ttl=_initialize_ttl,
            format_ttl_failure=lambda exc: f'rq:{job.id} STATUS TTL initialization failed ({exc})',
            build_rsync_cmd=lambda run_right, _undisturbify: _build_fork_rsync_cmd(
                run_right,
                undisturbify=_undisturbify,
            ),
            clean_env_for_system_tools=_clean_env_for_system_tools,
        )

        if undisturbify:
            StatusMessenger.publish(status_channel, 'Rerunning WEPP...\n')
            final_wepp_job = run_wepp_rq(new_runid)

            conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
            with redis.Redis(**conn_kwargs) as redis_conn:
                q = Queue(connection=redis_conn)
                q.enqueue(
                    _finish_fork_rq,
                    args=[runid],
                    depends_on=final_wepp_job,
                )
        else:
            StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
            StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   fork FORK_COMPLETE')

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:1173", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   fork FORK_FAILED')
        raise


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

        rap_ts = RAP_TS.getInstance(wd)
        if options:
            try:
                rap_ts.logger.info('RAP_TS job options: %s', json.dumps(options, sort_keys=True))
            except Exception:
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

    except Exception:
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

        openet_ts = OpenET_TS.getInstance(wd)
        if options:
            try:
                openet_ts.logger.info('OpenET_TS job options: %s', json.dumps(options, sort_keys=True))
            except Exception:
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

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq.py:1270", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise
