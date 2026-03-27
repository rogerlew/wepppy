"""WP-4 service orchestration for features export execution and cache handling."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import quote
from uuid import uuid4

from wepppy.nodb.core import Watershed
from wepppy.nodb.unitizer import Unitizer

from .cache_key import CacheKeyParts, build_cache_key, get_cache_index_entry, upsert_cache_index_entry
from .catalog_loader import LayerCatalog, load_layer_catalog
from .contracts import DEFAULT_SWAT_RUN_ID, ResolvedExportPlan
from .dependency_tracker import DependencySnapshot, build_dependency_snapshot
from .exporters import (
    ExportArtifactMetadata,
    ExportedLayerArtifact,
    ExportWriterRequest,
    PreparedLayerPayload,
    get_export_writer,
)
from .manifest import build_export_manifest, write_export_manifest
from .planner import resolve_export_plan

FEATURES_EXPORT_ROOT_RELPATH = "export/features"
FEATURES_EXPORT_ARTIFACTS_RELPATH = "export/features/artifacts"
FEATURES_EXPORT_JOBS_RELPATH = "export/features/jobs"
FEATURES_EXPORT_MANIFEST_NAME = "manifest.json"
_GPKG_APPLICATION_ID = 0x47504B47


class FeaturesExportServiceError(RuntimeError):
    """Service-layer error with canonical HTTP status and error code metadata."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 500,
        code: str = "features_export_error",
        details: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = int(status_code)
        self.code = code
        self.details = details or message


@dataclass(frozen=True)
class FeaturesExportSubmission:
    """Resolved submission context used by worker execution paths."""

    catalog: LayerCatalog
    plan: ResolvedExportPlan
    dependency_snapshot: DependencySnapshot
    cache_key_parts: CacheKeyParts
    unitizer_preferences_fingerprint: str | None


def prepare_export_submission(
    wd: str | Path,
    payload: dict[str, object],
    *,
    catalog: LayerCatalog | None = None,
) -> FeaturesExportSubmission:
    """Validate and normalize one submit payload and compute WP-2 cache context."""

    wd_path = Path(wd).resolve()
    layer_catalog = catalog or load_layer_catalog()
    plan = resolve_export_plan(payload, layer_catalog)
    resolved_plan = _resolve_plan_swat_run_id(plan, wd_path)

    dependency_snapshot = build_dependency_snapshot(
        resolved_plan,
        layer_catalog,
        wd_path,
        nodb_ref_resolver=_resolve_nodb_ref_relpath,
    )

    unitizer_preferences_fingerprint = _resolve_unitizer_preferences_fingerprint(
        wd_path,
        units=resolved_plan.request.units,
    )

    cache_key_parts = build_cache_key(
        resolved_plan,
        dependency_snapshot.fingerprint,
        unitizer_preferences_fingerprint=unitizer_preferences_fingerprint,
    )

    return FeaturesExportSubmission(
        catalog=layer_catalog,
        plan=resolved_plan,
        dependency_snapshot=dependency_snapshot,
        cache_key_parts=cache_key_parts,
        unitizer_preferences_fingerprint=unitizer_preferences_fingerprint,
    )


def _resolve_nodb_ref_relpath(wd: str, controller: str, attribute: str) -> str | Path:
    wd_path = Path(wd).resolve()
    controller_key = str(controller).strip().lower()
    attribute_key = str(attribute).strip()

    if not controller_key or not attribute_key:
        raise FeaturesExportServiceError(
            "Invalid nodb_ref locator tokens.",
            status_code=400,
            code="validation_error",
            details=f"controller={controller!r}, attribute={attribute!r}",
        )

    if controller_key != "watershed":
        raise FeaturesExportServiceError(
            f"Unsupported nodb_ref controller {controller_key!r}.",
            status_code=400,
            code="validation_error",
            details="Only nodb:watershed.<attribute> locators are supported.",
        )

    watershed = Watershed.getInstance(str(wd_path))
    if watershed is None:
        raise FeaturesExportServiceError(
            "Watershed controller is unavailable for nodb_ref resolution.",
            status_code=404,
            code="not_found",
            details=f"Unable to hydrate watershed controller for {wd_path}.",
        )

    if not hasattr(watershed, attribute_key):
        raise FeaturesExportServiceError(
            f"nodb_ref attribute {attribute_key!r} is not available on controller {controller_key!r}.",
            status_code=400,
            code="validation_error",
        )

    resolved_value = getattr(watershed, attribute_key)
    if callable(resolved_value):
        resolved_value = resolved_value()

    if not isinstance(resolved_value, (str, Path)) or not str(resolved_value).strip():
        raise FeaturesExportServiceError(
            f"nodb_ref attribute {attribute_key!r} did not resolve to a path.",
            status_code=404,
            code="not_found",
            details=f"nodb:{controller_key}.{attribute_key} returned {resolved_value!r}.",
        )

    return resolved_value


def execute_features_export(
    wd: str | Path,
    *,
    runid: str,
    config: str,
    payload: dict[str, object],
    job_id: str,
    force_cache_hit: bool = False,
) -> dict[str, object]:
    """Execute one features export job and return canonical jobinfo.result payload."""

    wd_path = Path(wd).resolve()
    if not isinstance(job_id, str) or not job_id:
        raise FeaturesExportServiceError("job_id must be a non-empty string.", status_code=500)

    submission = prepare_export_submission(wd_path, payload)
    cache_key = submission.cache_key_parts.cache_key
    cache_entry = get_cache_index_entry(wd_path, cache_key)

    if force_cache_hit and cache_entry is None:
        raise FeaturesExportServiceError(
            "Cached features export artifact mapping not found.",
            status_code=404,
            code="not_found",
            details=f"No cache index entry found for key {cache_key}.",
        )

    if cache_entry is not None:
        if not _cache_entry_has_valid_artifact_for_format(
            wd_path,
            cache_entry,
            format_token=submission.plan.request.format,
        ):
            cache_entry = None

    if cache_entry is not None:
        return _finalize_cache_hit(
            wd_path,
            runid=runid,
            config=config,
            job_id=job_id,
            submission=submission,
            cache_entry=cache_entry,
        )

    if force_cache_hit:
        raise FeaturesExportServiceError(
            "Cache hit was requested but no cache entry is available.",
            status_code=404,
            code="not_found",
        )

    return _run_cache_miss_export(
        wd_path,
        runid=runid,
        config=config,
        job_id=job_id,
        submission=submission,
    )


def resolve_download_artifact_path(
    wd: str | Path,
    *,
    job_id: str,
    job_result: dict[str, object] | None,
) -> tuple[Path, str]:
    """Resolve a job-scoped artifact file path for the download endpoint."""

    wd_path = Path(wd).resolve()
    artifact_relpath = _artifact_relpath_from_result(job_result)

    if artifact_relpath is None:
        manifest = load_job_manifest(wd_path, job_id)
        if manifest is None:
            raise FeaturesExportServiceError(
                "Features export artifact mapping not found for job.",
                status_code=404,
                code="not_found",
                details=f"Missing job manifest for {job_id}.",
            )
        artifact_relpath = _artifact_relpath_from_manifest(manifest)

    if artifact_relpath is None:
        raise FeaturesExportServiceError(
            "Features export artifact mapping not found for job.",
            status_code=404,
            code="not_found",
            details=f"Missing artifact_relpath for job {job_id}.",
        )

    artifact_path = _resolve_relpath(wd_path, artifact_relpath)
    if not artifact_path.is_file():
        raise FeaturesExportServiceError(
            "Features export artifact file not found.",
            status_code=404,
            code="not_found",
            details=f"Missing artifact at {artifact_relpath}.",
        )

    return artifact_path, artifact_relpath


def load_job_manifest(wd: str | Path, job_id: str) -> dict[str, object] | None:
    """Load job-scoped manifest JSON when present; return None when absent."""

    wd_path = Path(wd).resolve()
    job_manifest_relpath = _job_manifest_relpath(job_id)
    manifest_path = _resolve_relpath(wd_path, job_manifest_relpath)
    if not manifest_path.exists():
        return None

    try:
        parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FeaturesExportServiceError(
            "Failed to parse features export job manifest.",
            code="manifest_invalid",
            details=str(exc),
        ) from exc

    if not isinstance(parsed, dict):
        raise FeaturesExportServiceError(
            "Features export job manifest must be a JSON object.",
            code="manifest_invalid",
            details=f"Manifest payload for job {job_id} is not an object.",
        )

    return parsed


def cache_entry_supports_cache_hit(
    wd: str | Path,
    *,
    cache_entry: dict[str, object] | None,
    format_token: str,
) -> bool:
    """Return whether one cache entry can safely serve a forced cache-hit flow."""

    if not isinstance(cache_entry, dict):
        return False
    wd_path = Path(wd).resolve()
    return _cache_entry_has_valid_artifact_for_format(
        wd_path,
        cache_entry,
        format_token=format_token,
    )


def _run_cache_miss_export(
    wd: Path,
    *,
    runid: str,
    config: str,
    job_id: str,
    submission: FeaturesExportSubmission,
) -> dict[str, object]:
    artifact_id = uuid4().hex
    artifact_dir_relpath = f"{FEATURES_EXPORT_ARTIFACTS_RELPATH}/{artifact_id}"
    artifact_dir = _resolve_relpath(wd, artifact_dir_relpath)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    layer_payloads = _build_layer_payloads(submission)
    writer = get_export_writer(submission.plan.request.format)
    artifact = writer.write(
        ExportWriterRequest(
            plan=submission.plan,
            layer_payloads=layer_payloads,
            artifact_dir=artifact_dir,
            artifact_basename="features_export",
        )
    )

    artifact_relpath = _to_relpath(wd, Path(artifact.artifact_path))
    generation_timestamp_utc = _utcnow_iso()

    manifest = build_export_manifest(
        plan=submission.plan,
        artifact=artifact,
        dependency_snapshot=submission.dependency_snapshot,
        artifact_id=artifact_id,
        cache_hit=False,
        source_job_id=None,
        generation_timestamp_utc=generation_timestamp_utc,
        requested_crs=submission.plan.request.crs,
        resolved_crs=submission.plan.request.crs,
    )

    artifact_manifest_relpath = f"{artifact_dir_relpath}/{FEATURES_EXPORT_MANIFEST_NAME}"
    write_export_manifest(_resolve_relpath(wd, artifact_manifest_relpath), manifest)

    job_manifest_relpath = _job_manifest_relpath(job_id)
    write_export_manifest(_resolve_relpath(wd, job_manifest_relpath), manifest)

    warnings_payload = _normalize_warnings_payload(manifest.get("warnings"))
    cache_entry = {
        "artifact_id": artifact_id,
        "artifact_relpath": artifact_relpath,
        "artifact_path": str(_resolve_relpath(wd, artifact_relpath)),
        "artifact_paths": [artifact_relpath],
        "artifact_format": artifact.format,
        "layer_outputs": [layer.to_mapping() for layer in artifact.layer_outputs],
        "packaged_member_relpaths": list(artifact.packaged_member_relpaths),
        "source_job_id": job_id,
        "manifest_relpath": artifact_manifest_relpath,
        "warnings": warnings_payload,
    }
    upsert_cache_index_entry(wd, submission.cache_key_parts.cache_key, cache_entry)

    return {
        "artifact_id": artifact_id,
        "artifact_relpath": artifact_relpath,
        "download_url": _download_url(runid, config, artifact_relpath),
        "cache_hit": False,
        "source_job_id": None,
        "manifest_relpath": job_manifest_relpath,
        "warnings": warnings_payload,
    }


def _finalize_cache_hit(
    wd: Path,
    *,
    runid: str,
    config: str,
    job_id: str,
    submission: FeaturesExportSubmission,
    cache_entry: dict[str, object],
) -> dict[str, object]:
    artifact_id = str(cache_entry.get("artifact_id") or "").strip()
    if not artifact_id:
        raise FeaturesExportServiceError(
            "Cached features export artifact mapping is invalid.",
            status_code=404,
            code="not_found",
            details="Cache entry is missing artifact_id.",
        )

    artifact_relpath = _cache_entry_artifact_relpath(cache_entry)
    if artifact_relpath is None:
        raise FeaturesExportServiceError(
            "Cached features export artifact mapping is invalid.",
            status_code=404,
            code="not_found",
            details="Cache entry is missing artifact_relpath.",
        )

    artifact_path = _resolve_relpath(wd, artifact_relpath)
    if not artifact_path.is_file():
        raise FeaturesExportServiceError(
            "Cached features export artifact file is missing.",
            status_code=404,
            code="not_found",
            details=f"Missing cached artifact at {artifact_relpath}.",
        )

    source_job_id_raw = cache_entry.get("source_job_id")
    source_job_id = str(source_job_id_raw).strip() if source_job_id_raw is not None else None
    if source_job_id == "":
        source_job_id = None

    warnings_payload = _normalize_warnings_payload(cache_entry.get("warnings"))
    generation_timestamp_utc = _utcnow_iso()

    artifact_metadata = _artifact_metadata_from_cache_entry(
        cache_entry,
        plan=submission.plan,
        artifact_relpath=artifact_relpath,
        artifact_path=str(artifact_path),
    )

    manifest = build_export_manifest(
        plan=submission.plan,
        artifact=artifact_metadata,
        dependency_snapshot=submission.dependency_snapshot,
        artifact_id=artifact_id,
        cache_hit=True,
        source_job_id=source_job_id,
        generation_timestamp_utc=generation_timestamp_utc,
        requested_crs=submission.plan.request.crs,
        resolved_crs=submission.plan.request.crs,
        additional_warnings=warnings_payload,
    )

    job_manifest_relpath = _job_manifest_relpath(job_id)
    write_export_manifest(_resolve_relpath(wd, job_manifest_relpath), manifest)

    return {
        "artifact_id": artifact_id,
        "artifact_relpath": artifact_relpath,
        "download_url": _download_url(runid, config, artifact_relpath),
        "cache_hit": True,
        "source_job_id": source_job_id,
        "manifest_relpath": job_manifest_relpath,
        "warnings": warnings_payload,
    }


def _build_layer_payloads(
    submission: FeaturesExportSubmission,
) -> dict[str, PreparedLayerPayload]:
    payloads: dict[str, PreparedLayerPayload] = {}
    entry_counts_by_output_layer_id: dict[str, int] = {}

    for entry in submission.dependency_snapshot.entries:
        output_layer_id = entry.output_layer_id
        if output_layer_id is None:
            continue
        entry_counts_by_output_layer_id[output_layer_id] = (
            entry_counts_by_output_layer_id.get(output_layer_id, 0) + 1
        )

    for layer in submission.plan.layers:
        count = entry_counts_by_output_layer_id.get(layer.output_layer_id, 0)
        payload = {
            "layer_id": layer.layer_id,
            "output_layer_id": layer.output_layer_id,
            "scope": layer.scope,
            "scope_class": layer.scope_class,
            "dependency_fingerprint": submission.dependency_snapshot.fingerprint,
            "cache_key": submission.cache_key_parts.cache_key,
        }
        payloads[layer.output_layer_id] = PreparedLayerPayload(
            output_layer_id=layer.output_layer_id,
            payload=json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
            row_count=count,
            feature_count=count,
        )

    return payloads


def _resolve_plan_swat_run_id(plan: ResolvedExportPlan, wd: Path) -> ResolvedExportPlan:
    swat_run_id = plan.request.swat_run_id
    if swat_run_id != DEFAULT_SWAT_RUN_ID:
        return plan

    resolved_swat_run_id = _resolve_latest_swat_run_id_token(wd)
    return replace(
        plan,
        request=replace(plan.request, swat_run_id=resolved_swat_run_id),
    )


def _resolve_latest_swat_run_id_token(wd: Path) -> str:
    swat_outputs_dir = wd / "swat" / "outputs"
    if not swat_outputs_dir.is_dir():
        return "none"

    latest_path: Path | None = None
    latest_mtime: float | None = None

    for entry in swat_outputs_dir.iterdir():
        if not entry.is_dir() or not entry.name.startswith("run_"):
            continue
        try:
            stat_result = entry.stat()
        except OSError:
            continue
        if latest_mtime is None or stat_result.st_mtime > latest_mtime:
            latest_mtime = stat_result.st_mtime
            latest_path = entry

    if latest_path is None:
        return "none"

    token = latest_path.name[len("run_") :].strip()
    if token:
        return token
    return latest_path.name


def _resolve_unitizer_preferences_fingerprint(wd: Path, *, units: str) -> str | None:
    if units != "project":
        return None

    unitizer = Unitizer.getInstance(str(wd))
    fingerprint_getter = getattr(unitizer, "preferences_fingerprint", None)
    if not callable(fingerprint_getter):
        raise FeaturesExportServiceError(
            "Unitizer preferences fingerprint API is unavailable.",
            status_code=409,
            code="unitizer_unavailable",
            details="Unitizer controller does not expose preferences_fingerprint().",
        )

    fingerprint = fingerprint_getter()
    if not isinstance(fingerprint, str) or not fingerprint:
        raise FeaturesExportServiceError(
            "Unitizer preferences fingerprint is invalid.",
            status_code=409,
            code="unitizer_unavailable",
            details="Unitizer preferences fingerprint must be a non-empty string.",
        )
    return fingerprint


def _artifact_metadata_from_cache_entry(
    cache_entry: dict[str, object],
    *,
    plan: ResolvedExportPlan,
    artifact_relpath: str,
    artifact_path: str,
) -> ExportArtifactMetadata:
    format_token = str(cache_entry.get("artifact_format") or plan.request.format)
    layer_outputs = _layer_outputs_from_cache_entry(cache_entry, plan, artifact_relpath, format_token)
    packaged_member_relpaths_raw = cache_entry.get("packaged_member_relpaths")
    packaged_member_relpaths = _normalize_string_tuple(packaged_member_relpaths_raw)

    return ExportArtifactMetadata(
        format=format_token,
        artifact_relpath=artifact_relpath,
        artifact_path=artifact_path,
        layer_outputs=layer_outputs,
        warnings=(),
        packaged_member_relpaths=packaged_member_relpaths,
    )


def _layer_outputs_from_cache_entry(
    cache_entry: dict[str, object],
    plan: ResolvedExportPlan,
    artifact_relpath: str,
    format_token: str,
) -> tuple[ExportedLayerArtifact, ...]:
    raw_layer_outputs = cache_entry.get("layer_outputs")
    if isinstance(raw_layer_outputs, list):
        parsed_outputs: list[ExportedLayerArtifact] = []
        for entry in raw_layer_outputs:
            if not isinstance(entry, dict):
                continue
            try:
                parsed_outputs.append(
                    ExportedLayerArtifact(
                        layer_id=str(entry.get("layer_id") or ""),
                        output_layer_id=str(entry.get("output_layer_id") or ""),
                        scope=str(entry.get("scope") or "shared"),
                        scope_class=str(entry.get("scope_class") or "scope_invariant"),
                        format=str(entry.get("format") or format_token),
                        relpath=str(entry.get("relpath") or artifact_relpath),
                        row_count=_optional_int(entry.get("row_count")),
                        feature_count=_optional_int(entry.get("feature_count")),
                    )
                )
            except Exception:
                continue
        if parsed_outputs:
            return tuple(parsed_outputs)

    return tuple(
        ExportedLayerArtifact(
            layer_id=layer.layer_id,
            output_layer_id=layer.output_layer_id,
            scope=layer.scope,
            scope_class=layer.scope_class,
            format=format_token,
            relpath=artifact_relpath,
            row_count=None,
            feature_count=None,
        )
        for layer in plan.layers
    )


def _cache_entry_artifact_relpath(cache_entry: dict[str, object]) -> str | None:
    artifact_relpath = cache_entry.get("artifact_relpath")
    if isinstance(artifact_relpath, str) and artifact_relpath.strip():
        return artifact_relpath.strip()

    artifact_paths = cache_entry.get("artifact_paths")
    if isinstance(artifact_paths, list) and artifact_paths:
        first = artifact_paths[0]
        if isinstance(first, str) and first.strip():
            return first.strip()

    return None


def _artifact_relpath_from_result(job_result: dict[str, object] | None) -> str | None:
    if not isinstance(job_result, dict):
        return None
    value = job_result.get("artifact_relpath")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _artifact_relpath_from_manifest(manifest: dict[str, object]) -> str | None:
    artifact = manifest.get("artifact")
    if not isinstance(artifact, dict):
        return None

    artifact_relpath = artifact.get("artifact_relpath")
    if not isinstance(artifact_relpath, str) or not artifact_relpath.strip():
        return None

    token = artifact_relpath.strip()
    if token.startswith(f"{FEATURES_EXPORT_ROOT_RELPATH}/"):
        return token

    artifact_id = manifest.get("artifact_id")
    if isinstance(artifact_id, str) and artifact_id.strip():
        return f"{FEATURES_EXPORT_ARTIFACTS_RELPATH}/{artifact_id.strip()}/{token}"

    return token


def _cache_entry_has_valid_artifact_for_format(
    wd: Path,
    cache_entry: dict[str, object],
    *,
    format_token: str,
) -> bool:
    artifact_relpath = _cache_entry_artifact_relpath(cache_entry)
    if artifact_relpath is None:
        return False

    artifact_path = _resolve_relpath(wd, artifact_relpath)
    if not artifact_path.is_file():
        return False

    normalized_format = format_token.strip().lower()
    if normalized_format == "f_esri":
        normalized_format = "geodatabase"

    if normalized_format == "geopackage":
        return _is_valid_cached_geopackage(artifact_path)

    return True


def _is_valid_cached_geopackage(artifact_path: Path) -> bool:
    try:
        with artifact_path.open("rb") as handle:
            if not handle.read(16).startswith(b"SQLite format 3\x00"):
                return False
    except OSError:
        return False

    try:
        with sqlite3.connect(str(artifact_path)) as conn:
            application_id_row = conn.execute("PRAGMA application_id").fetchone()
            if not application_id_row:
                return False
            try:
                application_id = int(application_id_row[0])
            except (TypeError, ValueError):
                return False
            if application_id != _GPKG_APPLICATION_ID:
                return False

            gpkg_contents_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='gpkg_contents'"
            ).fetchone()
            return gpkg_contents_exists is not None
    except sqlite3.Error:
        return False


def _download_url(runid: str, config: str, artifact_relpath: str) -> str:
    browse_path = f"/runs/{runid}/{config}/download/{quote(artifact_relpath, safe='/')}"
    return f"{_site_prefix()}{browse_path}"


def _site_prefix() -> str:
    token = str(os.getenv("SITE_PREFIX", "/weppcloud")).strip()
    if not token or token == "/":
        return ""
    if not token.startswith("/"):
        token = f"/{token}"
    return token.rstrip("/")


def _job_manifest_relpath(job_id: str) -> str:
    return f"{FEATURES_EXPORT_JOBS_RELPATH}/{job_id}/{FEATURES_EXPORT_MANIFEST_NAME}"


def _resolve_relpath(wd: Path, relpath: str) -> Path:
    candidate = (wd / relpath).resolve()
    try:
        candidate.relative_to(wd)
    except ValueError as exc:
        raise FeaturesExportServiceError(
            "Resolved path escapes working directory.",
            status_code=500,
            code="path_escape",
            details=f"Resolved {candidate} outside {wd}.",
        ) from exc
    return candidate


def _to_relpath(wd: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(wd).as_posix()
    except ValueError as exc:
        raise FeaturesExportServiceError(
            "Artifact path escapes working directory.",
            status_code=500,
            code="path_escape",
            details=f"Resolved {resolved} outside {wd}.",
        ) from exc


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        token = value.strip()
        if not token:
            return None
        try:
            return int(token)
        except ValueError:
            return None
    return None


def _normalize_string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    normalized: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            continue
        token = entry.strip()
        if token:
            normalized.append(token)
    return tuple(normalized)


def _normalize_warnings_payload(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []

    normalized: list[dict[str, object]] = []
    for warning in value:
        if isinstance(warning, dict):
            normalized.append(dict(warning))
    return normalized


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "FEATURES_EXPORT_ARTIFACTS_RELPATH",
    "FEATURES_EXPORT_JOBS_RELPATH",
    "FEATURES_EXPORT_MANIFEST_NAME",
    "FEATURES_EXPORT_ROOT_RELPATH",
    "FeaturesExportServiceError",
    "FeaturesExportSubmission",
    "cache_entry_supports_cache_hit",
    "execute_features_export",
    "load_job_manifest",
    "prepare_export_submission",
    "resolve_download_artifact_path",
]
