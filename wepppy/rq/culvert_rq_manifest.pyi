from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Tuple

import redis

from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.topo.watershed_collection import WatershedFeature

def _write_run_metadata(path: Path, payload: dict[str, Any]) -> None: ...

def _write_batch_summary(path: Path, payload: dict[str, Any]) -> None: ...

def _escape_markdown_cell(value: str) -> str: ...

def _format_manifest_value(value: Optional[Any]) -> str: ...

def _format_manifest_error(error_payload: Any) -> Optional[str]: ...

def _load_outlet_coords(outlet_path: Path) -> Optional[Tuple[float, float]]: ...

def _sum_parquet_column(parquet_path: Path, column: str) -> Optional[float]: ...

def _compute_validation_metrics(
    *,
    run_wd: Path,
    culvert_point: Optional[Tuple[float, float]],
    watershed_feature: Optional[WatershedFeature],
) -> dict[str, float]: ...

def _count_parquet_rows(parquet_path: Path) -> Optional[int]: ...

def _load_run_metadata(path: Path) -> dict[str, Any]: ...

def _get_rq_connection() -> Optional[redis.Redis]: ...

def _fetch_job_info(
    job_id: Optional[str],
    *,
    redis_conn: Optional[redis.Redis],
) -> tuple[Optional[str], Optional[str]]: ...

def _write_runs_manifest(
    batch_root: Path,
    culvert_batch_uuid: str,
    runs: dict[str, Any],
    runner: CulvertsRunner,
    summary: dict[str, Any],
) -> Path: ...

def _write_run_skeletons_zip(batch_root: Path) -> Path: ...

