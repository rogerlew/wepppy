from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import time

import numpy as np
import rasterio
import redis
from rq import Queue, get_current_job
from rq.job import Job
from whitebox_tools import WhiteboxTools
from osgeo import gdal
from rasterio.windows import Window

from wepppy.all_your_base.geo import raster_stacker
from wepppy.all_your_base.geo.locationinfo import RasterDatasetInterpolator
from wepppy.all_your_base.geo.webclients import wmesque_retrieve
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.base import NoDbAlreadyLockedError
from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.nodb.core import Climate, Landuse, Soils, Watershed, Wepp
from wepppy.nodb.core.watershed import NoOutletFoundError
from wepppy.nodb.skeletonize import RUN_SKELETON_ALLOWLIST, skeletonize_run
from wepppy.nodb.wepp_nodb_post_utils import (
    activate_query_engine_for_run,
    ensure_hillslope_interchange,
    ensure_totalwatsed3,
    ensure_watershed_interchange,
)
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as nodir_resolve
from wepppy.runtime_paths.thaw_freeze import maintenance_lock as nodir_maintenance_lock
from wepppy.rq.topo_utils import _prune_stream_order
from wepppy.topo.watershed_collection import WatershedFeature
from . import culvert_rq_helpers as _helpers
from . import culvert_rq_manifest as _manifest
from . import culvert_rq_pipeline as _pipeline

logger = logging.getLogger(__name__)

TIMEOUT: int = 43_200
CULVERT_BATCH_RQ_JOB_KEY = "run_culvert_batch_rq"
CULVERT_BATCH_LOCK_RETRY_ATTEMPTS = 10
CULVERT_BATCH_LOCK_RETRY_SECONDS = 0.5
CULVERT_CLIP_RASTER_RETRY_ATTEMPTS = 2
CULVERT_CLIP_RASTER_RETRY_SECONDS = 0.25

D8_TO_DELTA: Dict[int, Tuple[int, int]] = {
    1: (-1, 1),
    2: (0, 1),
    4: (1, 1),
    8: (1, 0),
    16: (1, -1),
    32: (0, -1),
    64: (-1, -1),
    128: (-1, 0),
}


class CulvertBatchError(Exception):
    """Raised when a culvert batch fails."""

    def __init__(
        self,
        message: str,
        *,
        total: int = 0,
        succeeded: int = 0,
        failed: int = 0,
    ) -> None:
        super().__init__(message)
        self.total = total
        self.succeeded = succeeded
        self.failed = failed


class WatershedAreaBelowMinimumError(Exception):
    """Raised when a watershed area is below the configured minimum."""


_resolve_batch_root = _helpers._resolve_batch_root
_load_payload_json = _helpers._load_payload_json
_get_dem_cellsize_m = _helpers._get_dem_cellsize_m
_get_model_param_int = _helpers._get_model_param_int
_map_order_reduction_passes = _helpers._map_order_reduction_passes
_watershed_area_m2 = _helpers._watershed_area_m2
_watershed_area_sqm_property = _helpers._watershed_area_sqm_property
_minimum_watershed_area_error = _helpers._minimum_watershed_area_error
_select_watershed_label = _helpers._select_watershed_label
_get_wepppy_version = _helpers._get_wepppy_version

_write_run_metadata = _manifest._write_run_metadata
_write_batch_summary = _manifest._write_batch_summary
_escape_markdown_cell = _manifest._escape_markdown_cell
_format_manifest_value = _manifest._format_manifest_value
_format_manifest_error = _manifest._format_manifest_error
_load_outlet_coords = _manifest._load_outlet_coords
_sum_parquet_column = _manifest._sum_parquet_column
_compute_validation_metrics = _manifest._compute_validation_metrics
_count_parquet_rows = _manifest._count_parquet_rows
_load_run_metadata = _manifest._load_run_metadata
_get_rq_connection = _manifest._get_rq_connection
_fetch_job_info = _manifest._fetch_job_info
_write_runs_manifest = _manifest._write_runs_manifest
_write_run_skeletons_zip = _manifest._write_run_skeletons_zip


def _require_directory_root(wd: str, root: str) -> None:
    resolved = nodir_resolve(wd, root, view="effective")
    if resolved is not None and getattr(resolved, "form", "dir") != "dir":
        raise NoDirError(
            http_status=409,
            code="NODIR_ARCHIVE_ACTIVE",
            message=f"{root} root is archive-backed; directory root required",
        )


def _run_with_directory_root_lock(
    wd: str,
    root: str,
    callback,
    *,
    purpose: str,
):
    _require_directory_root(wd, root)
    with nodir_maintenance_lock(wd, root, purpose=purpose):
        _require_directory_root(wd, root)
        return callback()


def _run_with_directory_roots_lock(
    wd: str,
    roots: tuple[str, ...],
    callback,
    *,
    purpose: str,
):
    lock_roots = tuple(sorted({str(root) for root in roots}))
    for root in lock_roots:
        _require_directory_root(wd, root)

    with ExitStack() as stack:
        for root in lock_roots:
            stack.enter_context(nodir_maintenance_lock(wd, root, purpose=f"{purpose}/{root}"))
        for root in lock_roots:
            _require_directory_root(wd, root)
        return callback()


def _attach_batch_logger(runner: CulvertsRunner) -> None:
    base_logger = getattr(runner, "logger", None)
    if base_logger is None:
        return
    batch_logger = logging.getLogger(f"{base_logger.name}.culvert_rq")
    batch_logger.setLevel(logging.INFO)
    batch_logger.propagate = True
    global logger
    logger = batch_logger
    _manifest.logger = batch_logger


def run_culvert_batch_rq(culvert_batch_uuid: str) -> Job:
    """Orchestrate culvert batch processing and enqueue per-run jobs."""
    job = get_current_job()

    if job is not None:
        job.meta["culvert_batch_uuid"] = culvert_batch_uuid
        job.save()

    batch_root = _resolve_batch_root(culvert_batch_uuid)
    if not batch_root.is_dir():
        raise FileNotFoundError(
            f"Culvert batch root does not exist: {batch_root}"
        )

    payload_metadata = _load_payload_json(batch_root / "metadata.json")
    model_parameters = _load_payload_json(batch_root / "model-parameters.json")

    runner = CulvertsRunner.getInstance(str(batch_root), allow_nonexistent=True)
    if runner is None:
        runner = CulvertsRunner(str(batch_root), "culvert.cfg")
    if job is not None:
        try:
            runner.set_rq_job_id(CULVERT_BATCH_RQ_JOB_KEY, job.id)
        except Exception as exc:
            logger.warning(
                "culvert_batch %s: failed to persist parent job id %s - %s",
                culvert_batch_uuid,
                job.id,
                exc,
            )

    _attach_batch_logger(runner)
    logger.info(f"culvert_batch {culvert_batch_uuid}: starting")

    nlcd_db_override = runner._get_model_param_str(model_parameters, "nlcd_db")

    dem_src = runner._resolve_payload_path(
        payload_metadata, "dem", runner.DEFAULT_DEM_REL_PATH, str(batch_root)
    )
    streams_src = runner._resolve_payload_path(
        payload_metadata, "streams", "topo/streams.tif", str(batch_root)
    )
    watersheds_src = runner._resolve_payload_path(
        payload_metadata,
        "watersheds",
        runner.DEFAULT_WATERSHEDS_REL_PATH,
        str(batch_root),
    )
    flovec_src = batch_root / runner.DEFAULT_FLOVEC_REL_PATH
    netful_src = batch_root / runner.DEFAULT_NETFUL_REL_PATH
    chnjnt_src = batch_root / runner.DEFAULT_CHNJNT_REL_PATH

    for path_label, path in (
        ("DEM", dem_src),
        ("watersheds", watersheds_src),
        ("streams", streams_src),
    ):
        if not Path(path).exists():
            raise FileNotFoundError(f"{path_label} file does not exist: {path}")

    _generate_batch_topo(
        Path(dem_src),
        Path(streams_src),
        Path(flovec_src),
        Path(netful_src),
    )

    # Get cellsize from DEM for minimal stream pruning (2 * cellsize)
    ds = gdal.Open(str(dem_src))
    if ds is None:
        raise FileNotFoundError(f"Cannot open DEM: {dem_src}")
    gt = ds.GetGeoTransform()
    cellsize = abs(gt[1])  # pixel width
    ds = None  # close dataset

    min_length = 2.0 * cellsize
    logger.info(
        "culvert_batch %s: pruning short streams (min_length=%.1f, cellsize=%.1f)",
        culvert_batch_uuid,
        min_length,
        cellsize,
    )
    _prune_short_streams(Path(flovec_src), Path(netful_src), min_length)

    # Check model_parameters for order_reduction_passes override
    order_reduction_passes = runner.order_reduction_passes
    flow_accum_threshold = _get_model_param_int(
        model_parameters, "flow_accum_threshold"
    )
    flow_accum_label = (
        str(flow_accum_threshold)
        if flow_accum_threshold is not None
        else "100(default)"
    )
    if runner.order_reduction_mode == "map":
        mapped_passes = _map_order_reduction_passes(
            cellsize_m=cellsize,
            flow_accum_threshold=flow_accum_threshold,
        )
        if mapped_passes is not None:
            order_reduction_passes = mapped_passes
            logger.info(
                "culvert_batch %s: order_reduction_passes=%d (map mode, cellsize=%.2f, flow_accum_threshold=%s)",
                culvert_batch_uuid,
                order_reduction_passes,
                cellsize,
                flow_accum_label,
            )
    if model_parameters and "order_reduction_passes" in model_parameters:
        try:
            mp_value = int(model_parameters["order_reduction_passes"])
            if mp_value >= 0:
                order_reduction_passes = mp_value
                logger.info(
                    "culvert_batch %s: order_reduction_passes=%d (from model_parameters)",
                    culvert_batch_uuid,
                    order_reduction_passes,
                )
        except (TypeError, ValueError):
            pass
    if order_reduction_passes > 0:
        logger.info(
            "culvert_batch %s: pruning netful stream order (%s passes)",
            culvert_batch_uuid,
            order_reduction_passes,
        )
        _prune_stream_order(
            Path(flovec_src),
            Path(netful_src),
            order_reduction_passes,
        )

    _generate_stream_junctions(Path(flovec_src), Path(netful_src), Path(chnjnt_src))
    streams_chnjnt_src = batch_root / runner.DEFAULT_STREAMS_CHNJNT_REL_PATH
    _generate_stream_junctions(
        Path(flovec_src),
        Path(streams_src),
        streams_chnjnt_src,
    )

    run_ids = runner._load_run_ids(watersheds_src)
    run_config = runner._resolve_run_config(model_parameters)

    for attempt in range(1, CULVERT_BATCH_LOCK_RETRY_ATTEMPTS + 1):
        try:
            with runner.locked():
                runner._culvert_batch_uuid = culvert_batch_uuid
                runner._payload_metadata = deepcopy(payload_metadata)
                runner._model_parameters = (
                    deepcopy(model_parameters) if model_parameters else None
                )
                runner._runs = {}
                runner._run_config = run_config
            break
        except NoDbAlreadyLockedError:
            if attempt >= CULVERT_BATCH_LOCK_RETRY_ATTEMPTS:
                raise
            logger.warning(
                "culvert_batch %s: runner lock busy; retrying (%d/%d)",
                culvert_batch_uuid,
                attempt,
                CULVERT_BATCH_LOCK_RETRY_ATTEMPTS,
            )
            time.sleep(CULVERT_BATCH_LOCK_RETRY_SECONDS)

    base_wd = runner._ensure_base_project()
    if base_wd is None:
        raise ValueError("culvert_runner.base_runid is required to start a culvert batch")

    _ensure_batch_landuse_soils(
        culvert_batch_uuid=culvert_batch_uuid,
        dem_src=Path(dem_src),
        base_wd=Path(base_wd),
        nlcd_db_override=nlcd_db_override,
    )
    os.makedirs(runner.runs_dir, exist_ok=True)

    logger.info(f"culvert_batch {culvert_batch_uuid}: enqueued {len(run_ids)} runs")

    queued_jobs: Dict[str, str]
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        q = Queue("batch", connection=redis_conn)
        final_job, queued_jobs = _pipeline.enqueue_culvert_batch_jobs(
            q,
            job,
            culvert_batch_uuid=culvert_batch_uuid,
            run_ids=run_ids,
            tasks=sys.modules[__name__],
            timeout=TIMEOUT,
        )

    if queued_jobs:
        max_tries = 5
        for attempt in range(max_tries):
            try:
                with runner.locked():
                    for run_id, job_id in queued_jobs.items():
                        run_record = runner._runs.get(run_id)
                        if not run_record:
                            run_record = {
                                "runid": run_id,
                                "point_id": run_id,
                                "wd": str(Path(runner.runs_dir) / run_id),
                            }
                        run_record["job_id"] = job_id
                        runner._runs[run_id] = run_record
            except NoDbAlreadyLockedError as exc:
                if attempt + 1 == max_tries:
                    logger.warning(
                        "culvert_batch %s: skipping run job_id update after %d retries - %s",
                        culvert_batch_uuid,
                        max_tries,
                        exc,
                    )
                    break
                time.sleep(1.0)
            else:
                break

    return final_job


def run_culvert_run_rq(
    runid: str,
    culvert_batch_uuid: str,
    run_id: str,
) -> str:
    """Execute a single culvert run inside the batch queue."""
    job = get_current_job()
    if job is not None:
        job.meta["culvert_batch_uuid"] = culvert_batch_uuid
        job.meta["run_id"] = run_id
        job.save()

    batch_root = _resolve_batch_root(culvert_batch_uuid)
    if not batch_root.is_dir():
        raise FileNotFoundError(
            f"Culvert batch root does not exist: {batch_root}"
        )

    runner = CulvertsRunner.getInstance(str(batch_root), allow_nonexistent=True)
    if runner is None:
        runner = CulvertsRunner(str(batch_root), "culvert.cfg")

    _attach_batch_logger(runner)
    logger.info(f"culvert_run {culvert_batch_uuid}/{run_id}: starting")

    payload_metadata = _load_payload_json(batch_root / "metadata.json")
    model_parameters = _load_payload_json(batch_root / "model-parameters.json")
    dem_path = runner._resolve_payload_path(
        payload_metadata, "dem", runner.DEFAULT_DEM_REL_PATH, str(batch_root)
    )
    cellsize_m = _get_dem_cellsize_m(payload_metadata, Path(dem_path))
    buffer_m = runner.contains_point_buffer_m
    buffer_px = runner.contains_point_buffer_px
    if buffer_m is None and buffer_px > 0 and cellsize_m is not None:
        buffer_m = float(buffer_px) * cellsize_m

    # Note: We skip locking here because run_culvert_batch_rq already
    # initialized the shared runner state. Acquiring a lock would cause
    # contention when multiple workers process runs in parallel.
    if runner.culvert_batch_uuid is None:
        with runner.locked():
            if runner.culvert_batch_uuid is None:
                runner._culvert_batch_uuid = culvert_batch_uuid

    watersheds_path = runner._resolve_payload_path(
        payload_metadata,
        "watersheds",
        runner.DEFAULT_WATERSHEDS_REL_PATH,
        str(batch_root),
    )
    watershed_features = runner.load_watershed_features(watersheds_path)
    watershed_feature = watershed_features.get(run_id)
    culvert_points_path = runner._resolve_payload_path(
        payload_metadata,
        "culvert_points",
        runner.DEFAULT_CULVERT_POINTS_REL_PATH,
        str(batch_root),
    )
    wepppy_version = _get_wepppy_version()

    try:
        culvert_points, culvert_points_crs = runner.load_culvert_points(
            culvert_points_path
        )
    except Exception as exc:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/culvert_rq.py:413", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        error_payload = {
            "type": "CulvertPointsLoadError",
            "message": str(exc),
        }
        return _record_validation_failure(
            runner=runner,
            run_id=run_id,
            culvert_batch_uuid=culvert_batch_uuid,
            run_config=runner.run_config,
            wepppy_version=wepppy_version,
            error_payload=error_payload,
        )

    culvert_point = culvert_points.get(run_id)
    if culvert_point is None:
        error_payload = {
            "type": "CulvertPointMissingError",
            "message": f"Culvert point missing for Point_ID {run_id}",
        }
        return _record_validation_failure(
            runner=runner,
            run_id=run_id,
            culvert_batch_uuid=culvert_batch_uuid,
            run_config=runner.run_config,
            wepppy_version=wepppy_version,
            error_payload=error_payload,
        )

    if watershed_feature is None:
        error_payload = {
            "type": "WatershedFeatureMissingError",
            "message": f"Watershed feature missing for Point_ID {run_id}",
        }
        return _record_validation_failure(
            runner=runner,
            run_id=run_id,
            culvert_batch_uuid=culvert_batch_uuid,
            run_config=runner.run_config,
            wepppy_version=wepppy_version,
            error_payload=error_payload,
        )

    if not watershed_feature.contains_point(
        culvert_point,
        point_crs=culvert_points_crs,
        buffer_m=buffer_m,
    ):
        error_payload = {
            "type": "CulvertPointOutsideWatershedError",
            "message": (
                "Culvert point is outside the watershed polygon "
                f"(Point_ID {run_id})"
            ),
        }
        return _record_validation_failure(
            runner=runner,
            run_id=run_id,
            culvert_batch_uuid=culvert_batch_uuid,
            run_config=runner.run_config,
            wepppy_version=wepppy_version,
            error_payload=error_payload,
        )

    area_error = _minimum_watershed_area_error(
        run_id=run_id,
        watershed_feature=watershed_feature,
        minimum_watershed_area_m2=runner.minimum_watershed_area_m2,
    )
    if area_error is not None:
        return _record_validation_failure(
            runner=runner,
            run_id=run_id,
            culvert_batch_uuid=culvert_batch_uuid,
            run_config=runner.run_config,
            wepppy_version=wepppy_version,
            error_payload=area_error,
        )

    runner.create_run_if_missing(
        run_id,
        payload_metadata,
        model_parameters,
        watershed_feature=watershed_feature,
    )
    run_wd = Path(runner.runs_dir) / run_id
    if not run_wd.is_dir():
        raise FileNotFoundError(f"Culvert run directory missing: {run_wd}")

    nlcd_db_override = runner._get_model_param_str(model_parameters, "nlcd_db")

    status = _process_culvert_run(
        culvert_batch_uuid=culvert_batch_uuid,
        run_id=run_id,
        run_wd=run_wd,
        watershed_feature=watershed_feature,
        run_config=runner.run_config,
        wepppy_version=wepppy_version,
        nlcd_db_override=nlcd_db_override,
        minimum_watershed_area_m2=runner.minimum_watershed_area_m2,
    )
    if job is not None:
        job_created = job.created_at.isoformat() if job.created_at else None
        try:
            job_status = job.get_status()
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/culvert_rq.py:518", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            job_status = None
        if job_status == "started":
            job_status = "finished"
        max_tries = 5
        for attempt in range(max_tries):
            try:
                with runner.locked():
                    run_record = runner._runs.get(run_id, {})
                    run_record.setdefault("runid", run_id)
                    run_record.setdefault("point_id", run_id)
                    run_record.setdefault("wd", str(run_wd))
                    run_record["job_status"] = job_status
                    run_record["job_created"] = job_created
                    runner._runs[run_id] = run_record
            except NoDbAlreadyLockedError as exc:
                if attempt + 1 == max_tries:
                    logger.warning(
                        "culvert_run %s/%s: failed to update job metadata after %d retries - %s",
                        culvert_batch_uuid,
                        run_id,
                        max_tries,
                        exc,
                    )
                    break
                time.sleep(1.0)
            except Exception as exc:
                logger.warning(
                    "culvert_run %s/%s: failed to update job metadata - %s",
                    culvert_batch_uuid,
                    run_id,
                    exc,
                )
                break
            else:
                break

    return status


def run_culvert_batch_finalize_rq(culvert_batch_uuid: str) -> dict[str, Any]:
    """Rebuild culvert batch summary artifacts after retries or manual repairs."""
    return _final_culvert_batch_complete_rq(culvert_batch_uuid)


def _final_culvert_batch_complete_rq(culvert_batch_uuid: str) -> dict[str, Any]:
    batch_root = _resolve_batch_root(culvert_batch_uuid)
    if not batch_root.is_dir():
        raise FileNotFoundError(
            f"Culvert batch root does not exist: {batch_root}"
        )

    runner = CulvertsRunner.getInstance(str(batch_root), allow_nonexistent=True)
    if runner is None:
        raise FileNotFoundError(
            f"Culvert batch runner not found for: {batch_root}"
        )

    _attach_batch_logger(runner)
    runs = runner.runs
    runs_dir = batch_root / "runs"
    if runs_dir.is_dir():
        for entry in runs_dir.iterdir():
            if not entry.is_dir():
                continue
            run_id = entry.name
            if run_id not in runs:
                runs[run_id] = {
                    "runid": run_id,
                    "point_id": run_id,
                    "wd": str(entry),
                }
    payload_metadata = runner.payload_metadata
    if payload_metadata is None:
        try:
            payload_metadata = _load_payload_json(batch_root / "metadata.json")
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/culvert_rq.py:594", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            payload_metadata = None

    culvert_points: Dict[str, Tuple[float, float]] = {}
    watershed_features: Dict[str, WatershedFeature] = {}
    if payload_metadata is not None:
        try:
            culvert_points_path = runner._resolve_payload_path(
                payload_metadata,
                "culvert_points",
                runner.DEFAULT_CULVERT_POINTS_REL_PATH,
                str(batch_root),
            )
            culvert_points, _ = runner.load_culvert_points(culvert_points_path)
            watersheds_path = runner._resolve_payload_path(
                payload_metadata,
                "watersheds",
                runner.DEFAULT_WATERSHEDS_REL_PATH,
                str(batch_root),
            )
            watershed_features = runner.load_watershed_features(watersheds_path)
        except Exception as exc:
            logger.warning(
                "culvert_batch %s: unable to load validation metadata - %s",
                culvert_batch_uuid,
                exc,
            )
    succeeded = 0
    failed = 0
    skipped_no_outlet = 0
    for run_id, record in runs.items():
        run_wd = Path(record.get("wd") or (batch_root / "runs" / run_id))
        metadata_path = run_wd / "run_metadata.json"
        if metadata_path.is_file():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                metadata = {}
            status = metadata.get("status")
            if status == "success":
                succeeded += 1
            elif status == "skipped_no_outlet":
                skipped_no_outlet += 1
            else:
                failed += 1
            if status:
                record["status"] = status
            error_payload = metadata.get("error")
            if error_payload:
                record["error"] = error_payload
        else:
            failed += 1
        metrics = _compute_validation_metrics(
            run_wd=run_wd,
            culvert_point=culvert_points.get(run_id),
            watershed_feature=watershed_features.get(run_id),
        )
        if metrics:
            record["validation_metrics"] = metrics

    total = len(runs)
    summary = {
        "culvert_batch_uuid": culvert_batch_uuid,
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "skipped_no_outlet": skipped_no_outlet,
    }

    with runner.locked():
        for run_id, record in runs.items():
            run_record = runner._runs.get(run_id, {})
            run_record.update(record)
            runner._runs[run_id] = run_record
        runner._completed_at = datetime.now(timezone.utc).isoformat()
        runner._retention_days = runner.DEFAULT_RETENTION_DAYS
        runner._summary = summary

    _write_batch_summary(batch_root / "batch_summary.json", summary)
    try:
        _write_runs_manifest(batch_root, culvert_batch_uuid, runs, runner, summary)
    except Exception as exc:
        logger.warning(
            "culvert_batch %s: failed to write runs_manifest.md - %s",
            culvert_batch_uuid,
            exc,
        )
    try:
        _write_run_skeletons_zip(batch_root)
    except Exception as exc:
        logger.warning(
            "culvert_batch %s: failed to write weppcloud_run_skeletons.zip - %s",
            culvert_batch_uuid,
            exc,
        )

    # Log skipped runs for assessment
    if skipped_no_outlet > 0:
        logger.warning(
            f"culvert_batch {culvert_batch_uuid}: {skipped_no_outlet}/{total} runs "
            "skipped (no outlet - stream network too sparse)"
        )

    # Only raise error if all non-skipped runs failed
    processable = total - skipped_no_outlet
    if succeeded == 0 and processable > 0:
        logger.error(
            f"culvert_batch {culvert_batch_uuid}: all {processable} processable runs failed"
        )
        raise CulvertBatchError(
            f"All {processable} processable culvert runs failed ({skipped_no_outlet} skipped)",
            total=total,
            succeeded=succeeded,
            failed=failed,
        )

    if failed > 0:
        logger.warning(
            f"culvert_batch {culvert_batch_uuid}: {failed}/{total} runs failed"
        )
    else:
        logger.info(
            f"culvert_batch {culvert_batch_uuid}: {succeeded}/{total} runs succeeded, "
            f"{skipped_no_outlet} skipped"
        )

    return summary


def _generate_batch_topo(
    dem_path: Path,
    streams_path: Path,
    flovec_path: Path,
    netful_path: Path,
) -> None:
    """Generate shared topo rasters for culvert batch processing."""
    if not dem_path.exists():
        raise FileNotFoundError(f"DEM file does not exist: {dem_path}")
    if not streams_path.exists():
        raise FileNotFoundError(f"Streams file does not exist: {streams_path}")

    if flovec_path.exists():
        flovec_path.unlink()
    if netful_path.exists():
        netful_path.unlink()

    wbt = WhiteboxTools(verbose=False, raise_on_error=True)
    wbt.set_working_dir(str(flovec_path.parent))

    wbt.d8_pointer(dem=str(dem_path), output=str(flovec_path), esri_pntr=False)
    shutil.copy2(streams_path, netful_path)

    if not flovec_path.exists() or not netful_path.exists():
        raise RuntimeError("Failed to generate batch topo rasters.")


def _prune_short_streams(
    flovec_path: Path,
    netful_path: Path,
    min_length: float,
) -> None:
    if min_length <= 0:
        return
    if not flovec_path.exists():
        raise FileNotFoundError(f"Flow vector file does not exist: {flovec_path}")
    if not netful_path.exists():
        raise FileNotFoundError(f"Stream network file does not exist: {netful_path}")

    wbt = WhiteboxTools(verbose=False, raise_on_error=True)
    wbt.set_working_dir(str(netful_path.parent))

    output = netful_path.with_name("netful.short_pruned.tif")
    if output.exists():
        output.unlink()

    ret = wbt.remove_short_streams(
        d8_pntr=str(flovec_path),
        streams=str(netful_path),
        output=str(output),
        min_length=min_length,
        esri_pntr=False,
    )
    if ret != 0:
        raise RuntimeError(
            "RemoveShortStreams failed "
            f"(input={netful_path}, output={output}, min_length={min_length})"
        )

    os.replace(output, netful_path)


def _generate_stream_junctions(
    flovec_path: Path,
    netful_path: Path,
    chnjnt_path: Path,
) -> None:
    if not flovec_path.exists():
        raise FileNotFoundError(f"Flow vector file does not exist: {flovec_path}")
    if not netful_path.exists():
        raise FileNotFoundError(f"Stream network file does not exist: {netful_path}")

    wbt = WhiteboxTools(verbose=False, raise_on_error=True)
    wbt.set_working_dir(str(netful_path.parent))

    if chnjnt_path.exists():
        chnjnt_path.unlink()

    ret = wbt.stream_junction_identifier(
        d8_pntr=str(flovec_path),
        streams=str(netful_path),
        output=str(chnjnt_path),
    )
    if ret != 0 or not chnjnt_path.exists():
        raise RuntimeError(
            "StreamJunctionIdentifier failed "
            f"(flovec={flovec_path}, netful={netful_path}, output={chnjnt_path})"
        )


def _clip_raster_to_raster_with_retry(
    *,
    wbt: WhiteboxTools,
    input_path: Path,
    mask_path: Path,
    output_path: Path,
    attempts: int = CULVERT_CLIP_RASTER_RETRY_ATTEMPTS,
    retry_seconds: float = CULVERT_CLIP_RASTER_RETRY_SECONDS,
) -> None:
    """
    Run ClipRasterToRaster and tolerate transient cases where no output is written.
    """
    if attempts < 1:
        attempts = 1

    clip_error: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        if output_path.exists():
            output_path.unlink()
        try:
            wbt.clip_raster_to_raster(
                i=str(input_path),
                mask=str(mask_path),
                output=str(output_path),
            )
        except Exception as exc:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/culvert_rq.py:838", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            clip_error = exc
        else:
            if output_path.exists():
                return

        if attempt < attempts:
            if clip_error is None:
                logger.warning(
                    "ClipRasterToRaster produced no output; retrying (%d/%d) "
                    "(input=%s, mask=%s, output=%s)",
                    attempt,
                    attempts,
                    input_path,
                    mask_path,
                    output_path,
                )
            else:
                logger.warning(
                    "ClipRasterToRaster raised %s; retrying (%d/%d) "
                    "(input=%s, mask=%s, output=%s): %s",
                    type(clip_error).__name__,
                    attempt,
                    attempts,
                    input_path,
                    mask_path,
                    output_path,
                    clip_error,
                )
            time.sleep(retry_seconds)

    detail = (
        "ClipRasterToRaster failed "
        f"(input={input_path}, mask={mask_path}, output={output_path})"
    )
    if clip_error is not None:
        raise RuntimeError(f"{detail}: {clip_error}") from clip_error
    raise RuntimeError(detail)


def _generate_masked_stream_junctions(
    flovec_path: Path,
    netful_path: Path,
    watershed_mask_path: Path,
    chnjnt_path: Path,
) -> None:
    if not flovec_path.exists():
        raise FileNotFoundError(f"Flow vector file does not exist: {flovec_path}")
    if not netful_path.exists():
        raise FileNotFoundError(f"Stream network file does not exist: {netful_path}")
    if not watershed_mask_path.exists():
        raise FileNotFoundError(f"Watershed mask file does not exist: {watershed_mask_path}")

    wbt = WhiteboxTools(verbose=False, raise_on_error=True)
    wbt.set_working_dir(str(chnjnt_path.parent))

    masked_netful = chnjnt_path.parent / "netful.masked.tif"
    _clip_raster_to_raster_with_retry(
        wbt=wbt,
        input_path=netful_path,
        mask_path=watershed_mask_path,
        output_path=masked_netful,
    )

    chnjnt_vrt = chnjnt_path.with_suffix(".vrt")
    fallback_chnjnt_src: Optional[Path] = None
    if chnjnt_vrt.exists():
        fallback_chnjnt_src = chnjnt_vrt
    elif chnjnt_path.exists():
        if chnjnt_path.is_symlink():
            fallback_chnjnt_src = Path(os.path.realpath(chnjnt_path))
        else:
            fallback_chnjnt_src = chnjnt_path

    if not _raster_has_stream_cells(masked_netful):
        if _try_generate_masked_stream_junctions_from_fallback(
            wbt=wbt,
            fallback_chnjnt_src=fallback_chnjnt_src,
            watershed_mask_path=watershed_mask_path,
            chnjnt_path=chnjnt_path,
            chnjnt_vrt=chnjnt_vrt,
        ):
            return

    if chnjnt_path.exists():
        chnjnt_path.unlink()
    ret = wbt.stream_junction_identifier(
        d8_pntr=str(flovec_path),
        streams=str(masked_netful),
        output=str(chnjnt_path),
    )
    if ret != 0 or not chnjnt_path.exists():
        raise RuntimeError(
            "StreamJunctionIdentifier failed "
            f"(flovec={flovec_path}, streams={masked_netful}, output={chnjnt_path})"
        )
    if chnjnt_vrt.exists():
        chnjnt_vrt.unlink()


def _try_generate_masked_stream_junctions_from_fallback(
    *,
    wbt: WhiteboxTools,
    fallback_chnjnt_src: Optional[Path],
    watershed_mask_path: Path,
    chnjnt_path: Path,
    chnjnt_vrt: Path,
) -> bool:
    if fallback_chnjnt_src is None or not fallback_chnjnt_src.exists():
        logger.warning(
            "masked netful has no stream cells and no fallback junction source"
        )
        return False

    logger.info(
        "masked netful has no stream cells; clipping junctions from %s",
        fallback_chnjnt_src,
    )
    masked_chnjnt = chnjnt_path.with_name("chnjnt.masked.tif")
    _clip_raster_to_raster_with_retry(
        wbt=wbt,
        input_path=fallback_chnjnt_src,
        mask_path=watershed_mask_path,
        output_path=masked_chnjnt,
    )
    if chnjnt_path.exists():
        chnjnt_path.unlink()
    os.replace(masked_chnjnt, chnjnt_path)
    if chnjnt_vrt.exists():
        chnjnt_vrt.unlink()
    return True


def _is_nodata_value(value: Any, nodata: Optional[float]) -> bool:
    if nodata is None:
        return False
    try:
        if np.isnan(nodata):
            return bool(np.isnan(value))
    except TypeError:
        pass
    return value == nodata


def _raster_has_stream_cells(raster_path: Path) -> bool:
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        nodata = src.nodata

    if nodata is None:
        return bool(np.any(data > 0))
    if np.isnan(nodata):
        valid = ~np.isnan(data)
    else:
        valid = data != nodata
    return bool(np.any(valid & (data > 0)))


def _extend_watershed_mask_to_candidate(
    watershed_mask_path: Path,
    candidate: Tuple[int, int],
) -> bool:
    """Ensure the watershed mask includes the candidate row/col."""
    if not watershed_mask_path.exists():
        raise FileNotFoundError(
            f"Watershed mask file does not exist: {watershed_mask_path}"
        )

    row, col = candidate
    with rasterio.open(watershed_mask_path) as src:
        data = src.read(1)
        profile = src.profile.copy()
        height, width = data.shape

    if row < 0 or row >= height or col < 0 or col >= width:
        return False

    if data[row, col] != 0:
        return True

    data[row, col] = 1
    profile["driver"] = "GTiff"
    seeded_mask = watershed_mask_path.with_name(
        f"{watershed_mask_path.stem}.seeded.tif"
    )
    with rasterio.open(seeded_mask, "w", **profile) as dst:
        dst.write(data, 1)

    os.replace(seeded_mask, watershed_mask_path)
    logger.info(
        "_extend_watershed_mask_to_candidate: added mask pixel at (%s, %s)",
        row,
        col,
    )
    return True


def _parse_outlet_candidates_from_error(error_msg: str) -> Optional[Tuple[int, int]]:
    """
    Parse FindOutlet error to extract candidate exit locations.

    If all candidates exit at the same row/col, return that location.
    Otherwise return None.

    Error formats:
    "...Candidate 0: exited raster at row 19, col 66 without hitting a stream. | Candidate 1: ..."
    "...Candidate 0: reached raster edge at row 19, col 66 with junction count 0 (expected 1). ..."
    """
    import re
    pattern = (
        r"(?:exited raster|reached raster edge|Latest stream encountered) "
        r"at row (\d+), col (\d+)"
    )
    matches = re.findall(pattern, error_msg)

    if not matches:
        return None

    # Check if all candidates point to same location
    locations = set((int(r), int(c)) for r, c in matches)
    if len(locations) == 1:
        row, col = locations.pop()
        return row, col

    return None


def _seed_outlet_pixel(
    row: int,
    col: int,
    netful_path: Path,
    flovec_path: Path,
) -> None:
    """
    Seed a minimal stream stub at the specified row/col location.

    This writes a two-pixel stream (outlet + one upstream neighbor when found)
    so WhiteboxTools find_outlet can satisfy the junction-count constraint.
    """
    logger.info(f"_seed_outlet_pixel: seeding stream at pixel ({row}, {col})")

    # Read the netful and seed the pixel
    with rasterio.open(netful_path) as src:
        data = src.read(1)
        profile = src.profile.copy()
        height, width = data.shape

    if row < 0 or row >= height or col < 0 or col >= width:
        raise ValueError(
            f"_seed_outlet_pixel: outlet pixel ({row}, {col}) out of bounds "
            f"(height={height}, width={width})"
        )

    # Set the outlet cell to 1 (stream)
    data[row, col] = 1

    upstream_pixel = None
    with rasterio.open(flovec_path) as fv:
        flovec = fv.read(1)
        flovec_nodata = fv.nodata

    for ptr_val, (dr, dc) in D8_TO_DELTA.items():
        nr = row - dr
        nc = col - dc
        if nr < 0 or nr >= height or nc < 0 or nc >= width:
            continue
        neighbor_ptr = flovec[nr, nc]
        if _is_nodata_value(neighbor_ptr, flovec_nodata):
            continue
        try:
            if int(neighbor_ptr) == ptr_val:
                upstream_pixel = (nr, nc)
                break
        except (TypeError, ValueError):
            continue

    if upstream_pixel is not None:
        up_row, up_col = upstream_pixel
        data[up_row, up_col] = 1
    else:
        logger.warning(
            "_seed_outlet_pixel: no upstream neighbor found for (%s, %s); "
            "junction count may remain 0",
            row,
            col,
        )

    # Write seeded netful to a temp tif
    seeded_tif = netful_path.with_name("netful.seeded.tif")
    profile['driver'] = 'GTiff'
    with rasterio.open(seeded_tif, 'w', **profile) as dst:
        dst.write(data, 1)

    if netful_path.suffix.lower() == ".vrt":
        # Create VRT pointing to seeded tif (overwrites original VRT)
        vrt_path = netful_path.with_name("netful.vrt")
        result = gdal.Translate(str(vrt_path), str(seeded_tif), format="VRT")
        if result is None:
            raise RuntimeError(f"Failed to create VRT: {vrt_path}")
        result = None  # Close dataset
        logger.info(
            f"_seed_outlet_pixel: wrote seeded netful to {seeded_tif}, updated VRT"
        )
    else:
        os.replace(seeded_tif, netful_path)
        logger.info(
            f"_seed_outlet_pixel: wrote seeded netful to {netful_path}"
        )


def _ensure_outlet_junction(
    chnjnt_path: Path,
    outlet_pixel: Tuple[int, int],
    target_mask_path: Optional[Path] = None,
) -> None:
    """
    Ensure a single outlet junction exists when stream_junction_identifier
    produces no junctions (common with single-pixel stream networks).
    """
    if not chnjnt_path.exists():
        raise FileNotFoundError(f"Stream junction file does not exist: {chnjnt_path}")

    with rasterio.open(chnjnt_path) as src:
        data = src.read(1)
        profile = src.profile.copy()

    if np.any(data > 0):
        return

    col, row = outlet_pixel
    height, width = data.shape
    if row < 0 or row >= height or col < 0 or col >= width:
        raise ValueError(
            f"_ensure_outlet_junction: outlet pixel ({col}, {row}) out of bounds "
            f"(height={height}, width={width})"
        )

    data[row, col] = 1
    profile['driver'] = 'GTiff'
    seeded_chnjnt = chnjnt_path.with_name("chnjnt.seeded.tif")
    with rasterio.open(seeded_chnjnt, 'w', **profile) as dst:
        dst.write(data, 1)

    os.replace(seeded_chnjnt, chnjnt_path)
    neighbor_sum = _sum_d8_neighbor_mask(target_mask_path, row, col)
    logger.info(
        "_ensure_outlet_junction: seeded outlet junction at (%s, %s); "
        "target_mask_d8_neighbor_sum=%s",
        col,
        row,
        neighbor_sum if neighbor_sum is not None else "-",
    )


def _ensure_batch_landuse_soils(
    *,
    culvert_batch_uuid: str,
    dem_src: Path,
    base_wd: Path,
    nlcd_db_override: Optional[str],
) -> tuple[Path, Path]:
    batch_root = _resolve_batch_root(culvert_batch_uuid)
    landuse_root = batch_root / "landuse"
    soils_root = batch_root / "soils"

    nlcd_30m = landuse_root / "nlcd_30m.tif"
    nlcd_resampled = landuse_root / "nlcd.tif"
    ssurgo_30m = soils_root / "ssurgo_30m.tif"
    ssurgo_resampled = soils_root / "ssurgo.tif"

    runner = CulvertsRunner.getInstance(str(batch_root), allow_nonexistent=True)
    if runner is None:
        runner = CulvertsRunner(str(batch_root), "culvert.cfg")

    landuse = Landuse.getInstance(str(base_wd))
    soils = Soils.getInstance(str(base_wd))

    if landuse.wmesque_version != 2:
        raise ValueError(
            f"Culvert batches require wmesque version 2 for landuse (got {landuse.wmesque_version})."
        )
    if soils.wmesque_version != 2:
        raise ValueError(
            f"Culvert batches require wmesque version 2 for soils (got {soils.wmesque_version})."
        )

    nlcd_db = nlcd_db_override or landuse.nlcd_db
    ssurgo_db = soils.ssurgo_db

    if nlcd_db is None:
        raise ValueError("nlcd_db is required to build culvert landuse maps")
    if ssurgo_db is None:
        raise ValueError("ssurgo_db is required to build culvert soils maps")

    rdi = RasterDatasetInterpolator(str(dem_src))
    extent_wgs84 = list(rdi.extent)
    extent_native = [rdi.left, rdi.lower, rdi.right, rdi.upper]
    extent_crs = rdi.proj4 or None

    with runner.locked():
        os.makedirs(landuse_root, exist_ok=True)
        os.makedirs(soils_root, exist_ok=True)

        if not nlcd_30m.exists():
            nlcd_extent = extent_wgs84
            nlcd_extent_crs = None
            if landuse.wmesque_version == 2 and extent_crs is not None:
                nlcd_extent = extent_native
                nlcd_extent_crs = extent_crs
            wmesque_retrieve(
                nlcd_db,
                nlcd_extent,
                str(nlcd_30m),
                30.0,
                v=landuse.wmesque_version,
                wmesque_endpoint=landuse.wmesque_endpoint,
                extent_crs=nlcd_extent_crs,
            )
        if not ssurgo_30m.exists():
            ssurgo_extent = extent_wgs84
            ssurgo_extent_crs = None
            if soils.wmesque_version == 2 and extent_crs is not None:
                ssurgo_extent = extent_native
                ssurgo_extent_crs = extent_crs
            wmesque_retrieve(
                ssurgo_db,
                ssurgo_extent,
                str(ssurgo_30m),
                30.0,
                v=soils.wmesque_version,
                wmesque_endpoint=soils.wmesque_endpoint,
                extent_crs=ssurgo_extent_crs,
            )

        if not nlcd_resampled.exists():
            raster_stacker(str(nlcd_30m), str(dem_src), str(nlcd_resampled), resample="near")
        if not ssurgo_resampled.exists():
            raster_stacker(str(ssurgo_30m), str(dem_src), str(ssurgo_resampled), resample="near")

    return nlcd_resampled, ssurgo_resampled


def _process_culvert_run(
    *,
    culvert_batch_uuid: str,
    run_id: str,
    run_wd: Path,
    watershed_feature: Optional[WatershedFeature],
    run_config: str,
    wepppy_version: Optional[str],
    nlcd_db_override: Optional[str],
    minimum_watershed_area_m2: Optional[float],
) -> str:
    """
    Process a single culvert run.

    Returns "success", "failed", or "skipped_no_outlet".
    """
    runid = f"culvert;;{culvert_batch_uuid};;{run_id}"
    started_at = datetime.now(timezone.utc)
    status = "success"
    error_payload = None

    logger.info(f"culvert_run {culvert_batch_uuid}/{run_id}: starting")

    try:
        if watershed_feature is None:
            raise ValueError(f"Watershed feature not found for Point_ID {run_id}")

        wd = str(run_wd)
        watershed = Watershed.getInstance(wd)
        landuse = Landuse.getInstance(wd)
        soils = Soils.getInstance(wd)
        climate = Climate.getInstance(wd)  # Settings from copied base project
        wepp = Wepp.getInstance(wd)

        if nlcd_db_override is not None:
            landuse.nlcd_db = nlcd_db_override

        def _mutate_watershed() -> None:
            wbt = watershed._ensure_wbt()

            # Try find_outlet; if it fails due to no streams, seed and retry.
            outlet_pixel: Optional[Tuple[int, int]] = None
            try:
                watershed.find_outlet(watershed_feature=watershed_feature)
                area_error = _minimum_watershed_area_error(
                    run_id=run_id,
                    watershed_feature=watershed_feature,
                    minimum_watershed_area_m2=minimum_watershed_area_m2,
                )
                if area_error is not None:
                    raise WatershedAreaBelowMinimumError(area_error["message"])
            except NoOutletFoundError as e:
                # Parse error to find where all candidates converge.
                seed_loc = _parse_outlet_candidates_from_error(str(e))
                if seed_loc is None:
                    # Candidates don't converge - can't seed.
                    raise

                candidate_row, candidate_col = seed_loc
                target_mask = Path(watershed.target_watershed_path)
                if not target_mask.exists():
                    logger.info(
                        "culvert_run %s/%s: rebuilding target watershed mask at %s",
                        culvert_batch_uuid,
                        run_id,
                        target_mask,
                    )
                    ron = watershed.ron_instance
                    watershed_feature.build_raster_mask(
                        template_filepath=ron.dem_fn,
                        dst_filepath=str(target_mask),
                    )

                area_error = _minimum_watershed_area_error(
                    run_id=run_id,
                    watershed_feature=watershed_feature,
                    minimum_watershed_area_m2=minimum_watershed_area_m2,
                )
                if area_error is not None:
                    raise WatershedAreaBelowMinimumError(area_error["message"])

                if not _extend_watershed_mask_to_candidate(
                    target_mask,
                    (candidate_row, candidate_col),
                ):
                    logger.warning(
                        "culvert_run %s/%s: candidate (%s, %s) outside watershed mask",
                        culvert_batch_uuid,
                        run_id,
                        candidate_row,
                        candidate_col,
                    )
                    raise

                row, col = candidate_row, candidate_col
                logger.info(
                    "culvert_run %s/%s: no streams in watershed, seeding at (%s, %s) "
                    "from candidate (%s, %s)",
                    culvert_batch_uuid,
                    run_id,
                    row,
                    col,
                    candidate_row,
                    candidate_col,
                )

                _seed_outlet_pixel(
                    row=row,
                    col=col,
                    netful_path=Path(wbt.netful),
                    flovec_path=Path(wbt.flovec),
                )

                # Retry find_outlet with seeded stream.
                watershed.find_outlet(watershed_feature=None)  # mask already built
            outlet = watershed.outlet
            if outlet is not None:
                outlet_pixel = outlet.pixel_coords
            if outlet_pixel is not None:
                target_mask = Path(watershed.target_watershed_path)
                if target_mask.exists():
                    col, row = outlet_pixel
                    if not _extend_watershed_mask_to_candidate(target_mask, (row, col)):
                        logger.warning(
                            "culvert_run %s/%s: outlet pixel (%s, %s) out of bounds for %s",
                            culvert_batch_uuid,
                            run_id,
                            row,
                            col,
                            target_mask,
                        )

            _generate_masked_stream_junctions(
                Path(wbt.flovec),
                Path(wbt.netful),
                Path(watershed.target_watershed_path),
                Path(wbt.chnjnt),
            )
            if outlet_pixel is not None:
                _ensure_outlet_junction(
                    Path(wbt.chnjnt),
                    outlet_pixel,
                    Path(watershed.target_watershed_path),
                )

            watershed.build_subcatchments()
            # Reduce per-hillslope cost for batch processing.
            watershed.representative_flowpath = True
            watershed.abstract_watershed()

        _run_with_directory_root_lock(
            wd,
            "watershed",
            _mutate_watershed,
            purpose="culvert-run-watershed",
        )
        batch_root = _resolve_batch_root(culvert_batch_uuid)
        nlcd_map = batch_root / "landuse" / "nlcd.tif"
        ssurgo_map = batch_root / "soils" / "ssurgo.tif"
        if not nlcd_map.exists():
            raise FileNotFoundError(f"Batch NLCD map does not exist: {nlcd_map}")
        if not ssurgo_map.exists():
            raise FileNotFoundError(f"Batch SSURGO map does not exist: {ssurgo_map}")

        def _mutate_landuse_and_soils() -> None:
            landuse.clean()
            soils.clean()
            landuse.symlink_landuse_map(str(nlcd_map), as_cropped_vrt=True)
            soils.symlink_soils_map(str(ssurgo_map), as_cropped_vrt=True)
            landuse.build(retrieve_nlcd=False)
            soils.build(retrieve_gridded_ssurgo=False)

        _run_with_directory_roots_lock(
            wd,
            ("landuse", "soils"),
            _mutate_landuse_and_soils,
            purpose="culvert-run-landuse-soils",
        )

        _run_with_directory_root_lock(
            wd,
            "climate",
            lambda: climate.build(),
            purpose="culvert-run-climate",
        )

        wepp.clean()
        wepp.prep_hillslopes()
        wepp.run_hillslopes()
        ensure_hillslope_interchange(wepp, climate)
        wepp.prep_watershed()
        wepp.run_watershed()
        ensure_totalwatsed3(wepp, climate)
        ensure_watershed_interchange(wepp, climate)
        activate_query_engine_for_run(wepp)
    except NoOutletFoundError as exc:
        # Gracefully handle sparse network - culvert watershed has no stream intersection
        status = "skipped_no_outlet"
        error_payload = {"type": "NoOutletFoundError", "message": str(exc)}
        logger.warning(f"culvert_run {culvert_batch_uuid}/{run_id}: skipped (no outlet) - {exc}")
    except Exception as exc:
        status = "failed"
        error_payload = {"type": type(exc).__name__, "message": str(exc)}
        logger.error(f"culvert_run {culvert_batch_uuid}/{run_id}: failed - {exc}")
    else:
        logger.info(f"culvert_run {culvert_batch_uuid}/{run_id}: completed")
    finally:
        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()

        run_metadata = {
            "runid": runid,
            "point_id": run_id,
            "culvert_batch_uuid": culvert_batch_uuid,
            "config": run_config,
            "status": status,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": duration_seconds,
        }
        if wepppy_version is not None:
            run_metadata["wepppy_version"] = wepppy_version
        if error_payload is not None:
            run_metadata["error"] = error_payload

        _write_run_metadata(run_wd / "run_metadata.json", run_metadata)
        try:
            dev_mode = os.getenv("DEV_MODE", "false").strip().lower() in ("1", "true", "yes")
            if dev_mode and status == "failed":
                logger.info(
                    "culvert_run %s/%s: skipping skeletonize (DEV_MODE + failed)",
                    culvert_batch_uuid,
                    run_id,
                )
            else:
                skeletonize_run(run_wd, RUN_SKELETON_ALLOWLIST)
        except Exception as exc:
            logger.warning(
                "culvert_run %s/%s: skeletonize failed - %s",
                culvert_batch_uuid,
                run_id,
                exc,
            )

    return status


def _record_validation_failure(
    *,
    runner: CulvertsRunner,
    run_id: str,
    culvert_batch_uuid: str,
    run_config: str,
    wepppy_version: Optional[str],
    error_payload: dict[str, str],
) -> str:
    run_wd = Path(runner.runs_dir) / run_id
    run_wd.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc)
    completed_at = started_at
    run_metadata = {
        "runid": f"culvert;;{culvert_batch_uuid};;{run_id}",
        "point_id": run_id,
        "culvert_batch_uuid": culvert_batch_uuid,
        "config": run_config,
        "status": "failed",
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": 0.0,
        "error": error_payload,
    }
    if wepppy_version is not None:
        run_metadata["wepppy_version"] = wepppy_version
    _write_run_metadata(run_wd / "run_metadata.json", run_metadata)

    max_tries = 5
    for attempt in range(max_tries):
        try:
            with runner.locked():
                run_record = runner._runs.get(run_id, {})
                run_record.setdefault("runid", run_id)
                run_record.setdefault("point_id", run_id)
                run_record.setdefault("wd", str(run_wd))
                run_record["status"] = "failed"
                run_record["error"] = error_payload
                runner._runs[run_id] = run_record
        except NoDbAlreadyLockedError as exc:
            if attempt + 1 == max_tries:
                logger.warning(
                    "culvert_run %s/%s: failed to persist validation error after %d retries - %s",
                    culvert_batch_uuid,
                    run_id,
                    max_tries,
                    exc,
                )
                break
            time.sleep(1.0)
        except Exception as exc:
            logger.warning(
                "culvert_run %s/%s: failed to persist validation error - %s",
                culvert_batch_uuid,
                run_id,
                exc,
            )
            break
        else:
            break

    logger.warning(
        "culvert_run %s/%s: validation failed - %s",
        culvert_batch_uuid,
        run_id,
        error_payload.get("message"),
    )
    return "failed"


def _sum_d8_neighbor_mask(
    mask_path: Optional[Path],
    row: int,
    col: int,
) -> Optional[int]:
    if mask_path is None or not mask_path.exists():
        return None
    try:
        with rasterio.open(mask_path) as src:
            height = src.height
            width = src.width
            nodata = src.nodata
            row_start = max(row - 1, 0)
            col_start = max(col - 1, 0)
            row_stop = min(row + 2, height)
            col_stop = min(col + 2, width)
            window = Window(
                col_start,
                row_start,
                col_stop - col_start,
                row_stop - row_start,
            )
            data = src.read(1, window=window)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/culvert_rq.py:1597", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return None

    offset_row = row - row_start
    offset_col = col - col_start
    total = 0
    for dr, dc in D8_TO_DELTA.values():
        nr = offset_row + dr
        nc = offset_col + dc
        if nr < 0 or nc < 0 or nr >= data.shape[0] or nc >= data.shape[1]:
            continue
        value = data[nr, nc]
        if _is_nodata_value(value, nodata):
            continue
        if value > 0:
            total += 1
    return total


__all__ = [
    "TIMEOUT",
    "run_culvert_batch_rq",
    "run_culvert_run_rq",
    "run_culvert_batch_finalize_rq",
    "CulvertBatchError",
]
