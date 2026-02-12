from __future__ import annotations

import json
import math
import logging
import os
import shutil
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
from wepppy.rq.topo_utils import _prune_stream_order
from wepppy.topo.watershed_collection import WatershedFeature

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


def _attach_batch_logger(runner: CulvertsRunner) -> None:
    base_logger = getattr(runner, "logger", None)
    if base_logger is None:
        return
    batch_logger = logging.getLogger(f"{base_logger.name}.culvert_rq")
    batch_logger.setLevel(logging.INFO)
    batch_logger.propagate = True
    global logger
    logger = batch_logger


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

    child_jobs: List[Job] = []
    queued_jobs: Dict[str, str] = {}
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        q = Queue("batch", connection=redis_conn)
        for run_id in run_ids:
            runid = f"culvert;;{culvert_batch_uuid};;{run_id}"
            child_job = q.enqueue_call(
                func=run_culvert_run_rq,
                args=[runid, culvert_batch_uuid, run_id],
                timeout=TIMEOUT,
            )
            child_job.meta["runid"] = runid
            child_job.meta["culvert_batch_uuid"] = culvert_batch_uuid
            child_job.meta["run_id"] = run_id
            child_job.save()
            if job is not None:
                job.meta[f"jobs:0,runid:{runid}"] = child_job.id
                job.save()
            child_jobs.append(child_job)
            queued_jobs[run_id] = child_job.id
            # Stagger job starts to reduce file contention on shared VRT sources
            time.sleep(1)

        final_job = q.enqueue_call(
            func=_final_culvert_batch_complete_rq,
            args=[culvert_batch_uuid],
            timeout=TIMEOUT,
            depends_on=child_jobs if child_jobs else None,
        )
        final_job.meta["culvert_batch_uuid"] = culvert_batch_uuid
        final_job.save()
        if job is not None:
            job.meta["jobs:1,func:_final_culvert_batch_complete_rq"] = final_job.id
            job.save()

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


def _resolve_batch_root(culvert_batch_uuid: str) -> Path:
    culverts_root = Path(os.getenv("CULVERTS_ROOT", "/wc1/culverts")).resolve()
    return culverts_root / culvert_batch_uuid


def _load_payload_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Missing payload file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Payload JSON must be an object: {path}")
    return payload


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
        if fallback_chnjnt_src is not None and fallback_chnjnt_src.exists():
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
            return
        logger.warning(
            "masked netful has no stream cells and no fallback junction source"
        )

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

        wbt = watershed._ensure_wbt()

        # Try find_outlet; if it fails due to no streams, seed and retry
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
            # Parse error to find where all candidates converge
            seed_loc = _parse_outlet_candidates_from_error(str(e))
            if seed_loc is None:
                # Candidates don't converge - can't seed
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

            # Retry find_outlet with seeded stream
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
        watershed.representative_flowpath = True  # Reduce per-hillslope cost for batch processing
        watershed.abstract_watershed()
        batch_root = _resolve_batch_root(culvert_batch_uuid)
        nlcd_map = batch_root / "landuse" / "nlcd.tif"
        ssurgo_map = batch_root / "soils" / "ssurgo.tif"
        if not nlcd_map.exists():
            raise FileNotFoundError(f"Batch NLCD map does not exist: {nlcd_map}")
        if not ssurgo_map.exists():
            raise FileNotFoundError(f"Batch SSURGO map does not exist: {ssurgo_map}")
        landuse.clean()
        soils.clean()
        landuse.symlink_landuse_map(str(nlcd_map), as_cropped_vrt=True)
        soils.symlink_soils_map(str(ssurgo_map), as_cropped_vrt=True)
        landuse.build(retrieve_nlcd=False)
        soils.build(retrieve_gridded_ssurgo=False)
        climate.build()

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


def _write_run_metadata(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _write_batch_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _format_manifest_value(value: Optional[Any]) -> str:
    if value is None:
        return "-"
    text = str(value).strip()
    if not text:
        return "-"
    return _escape_markdown_cell(text)


def _format_manifest_error(error_payload: Any) -> Optional[str]:
    if not error_payload:
        return None
    if isinstance(error_payload, dict):
        err_type = error_payload.get("type")
        err_message = error_payload.get("message")
        if err_type and err_message:
            return f"{err_type}: {err_message}"
        if err_type:
            return str(err_type)
        if err_message:
            return str(err_message)
        return None
    return str(error_payload)


def _load_outlet_coords(outlet_path: Path) -> Optional[Tuple[float, float]]:
    if not outlet_path.is_file():
        return None
    try:
        payload = json.loads(outlet_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    features = payload.get("features") or []
    if not features:
        return None
    feature = features[0] or {}
    geometry = feature.get("geometry") or {}
    if geometry.get("type") != "Point":
        return None
    coords = geometry.get("coordinates") or []
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None
    try:
        return float(coords[0]), float(coords[1])
    except (TypeError, ValueError):
        return None


def _sum_parquet_column(parquet_path: Path, column: str) -> Optional[float]:
    if not parquet_path.is_file():
        return None
    try:
        import duckdb

        con = duckdb.connect()
        sanitized = str(parquet_path).replace("'", "''")
        result = con.execute(
            f"SELECT SUM({column}) FROM read_parquet('{sanitized}')"
        ).fetchone()
        con.close()
        if result and result[0] is not None:
            return float(result[0])
    except Exception:
        pass
    try:
        import pyarrow.compute as pc
        import pyarrow.parquet as pq

        table = pq.read_table(parquet_path, columns=[column])
        total = pc.sum(table[column]).as_py()
        if total is not None:
            return float(total)
    except Exception:
        return None
    return None


def _get_dem_cellsize_m(
    payload_metadata: Dict[str, Any],
    dem_path: Path,
) -> Optional[float]:
    dem_meta = payload_metadata.get("dem")
    if isinstance(dem_meta, dict):
        value = dem_meta.get("resolution_m")
        if value is not None:
            try:
                parsed = float(value)
                if parsed > 0:
                    return parsed
            except (TypeError, ValueError):
                pass
    if not dem_path.exists():
        return None
    try:
        with rasterio.open(dem_path) as src:
            res_x, res_y = src.res
            cellsize = abs(res_x) if res_x else abs(res_y)
    except Exception:
        return None
    if cellsize <= 0:
        return None
    return float(cellsize)


def _get_model_param_int(
    model_parameters: Optional[Dict[str, Any]],
    key: str,
) -> Optional[int]:
    if not model_parameters:
        return None
    value = model_parameters.get(key)
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _map_order_reduction_passes(
    *,
    cellsize_m: Optional[float],
    flow_accum_threshold: Optional[int],
) -> Optional[int]:
    if cellsize_m is None or cellsize_m <= 0:
        return None
    effective_cellsize = cellsize_m
    if flow_accum_threshold is None or flow_accum_threshold <= 0:
        flow_accum_threshold = 100
    effective_cellsize = cellsize_m * math.sqrt(flow_accum_threshold / 100.0)
    if effective_cellsize <= 1.0:
        return 3
    if effective_cellsize <= 4.0:
        return 2
    return 1


def _watershed_area_m2(feature: Optional[WatershedFeature]) -> Optional[float]:
    if feature is None:
        return None
    props = feature.properties or {}
    value = props.get("area_sqm")
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    return float(feature.area_m2)


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


def _watershed_area_sqm_property(
    feature: Optional[WatershedFeature],
) -> Optional[float]:
    if feature is None:
        return None
    props = feature.properties or {}
    if "area_sqm" not in props:
        return None
    value = props.get("area_sqm")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _minimum_watershed_area_error(
    *,
    run_id: str,
    watershed_feature: Optional[WatershedFeature],
    minimum_watershed_area_m2: Optional[float],
) -> Optional[dict[str, str]]:
    if minimum_watershed_area_m2 is None or minimum_watershed_area_m2 <= 0:
        return None
    area_sqm = _watershed_area_sqm_property(watershed_feature)
    if area_sqm is None:
        return None
    if area_sqm >= minimum_watershed_area_m2:
        return None
    return {
        "type": WatershedAreaBelowMinimumError.__name__,
        "message": (
            f"Watershed area {area_sqm:.2f} m^2 below minimum "
            f"{minimum_watershed_area_m2:.2f} m^2 (Point_ID {run_id})"
        ),
    }


def _compute_validation_metrics(
    *,
    run_wd: Path,
    culvert_point: Optional[Tuple[float, float]],
    watershed_feature: Optional[WatershedFeature],
) -> dict[str, float]:
    metrics: dict[str, float] = {}

    if culvert_point is not None:
        metrics["culvert_easting"] = float(culvert_point[0])
        metrics["culvert_northing"] = float(culvert_point[1])

    outlet_coords = _load_outlet_coords(run_wd / "dem" / "wbt" / "outlet.geojson")
    if outlet_coords is not None:
        metrics["outlet_easting"] = float(outlet_coords[0])
        metrics["outlet_northing"] = float(outlet_coords[1])

    if culvert_point is not None and outlet_coords is not None:
        metrics["culvert_outlet_distance_m"] = float(
            math.hypot(outlet_coords[0] - culvert_point[0], outlet_coords[1] - culvert_point[1])
        )

    target_area = _watershed_area_m2(watershed_feature)
    if target_area is not None:
        metrics["target_watershed_area_m2"] = target_area

    hillslope_area = _sum_parquet_column(
        run_wd / "watershed" / "hillslopes.parquet",
        "area",
    )
    channel_area = _sum_parquet_column(
        run_wd / "watershed" / "channels.parquet",
        "area",
    )
    if hillslope_area is not None or channel_area is not None:
        metrics["bounds_area_m2"] = float((hillslope_area or 0.0) + (channel_area or 0.0))

    return metrics


def _count_parquet_rows(parquet_path: Path) -> Optional[int]:
    if not parquet_path.is_file():
        return None
    try:
        import pyarrow.parquet as pq

        parquet_file = pq.ParquetFile(parquet_path)
        metadata = parquet_file.metadata
        if metadata is not None:
            return int(metadata.num_rows)
    except Exception:
        pass
    try:
        import duckdb

        con = duckdb.connect()
        sanitized = str(parquet_path).replace("'", "''")
        result = con.execute(
            f"SELECT COUNT(*) FROM read_parquet('{sanitized}')"
        ).fetchone()
        con.close()
        if result:
            return int(result[0])
    except Exception:
        return None
    return None


def _select_watershed_label(feature: Optional[WatershedFeature]) -> Optional[str]:
    if feature is None:
        return None
    props = feature.properties or {}
    candidates = (
        "watershed_",
        "watershed",
        "Watershed",
        "watershed_name",
        "WatershedName",
        "name",
        "Name",
        "label",
        "Label",
        "id",
        "ID",
    )
    for key in candidates:
        value = props.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    if feature.id is not None:
        text = str(feature.id).strip()
        if text:
            return text
    return None


def _load_run_metadata(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _get_rq_connection() -> Optional[redis.Redis]:
    try:
        conn = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
        conn.ping()
        return conn
    except Exception:
        return None


def _fetch_job_info(
    job_id: Optional[str],
    *,
    redis_conn: Optional[redis.Redis],
) -> tuple[Optional[str], Optional[str]]:
    if not job_id or redis_conn is None:
        return None, None
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        return None, None
    try:
        status = job.get_status()
    except Exception:
        status = None
    created_at = job.created_at.isoformat() if job.created_at else None
    return str(status) if status is not None else None, created_at


def _write_runs_manifest(
    batch_root: Path,
    culvert_batch_uuid: str,
    runs: dict[str, Any],
    runner: CulvertsRunner,
    summary: dict[str, Any],
) -> Path:
    payload_metadata = runner.payload_metadata
    if payload_metadata is None:
        try:
            payload_metadata = _load_payload_json(batch_root / "metadata.json")
        except Exception:
            payload_metadata = None

    watershed_features: dict[str, WatershedFeature] = {}
    if payload_metadata is not None:
        try:
            watersheds_src = runner._resolve_payload_path(
                payload_metadata,
                "watersheds",
                runner.DEFAULT_WATERSHEDS_REL_PATH,
                str(batch_root),
            )
            watershed_features = runner.load_watershed_features(watersheds_src)
        except Exception as exc:
            logger.warning(
                "culvert_batch %s: unable to load watershed features for manifest - %s",
                culvert_batch_uuid,
                exc,
            )

    source_payload = payload_metadata.get("source") if payload_metadata else None
    if not isinstance(source_payload, dict):
        source_payload = {}

    source_system = _format_manifest_value(source_payload.get("system"))
    source_project = _format_manifest_value(source_payload.get("project_id"))
    source_user = _format_manifest_value(source_payload.get("user_id"))
    source_created = _format_manifest_value(
        payload_metadata.get("created_at") if payload_metadata else None
    )
    source_culvert_count = _format_manifest_value(
        payload_metadata.get("culvert_count") if payload_metadata else None
    )

    total_value = _format_manifest_value(summary.get("total"))
    succeeded_value = _format_manifest_value(summary.get("succeeded"))
    failed_value = _format_manifest_value(summary.get("failed"))
    skipped_value = _format_manifest_value(summary.get("skipped_no_outlet"))

    rows: list[str] = []
    redis_conn = _get_rq_connection()
    try:
        for run_id in sorted(runs.keys(), key=lambda value: str(value)):
            record = runs.get(run_id) or {}
            run_wd = Path(record.get("wd") or (batch_root / "runs" / run_id))
            run_metadata = _load_run_metadata(run_wd / "run_metadata.json")
            runid_slug = run_metadata.get("runid") or f"culvert;;{culvert_batch_uuid};;{run_id}"
            point_id = run_metadata.get("point_id") or run_id
            status_value = run_metadata.get("status") or record.get("status")
            error_value = _format_manifest_error(
                run_metadata.get("error") or record.get("error")
            )

            watershed_label = _select_watershed_label(
                watershed_features.get(str(run_id))
            )
            subcatchments = _count_parquet_rows(
                run_wd / "watershed" / "hillslopes.parquet"
            )
            channels = _count_parquet_rows(
                run_wd / "watershed" / "channels.parquet"
            )

            job_id = record.get("job_id")
            job_status, job_created = _fetch_job_info(
                str(job_id) if job_id else None,
                redis_conn=redis_conn,
            )
            metrics = record.get("validation_metrics") or {}
            culvert_easting = metrics.get("culvert_easting")
            culvert_northing = metrics.get("culvert_northing")
            outlet_easting = metrics.get("outlet_easting")
            outlet_northing = metrics.get("outlet_northing")
            distance_m = metrics.get("culvert_outlet_distance_m")
            target_area_m2 = metrics.get("target_watershed_area_m2")
            bounds_area_m2 = metrics.get("bounds_area_m2")

            columns = [
                point_id,
                watershed_label,
                subcatchments,
                channels,
                culvert_batch_uuid,
                runid_slug,
                job_id,
                job_status,
                job_created,
                status_value,
                error_value,
                culvert_easting,
                culvert_northing,
                outlet_easting,
                outlet_northing,
                distance_m,
                target_area_m2,
                bounds_area_m2,
            ]
            formatted = [_format_manifest_value(value) for value in columns]
            rows.append("| " + " | ".join(formatted) + " |")
    finally:
        if redis_conn is not None:
            redis_conn.close()

    manifest_path = batch_root / "runs_manifest.md"
    lines = [
        "# Runs Manifest",
        "## Source",
        f"- source.system: {source_system}",
        f"- source.project_id: {source_project}",
        f"- source.user_id: {source_user}",
        f"- created_at: {source_created}",
        f"- culvert_count: {source_culvert_count}",
        f"- batch_uuid: {culvert_batch_uuid}",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Batch Summary",
        f"- total: {total_value}",
        f"- succeeded: {succeeded_value}",
        f"- failed: {failed_value}",
        f"- skipped_no_outlet: {skipped_value}",
        "",
        "| Point_ID/runid | watershed | n_subcatchments | n_channels | batch_uuid | runid_slug | rq_job_id | job_status | job_created | status | error | culvert_easting | culvert_northing | outlet_easting | outlet_northing | culvert_outlet_distance_m | target_watershed_area_m2 | bounds_area_m2 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines.extend(rows)
    lines.append("")

    manifest_path.write_text("\n".join(lines), encoding="utf-8")
    return manifest_path


def _write_run_skeletons_zip(batch_root: Path) -> Path:
    runs_dir = batch_root / "runs"
    if not runs_dir.is_dir():
        raise FileNotFoundError(f"Runs directory does not exist: {runs_dir}")
    output_path = batch_root / "weppcloud_run_skeletons.zip"
    if output_path.exists():
        output_path.unlink()
    with zipfile.ZipFile(
        output_path, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for extra in (
            batch_root / "runs_manifest.md",
            batch_root / "culverts_runner.nodb",
        ):
            if extra.is_file():
                archive.write(extra, extra.relative_to(batch_root).as_posix())
        for root, _dirnames, filenames in os.walk(
            runs_dir, topdown=True, followlinks=False
        ):
            root_path = Path(root)
            for name in filenames:
                file_path = root_path / name
                arcname = file_path.relative_to(batch_root).as_posix()
                archive.write(file_path, arcname)
    return output_path


def _get_wepppy_version() -> Optional[str]:
    try:
        return importlib_metadata.version("wepppy")
    except importlib_metadata.PackageNotFoundError:
        return None


__all__ = [
    "TIMEOUT",
    "run_culvert_batch_rq",
    "run_culvert_run_rq",
    "CulvertBatchError",
]
