from __future__ import annotations

import json
import logging
import os
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Dict, List, Optional

import redis
from rq import Queue, get_current_job
from rq.job import Job
from whitebox_tools import WhiteboxTools
from osgeo import gdal

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.nodb.core import Climate, Landuse, Soils, Watershed, Wepp
from wepppy.nodb.core.watershed import NoOutletFoundError
from wepppy.nodb.wepp_nodb_post_utils import (
    activate_query_engine_for_run,
    ensure_hillslope_interchange,
    ensure_totalwatsed3,
    ensure_watershed_interchange,
)
from wepppy.topo.watershed_collection import WatershedFeature

logger = logging.getLogger(__name__)

TIMEOUT: int = 43_200


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


def run_culvert_batch_rq(culvert_batch_uuid: str) -> Job:
    """Orchestrate culvert batch processing and enqueue per-run jobs."""
    job = get_current_job()

    if job is not None:
        job.meta["culvert_batch_uuid"] = culvert_batch_uuid
        job.save()

    logger.info(f"culvert_batch {culvert_batch_uuid}: starting")

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

    run_ids = runner._load_run_ids(watersheds_src)
    run_config = runner._resolve_run_config(model_parameters)

    with runner.locked():
        runner._culvert_batch_uuid = culvert_batch_uuid
        runner._payload_metadata = deepcopy(payload_metadata)
        runner._model_parameters = deepcopy(model_parameters) if model_parameters else None
        runner._runs = {}
        runner._run_config = run_config

    runner._ensure_base_project()
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

    logger.info(f"culvert_run {culvert_batch_uuid}/{run_id}: starting")

    batch_root = _resolve_batch_root(culvert_batch_uuid)
    if not batch_root.is_dir():
        raise FileNotFoundError(
            f"Culvert batch root does not exist: {batch_root}"
        )

    runner = CulvertsRunner.getInstance(str(batch_root), allow_nonexistent=True)
    if runner is None:
        runner = CulvertsRunner(str(batch_root), "culvert.cfg")

    payload_metadata = _load_payload_json(batch_root / "metadata.json")
    model_parameters = _load_payload_json(batch_root / "model-parameters.json")

    # Note: We skip locking here because run_culvert_batch_rq already
    # initialized the shared runner state. Acquiring a lock would cause
    # contention when multiple workers process runs in parallel.

    runner.create_run_if_missing(run_id, payload_metadata, model_parameters)
    watersheds_path = runner._resolve_payload_path(
        payload_metadata,
        "watersheds",
        runner.DEFAULT_WATERSHEDS_REL_PATH,
        str(batch_root),
    )
    watershed_features = runner.load_watershed_features(watersheds_path)
    run_wd = Path(runner.runs_dir) / run_id
    if not run_wd.is_dir():
        raise FileNotFoundError(f"Culvert run directory missing: {run_wd}")
    wepppy_version = _get_wepppy_version()

    return _process_culvert_run(
        culvert_batch_uuid=culvert_batch_uuid,
        run_id=run_id,
        run_wd=run_wd,
        watershed_feature=watershed_features.get(run_id),
        run_config=runner.run_config,
        wepppy_version=wepppy_version,
    )


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

    runs = runner.runs
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
        else:
            failed += 1

    with runner.locked():
        runner._completed_at = datetime.now(timezone.utc).isoformat()
        runner._retention_days = runner.DEFAULT_RETENTION_DAYS

    total = len(runs)
    summary = {
        "culvert_batch_uuid": culvert_batch_uuid,
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "skipped_no_outlet": skipped_no_outlet,
    }

    _write_batch_summary(batch_root / "batch_summary.json", summary)

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


def _prune_stream_order(
    flovec_path: Path,
    netful_path: Path,
    passes: int,
) -> None:
    """Prune first-order streams from the network.

    Creates intermediate files:
    - netful.strahler.tif (initial Strahler order raster)
    - netful.strahler_pruned_*.tif (order rasters for intermediate passes)
    - netful.pruned_{N}.tif (binary stream map from the final pass)

    The final pruned result is copied to netful.tif, and intermediates are kept
    for debugging and verification.
    """
    if passes < 0:
        raise ValueError("order_reduction_passes must be >= 0")
    if passes == 0:
        return

    if not flovec_path.exists():
        raise FileNotFoundError(f"Flow vector file does not exist: {flovec_path}")
    if not netful_path.exists():
        raise FileNotFoundError(f"Stream network file does not exist: {netful_path}")

    wbt = WhiteboxTools(verbose=False, raise_on_error=True)
    wbt.set_working_dir(str(netful_path.parent))

    strahler_path = netful_path.with_name("netful.strahler.tif")
    if strahler_path.exists():
        strahler_path.unlink()

    ret = wbt.strahler_stream_order(
        d8_pntr=str(flovec_path),
        streams=str(netful_path),
        output=str(strahler_path),
        esri_pntr=False,
        zero_background=False,
    )
    if ret != 0 or not strahler_path.exists():
        raise RuntimeError(
            "StrahlerStreamOrder failed "
            f"(flovec={flovec_path}, streams={netful_path}, output={strahler_path})"
        )

    current = strahler_path
    for idx in range(passes):
        is_final = idx == passes - 1
        output = (
            netful_path.with_name(f"netful.pruned_{idx + 1}.tif")
            if is_final
            else netful_path.with_name(f"netful.strahler_pruned_{idx + 1}.tif")
        )
        if output.exists():
            output.unlink()
        ret = wbt.prune_strahler_stream_order(
            streams=str(current),
            output=str(output),
            binary_output=is_final,
        )
        if ret != 0:
            raise RuntimeError(
                "PruneStrahlerStreamOrder failed "
                f"(pass {idx + 1}, input={current}, output={output})"
            )
        logger.info(
            "pruned stream order pass %d: %s -> %s",
            idx + 1,
            current.name,
            output.name,
        )
        # Keep intermediate files for debugging - only advance current pointer
        current = output

    # Copy the final pruned result back to the original netful.tif
    if current != netful_path:
        shutil.copy2(current, netful_path)


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


def _process_culvert_run(
    *,
    culvert_batch_uuid: str,
    run_id: str,
    run_wd: Path,
    watershed_feature: Optional[WatershedFeature],
    run_config: str,
    wepppy_version: Optional[str],
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

        watershed.find_outlet(watershed_feature)
        watershed.build_subcatchments()
        watershed.abstract_watershed()
        landuse.build()
        soils.build()
        climate.build()

        wepp.clean()
        wepp._check_and_set_baseflow_map()
        wepp._check_and_set_phosphorus_map()
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

    return status


def _write_run_metadata(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _write_batch_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


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
