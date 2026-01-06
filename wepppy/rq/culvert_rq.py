from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Optional

from rq import get_current_job

from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.nodb.core import Climate, Landuse, Soils, Watershed, Wepp
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


def run_culvert_batch_rq(culvert_batch_uuid: str) -> dict[str, Any]:
    """
    Entrypoint for culvert batch processing.

    Returns a summary dict with batch results. Raises CulvertBatchError
    if all runs fail.
    """
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

    run_ids = runner.create_runs(
        culvert_batch_uuid,
        str(batch_root),
        payload_metadata,
        model_parameters=model_parameters,
    )

    logger.info(f"culvert_batch {culvert_batch_uuid}: created {len(run_ids)} runs")

    watersheds_path = runner._resolve_payload_path(
        payload_metadata,
        "watersheds",
        runner.DEFAULT_WATERSHEDS_REL_PATH,
        str(batch_root),
    )
    watershed_features = runner.load_watershed_features(watersheds_path)
    wepppy_version = _get_wepppy_version()

    succeeded = 0
    failed = 0

    for run_id in run_ids:
        run_wd = Path(runner.runs_dir) / run_id
        status = _process_culvert_run(
            culvert_batch_uuid=culvert_batch_uuid,
            run_id=run_id,
            run_wd=run_wd,
            watershed_feature=watershed_features.get(run_id),
            run_config=runner.run_config,
            wepppy_version=wepppy_version,
        )
        if status == "success":
            succeeded += 1
        else:
            failed += 1

    with runner.locked():
        runner._completed_at = datetime.now(timezone.utc).isoformat()
        runner._retention_days = runner.DEFAULT_RETENTION_DAYS

    total = len(run_ids)
    summary = {
        "culvert_batch_uuid": culvert_batch_uuid,
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
    }

    _write_batch_summary(batch_root / "batch_summary.json", summary)

    if succeeded == 0 and total > 0:
        logger.error(
            f"culvert_batch {culvert_batch_uuid}: all {total} runs failed"
        )
        raise CulvertBatchError(
            f"All {total} culvert runs failed",
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
            f"culvert_batch {culvert_batch_uuid}: all {total} runs succeeded"
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

    Returns "success" or "failed".
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
        climate = Climate.getInstance(wd)
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


__all__ = ["TIMEOUT", "run_culvert_batch_rq", "CulvertBatchError"]
