from __future__ import annotations

import json
import logging
import math
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

import redis
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.nodir.parquet_sidecars import pick_existing_parquet_path
from wepppy.topo.watershed_collection import WatershedFeature

from . import culvert_rq_helpers as _helpers

logger = logging.getLogger(__name__)


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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/culvert_rq_manifest.py:103", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        pass
    try:
        import pyarrow.compute as pc
        import pyarrow.parquet as pq

        table = pq.read_table(parquet_path, columns=[column])
        total = pc.sum(table[column]).as_py()
        if total is not None:
            return float(total)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/culvert_rq_manifest.py:113", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return None
    return None


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

    target_area = _helpers._watershed_area_m2(watershed_feature)
    if target_area is not None:
        metrics["target_watershed_area_m2"] = target_area

    hillslopes_parquet = pick_existing_parquet_path(run_wd, "watershed/hillslopes.parquet")
    channels_parquet = pick_existing_parquet_path(run_wd, "watershed/channels.parquet")
    hillslope_area = (
        _sum_parquet_column(hillslopes_parquet, "area") if hillslopes_parquet else None
    )
    channel_area = (
        _sum_parquet_column(channels_parquet, "area") if channels_parquet else None
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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/culvert_rq_manifest.py:168", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/culvert_rq_manifest.py:181", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return None
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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/culvert_rq_manifest.py:200", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/culvert_rq_manifest.py:213", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return None, None
    try:
        status = job.get_status()
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/culvert_rq_manifest.py:217", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
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
            payload_metadata = _helpers._load_payload_json(batch_root / "metadata.json")
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/culvert_rq_manifest.py:234", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
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

            watershed_label = _helpers._select_watershed_label(
                watershed_features.get(str(run_id))
            )
            hillslopes_parquet = pick_existing_parquet_path(
                run_wd, "watershed/hillslopes.parquet"
            )
            channels_parquet = pick_existing_parquet_path(
                run_wd, "watershed/channels.parquet"
            )
            subcatchments = (
                _count_parquet_rows(hillslopes_parquet) if hillslopes_parquet else None
            )
            channels = _count_parquet_rows(channels_parquet) if channels_parquet else None

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

