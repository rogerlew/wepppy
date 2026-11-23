"""Build the run outputs snapshot and verify the files advertised by export jobs."""
from __future__ import annotations

import errno
import hashlib
import json
import logging
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from wepppy.all_your_base.file_digest import sha256_file
from wepppy.nodb.mods.features_export import (
    FeaturesExportServiceError,
    load_job_manifest,
    resolve_download_artifact_path,
)
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.rq.job_info import get_wepppy_rq_job_info
from wepppy.weppcloud.utils.helpers import get_wd

from .openapi import rq_operation_id
from .schema_defaults_runtime import (
    FEATURES_EXPORT_JOB_KEY,
    RUN_STATE_DOMAIN_OUTPUTS,
    UNKNOWN_SOURCE_RUN_STATE_REVISION,
    UNKNOWN_UPDATED_AT,
    RuntimeState,
    _run_state_vector,
    _runtime_snapshot_updated_at,
    _snapshot_freshness,
)

logger = logging.getLogger("wepppy.microservices.rq_engine.schema_defaults_routes")


def _parse_iso_datetime(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None

    try:
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path, *, size_bytes: int | None = None, mtime_ns: int | None = None) -> str:
    before = path.stat()
    expected_size = int(size_bytes) if size_bytes is not None else before.st_size
    expected_mtime = int(mtime_ns) if mtime_ns is not None else before.st_mtime_ns
    expected = (expected_size, expected_mtime)
    if (before.st_size, before.st_mtime_ns) != expected:
        raise OSError(errno.ESTALE, "Export artifact metadata changed", str(path))
    digest = sha256_file(path)
    after = path.stat()
    if ((after.st_size, after.st_mtime_ns) != expected
            or (before.st_dev, before.st_ino, before.st_ctime_ns) !=
               (after.st_dev, after.st_ino, after.st_ctime_ns)):
        raise OSError(errno.ESTALE, "Export artifact changed while hashing", str(path))
    return digest


def _artifact_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".zip":
        return "zip"
    if suffix == ".gpkg":
        return "geopackage"
    if suffix == ".gdb":
        return "geodatabase"
    return suffix.lstrip(".") or "artifact"


def _source_revision(manifest: Mapping[str, Any] | None, job_result: Mapping[str, Any] | None) -> str:
    if isinstance(manifest, Mapping):
        revision = str(
            manifest.get("source_run_state_revision") or manifest.get("run_state_revision") or ""
        ).strip()
        if revision:
            return revision

        request = manifest.get("request")
        if isinstance(request, Mapping):
            resolved = request.get("resolved")
            if isinstance(resolved, Mapping):
                revision = str(resolved.get("run_state_revision") or "").strip()
                if revision:
                    return revision

    if isinstance(job_result, Mapping):
        revision = str(
            job_result.get("source_run_state_revision") or job_result.get("run_state_revision") or ""
        ).strip()
        if revision:
            return revision
    return UNKNOWN_SOURCE_RUN_STATE_REVISION


def _features_export_record(
    runtime: RuntimeState,
    artifact_path: Path,
    wd: str,
    job_id: str,
    job_result: Mapping[str, Any] | None,
    job_info: Mapping[str, Any],
) -> dict[str, Any]:
    artifact_stat = artifact_path.stat()
    manifest = load_job_manifest(wd, job_id)

    produced_at = None
    if isinstance(manifest, Mapping):
        produced_at = _parse_iso_datetime(manifest.get("generated_at_utc"))
    if produced_at is None:
        produced_at = _parse_iso_datetime(job_info.get("ended_at"))
    if produced_at is None:
        produced_at = UNKNOWN_UPDATED_AT

    source_run_state_revision = _source_revision(manifest, job_result)

    artifact_id = (
        str((job_result or {}).get("artifact_id") or "").strip()
        if isinstance(job_result, Mapping)
        else ""
    )
    if not artifact_id:
        artifact_id = f"features_export_{job_id}"

    download_url_template = "/rq-engine/api/runs/{runid}/{config}/export/features/job/{job_id}/download"
    download_url = download_url_template.format(
        runid=runtime.runid,
        config=runtime.config,
        job_id=job_id,
    )
    content_type = mimetypes.guess_type(str(artifact_path))[0] or "application/octet-stream"

    return {
        "id": artifact_id,
        "kind": _artifact_kind(artifact_path),
        "producer_operation_id": rq_operation_id("export_features_submit"),
        "producer_step_id": "export-features",
        "producer_job_id": job_id,
        "produced_at": produced_at,
        "source_run_state_revision": source_run_state_revision,
        "expires_at": None,
        "content_type": content_type,
        "size_bytes": artifact_stat.st_size,
        "sha256": _sha256_file(
            artifact_path,
            size_bytes=artifact_stat.st_size,
            mtime_ns=getattr(artifact_stat, "st_mtime_ns", None),
        ),
        "result_source": "jobinfo.result",
        "download_url": download_url,
        "download_url_params": {
            "runid": runtime.runid,
            "config": runtime.config,
            "job_id": job_id,
        },
        "download_url_template": download_url_template,
    }


def _build_features_export_artifact(runtime: RuntimeState, *, wd: str) -> dict[str, Any] | None:
    try:
        prep = RedisPrep.getInstance(wd)
        job_id = prep.get_rq_job_id(FEATURES_EXPORT_JOB_KEY)
        if not job_id:
            job_id = prep.get_rq_job_ids().get(FEATURES_EXPORT_JOB_KEY)
        if not job_id:
            return None

        job_info = get_wepppy_rq_job_info(job_id)
        job_runid = str(job_info.get("runid") or "").strip()
        if job_runid and job_runid != runtime.runid:
            logger.warning(
                "rq-engine outputs ignored features-export artifact with mismatched runid",
                extra={"requested_runid": runtime.runid, "job_runid": job_runid, "job_id": job_id},
            )
            return None

        job_status = str(job_info.get("status") or "").strip().lower()
        if job_status != "finished":
            return None

        job_result = job_info.get("result")
        if not isinstance(job_result, Mapping):
            job_result = None

        artifact_path, _artifact_relpath = resolve_download_artifact_path(
            wd,
            job_id=job_id,
            job_result=job_result,
        )
        artifact_path = artifact_path.resolve()
        wd_path = Path(wd).resolve()
        if wd_path != artifact_path and wd_path not in artifact_path.parents:
            logger.warning(
                "rq-engine outputs ignored artifact path outside run directory",
                extra={"runid": runtime.runid, "job_id": job_id, "artifact_path": str(artifact_path)},
            )
            return None

        return _features_export_record(runtime, artifact_path, wd, job_id, job_result, job_info)
    except (FeaturesExportServiceError, FileNotFoundError, OSError):
        return None
    except Exception:  # broad-except: outputs discovery best-effort boundary
        logger.exception("rq-engine outputs features-export artifact discovery failed")
        return None


def _outputs_export_catalog() -> list[dict[str, Any]]:
    return [
        {
            "operation_id": rq_operation_id("export_ermit"),
            "path": "/api/runs/{runid}/{config}/export/ermit",
            "method": "GET",
            "response_mode": "file",
        },
        {
            "operation_id": rq_operation_id("export_ermit_submit"),
            "path": "/api/runs/{runid}/{config}/export/ermit",
            "method": "POST",
            "response_mode": "json",
        },
        {
            "operation_id": rq_operation_id("export_ermit_download"),
            "path": "/api/runs/{runid}/{config}/export/ermit/job/{job_id}/download",
            "method": "GET",
            "response_mode": "file",
        },
        {
            "operation_id": rq_operation_id("export_geopackage"),
            "path": "/api/runs/{runid}/{config}/export/geopackage",
            "method": "GET",
            "response_mode": "file",
        },
        {
            "operation_id": rq_operation_id("export_geodatabase"),
            "path": "/api/runs/{runid}/{config}/export/geodatabase",
            "method": "GET",
            "response_mode": "file",
        },
        {
            "operation_id": rq_operation_id("export_prep_details"),
            "path": "/api/runs/{runid}/{config}/export/prep_details",
            "method": "GET",
            "response_mode": "file",
        },
        {
            "operation_id": rq_operation_id("export_features_submit"),
            "path": "/api/runs/{runid}/{config}/export/features",
            "method": "POST",
            "response_mode": "json",
        },
        {
            "operation_id": rq_operation_id("export_features_download"),
            "path": "/api/runs/{runid}/{config}/export/features/job/{job_id}/download",
            "method": "GET",
            "response_mode": "file",
        },
        {
            "operation_id": rq_operation_id("export_features_download_published"),
            "path": "/api/runs/{runid}/{config}/export/features/published/{profile}/download",
            "method": "GET",
            "response_mode": "file",
        },
    ]


def _build_outputs_payload(runtime: RuntimeState) -> dict[str, Any]:
    artifacts: list[dict[str, Any]] = []
    feature_artifact = _build_features_export_artifact(runtime, wd=get_wd(runtime.runid))
    if feature_artifact is not None:
        artifacts.append(feature_artifact)

    artifacts.sort(
        key=lambda artifact: (
            str(artifact.get("produced_at") or ""),
            str(artifact.get("id") or ""),
        ),
        reverse=True,
    )

    exports = _outputs_export_catalog()
    data_updated_candidates = [str(item.get("produced_at")) for item in artifacts if item.get("produced_at")]
    data_updated_at = max(data_updated_candidates) if data_updated_candidates else None
    data_state = "materialized" if artifacts else "not_materialized"

    revision_input = {
        "metadata_revision": runtime.run_state_revision,
        "artifacts": artifacts,
        "exports": exports,
    }
    revision_digest = hashlib.sha256(
        json.dumps(revision_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]
    outputs_revision = f"runstate:{runtime.runid}:{revision_digest}"
    freshness = _snapshot_freshness(
        data_state=data_state,
        data_updated_at=data_updated_at,
        fallback_updated_at=_runtime_snapshot_updated_at(
            runid=runtime.runid,
            generated_at=runtime.generated_at,
        ),
    )

    return {
        "run_state_domain": RUN_STATE_DOMAIN_OUTPUTS,
        "run_state_revision": outputs_revision,
        "run_state_vector": _run_state_vector(
            metadata_revision=runtime.run_state_revision,
            outputs_revision=outputs_revision,
        ),
        **freshness,
        "etag": f'W/"outputs:{runtime.runid}:{revision_digest}"',
        "artifacts": artifacts,
        "exports": exports,
    }
