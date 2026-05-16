from __future__ import annotations

"""
RQ tasks that manage project-level preparation, execution, and archival flows.

Each helper wraps a discrete step in the WEPP project lifecycle - from DEM
ingest and landuse building through run forking and archive restoration -
emitting status updates for the front-end while coordinating NoDb controllers.
"""

import errno
import copy
from contextlib import ExitStack
import inspect
import logging
import json
import os
import re
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
from wepppy.nodb.mods.disturbed import Disturbed
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

_hostname = socket.gethostname()
_logger = logging.getLogger(__name__)

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)

TIMEOUT: int = 43_200
FETCH_DEM_AND_BUILD_CHANNELS_CHILD_TIMEOUT: int = int(
    os.getenv("RQ_ENGINE_FETCH_DEM_BUILD_CHANNELS_TIMEOUT", "600")
)
DEFAULT_ZOOM: int = 12
DIRECTORY_ROOT_LOCK_RETRY_ATTEMPTS: int = 5
DIRECTORY_ROOT_LOCK_RETRY_SECONDS: float = 1.0
LANDUSE_MAPPING_BATCH_MAX_EDITS: int = 500
LANDUSE_MAPPING_MAX_KEY_LENGTH: int = 128
LANDUSE_MAPPING_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")

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
):
    retry_attempts = max(1, int(DIRECTORY_ROOT_LOCK_RETRY_ATTEMPTS))
    retry_delay_seconds = max(0.0, float(DIRECTORY_ROOT_LOCK_RETRY_SECONDS))

    for attempt in range(1, retry_attempts + 1):
        _require_directory_root(wd, root)
        try:
            with nodir_maintenance_lock(wd, root, purpose=purpose):
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
) -> None:
    """Delineate channels for the watershed using configured thresholds.

    Args:
        runid: Identifier used to locate the working directory.
        csa: Contributing source area threshold.
        mcl: Minimum channel length threshold.
        stream_pruning_method: Optional stream-pruning selection (`ifolp` or `remove_short_streams`).
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
            clear_nodb_file_cache(runid, pup_relpath="watershed.nodb")
            watershed = Watershed.getInstance(wd)
            if watershed.delineation_backend_is_topaz:
                clear_nodb_file_cache(runid, pup_relpath="topaz.nodb")
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

        _run_with_directory_root_lock(
            wd,
            "watershed",
            _mutate_watershed,
            purpose="build-channels-rq",
        )
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
                    ),
                    timeout=FETCH_DEM_AND_BUILD_CHANNELS_CHILD_TIMEOUT,
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
                    ),
                    timeout=FETCH_DEM_AND_BUILD_CHANNELS_CHILD_TIMEOUT,
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
            clear_nodb_file_cache(runid, pup_relpath="watershed.nodb")
            watershed = Watershed.getInstance(wd)
            if watershed.delineation_backend_is_topaz:
                clear_nodb_file_cache(runid, pup_relpath="topaz.nodb")
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

        _run_with_directory_root_lock(
            wd,
            "watershed",
            _mutate_watershed,
            purpose="build-subcatchments-rq",
        )
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

        _run_with_directory_root_lock(
            wd,
            "watershed",
            _mutate_watershed,
            purpose="abstract-watershed-rq",
        )
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
            except Exception:
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
    except Exception:
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


def _reset_forked_run_job_markers(new_runid: str, new_wd: str, status_channel: str) -> None:
    """Clear inherited async job markers from a newly forked run."""
    StatusMessenger.publish(status_channel, "Clearing inherited job markers...\n")

    clear_nodb_file_cache(new_runid, pup_relpath="wepp.nodb")
    clear_locks(new_runid, pup_relpath="wepp.nodb")
    wepp = Wepp.tryGetInstance(new_wd)
    if wepp is not None:
        wepp.persist_job_hint(job_id=None, job_key=None)

    prep = RedisPrep.tryGetInstance(new_wd)
    if prep is not None:
        queued_job_keys = tuple(prep.get_rq_job_ids().keys())
        for key in queued_job_keys:
            prep.redis.hdel(prep.run_id, f"rq:{key}")
        if queued_job_keys:
            prep.dump()

        if prep.get_archive_job_id():
            prep.clear_archive_job_id()

    StatusMessenger.publish(status_channel, "Clearing inherited job markers... done.\n")


@with_exception_logging
def fork_rq(
    runid: str,
    new_runid: str,
    undisturbify: bool = False,
    skip_wepp_runs_output: bool = False,
) -> None:
    job = get_current_job()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{runid}:fork'

    try:
        StatusMessenger.publish(
            status_channel, f'rq:{job.id} STARTED {func_name}({runid})'
        )
        StatusMessenger.publish(status_channel, f'undisturbify: {undisturbify}')
        StatusMessenger.publish(status_channel, f'skip_wepp_runs_output: {skip_wepp_runs_output}')

        def _initialize_ttl(wd: str) -> None:
            from wepppy.weppcloud.utils.run_ttl import initialize_ttl
            initialize_ttl(wd)

        new_wd = _fork_helpers.prepare_fork_run(
            runid,
            new_runid,
            undisturbify=undisturbify,
            skip_wepp_runs_output=skip_wepp_runs_output,
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
            build_rsync_cmd=lambda run_right, _undisturbify, _skip_wepp_runs_output: _build_fork_rsync_cmd(
                run_right,
                undisturbify=_undisturbify,
                skip_wepp_runs_output=_skip_wepp_runs_output,
            ),
            clean_env_for_system_tools=_clean_env_for_system_tools,
        )
        _reset_forked_run_job_markers(new_runid, new_wd, status_channel)

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

        clear_nodb_file_cache(runid, pup_relpath="rap_ts.nodb")
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

        clear_nodb_file_cache(runid, pup_relpath="openet_ts.nodb")
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
