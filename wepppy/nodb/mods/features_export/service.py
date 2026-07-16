"""WP-4 service orchestration for features export execution and cache handling."""

from __future__ import annotations

import collections.abc as cabc
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import string
import re
import shutil
from typing import cast
from uuid import uuid4
import zipfile

import duckdb
import geopandas as gpd
import pandas as pd

from wepppy import f_esri
from wepppy.nodb.core import Watershed
from wepppy.nodb.mods.ag_fields import AgFields
from wepppy.nodb.unitizer import Unitizer
from wepppy.runtime_paths import pick_existing_parquet_path
from wepppy.runtime_paths.materialize import materialize_path_if_archive

from .carrier_layer_materializer import materialize_carrier_layer_core
from .cache_rehydration import (
    artifact_metadata_from_cache_entry as _artifact_metadata_from_cache_entry_helper,
    artifact_relpath_from_result as _artifact_relpath_from_result_helper,
    cache_entry_artifact_relpath as _cache_entry_artifact_relpath_helper,
    layer_outputs_from_cache_entry as _layer_outputs_from_cache_entry_helper,
)
from .cache_key import (
    CacheKeyParts,
    build_cache_key,
    get_cache_index_entry,
    load_cache_index,
    upsert_cache_index_entry,
)
from .catalog_loader import LayerCatalog, load_layer_catalog
from .column_selection import (
    column_metadata_by_id as _column_metadata_by_id_helper,
    dedupe_identity_selected_columns as _dedupe_identity_selected_columns_helper,
    infer_display_unit_for_column as _infer_display_unit_for_column_helper,
    required_identity_columns as _required_identity_columns_helper,
    resolve_selected_columns as _resolve_selected_columns_helper,
)
from .contracts import (
    DEFAULT_SWAT_RUN_ID,
    ExportWarning,
    NormalizedTemporalEvent,
    ResolvedExportPlan,
    ResolvedLayerPlan,
)
from .dependency_tracker import DependencySnapshot, build_dependency_snapshot
from .discovery import layer_key_candidates, resolve_geometry_relpath
from .duckdb_materializer import (
    LayerCarrierInput,
    materialize_carrier_core,
)
from .exporters import (
    ExportArtifactMetadata,
    ExportedLayerArtifact,
    ExportWriterRequest,
    PreparedLayerPayload,
    get_export_writer,
)
from .exporters.packaging import package_files_as_zip
from .geometry_carriers import attach_geometry_once, build_canonical_geometry_carrier
from .identity_columns import normalize_identity_output_columns
from .join_planner import JOIN_KEY_COLUMN, MaterializationContractError
from .legacy_source_materializer import build_legacy_merged_frame
from .manifest import build_export_manifest, write_export_manifest
from .manifest_builder import build_output_layer_column_metadata
from .output_column_naming import apply_unitized_column_suffixes
from .planner import resolve_export_plan
from .profiles import load_builtin_profiles, normalize_profile_key
from .readme_builder import build_export_readme
from .tabular_temporal_layout import reshape_temporal_wide_to_long

FEATURES_EXPORT_ROOT_RELPATH = "export/features"
FEATURES_EXPORT_ARTIFACTS_RELPATH = "export/features/artifacts"
FEATURES_EXPORT_JOBS_RELPATH = "export/features/jobs"
FEATURES_EXPORT_PUBLISHED_RELPATH = "export/features/published"
FEATURES_EXPORT_PUBLISHED_INDEX_RELPATH = f"{FEATURES_EXPORT_PUBLISHED_RELPATH}/index.json"
FEATURES_EXPORT_MANIFEST_NAME = "manifest.json"
FEATURES_EXPORT_ARTIFACT_README_NAME = "README.md"
FEATURES_EXPORT_PUBLICATION_SCHEMA_VERSION = 1
_GPKG_APPLICATION_ID = 0x47504B47
_CONSOLIDATED_JOIN_KEY_COLUMN = JOIN_KEY_COLUMN
_SAFE_TOKEN_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
_PROFILE_TOKEN_PATTERN = re.compile(r"[^a-z0-9]+")
_TOPAZ_ID_COLUMN = "topaz_id"
_WEPP_ID_COLUMN = "wepp_id"
_PUBLISHED_PROFILE_ALIASES: dict[str, str] = {
    "post-wepp": "prep-wepp",
    "post_wepp": "prep-wepp",
    "prep-wepp": "prep-wepp",
    "prep_wepp": "prep-wepp",
    "post-wepp-gpkg-gdb": "prep-wepp-gpkg-gdb",
    "post_wepp_gpkg_gdb": "prep-wepp-gpkg-gdb",
    "prep-wepp-gpkg-gdb": "prep-wepp-gpkg-gdb",
    "prep_wepp_gpkg_gdb": "prep-wepp-gpkg-gdb",
    "post-wepp-geodatabase": "prep-wepp-geodatabase",
    "post_wepp_geodatabase": "prep-wepp-geodatabase",
    "prep-wepp-geodatabase": "prep-wepp-geodatabase",
    "prep_wepp_geodatabase": "prep-wepp-geodatabase",
    "prep-details": "prep-details",
    "prep_details": "prep-details",
}
_PUBLISHED_PROFILE_TO_BUILTIN_KEY: dict[str, str] = {
    "prep-wepp": "post_wepp",
    "prep-wepp-gpkg-gdb": "post_wepp",
    "prep-wepp-geodatabase": "post_wepp",
    "prep-details": "prep_details",
}
_PUBLISHED_PROFILE_FORMAT_OVERRIDES: dict[str, str] = {
    "prep-wepp-geodatabase": "geodatabase",
}


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


@dataclass(frozen=True)
class _LayerFrameResult:
    layer: ResolvedLayerPlan
    frame: gpd.GeoDataFrame
    selected_columns: tuple[str, ...]
    unit_mapping: dict[str, str]
    warnings: tuple[ExportWarning, ...]


@dataclass(frozen=True)
class _LayerCoreResult:
    layer: ResolvedLayerPlan
    frame: pd.DataFrame
    selected_columns: tuple[str, ...]
    unit_mapping: dict[str, str]
    warnings: tuple[ExportWarning, ...]
    catalog_layer_raw: dict[str, object]


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
    _require_current_ag_fields_interchange(wd_path, resolved_plan)

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


def _require_current_ag_fields_interchange(
    wd: Path,
    plan: ResolvedExportPlan,
) -> None:
    """Reject stale AgFields metric reads without preparing or mutating assets."""
    if not any(layer.family == "ag_fields_metrics" for layer in plan.layers):
        return

    ag_fields = cast(
        AgFields | None,
        AgFields.load_detached(str(wd), allow_nonexistent=True),
    )
    if ag_fields is None or not ag_fields.has_current_wepp_ag_fields_interchange():
        raise FeaturesExportServiceError(
            "AgFields interchange is not current for the requested metric layer.",
            status_code=409,
            code="ag_fields_interchange_not_current",
            details=(
                "Run the current AgFields sub-field WEPP stage successfully before "
                "exporting AgFields metrics."
            ),
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
    # Some legacy/forked runs are missing the export root. Create it lazily so
    # features export can materialize artifacts without pre-seeded directories.
    _resolve_relpath(wd_path, "export").mkdir(parents=True, exist_ok=True)

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


def normalize_published_profile_id(profile: str) -> str | None:
    """Normalize one publication profile token to canonical kebab-case id."""

    if not isinstance(profile, str):
        return None
    token = _PROFILE_TOKEN_PATTERN.sub("-", profile.strip().lower()).strip("-")
    if not token:
        return None
    return _PUBLISHED_PROFILE_ALIASES.get(token)


def resolve_published_profile_request(
    profile: str,
    *,
    format_override: str | None = None,
) -> tuple[str, dict[str, object]]:
    """Return canonical published profile id and normalized request payload."""

    canonical_profile = normalize_published_profile_id(profile)
    if canonical_profile is None:
        raise FeaturesExportServiceError(
            "Unknown published features export profile.",
            status_code=404,
            code="not_found",
            details=f"Unknown published profile {profile!r}.",
        )

    builtin_key = _PUBLISHED_PROFILE_TO_BUILTIN_KEY.get(canonical_profile)
    if not isinstance(builtin_key, str) or not builtin_key:
        raise FeaturesExportServiceError(
            "Published profile mapping is not configured.",
            status_code=500,
            code="profile_resolution_error",
            details=f"Missing built-in mapping for profile {canonical_profile!r}.",
        )

    request_by_builtin_key: dict[str, dict[str, object]] = {}
    for row in load_builtin_profiles():
        profile_key = normalize_profile_key(str(row.get("key") or ""))
        request_mapping = row.get("request")
        if not profile_key or not isinstance(request_mapping, dict):
            continue
        normalized_request = json.loads(
            json.dumps(request_mapping, sort_keys=True, separators=(",", ":"))
        )
        if isinstance(normalized_request, dict):
            request_by_builtin_key[profile_key] = normalized_request

    request_payload = request_by_builtin_key.get(builtin_key)
    if request_payload is None:
        raise FeaturesExportServiceError(
            "Published profile is unavailable.",
            status_code=409,
            code="profile_unavailable",
            details=f"Built-in profile {builtin_key!r} is not available.",
        )

    resolved_format_override = _PUBLISHED_PROFILE_FORMAT_OVERRIDES.get(canonical_profile)
    if isinstance(resolved_format_override, str) and resolved_format_override.strip():
        request_payload["format"] = resolved_format_override.strip()

    if isinstance(format_override, str) and format_override.strip():
        request_payload["format"] = format_override.strip()

    return canonical_profile, request_payload


def load_publication_registry(wd: str | Path) -> dict[str, object]:
    """Load publication registry mapping for one run root."""

    wd_path = Path(wd).resolve()
    registry_path = _resolve_relpath(wd_path, FEATURES_EXPORT_PUBLISHED_INDEX_RELPATH)
    if not registry_path.exists():
        return _empty_publication_registry()

    try:
        parsed = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FeaturesExportServiceError(
            "Failed to parse features export publication registry.",
            code="publication_registry_invalid",
            details=str(exc),
        ) from exc

    if not isinstance(parsed, dict):
        raise FeaturesExportServiceError(
            "Features export publication registry must be a JSON object.",
            code="publication_registry_invalid",
            details=f"Invalid registry payload type: {type(parsed).__name__}.",
        )

    return _normalize_publication_registry(parsed)


def publish_profile_artifact(
    wd: str | Path,
    *,
    profile: str,
    job_id: str,
    job_result: dict[str, object] | None,
) -> dict[str, object]:
    """Publish one completed export job result to the profile registry."""

    wd_path = Path(wd).resolve()
    canonical_profile, request_payload = resolve_published_profile_request(profile)
    if not isinstance(job_id, str) or not job_id:
        raise FeaturesExportServiceError("job_id must be a non-empty string.", status_code=500)

    artifact_relpath = _artifact_relpath_from_result(job_result)
    if artifact_relpath is None:
        manifest = load_job_manifest(wd_path, job_id)
        if manifest is not None:
            artifact_relpath = _artifact_relpath_from_manifest(manifest)

    if artifact_relpath is None:
        raise FeaturesExportServiceError(
            "Published features export artifact mapping is invalid.",
            status_code=404,
            code="not_found",
            details=f"Missing artifact_relpath for job {job_id}.",
        )

    artifact_path = _resolve_relpath(wd_path, artifact_relpath)
    if not artifact_path.is_file():
        raise FeaturesExportServiceError(
            "Published features export artifact file not found.",
            status_code=404,
            code="not_found",
            details=f"Missing artifact at {artifact_relpath}.",
        )

    submission = prepare_export_submission(wd_path, request_payload)
    manifest_relpath = _job_manifest_relpath(job_id)
    if isinstance(job_result, dict):
        candidate_manifest_relpath = job_result.get("manifest_relpath")
        if isinstance(candidate_manifest_relpath, str) and candidate_manifest_relpath.strip():
            manifest_relpath = candidate_manifest_relpath.strip()

    entry: dict[str, object] = {
        "profile": canonical_profile,
        "job_id": job_id,
        "artifact_id": (
            str(job_result.get("artifact_id") or "").strip()
            if isinstance(job_result, dict)
            else ""
        ),
        "artifact_relpath": artifact_relpath,
        "manifest_relpath": manifest_relpath,
        "format": str(submission.plan.request.format),
        "request_hash": str(submission.cache_key_parts.request_hash),
        "dependency_fingerprint": str(submission.dependency_snapshot.fingerprint),
        "cache_key": str(submission.cache_key_parts.cache_key),
        "published_at_utc": _utcnow_iso(),
    }

    registry = load_publication_registry(wd_path)
    profiles = registry.setdefault("profiles", {})
    if not isinstance(profiles, dict):
        profiles = {}
        registry["profiles"] = profiles
    profiles[canonical_profile] = entry
    registry["updated_at_utc"] = _utcnow_iso()
    _write_publication_registry(wd_path, registry)
    return entry


def co_create_post_wepp_geodatabase_artifact(
    wd: str | Path,
    *,
    source_job_id: str,
    source_job_result: dict[str, object] | None,
) -> dict[str, object]:
    """Create one FileGDB artifact from a completed prep-wepp GeoPackage artifact."""

    wd_path = Path(wd).resolve()
    if not isinstance(source_job_id, str) or not source_job_id:
        raise FeaturesExportServiceError("source_job_id must be a non-empty string.", status_code=500)

    if not f_esri.has_f_esri:
        raise FeaturesExportServiceError(
            "Geodatabase co-creation requires f_esri backend capability, but it is unavailable.",
            status_code=409,
            code="export_backend_unavailable",
        )

    source_artifact_path, source_artifact_relpath = resolve_download_artifact_path(
        wd_path,
        job_id=source_job_id,
        job_result=source_job_result,
    )
    gpkg_path = _resolve_geopackage_co_creation_source(
        source_artifact_path=source_artifact_path,
        source_artifact_relpath=source_artifact_relpath,
    )
    artifact_dir = source_artifact_path.parent
    gdb_container_path = artifact_dir / "features_export.gdb"
    gdb_zip_path = gdb_container_path.with_suffix(".gdb.zip")
    if gdb_container_path.exists() and gdb_container_path.is_dir():
        shutil.rmtree(gdb_container_path, ignore_errors=True)
    if gdb_zip_path.exists() and gdb_zip_path.is_file():
        gdb_zip_path.unlink()

    f_esri.c2c_gpkg_to_gdb(str(gpkg_path), str(gdb_container_path), zip_output=True)

    if not gdb_zip_path.is_file():
        raise FeaturesExportServiceError(
            "f_esri conversion did not produce expected FileGDB archive.",
            status_code=500,
            code="artifact_missing",
            details=f"Missing geodatabase archive at {gdb_zip_path}.",
        )
    if gdb_container_path.exists():
        if gdb_container_path.is_dir():
            shutil.rmtree(gdb_container_path)
        else:
            gdb_container_path.unlink()

    gdb_artifact_relpath = _to_relpath(wd_path, gdb_zip_path)
    geodatabase_request = resolve_published_profile_request("prep-wepp-geodatabase")[1]
    submission = prepare_export_submission(wd_path, geodatabase_request)
    _upsert_co_created_published_cache_entry(
        wd_path,
        cache_key=submission.cache_key_parts.cache_key,
        artifact_relpath=gdb_artifact_relpath,
        artifact_path=gdb_zip_path,
        source_job_id=source_job_id,
        source_job_result=source_job_result,
    )

    source_manifest_relpath = (
        str(source_job_result.get("manifest_relpath") or "").strip()
        if isinstance(source_job_result, dict)
        else ""
    )
    if not source_manifest_relpath:
        source_manifest_relpath = _job_manifest_relpath(source_job_id)

    source_artifact_id = (
        str(source_job_result.get("artifact_id") or "").strip()
        if isinstance(source_job_result, dict)
        else ""
    )
    if source_artifact_id:
        geodatabase_artifact_id = f"{source_artifact_id}-geodatabase"
    else:
        geodatabase_artifact_id = gdb_zip_path.parent.name

    return {
        "artifact_id": geodatabase_artifact_id,
        "artifact_relpath": gdb_artifact_relpath,
        "manifest_relpath": source_manifest_relpath,
    }


def publish_profile_execution_artifacts(
    wd: str | Path,
    *,
    requested_profile: str,
    job_id: str,
    job_result: dict[str, object] | None,
) -> dict[str, dict[str, object]]:
    """Publish profile artifacts, including optional co-created companions."""

    canonical_profile = normalize_published_profile_id(requested_profile)
    if canonical_profile is None:
        raise FeaturesExportServiceError(
            "Unknown published features export profile.",
            status_code=404,
            code="not_found",
            details=f"Unknown published profile {requested_profile!r}.",
        )

    published_entries: dict[str, dict[str, object]] = {}
    if canonical_profile == "prep-wepp-gpkg-gdb":
        published_entries["prep-wepp"] = publish_profile_artifact(
            wd,
            profile="prep-wepp",
            job_id=job_id,
            job_result=job_result,
        )
        geodatabase_result = co_create_post_wepp_geodatabase_artifact(
            wd,
            source_job_id=job_id,
            source_job_result=job_result,
        )
        published_entries["prep-wepp-geodatabase"] = publish_profile_artifact(
            wd,
            profile="prep-wepp-geodatabase",
            job_id=job_id,
            job_result=geodatabase_result,
        )
        return published_entries

    published_entries[canonical_profile] = publish_profile_artifact(
        wd,
        profile=canonical_profile,
        job_id=job_id,
        job_result=job_result,
    )
    return published_entries


def resolve_published_artifact_path(
    wd: str | Path,
    *,
    profile: str,
) -> tuple[Path, str]:
    """Resolve one published artifact path with stale-registry validation."""

    wd_path = Path(wd).resolve()
    canonical_profile, request_payload = resolve_published_profile_request(profile)
    registry = load_publication_registry(wd_path)
    profiles = registry.get("profiles")
    if not isinstance(profiles, dict):
        profiles = {}

    raw_entry = profiles.get(canonical_profile)
    if not isinstance(raw_entry, dict):
        raise FeaturesExportServiceError(
            "Published features export profile is not available.",
            status_code=404,
            code="not_found",
            details=f"No published artifact for profile {canonical_profile!r}.",
        )

    entry = _normalize_publication_entry(canonical_profile, raw_entry)
    artifact_relpath = str(entry.get("artifact_relpath") or "").strip()
    if not artifact_relpath:
        raise _stale_publication_error(
            canonical_profile,
            "Registry entry is missing artifact_relpath.",
        )

    artifact_path = _resolve_relpath(wd_path, artifact_relpath)
    if not artifact_path.is_file():
        raise FeaturesExportServiceError(
            "Published features export artifact file not found.",
            status_code=404,
            code="not_found",
            details=f"Missing artifact at {artifact_relpath}.",
        )

    canonical_request_format = str(request_payload.get("format") or "").strip().lower()
    expected_cache_key = str(entry.get("cache_key") or "").strip()
    expected_request_hash = str(entry.get("request_hash") or "").strip()
    expected_dependency_fingerprint = str(entry.get("dependency_fingerprint") or "").strip()
    expected_format = str(entry.get("format") or "").strip().lower()

    if expected_format and expected_format != canonical_request_format:
        raise _stale_publication_error(
            canonical_profile,
            "Published format no longer matches canonical profile request.",
        )

    resolved_cache_key = expected_cache_key
    cache_entry = get_cache_index_entry(wd_path, resolved_cache_key) if resolved_cache_key else None

    if cache_entry is not None:
        cache_artifact_relpath = _cache_entry_artifact_relpath(cache_entry)
        if cache_artifact_relpath != artifact_relpath:
            cache_entry = None

    if cache_entry is None:
        matched_cache_entries = _find_cache_entries_by_artifact_relpath(
            wd_path,
            artifact_relpath=artifact_relpath,
        )
        if not matched_cache_entries:
            raise _stale_publication_error(
                canonical_profile,
                "Published cache entry is missing.",
            )
        resolved_cache_key, cache_entry = _select_latest_cache_entry(matched_cache_entries)

    cache_artifact_relpath = _cache_entry_artifact_relpath(cache_entry)
    if cache_artifact_relpath is None:
        raise _stale_publication_error(
            canonical_profile,
            "Published cache entry is missing artifact mapping.",
        )
    if cache_artifact_relpath != artifact_relpath:
        raise _stale_publication_error(
            canonical_profile,
            "Published artifact no longer matches cache mapping.",
        )
    if not _cache_entry_has_valid_artifact_for_format(
        wd_path,
        cache_entry,
        format_token=canonical_request_format,
    ):
        raise _stale_publication_error(
            canonical_profile,
            "Published artifact is incompatible with canonical profile format.",
        )

    parsed_request_hash, parsed_dependency_fingerprint = _parse_cache_key_components(resolved_cache_key)
    resolved_request_hash = parsed_request_hash or expected_request_hash
    resolved_dependency_fingerprint = parsed_dependency_fingerprint or expected_dependency_fingerprint
    if not resolved_request_hash or not resolved_dependency_fingerprint:
        raise _stale_publication_error(
            canonical_profile,
            "Published cache key cannot be resolved to request/dependency fingerprints.",
        )

    registry_repair_required = False
    if entry.get("cache_key") != resolved_cache_key:
        entry["cache_key"] = resolved_cache_key
        registry_repair_required = True
    if entry.get("request_hash") != resolved_request_hash:
        entry["request_hash"] = resolved_request_hash
        registry_repair_required = True
    if entry.get("dependency_fingerprint") != resolved_dependency_fingerprint:
        entry["dependency_fingerprint"] = resolved_dependency_fingerprint
        registry_repair_required = True
    if entry.get("format") != canonical_request_format:
        entry["format"] = canonical_request_format
        registry_repair_required = True

    if registry_repair_required:
        profiles[canonical_profile] = entry
        registry["updated_at_utc"] = _utcnow_iso()
        _write_publication_registry(wd_path, registry)

    return artifact_path, artifact_relpath


def _upsert_co_created_published_cache_entry(
    wd: Path,
    *,
    cache_key: str,
    artifact_relpath: str,
    artifact_path: Path,
    source_job_id: str,
    source_job_result: dict[str, object] | None,
) -> None:
    source_warnings = _normalize_warnings_payload(
        source_job_result.get("warnings") if isinstance(source_job_result, dict) else None
    )
    source_manifest_relpath = (
        str(source_job_result.get("manifest_relpath") or "").strip()
        if isinstance(source_job_result, dict)
        else ""
    )
    if not source_manifest_relpath:
        source_manifest_relpath = _job_manifest_relpath(source_job_id)

    source_artifact_id = (
        str(source_job_result.get("artifact_id") or "").strip()
        if isinstance(source_job_result, dict)
        else ""
    )
    if source_artifact_id:
        artifact_id = f"{source_artifact_id}-geodatabase"
    else:
        artifact_id = artifact_path.parent.name

    cache_entry = {
        "artifact_id": artifact_id,
        "artifact_relpath": artifact_relpath,
        "artifact_path": str(artifact_path),
        "artifact_paths": [artifact_relpath],
        "artifact_format": "geodatabase",
        "layer_outputs": [],
        "packaged_member_relpaths": [artifact_path.name],
        "source_job_id": source_job_id,
        "manifest_relpath": source_manifest_relpath,
        "warnings": source_warnings,
    }
    upsert_cache_index_entry(wd, cache_key, cache_entry)


def _resolve_geopackage_co_creation_source(
    *,
    source_artifact_path: Path,
    source_artifact_relpath: str,
) -> Path:
    if source_artifact_path.suffix.lower() == ".gpkg" and source_artifact_path.is_file():
        return source_artifact_path

    artifact_dir = source_artifact_path.parent
    gpkg_candidates = sorted(
        candidate
        for candidate in artifact_dir.glob("*.gpkg")
        if candidate.is_file()
    )
    if gpkg_candidates:
        return gpkg_candidates[0]

    if source_artifact_path.suffix.lower() != ".zip":
        raise FeaturesExportServiceError(
            "Prep-wepp geodatabase co-creation requires a GeoPackage source artifact.",
            status_code=409,
            code="materialization_error",
            details=f"Artifact {source_artifact_relpath} does not expose a GeoPackage payload.",
        )

    extracted_path = artifact_dir / "features_export.geodatabase_source.gpkg"
    try:
        with zipfile.ZipFile(source_artifact_path, mode="r") as zip_handle:
            gpkg_members = sorted(
                member for member in zip_handle.namelist() if member.lower().endswith(".gpkg")
            )
            if not gpkg_members:
                raise FeaturesExportServiceError(
                    "Prep-wepp geodatabase co-creation requires a GeoPackage source artifact.",
                    status_code=409,
                    code="materialization_error",
                    details=(
                        f"Artifact {source_artifact_relpath} does not contain a .gpkg payload member."
                    ),
                )
            with zip_handle.open(gpkg_members[0], mode="r") as source_handle:
                extracted_path.write_bytes(source_handle.read())
    except (zipfile.BadZipFile, OSError, KeyError) as exc:
        raise FeaturesExportServiceError(
            "Prep-wepp geodatabase co-creation failed while reading GeoPackage payload.",
            status_code=500,
            code="artifact_missing",
            details=str(exc),
        ) from exc

    return extracted_path


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

    (
        materialized_plan,
        layer_payloads,
        column_metadata_by_output_layer_id,
    ) = _materialize_export_payloads(
        submission,
        wd=wd,
        runid=runid,
    )
    writer = get_export_writer(submission.plan.request.format)
    writer_artifact = writer.write(
        ExportWriterRequest(
            plan=materialized_plan,
            layer_payloads=layer_payloads,
            artifact_dir=artifact_dir,
            artifact_basename="features_export",
        )
    )
    generation_timestamp_utc = _utcnow_iso()

    payload_member_sources = _payload_member_sources(
        artifact=writer_artifact,
        artifact_dir=artifact_dir,
    )

    bundle_member_sources: dict[str, Path] = {}
    bundle_member_sources.update(payload_member_sources)

    bundle_filename = _bundle_filename(submission.plan.request.format)
    bundle_path = artifact_dir / bundle_filename
    artifact_relpath = _to_relpath(wd, bundle_path)

    planned_packaged_member_relpaths = tuple(
        sorted(
            (
                *bundle_member_sources.keys(),
                FEATURES_EXPORT_MANIFEST_NAME,
                FEATURES_EXPORT_ARTIFACT_README_NAME,
            )
        )
    )
    bundle_artifact = ExportArtifactMetadata(
        format=writer_artifact.format,
        artifact_relpath=bundle_filename,
        artifact_path=str(bundle_path),
        layer_outputs=writer_artifact.layer_outputs,
        warnings=writer_artifact.warnings,
        packaged_member_relpaths=planned_packaged_member_relpaths,
    )

    manifest = build_export_manifest(
        plan=materialized_plan,
        artifact=bundle_artifact,
        dependency_snapshot=submission.dependency_snapshot,
        artifact_id=artifact_id,
        cache_hit=False,
        source_job_id=None,
        generation_timestamp_utc=generation_timestamp_utc,
        requested_crs=submission.plan.request.crs,
        resolved_crs=submission.plan.request.crs,
        column_metadata_by_output_layer_id=column_metadata_by_output_layer_id,
        request_column_selection_by_layer_id=_request_column_selection_payload(submission.plan),
    )

    artifact_manifest_relpath = f"{artifact_dir_relpath}/{FEATURES_EXPORT_MANIFEST_NAME}"
    artifact_manifest_path = _resolve_relpath(wd, artifact_manifest_relpath)
    write_export_manifest(artifact_manifest_path, manifest)

    readme_path = artifact_dir / FEATURES_EXPORT_ARTIFACT_README_NAME
    readme_path.write_text(
        build_export_readme(
            manifest=manifest,
            runid=runid,
            config=config,
        ),
        encoding="utf-8",
    )

    bundle_member_sources[FEATURES_EXPORT_MANIFEST_NAME] = artifact_manifest_path
    bundle_member_sources[FEATURES_EXPORT_ARTIFACT_README_NAME] = readme_path

    packaged_member_relpaths = package_files_as_zip(bundle_path, bundle_member_sources)

    job_manifest_relpath = _job_manifest_relpath(job_id)
    write_export_manifest(_resolve_relpath(wd, job_manifest_relpath), manifest)

    _cleanup_intermediate_writer_artifact(
        artifact=writer_artifact,
        retained_sources=(
            *tuple(bundle_member_sources.values()),
            bundle_path,
        ),
    )

    warnings_payload = _normalize_warnings_payload(manifest.get("warnings"))
    cache_entry = {
        "artifact_id": artifact_id,
        "artifact_relpath": artifact_relpath,
        "artifact_path": str(bundle_path),
        "artifact_paths": [artifact_relpath],
        "artifact_format": submission.plan.request.format,
        "layer_outputs": [layer.to_mapping() for layer in writer_artifact.layer_outputs],
        "packaged_member_relpaths": list(packaged_member_relpaths),
        "source_job_id": job_id,
        "manifest_relpath": artifact_manifest_relpath,
        "warnings": warnings_payload,
    }
    upsert_cache_index_entry(wd, submission.cache_key_parts.cache_key, cache_entry)

    return {
        "artifact_id": artifact_id,
        "artifact_relpath": artifact_relpath,
        "download_url": _job_download_url(runid, config, job_id),
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
        request_column_selection_by_layer_id=_request_column_selection_payload(submission.plan),
    )

    job_manifest_relpath = _job_manifest_relpath(job_id)
    write_export_manifest(_resolve_relpath(wd, job_manifest_relpath), manifest)

    return {
        "artifact_id": artifact_id,
        "artifact_relpath": artifact_relpath,
        "download_url": _job_download_url(runid, config, job_id),
        "cache_hit": True,
        "source_job_id": source_job_id,
        "manifest_relpath": job_manifest_relpath,
        "warnings": warnings_payload,
    }


def _materialize_export_payloads(
    submission: FeaturesExportSubmission,
    *,
    wd: Path,
    runid: str,
) -> tuple[ResolvedExportPlan, dict[str, PreparedLayerPayload], dict[str, dict[str, object]]]:
    materialized_plan, grouped_layers = _build_materialized_execution_plan(submission.plan, runid=runid)
    entries_by_output_layer_id = _dependency_entries_by_output_layer_id(submission.dependency_snapshot.entries)

    layer_core_results: dict[str, _LayerCoreResult] = {}
    legacy_frame_results: dict[str, _LayerFrameResult] = {}
    for layer in submission.plan.layers:
        catalog_layer = submission.catalog.get_layer(layer.layer_id)
        if catalog_layer is None:
            raise FeaturesExportServiceError(
                "Resolved export layer is missing from catalog.",
                status_code=500,
                code="catalog_resolution_error",
                details=f"Missing catalog definition for {layer.layer_id!r}.",
            )

        dependency_entries = entries_by_output_layer_id.get(layer.output_layer_id, [])
        if not layer.carrier_layer:
            legacy_frame_results[layer.output_layer_id] = _build_layer_frame_from_sources(
                wd=wd,
                layer=layer,
                catalog_layer_raw=catalog_layer.raw,
                request_plan=submission.plan,
                dependency_entries=dependency_entries,
                units_mode=submission.plan.request.units,
            )
            continue

        try:
            carrier_core = materialize_carrier_layer_core(
                wd=wd,
                layer=layer,
                catalog_layer_raw=_as_mapping(catalog_layer.raw),
                request_plan=submission.plan,
                dependency_entries=dependency_entries,
                consolidated_join_key_column=_CONSOLIDATED_JOIN_KEY_COLUMN,
            )
        except MaterializationContractError as exc:
            raise FeaturesExportServiceError(
                "Key-first layer materialization failed.",
                status_code=500,
                code="materialization_error",
                details=exc.details,
            ) from exc

        layer_core_results[layer.output_layer_id] = _LayerCoreResult(
            layer=layer,
            frame=carrier_core.frame,
            selected_columns=carrier_core.selected_columns,
            unit_mapping=carrier_core.unit_mapping,
            warnings=carrier_core.warnings,
            catalog_layer_raw=_as_mapping(catalog_layer.raw),
        )

    payloads: dict[str, PreparedLayerPayload] = {}
    column_metadata_by_output_layer_id: dict[str, dict[str, object]] = {}
    use_tabular_payload = _request_uses_tabular_payload(submission.plan)
    use_tabular_long_layout = _request_uses_tabular_long_layout(submission.plan)
    tabular_event_selector = (
        submission.plan.request.temporal.event
        if submission.plan.request.temporal is not None
        else None
    )
    watershed_identity_lookup_cache: dict[
        tuple[str, str],
        tuple[dict[str, object], dict[str, object]] | None,
    ] = {}

    for layer in materialized_plan.layers:
        source_layers = grouped_layers.get(layer.output_layer_id, ())
        if not source_layers:
            continue

        if not layer.carrier_layer:
            source_results = [legacy_frame_results[item.output_layer_id] for item in source_layers]
            payload, column_metadata = _build_materialized_layer_payload(
                layer,
                source_results=source_results,
                use_tabular_payload=use_tabular_payload,
                requested_crs=submission.plan.request.crs,
            )
            payloads[layer.output_layer_id] = payload
            column_metadata_by_output_layer_id[layer.output_layer_id] = column_metadata
            continue

        source_results = [layer_core_results[item.output_layer_id] for item in source_layers]
        try:
            payload, column_metadata = _build_key_first_materialized_layer_payload(
                wd=wd,
                layer=layer,
                source_layers=source_layers,
                source_results=source_results,
                entries_by_output_layer_id=entries_by_output_layer_id,
                use_tabular_payload=use_tabular_payload,
                use_tabular_long_layout=use_tabular_long_layout,
                tabular_event_selector=tabular_event_selector,
                watershed_identity_lookup_cache=watershed_identity_lookup_cache,
                units_mode=submission.plan.request.units,
                requested_crs=submission.plan.request.crs,
            )
        except MaterializationContractError as exc:
            raise FeaturesExportServiceError(
                "Key-first carrier materialization failed.",
                status_code=500,
                code="materialization_error",
                details=exc.details,
            ) from exc

        payloads[layer.output_layer_id] = payload
        column_metadata_by_output_layer_id[layer.output_layer_id] = column_metadata

    return materialized_plan, payloads, column_metadata_by_output_layer_id


def _dependency_entries_by_output_layer_id(
    entries: cabc.Sequence[object],
) -> dict[str, list[object]]:
    by_output_layer_id: dict[str, list[object]] = {}
    for entry in entries:
        output_layer_id = getattr(entry, "output_layer_id", None)
        if not isinstance(output_layer_id, str) or not output_layer_id:
            continue
        by_output_layer_id.setdefault(output_layer_id, []).append(entry)
    return by_output_layer_id


def _build_key_first_materialized_layer_payload(
    *,
    wd: Path,
    layer: ResolvedLayerPlan,
    source_layers: cabc.Sequence[ResolvedLayerPlan],
    source_results: cabc.Sequence[_LayerCoreResult],
    entries_by_output_layer_id: cabc.Mapping[str, cabc.Sequence[object]],
    use_tabular_payload: bool,
    use_tabular_long_layout: bool,
    tabular_event_selector: NormalizedTemporalEvent | None,
    watershed_identity_lookup_cache: dict[
        tuple[str, str],
        tuple[dict[str, object], dict[str, object]] | None,
    ],
    units_mode: str,
    requested_crs: str = "wgs",
) -> tuple[PreparedLayerPayload, dict[str, object]]:
    if not source_results:
        raise MaterializationContractError(
            "No source tables were available for carrier payload materialization.",
            details=f"output_layer_id={layer.output_layer_id!r}",
        )

    warnings: list[ExportWarning] = []
    layer_inputs: list[LayerCarrierInput] = []
    for result in source_results:
        warnings.extend(result.warnings)
        aligned_frame = _align_carrier_identity_join_key(
            frame=result.frame,
            wd=wd,
            carrier_layer=layer.carrier_layer,
            cache=watershed_identity_lookup_cache,
        )
        layer_inputs.append(
            LayerCarrierInput(
                layer_id=result.layer.layer_id,
                dataframe=aligned_frame,
                selected_columns=result.selected_columns,
                unit_mapping=result.unit_mapping,
            )
        )

    allow_non_unique_carrier_keys = (
        layer.temporal_mode == "event"
        or any(_layer_join_allows_non_unique_keys(result.catalog_layer_raw) for result in source_results)
    )

    carrier_core = materialize_carrier_core(
        carrier_label=layer.output_layer_id,
        layer_inputs=layer_inputs,
        allow_non_unique_keys=allow_non_unique_carrier_keys,
    )

    if use_tabular_payload:
        merged_table = carrier_core.dataframe.copy()

        selected_columns = _carrier_selected_columns(
            merged=merged_table,
            carrier_core=carrier_core,
            source_results=source_results,
        )
        unit_mapping = _carrier_unit_mapping(
            selected_columns=selected_columns,
            carrier_core=carrier_core,
            source_results=source_results,
        )
        merged_table, unit_mapping = _apply_unit_conversions(
            wd=wd,
            frame=merged_table,
            selected_columns=selected_columns,
            unit_mapping=unit_mapping,
            units_mode=units_mode,
        )
        if use_tabular_long_layout:
            temporal_long = reshape_temporal_wide_to_long(
                frame=merged_table,
                selected_columns=selected_columns,
                unit_mapping=unit_mapping,
                temporal_mode=layer.temporal_mode,
                event_selector=tabular_event_selector,
            )
            merged_table = temporal_long.frame
            selected_columns = temporal_long.selected_columns
            unit_mapping = temporal_long.unit_mapping

        merged_table, selected_columns, unit_mapping = apply_unitized_column_suffixes(
            frame=merged_table,
            selected_columns=selected_columns,
            unit_mapping=unit_mapping,
            geometry_name="",
            consolidated_join_key_column=_CONSOLIDATED_JOIN_KEY_COLUMN,
        )
        merged_table, selected_columns, unit_mapping = normalize_identity_output_columns(
            frame=merged_table,
            selected_columns=selected_columns,
            unit_mapping=unit_mapping,
            geometry_name=None,
            consolidated_join_key_column=_CONSOLIDATED_JOIN_KEY_COLUMN,
        )
        merged_table = _backfill_tabular_identity_from_watershed(
            frame=merged_table,
            wd=wd,
            carrier_layer=layer.carrier_layer,
            cache=watershed_identity_lookup_cache,
        )
        merged_table = merged_table.drop(columns=[_CONSOLIDATED_JOIN_KEY_COLUMN], errors="ignore")

        projection_columns = [column for column in selected_columns if column in merged_table.columns]
        selected_columns = tuple(_dedupe_identity_selected_columns(projection_columns))
        table_frame = pd.DataFrame(merged_table[list(selected_columns)]).copy()

        row_count = int(len(table_frame.index))
        feature_count = row_count

        description_mapping = _column_description_mapping_for_selected_columns(
            selected_columns=selected_columns,
            unit_mapping=unit_mapping,
            catalog_layer_raws=tuple(result.catalog_layer_raw for result in source_results),
        )

        column_metadata = build_output_layer_column_metadata(
            source_layer_ids=carrier_core.source_layer_ids,
            selected_columns=selected_columns,
            unit_mapping=unit_mapping,
            description_mapping=description_mapping,
            materialization={
                "strategy": "key_first_tabular_no_geometry",
                "carrier_layer": layer.carrier_layer,
                "core_row_count": int(len(carrier_core.dataframe.index)),
            },
        )

        return (
            PreparedLayerPayload(
                output_layer_id=layer.output_layer_id,
                payload=b"",
                tabular_frame=table_frame,
                row_count=row_count,
                feature_count=feature_count,
                warnings=tuple(warnings),
            ),
            column_metadata,
        )

    candidate_key_tokens: list[str] = []
    geometry_relpaths: list[str] = []
    for source_layer, source_result in zip(source_layers, source_results):
        candidate_key_tokens.extend(layer_key_candidates(source_result.catalog_layer_raw))
        dependency_entries = entries_by_output_layer_id.get(source_layer.output_layer_id, ())
        geometry_relpath = resolve_geometry_relpath(dependency_entries)
        if geometry_relpath is not None:
            geometry_relpaths.append(geometry_relpath)

    geometry_carrier = build_canonical_geometry_carrier(
        wd=wd,
        carrier_layer=layer.carrier_layer,
        geometry_relpaths=geometry_relpaths,
        candidate_key_tokens=candidate_key_tokens,
    )
    geometry_keys = set(geometry_carrier.dataframe[_CONSOLIDATED_JOIN_KEY_COLUMN].tolist())
    core_for_geometry = carrier_core.dataframe[
        carrier_core.dataframe[_CONSOLIDATED_JOIN_KEY_COLUMN].isin(geometry_keys)
    ].reset_index(drop=True)
    if core_for_geometry.empty:
        if layer.temporal_mode != "event":
            raise MaterializationContractError(
                "Carrier core contains no keys that match canonical carrier geometry.",
                details=f"output_layer_id={layer.output_layer_id!r}; carrier={layer.carrier_layer!r}",
            )

        seed_keys = sorted(geometry_keys)
        placeholder: dict[str, object] = {_CONSOLIDATED_JOIN_KEY_COLUMN: seed_keys}
        for column_name in carrier_core.selected_columns:
            if column_name == _CONSOLIDATED_JOIN_KEY_COLUMN or column_name in placeholder:
                continue
            placeholder[column_name] = [None] * len(seed_keys)
        core_for_geometry = pd.DataFrame(placeholder)

    merged = attach_geometry_once(
        core_table=core_for_geometry,
        geometry_carrier=geometry_carrier,
        allow_non_unique_keys=allow_non_unique_carrier_keys,
    )
    if layer.temporal_mode == "event":
        merged = _backfill_identity_from_geometry_key(
            merged,
            geometry_key_column=geometry_carrier.key_column,
            consolidated_join_key_column=_CONSOLIDATED_JOIN_KEY_COLUMN,
        )

    selected_columns = _carrier_selected_columns(
        merged=merged,
        carrier_core=carrier_core,
        source_results=source_results,
    )
    unit_mapping = _carrier_unit_mapping(
        selected_columns=selected_columns,
        carrier_core=carrier_core,
        source_results=source_results,
    )
    merged, unit_mapping = _apply_unit_conversions(
        wd=wd,
        frame=merged,
        selected_columns=selected_columns,
        unit_mapping=unit_mapping,
        units_mode=units_mode,
    )
    if use_tabular_long_layout:
        temporal_long = reshape_temporal_wide_to_long(
            frame=merged,
            selected_columns=selected_columns,
            unit_mapping=unit_mapping,
            temporal_mode=layer.temporal_mode,
            event_selector=tabular_event_selector,
        )
        merged = temporal_long.frame
        selected_columns = temporal_long.selected_columns
        unit_mapping = temporal_long.unit_mapping

    geometry_name = merged.geometry.name
    merged, selected_columns, unit_mapping = apply_unitized_column_suffixes(
        frame=merged,
        selected_columns=selected_columns,
        unit_mapping=unit_mapping,
        geometry_name=geometry_name,
        consolidated_join_key_column=_CONSOLIDATED_JOIN_KEY_COLUMN,
    )
    merged, selected_columns, unit_mapping = normalize_identity_output_columns(
        frame=merged,
        selected_columns=selected_columns,
        unit_mapping=unit_mapping,
        geometry_name=geometry_name,
        consolidated_join_key_column=_CONSOLIDATED_JOIN_KEY_COLUMN,
    )

    merged = merged.drop(columns=[_CONSOLIDATED_JOIN_KEY_COLUMN], errors="ignore")
    geometry_name = merged.geometry.name
    projection_columns = [column for column in selected_columns if column in merged.columns and column != geometry_name]
    selected_columns = tuple(_dedupe_identity_selected_columns(projection_columns))
    merged = gpd.GeoDataFrame(
        merged[list(selected_columns) + [geometry_name]],
        geometry=geometry_name,
        crs=merged.crs,
    )
    merged = _project_spatial_frame_for_request(
        merged,
        requested_crs=requested_crs,
    )

    row_count = int(len(merged.index))
    feature_count = int(merged.geometry.notna().sum())
    payload = _serialize_feature_collection_payload(
        merged,
        layer_id=layer.layer_id,
        output_layer_id=layer.output_layer_id,
        scope=layer.scope,
        scope_class=layer.scope_class,
    )

    description_mapping = _column_description_mapping_for_selected_columns(
        selected_columns=selected_columns,
        unit_mapping=unit_mapping,
        catalog_layer_raws=tuple(result.catalog_layer_raw for result in source_results),
    )

    column_metadata = build_output_layer_column_metadata(
        source_layer_ids=carrier_core.source_layer_ids,
        selected_columns=selected_columns,
        unit_mapping=unit_mapping,
        description_mapping=description_mapping,
        materialization={
            "strategy": "key_first_geometry_last",
            "carrier_layer": layer.carrier_layer,
            "carrier_key_column": geometry_carrier.key_column,
            "geometry_relpath": geometry_carrier.geometry_relpath,
            "core_row_count": int(len(core_for_geometry.index)),
            "geometry_row_count": int(len(geometry_carrier.dataframe.index)),
        },
    )

    return (
        PreparedLayerPayload(
            output_layer_id=layer.output_layer_id,
            payload=payload,
            row_count=row_count,
            feature_count=feature_count,
            warnings=tuple(warnings),
        ),
        column_metadata,
    )


def _carrier_selected_columns(
    *,
    merged: pd.DataFrame,
    carrier_core: object,
    source_results: cabc.Sequence[_LayerCoreResult],
) -> tuple[str, ...]:
    geometry_name = merged.geometry.name if isinstance(merged, gpd.GeoDataFrame) else None
    selected_columns: list[str] = []
    for column_name in getattr(carrier_core, "selected_columns", ()):
        if column_name in merged.columns and column_name != geometry_name and column_name not in selected_columns:
            selected_columns.append(column_name)

    for source_result in source_results:
        for column_name in source_result.selected_columns:
            if column_name in merged.columns and column_name != geometry_name and column_name not in selected_columns:
                selected_columns.append(column_name)
        for required_column in _required_identity_columns(source_result.catalog_layer_raw):
            if required_column in merged.columns and required_column != geometry_name and required_column not in selected_columns:
                selected_columns.append(required_column)

    if not selected_columns:
        selected_columns = [
            column_name
            for column_name in merged.columns
            if column_name not in {geometry_name, _CONSOLIDATED_JOIN_KEY_COLUMN}
        ]

    return tuple(_dedupe_identity_selected_columns(selected_columns))


def _backfill_identity_from_geometry_key(
    frame: pd.DataFrame,
    *,
    geometry_key_column: str,
    consolidated_join_key_column: str,
) -> pd.DataFrame:
    if consolidated_join_key_column not in frame.columns:
        return frame

    key_token = _normalize_join_token(geometry_key_column)
    if not key_token:
        return frame

    result = frame.copy()
    join_values = result[consolidated_join_key_column]
    for column_name in result.columns:
        if column_name == consolidated_join_key_column:
            continue
        if _normalize_join_token(column_name) != key_token:
            continue

        series = result[column_name]
        missing_mask = series.isna()
        if not missing_mask.any():
            continue

        if pd.api.types.is_numeric_dtype(series):
            fill_values = pd.to_numeric(join_values, errors="coerce")
        else:
            fill_values = join_values
        result.loc[missing_mask, column_name] = fill_values.loc[missing_mask]

    return result


def _align_carrier_identity_join_key(
    *,
    frame: pd.DataFrame,
    wd: Path,
    carrier_layer: str | None,
    cache: dict[
        tuple[str, str],
        tuple[dict[str, object], dict[str, object]] | None,
    ],
) -> pd.DataFrame:
    if _CONSOLIDATED_JOIN_KEY_COLUMN not in frame.columns:
        return frame

    carrier_token = str(carrier_layer or "").strip().lower()
    if carrier_token not in {"sbs_map-subcatchments", "chan_map-channels"}:
        return frame

    has_topaz = _TOPAZ_ID_COLUMN in frame.columns
    has_wepp = _WEPP_ID_COLUMN in frame.columns
    if not has_topaz and not has_wepp:
        return frame

    result = frame.copy()
    if not has_topaz:
        result[_TOPAZ_ID_COLUMN] = pd.Series(
            [None] * len(result.index),
            index=result.index,
            dtype="object",
        )
    if not has_wepp:
        result[_WEPP_ID_COLUMN] = pd.Series(
            [None] * len(result.index),
            index=result.index,
            dtype="object",
        )

    result = _backfill_tabular_identity_from_watershed(
        frame=result,
        wd=wd,
        carrier_layer=carrier_layer,
        cache=cache,
    )

    normalized_join = result[_CONSOLIDATED_JOIN_KEY_COLUMN].map(_canonical_join_value)
    preferred_identity_order = (_TOPAZ_ID_COLUMN, _WEPP_ID_COLUMN)
    # Allow retargeting onto synthesized identity columns when watershed lookup
    # backfill resolved them and the one-to-one guardrails below are satisfied.
    retargetable_identity_columns = {
        _TOPAZ_ID_COLUMN: bool(result[_TOPAZ_ID_COLUMN].map(_canonical_join_value).notna().any()),
        _WEPP_ID_COLUMN: bool(result[_WEPP_ID_COLUMN].map(_canonical_join_value).notna().any()),
    }

    existing_join_non_null = normalized_join.dropna()
    existing_join_unique_count = int(existing_join_non_null.nunique())

    for identity_column in preferred_identity_order:
        if not retargetable_identity_columns.get(identity_column, False):
            continue

        identity_series = result[identity_column].map(_canonical_join_value)
        identity_non_null = identity_series.dropna()
        if identity_non_null.empty:
            continue

        if existing_join_unique_count == 0:
            normalized_join = identity_series
            existing_join_non_null = normalized_join.dropna()
            existing_join_unique_count = int(existing_join_non_null.nunique())
            break

        overlap_mask = normalized_join.notna() & identity_series.notna()
        if not overlap_mask.any():
            continue

        overlap_frame = pd.DataFrame(
            {
                "join": normalized_join.loc[overlap_mask],
                "identity": identity_series.loc[overlap_mask],
            }
        ).drop_duplicates()

        # Retarget only when the identity domain covers every resolved join key
        # and preserves one-to-one key cardinality.
        if int(overlap_frame["join"].nunique()) != existing_join_unique_count:
            continue
        if int(overlap_frame["identity"].nunique()) != int(identity_non_null.nunique()):
            continue
        if int(overlap_frame["identity"].nunique()) != existing_join_unique_count:
            continue

        normalized_join = identity_series
        existing_join_non_null = normalized_join.dropna()
        existing_join_unique_count = int(existing_join_non_null.nunique())
        break

    fill_identity_order = list(preferred_identity_order)
    if normalized_join.notna().any():
        scored_order: list[tuple[int, int, str]] = []
        for order_index, identity_column in enumerate(preferred_identity_order):
            identity_series = result[identity_column].map(_canonical_join_value)
            overlap_mask = normalized_join.notna() & identity_series.notna()
            match_score = 0
            if overlap_mask.any():
                match_score = int(
                    (normalized_join.loc[overlap_mask] == identity_series.loc[overlap_mask]).sum()
                )
            scored_order.append((-match_score, order_index, identity_column))
        scored_order.sort()
        fill_identity_order = [entry[2] for entry in scored_order]

    missing_join_mask = normalized_join.isna()
    if missing_join_mask.any():
        for identity_column in fill_identity_order:
            identity_series = result[identity_column].map(_canonical_join_value)
            fill_mask = missing_join_mask & identity_series.notna()
            if fill_mask.any():
                normalized_join.loc[fill_mask] = identity_series.loc[fill_mask]
                missing_join_mask = normalized_join.isna()
            if not missing_join_mask.any():
                break

    if not normalized_join.notna().any():
        return result

    result[_CONSOLIDATED_JOIN_KEY_COLUMN] = normalized_join
    return result


def _backfill_tabular_identity_from_watershed(
    *,
    frame: pd.DataFrame,
    wd: Path,
    carrier_layer: str | None,
    cache: dict[
        tuple[str, str],
        tuple[dict[str, object], dict[str, object]] | None,
    ],
) -> pd.DataFrame:
    if _TOPAZ_ID_COLUMN not in frame.columns or _WEPP_ID_COLUMN not in frame.columns:
        return frame

    missing_topaz = frame[_TOPAZ_ID_COLUMN].isna()
    missing_wepp = frame[_WEPP_ID_COLUMN].isna()
    if not missing_topaz.any() and not missing_wepp.any():
        return frame

    lookup = _load_watershed_identity_lookup(
        wd=wd,
        carrier_layer=carrier_layer,
        cache=cache,
    )
    if lookup is None:
        return frame
    topaz_by_wepp, wepp_by_topaz = lookup
    if not topaz_by_wepp and not wepp_by_topaz:
        return frame

    result = frame.copy()
    result[_TOPAZ_ID_COLUMN] = _fill_missing_identity_values(
        target_series=result[_TOPAZ_ID_COLUMN],
        source_series=result[_WEPP_ID_COLUMN],
        lookup=topaz_by_wepp,
    )
    result[_WEPP_ID_COLUMN] = _fill_missing_identity_values(
        target_series=result[_WEPP_ID_COLUMN],
        source_series=result[_TOPAZ_ID_COLUMN],
        lookup=wepp_by_topaz,
    )
    result[_TOPAZ_ID_COLUMN] = _fill_missing_identity_values(
        target_series=result[_TOPAZ_ID_COLUMN],
        source_series=result[_WEPP_ID_COLUMN],
        lookup=topaz_by_wepp,
    )
    return result


def _load_watershed_identity_lookup(
    *,
    wd: Path,
    carrier_layer: str | None,
    cache: dict[
        tuple[str, str],
        tuple[dict[str, object], dict[str, object]] | None,
    ],
) -> tuple[dict[str, object], dict[str, object]] | None:
    carrier_token = str(carrier_layer or "").strip().lower()
    cache_key = (str(wd.resolve()), carrier_token)
    cached = cache.get(cache_key)
    if cache_key in cache:
        return cached

    topaz_by_wepp: dict[str, object] = {}
    wepp_by_topaz: dict[str, object] = {}
    ambiguous_wepp_keys: set[str] = set()
    ambiguous_topaz_keys: set[str] = set()

    for relpath in _watershed_identity_relpaths_for_carrier(carrier_token):
        parquet_path = pick_existing_parquet_path(wd, relpath)
        if parquet_path is None:
            continue

        for topaz_value, wepp_value in _read_watershed_identity_pairs(parquet_path):
            _merge_watershed_identity_pair(
                topaz_value=topaz_value,
                wepp_value=wepp_value,
                topaz_by_wepp=topaz_by_wepp,
                wepp_by_topaz=wepp_by_topaz,
                ambiguous_wepp_keys=ambiguous_wepp_keys,
                ambiguous_topaz_keys=ambiguous_topaz_keys,
            )

    for ambiguous_wepp in ambiguous_wepp_keys:
        topaz_by_wepp.pop(ambiguous_wepp, None)
    for ambiguous_topaz in ambiguous_topaz_keys:
        wepp_by_topaz.pop(ambiguous_topaz, None)

    lookup: tuple[dict[str, object], dict[str, object]] | None = None
    if topaz_by_wepp or wepp_by_topaz:
        lookup = (topaz_by_wepp, wepp_by_topaz)

    cache[cache_key] = lookup
    return lookup


def _watershed_identity_relpaths_for_carrier(carrier_token: str) -> tuple[str, ...]:
    if carrier_token == "chan_map-channels":
        return ("watershed/channels.parquet", "watershed/hillslopes.parquet")
    return ("watershed/hillslopes.parquet", "watershed/channels.parquet")


def _read_watershed_identity_pairs(parquet_path: Path) -> tuple[tuple[object, object], ...]:
    frame = pd.read_parquet(parquet_path)
    column_lookup = _normalized_column_lookup(frame.columns)
    topaz_column = column_lookup.get("topazid")
    wepp_column = column_lookup.get("weppid")
    if topaz_column is None or wepp_column is None:
        return ()

    pairs_frame = frame[[topaz_column, wepp_column]].dropna(how="any")
    if pairs_frame.empty:
        return ()
    return tuple(pairs_frame.itertuples(index=False, name=None))


def _merge_watershed_identity_pair(
    *,
    topaz_value: object,
    wepp_value: object,
    topaz_by_wepp: dict[str, object],
    wepp_by_topaz: dict[str, object],
    ambiguous_wepp_keys: set[str],
    ambiguous_topaz_keys: set[str],
) -> None:
    topaz_key = _canonical_join_value(topaz_value)
    wepp_key = _canonical_join_value(wepp_value)
    if topaz_key is None or wepp_key is None:
        return

    existing_topaz = topaz_by_wepp.get(wepp_key)
    if existing_topaz is None:
        topaz_by_wepp[wepp_key] = topaz_value
    elif _canonical_join_value(existing_topaz) != topaz_key:
        ambiguous_wepp_keys.add(wepp_key)

    existing_wepp = wepp_by_topaz.get(topaz_key)
    if existing_wepp is None:
        wepp_by_topaz[topaz_key] = wepp_value
    elif _canonical_join_value(existing_wepp) != wepp_key:
        ambiguous_topaz_keys.add(topaz_key)


def _fill_missing_identity_values(
    *,
    target_series: pd.Series,
    source_series: pd.Series,
    lookup: cabc.Mapping[str, object],
) -> pd.Series:
    if not lookup:
        return target_series

    missing_mask = target_series.isna()
    if not missing_mask.any():
        return target_series

    source_keys = source_series.map(_canonical_join_value)
    mapped_values = source_keys.map(lookup)
    fill_mask = missing_mask & mapped_values.notna()
    if not fill_mask.any():
        return target_series

    filled = target_series.copy()
    filled.loc[fill_mask] = mapped_values.loc[fill_mask]
    return filled


def _carrier_unit_mapping(
    *,
    selected_columns: cabc.Sequence[str],
    carrier_core: object,
    source_results: cabc.Sequence[_LayerCoreResult],
) -> dict[str, str]:
    merged_units: dict[str, str] = {}
    for column_name, unit_value in getattr(carrier_core, "unit_mapping", {}).items():
        if isinstance(unit_value, str) and unit_value.strip():
            merged_units[column_name] = unit_value.strip()

    for source_result in source_results:
        for column_name, unit_value in source_result.unit_mapping.items():
            if column_name in merged_units:
                continue
            if isinstance(unit_value, str) and unit_value.strip():
                merged_units[column_name] = unit_value.strip()

    resolved: dict[str, str] = {}
    for column_name in selected_columns:
        unit_value = merged_units.get(column_name)
        if isinstance(unit_value, str) and unit_value.strip():
            resolved[column_name] = unit_value.strip()
        else:
            resolved[column_name] = _infer_display_unit_for_column(column_name)
    return resolved


def _apply_unit_conversions(
    *,
    wd: Path,
    frame: pd.DataFrame,
    selected_columns: cabc.Sequence[str],
    unit_mapping: cabc.Mapping[str, str],
    units_mode: str,
) -> tuple[pd.DataFrame, dict[str, str]]:
    resolved_columns = [column for column in selected_columns if column in frame.columns]
    if not resolved_columns:
        return frame, dict(unit_mapping)

    conversion_units: dict[str, str] = {}
    for column_name in resolved_columns:
        unit_value = str(unit_mapping.get(column_name) or "").strip()
        if not unit_value:
            unit_value = _infer_display_unit_for_column(column_name)
        if unit_value:
            conversion_units[column_name] = unit_value

    if not conversion_units:
        return frame, dict(unit_mapping)

    try:
        unitizer = Unitizer.getInstance(str(wd), allow_nonexistent=True)
    except FileNotFoundError as exc:
        if units_mode == "project":
            raise FeaturesExportServiceError(
                "Unitizer preferences are required for project unit conversions.",
                status_code=500,
                code="unitizer_unavailable",
                details=str(exc),
            ) from exc
        return frame, dict(unit_mapping)

    if unitizer is None:
        if units_mode == "project":
            raise FeaturesExportServiceError(
                "Unitizer preferences are required for project unit conversions.",
                status_code=500,
                code="unitizer_unavailable",
                details="unitizer.nodb is missing for requested project units mode.",
            )
        return frame, dict(unit_mapping)

    convert_table = getattr(unitizer, "convert_table", None)
    if not callable(convert_table):
        raise FeaturesExportServiceError(
            "Unitizer table conversion API is unavailable.",
            status_code=500,
            code="unitizer_unavailable",
            details="Unitizer controller does not expose convert_table().",
        )

    try:
        converted_table = convert_table(
            frame,
            conversion_units,
            units_mode=units_mode,
        )
    except (KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise FeaturesExportServiceError(
            "Unit conversion failed during features export materialization.",
            status_code=500,
            code="materialization_error",
            details=str(exc),
        ) from exc

    converted_frame = getattr(converted_table, "data", None)
    if not isinstance(converted_frame, pd.DataFrame):
        raise FeaturesExportServiceError(
            "Unitizer table conversion returned an invalid payload shape.",
            status_code=500,
            code="materialization_error",
            details="Expected pandas.DataFrame result from convert_table().",
        )

    if isinstance(frame, gpd.GeoDataFrame) and not isinstance(converted_frame, gpd.GeoDataFrame):
        geometry_name = frame.geometry.name
        if geometry_name in converted_frame.columns:
            converted_frame = gpd.GeoDataFrame(
                converted_frame,
                geometry=geometry_name,
                crs=frame.crs,
            )

    metadata_by_column = getattr(converted_table, "metadata_by_column", {})
    resolved_unit_mapping: dict[str, str] = dict(unit_mapping)
    for column_name in resolved_columns:
        column_metadata = (
            metadata_by_column.get(column_name)
            if isinstance(metadata_by_column, cabc.Mapping)
            else None
        )
        target_unit = _as_string(getattr(column_metadata, "target_unit", None))
        source_unit = _as_string(getattr(column_metadata, "source_unit", None))
        if target_unit:
            resolved_unit_mapping[column_name] = target_unit
        elif source_unit and column_name not in resolved_unit_mapping:
            resolved_unit_mapping[column_name] = source_unit
        elif column_name not in resolved_unit_mapping:
            resolved_unit_mapping[column_name] = _infer_display_unit_for_column(column_name)

    return converted_frame, resolved_unit_mapping


def _project_spatial_frame_for_request(
    frame: gpd.GeoDataFrame,
    *,
    requested_crs: str,
) -> gpd.GeoDataFrame:
    target = str(requested_crs or "wgs").strip().lower()
    if target == "wgs":
        if frame.crs is None:
            raise FeaturesExportServiceError(
                "Unable to resolve WGS84 projection without source CRS metadata.",
                status_code=500,
                code="materialization_error",
                details="Spatial frame is missing CRS metadata for WGS84 export.",
            )
        try:
            epsg = frame.crs.to_epsg()
        except Exception:  # boundary: CRS inspection must not crash export
            epsg = None
        if epsg == 4326:
            return frame
        try:
            return frame.to_crs(epsg=4326)
        except (RuntimeError, TypeError, ValueError) as exc:
            raise FeaturesExportServiceError(
                "Failed to reproject export layer to WGS84.",
                status_code=500,
                code="materialization_error",
                details=str(exc),
            ) from exc

    if target != "utm":
        return frame
    if frame.crs is None:
        raise FeaturesExportServiceError(
            "Unable to resolve UTM projection without source CRS metadata.",
            status_code=500,
            code="materialization_error",
            details="Spatial frame is missing CRS metadata for UTM export.",
        )

    try:
        utm_crs = frame.estimate_utm_crs()
    except (RuntimeError, TypeError, ValueError) as exc:
        raise FeaturesExportServiceError(
            "Failed to resolve UTM CRS for export layer.",
            status_code=500,
            code="materialization_error",
            details=str(exc),
        ) from exc

    if utm_crs is None:
        raise FeaturesExportServiceError(
            "Unable to resolve UTM CRS for export layer.",
            status_code=500,
            code="materialization_error",
            details="Could not estimate UTM EPSG from layer geometry.",
        )

    try:
        return frame.to_crs(utm_crs)
    except (RuntimeError, TypeError, ValueError) as exc:
        raise FeaturesExportServiceError(
            "Failed to reproject export layer to UTM CRS.",
            status_code=500,
            code="materialization_error",
            details=str(exc),
        ) from exc


def _build_materialized_execution_plan(
    plan: ResolvedExportPlan,
    *,
    runid: str,
) -> tuple[ResolvedExportPlan, dict[str, tuple[ResolvedLayerPlan, ...]]]:
    grouped_layers: dict[str, list[ResolvedLayerPlan]] = {}
    materialized_layers: list[ResolvedLayerPlan] = []

    consolidation_groups: dict[tuple[str, str, str, str], list[ResolvedLayerPlan]] = {}
    passthrough_layers: list[ResolvedLayerPlan] = []

    for layer in sorted(plan.layers, key=lambda item: item.output_layer_id):
        if _should_consolidate_layer(layer):
            consolidation_scope = _consolidation_scope_for_layer(
                layer=layer,
            )
            group_key = (
                layer.context,
                layer.selector_id or "",
                consolidation_scope,
                layer.carrier_layer or "",
            )
            consolidation_groups.setdefault(group_key, []).append(layer)
        else:
            passthrough_layers.append(layer)

    for layer in passthrough_layers:
        materialized_layers.append(layer)
        grouped_layers[layer.output_layer_id] = (layer,)

    for group_key, group_layers in sorted(consolidation_groups.items()):
        context, selector_id, scope, carrier = group_key
        representative = sorted(group_layers, key=lambda item: item.layer_id)[0]
        output_layer_id = _carrier_output_layer_id(
            runid=runid,
            context=context,
            selector_id=selector_id or None,
            scope=scope,
            carrier_layer=carrier,
        )
        materialized = ResolvedLayerPlan(
            layer_id=f"{representative.family}.{carrier}",
            family=representative.family,
            scope_class=representative.scope_class,
            scope=scope,
            output_layer_id=output_layer_id,
            temporal_mode=representative.temporal_mode,
            context=context,
            selector_id=selector_id or None,
            carrier_layer=carrier,
        )
        materialized_layers.append(materialized)
        grouped_layers[output_layer_id] = tuple(sorted(group_layers, key=lambda item: item.layer_id))

    materialized_layers.sort(key=lambda item: item.output_layer_id)
    materialized_plan = replace(plan, layers=tuple(materialized_layers))
    return materialized_plan, {key: tuple(value) for key, value in grouped_layers.items()}


def _should_consolidate_layer(layer: ResolvedLayerPlan) -> bool:
    return bool(layer.carrier_layer)


def _consolidation_scope_for_layer(
    *,
    layer: ResolvedLayerPlan,
) -> str:
    if layer.context == "base" and layer.scope == "shared":
        return "baseline"
    return layer.scope


def _carrier_output_layer_id(
    *,
    runid: str,
    context: str,
    selector_id: str | None,
    scope: str,
    carrier_layer: str,
) -> str:
    safe_runid = _safe_layer_token(runid)
    safe_carrier = _safe_layer_token(carrier_layer)
    if context == "base":
        if scope == "roads":
            return f"{safe_runid}-roads-{safe_carrier}"
        return f"{safe_runid}-{safe_carrier}"

    selector_token = _safe_layer_token(selector_id or "unknown")
    if context == "scenario":
        return f"{safe_runid}-scenario-{selector_token}-{safe_carrier}"
    if context == "contrast":
        return f"{safe_runid}-contrast-{selector_token}-{safe_carrier}"
    return f"{safe_runid}-{_safe_layer_token(context)}-{selector_token}-{safe_carrier}"


def _safe_layer_token(value: str) -> str:
    token = _SAFE_TOKEN_PATTERN.sub("-", str(value)).strip("-")
    return token or "layer"


def _build_materialized_layer_payload(
    layer: ResolvedLayerPlan,
    *,
    source_results: cabc.Sequence[_LayerFrameResult],
    use_tabular_payload: bool,
    requested_crs: str = "wgs",
) -> tuple[PreparedLayerPayload, dict[str, object]]:
    if not source_results:
        raise FeaturesExportServiceError(
            "No source layers were available for materialized payload.",
            status_code=500,
            code="materialization_error",
            details=f"output_layer_id={layer.output_layer_id!r}",
        )

    source_sorted = sorted(source_results, key=lambda item: item.layer.layer_id)
    warnings: list[ExportWarning] = []
    for result in source_sorted:
        warnings.extend(result.warnings)

    if len(source_sorted) != 1:
        raise FeaturesExportServiceError(
            "Unexpected passthrough materialization group cardinality.",
            status_code=500,
            code="materialization_error",
            details=(
                f"output_layer_id={layer.output_layer_id!r}; "
                f"source_count={len(source_sorted)}"
            ),
        )

    merged = source_sorted[0].frame.copy()
    selected_columns = list(source_sorted[0].selected_columns)
    unit_mapping = dict(source_sorted[0].unit_mapping)
    source_layer_ids = [source_sorted[0].layer.layer_id]

    merged = merged.drop(columns=[_CONSOLIDATED_JOIN_KEY_COLUMN], errors="ignore")
    selected_columns = [column for column in selected_columns if column in merged.columns and column != merged.geometry.name]
    selected_columns = _dedupe_identity_selected_columns(selected_columns)

    if use_tabular_payload:
        table_frame = pd.DataFrame(merged[selected_columns]).copy()
        row_count = int(len(table_frame.index))
        feature_count = row_count
        payload: str | bytes = b""
    else:
        merged = _project_spatial_frame_for_request(
            merged,
            requested_crs=requested_crs,
        )
        row_count = int(len(merged.index))
        feature_count = int(merged.geometry.notna().sum())
        payload = _serialize_feature_collection_payload(
            merged,
            layer_id=layer.layer_id,
            output_layer_id=layer.output_layer_id,
            scope=layer.scope,
            scope_class=layer.scope_class,
        )
        table_frame = None

    resolved_unit_mapping = {
        column_name: unit_mapping.get(column_name, "non-unitized")
        for column_name in selected_columns
    }
    description_mapping = _column_description_mapping_for_selected_columns(
        selected_columns=selected_columns,
        unit_mapping=resolved_unit_mapping,
    )
    column_metadata = build_output_layer_column_metadata(
        source_layer_ids=source_layer_ids,
        selected_columns=selected_columns,
        unit_mapping=resolved_unit_mapping,
        description_mapping=description_mapping,
    )
    return (
        PreparedLayerPayload(
            output_layer_id=layer.output_layer_id,
            payload=payload,
            tabular_frame=table_frame,
            row_count=row_count,
            feature_count=feature_count,
            warnings=tuple(warnings),
        ),
        column_metadata,
    )

def _build_layer_frame_from_sources(
    *,
    wd: Path,
    layer: ResolvedLayerPlan,
    catalog_layer_raw: cabc.Mapping[str, object],
    request_plan: ResolvedExportPlan,
    dependency_entries: cabc.Sequence[object],
    units_mode: str,
) -> _LayerFrameResult:
    geometry_relpath = _layer_dependency_relpath(
        dependency_entries,
        dependency_role="geometry",
        dependency_id="geometry",
    )
    if geometry_relpath is None:
        raise FeaturesExportServiceError(
            "Geometry source is missing for requested export layer.",
            status_code=404,
            code="not_found",
            details=f"Unable to resolve geometry dependency for {layer.output_layer_id!r}.",
        )

    geometry_frame = _load_vector_dataframe(wd, geometry_relpath)
    join_contract = _as_mapping(catalog_layer_raw.get("join"))
    try:
        legacy_merged = build_legacy_merged_frame(
            wd=wd,
            layer_id=layer.layer_id,
            scope=layer.scope,
            catalog_layer_raw=catalog_layer_raw,
            dependency_entries=dependency_entries,
            geometry_relpath=geometry_relpath,
            geometry_frame=geometry_frame,
            join_contract=join_contract,
            merge_source_dataframe=_merge_source_dataframe,
        )
    except MaterializationContractError as exc:
        raise FeaturesExportServiceError(
            "Legacy layer materialization failed.",
            status_code=500,
            code="materialization_error",
            details=exc.details,
        ) from exc
    merged = legacy_merged.frame

    selected_columns, unit_mapping = _resolve_selected_columns(
        layer=layer,
        frame=merged,
        catalog_layer_raw=catalog_layer_raw,
        request_plan=request_plan,
        discovered_units=legacy_merged.discovered_units,
    )

    merged = _ensure_join_key_column(
        merged,
        join_contract=join_contract,
        catalog_layer_raw=catalog_layer_raw,
    )
    geometry_name = merged.geometry.name
    merged, unit_mapping = _apply_unit_conversions(
        wd=wd,
        frame=merged,
        selected_columns=selected_columns,
        unit_mapping=unit_mapping,
        units_mode=units_mode,
    )
    merged, selected_columns, unit_mapping = apply_unitized_column_suffixes(
        frame=merged,
        selected_columns=selected_columns,
        unit_mapping=unit_mapping,
        geometry_name=geometry_name,
        consolidated_join_key_column=_CONSOLIDATED_JOIN_KEY_COLUMN,
    )
    merged, selected_columns, unit_mapping = normalize_identity_output_columns(
        frame=merged,
        selected_columns=selected_columns,
        unit_mapping=unit_mapping,
        geometry_name=geometry_name,
        consolidated_join_key_column=_CONSOLIDATED_JOIN_KEY_COLUMN,
    )
    geometry_name = merged.geometry.name
    projection_columns: list[str] = []
    for column_name in selected_columns:
        if column_name in merged.columns and column_name != geometry_name:
            projection_columns.append(column_name)
    if _CONSOLIDATED_JOIN_KEY_COLUMN in merged.columns:
        projection_columns.append(_CONSOLIDATED_JOIN_KEY_COLUMN)
    merged = gpd.GeoDataFrame(
        merged[projection_columns + [geometry_name]],
        geometry=geometry_name,
        crs=merged.crs,
    )

    return _LayerFrameResult(
        layer=layer,
        frame=merged,
        selected_columns=tuple(column for column in projection_columns if column != _CONSOLIDATED_JOIN_KEY_COLUMN),
        unit_mapping=unit_mapping,
        warnings=legacy_merged.warnings,
    )


def _request_column_selection_payload(plan: ResolvedExportPlan) -> dict[str, dict[str, list[str]]]:
    payload: dict[str, dict[str, list[str]]] = {}
    for selection in plan.request.column_selection:
        selector_payload: dict[str, list[str]] = {}
        if selection.include is not None:
            selector_payload["include"] = list(selection.include)
        if selection.exclude is not None:
            selector_payload["exclude"] = list(selection.exclude)
        payload[selection.layer_id] = selector_payload
    return payload


def _resolve_selected_columns(
    *,
    layer: ResolvedLayerPlan,
    frame: pd.DataFrame,
    catalog_layer_raw: cabc.Mapping[str, object],
    request_plan: ResolvedExportPlan,
    discovered_units: cabc.Mapping[str, str] | None = None,
) -> tuple[tuple[str, ...], dict[str, str]]:
    return _resolve_selected_columns_helper(
        layer=layer,
        frame=frame,
        catalog_layer_raw=catalog_layer_raw,
        request_plan=request_plan,
        discovered_units=discovered_units,
        consolidated_join_key_column=_CONSOLIDATED_JOIN_KEY_COLUMN,
    )


def _column_description_mapping_for_selected_columns(
    *,
    selected_columns: cabc.Sequence[str],
    unit_mapping: cabc.Mapping[str, str],
    catalog_layer_raws: cabc.Sequence[cabc.Mapping[str, object]] = (),
) -> dict[str, str]:
    descriptions: dict[str, str] = {}

    for catalog_layer_raw in catalog_layer_raws:
        catalog_column_meta = _column_metadata_by_id_helper(catalog_layer_raw)
        for column_name in selected_columns:
            token = _as_string(column_name)
            if not token or token in descriptions:
                continue
            description_value = _as_string(
                _as_mapping(catalog_column_meta.get(token)).get("description")
            )
            if description_value:
                descriptions[token] = description_value

    for column_name in selected_columns:
        token = _as_string(column_name)
        if not token or token in descriptions:
            continue
        descriptions[token] = _default_column_description(
            token,
            unit_mapping.get(token),
        )

    return descriptions


def _default_column_description(column_name: str, unit_value: object) -> str:
    humanized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", column_name.replace("_", " "))
    humanized = re.sub(r"\s+", " ", humanized).strip()
    if not humanized:
        return "Exported column value."

    normalized = humanized.split(" ")
    normalized_tokens: list[str] = []
    for token in normalized:
        if token.lower() == "id":
            normalized_tokens.append("ID")
        elif token.lower() == "wepp":
            normalized_tokens.append("WEPP")
        else:
            normalized_tokens.append(token)
    sentence = " ".join(normalized_tokens)
    if sentence:
        sentence = f"{sentence[0].upper()}{sentence[1:]}"

    unit_token = _as_string(unit_value)
    if unit_token and unit_token != "non-unitized":
        return f"{sentence} ({unit_token})."
    return f"{sentence}."


def _required_identity_columns(catalog_layer_raw: cabc.Mapping[str, object]) -> set[str]:
    return _required_identity_columns_helper(catalog_layer_raw)


def _infer_display_unit_for_column(column_name: str) -> str:
    return _infer_display_unit_for_column_helper(column_name)


def _ensure_join_key_column(
    frame: gpd.GeoDataFrame,
    *,
    join_contract: cabc.Mapping[str, object],
    catalog_layer_raw: cabc.Mapping[str, object],
) -> gpd.GeoDataFrame:
    result = frame.copy()
    geometry_name = result.geometry.name
    identity_candidates: list[str] = []
    primary_key = _as_string(join_contract.get("primary_key"))
    if primary_key:
        identity_candidates.append(primary_key)
    identity_candidates.extend(_as_string_sequence(join_contract.get("fallback_keys")))
    geometry_contract = _as_mapping(catalog_layer_raw.get("geometry"))
    identity_candidates.extend(_as_string_sequence(geometry_contract.get("feature_id_keys")))

    selected_key = None
    for candidate in identity_candidates:
        if candidate and candidate in result.columns and candidate != geometry_name:
            selected_key = candidate
            break

    if selected_key is None:
        raise FeaturesExportServiceError(
            "Unable to resolve identity key for features export layer.",
            status_code=500,
            code="materialization_error",
            details=(
                f"identity_candidates={tuple(candidate for candidate in identity_candidates if candidate)!r}; "
                f"available_columns={tuple(column for column in result.columns if column != geometry_name)!r}"
            ),
        )

    result[_CONSOLIDATED_JOIN_KEY_COLUMN] = result[selected_key].map(_canonical_join_value)
    return result


def _layer_dependency_relpath(
    dependency_entries: cabc.Sequence[object],
    *,
    dependency_role: str,
    dependency_id: str,
) -> str | None:
    for entry in dependency_entries:
        role = _as_string(getattr(entry, "dependency_role", None))
        dep_id = _as_string(getattr(entry, "dependency_id", None))
        relpath = _as_string(getattr(entry, "relpath", None))
        if role == dependency_role and dep_id == dependency_id and relpath:
            return relpath
    return None


def _load_vector_dataframe(wd: Path, relpath: str) -> gpd.GeoDataFrame:
    source_path = materialize_path_if_archive(str(wd), relpath, purpose="export")
    try:
        frame = gpd.read_file(source_path)
    except (OSError, RuntimeError, ValueError) as exc:
        raise FeaturesExportServiceError(
            "Failed to read vector export source.",
            status_code=404,
            code="not_found",
            details=f"Unable to read vector source {relpath!r}: {exc}",
        ) from exc

    if frame.geometry.name not in frame.columns:
        raise FeaturesExportServiceError(
            "Vector export source is missing geometry column.",
            status_code=404,
            code="not_found",
            details=f"Vector source {relpath!r} did not expose a geometry column.",
        )
    return frame


def _dedupe_identity_selected_columns(columns: cabc.Sequence[str]) -> list[str]:
    return _dedupe_identity_selected_columns_helper(columns)


def _merge_source_dataframe(
    *,
    geometry_frame: gpd.GeoDataFrame,
    source_df: pd.DataFrame,
    source_id: str,
    join_contract: cabc.Mapping[str, object],
) -> tuple[gpd.GeoDataFrame, bool, dict[str, str]]:
    geometry_key, source_key = _resolve_join_keys(
        geometry_frame=geometry_frame,
        source_df=source_df,
        source_id=source_id,
        join_contract=join_contract,
    )
    if geometry_key is None or source_key is None:
        return geometry_frame, False, {}

    left = geometry_frame.copy()
    right = source_df.copy()

    left_join_key = "__features_export_join_key_left__"
    right_join_key = "__features_export_join_key_right__"

    left[left_join_key] = left[geometry_key].map(_canonical_join_value)
    right[right_join_key] = right[source_key].map(_canonical_join_value)

    duplicate_columns = [
        column for column in right.columns if column in left.columns and column not in {source_key}
    ]
    source_column_map: dict[str, str] = {column: column for column in right.columns}
    if duplicate_columns:
        rename_map: dict[str, str] = {}
        used_names = set(left.columns) | set(right.columns)
        source_suffix = _normalize_join_token(source_id) or "source"
        for column in duplicate_columns:
            renamed_column = _dedupe_column_name(
                f"{column}__{source_suffix}",
                used_names,
            )
            rename_map[column] = renamed_column
            used_names.add(renamed_column)
        right = right.rename(columns=rename_map)
        for source_column, resolved_column in rename_map.items():
            source_column_map[source_column] = resolved_column

    geometry_name = left.geometry.name
    left_non_geom = pd.DataFrame(left.drop(columns=[geometry_name]))
    right_non_geom = pd.DataFrame(right)
    left_rowid = "__features_export_left_rowid__"
    left_non_geom[left_rowid] = range(len(left_non_geom.index))

    joined = _duckdb_left_join_dataframe(
        left_df=left_non_geom,
        right_df=right_non_geom,
        left_key=left_join_key,
        right_key=right_join_key,
    )

    geometry_lookup = left.geometry.reset_index(drop=True)
    joined_geometry = joined[left_rowid].map(geometry_lookup)

    columns_to_drop = [left_join_key, right_join_key, left_rowid]
    if source_key != geometry_key and source_key in joined.columns and source_key not in left.columns:
        columns_to_drop.append(source_key)

    joined = joined.drop(columns=[column for column in columns_to_drop if column in joined.columns])
    joined[geometry_name] = joined_geometry.values
    merged_frame = gpd.GeoDataFrame(
        joined,
        geometry=geometry_name,
        crs=geometry_frame.crs,
    )
    return merged_frame, True, source_column_map


def _duckdb_left_join_dataframe(
    *,
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    left_key: str,
    right_key: str,
) -> pd.DataFrame:
    left_table = left_df.copy()
    right_table = right_df.copy()
    connection = duckdb.connect(database=":memory:")
    try:
        connection.register("left_table", left_table)
        connection.register("right_table", right_table)

        select_columns: list[str] = []
        for column_name in left_table.columns:
            select_columns.append(f'l.{_quote_ident(column_name)}')
        for column_name in right_table.columns:
            if column_name == right_key:
                continue
            select_columns.append(
                f'r.{_quote_ident(column_name)} AS {_quote_ident(column_name)}'
            )

        sql = (
            f"SELECT {', '.join(select_columns)} "
            f"FROM left_table l LEFT JOIN right_table r "
            f"ON l.{_quote_ident(left_key)} = r.{_quote_ident(right_key)}"
        )
        if "__features_export_left_rowid__" in left_table.columns:
            sql += " ORDER BY l.__features_export_left_rowid__"
        return connection.execute(sql).df()
    finally:
        connection.close()


def _quote_ident(identifier: str) -> str:
    escaped = str(identifier).replace('"', '""')
    return f'"{escaped}"'


def _resolve_join_keys(
    *,
    geometry_frame: gpd.GeoDataFrame,
    source_df: pd.DataFrame,
    source_id: str,
    join_contract: cabc.Mapping[str, object],
) -> tuple[str | None, str | None]:
    geometry_lookup = _normalized_column_lookup(geometry_frame.columns)
    source_lookup = _normalized_column_lookup(source_df.columns)

    candidate_tokens = _join_candidate_tokens(join_contract, source_id=source_id)
    for token in candidate_tokens:
        normalized = _normalize_join_token(token)
        if normalized in geometry_lookup and normalized in source_lookup:
            return geometry_lookup[normalized], source_lookup[normalized]

    fallback_tokens = ("wepp_id", "topaz_id", "chn_id", "channel_id", "id", "chn_enum")
    for token in fallback_tokens:
        normalized = _normalize_join_token(token)
        if normalized in geometry_lookup and normalized in source_lookup:
            return geometry_lookup[normalized], source_lookup[normalized]

    return None, None


def _join_candidate_tokens(
    join_contract: cabc.Mapping[str, object],
    *,
    source_id: str,
) -> tuple[str, ...]:
    tokens: list[str] = []
    seen: set[str] = set()

    source_key_map = _as_mapping(join_contract.get("source_key_map"))
    preferred_value = source_key_map.get(source_id)
    preferred_tokens = _as_string_sequence(preferred_value)
    primary_key = _as_string(join_contract.get("primary_key"))
    fallback_keys = _as_string_sequence(join_contract.get("fallback_keys"))

    for token in (*preferred_tokens, primary_key, *fallback_keys):
        if not token:
            continue
        normalized = _normalize_join_token(token)
        if normalized in seen:
            continue
        seen.add(normalized)
        tokens.append(token)

    return tuple(tokens)


def _normalized_column_lookup(columns: cabc.Iterable[object]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for column in columns:
        name = _as_string(column)
        if not name:
            continue
        normalized = _normalize_join_token(name)
        if not normalized or normalized in lookup:
            continue
        lookup[normalized] = name
    return lookup


def _dedupe_column_name(candidate: str, used_names: set[object]) -> str:
    base = candidate
    suffix = 2
    while candidate in used_names:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def _normalize_join_token(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch in string.ascii_lowercase + string.digits)


def _canonical_join_value(value: object) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass

    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return format(value, ".15g")

    text = str(value).strip()
    if not text:
        return None

    try:
        float_value = float(text)
    except ValueError:
        return text

    if float_value.is_integer():
        return str(int(float_value))
    return format(float_value, ".15g")


def _serialize_feature_collection_payload(
    frame: gpd.GeoDataFrame,
    *,
    layer_id: str,
    output_layer_id: str,
    scope: str,
    scope_class: str,
) -> str:
    feature_collection = json.loads(frame.to_json(drop_id=True))
    epsg_value = None
    if frame.crs is not None:
        try:
            epsg_value = frame.crs.to_epsg()
        except AttributeError:
            epsg_value = None

    payload: dict[str, object] = {
        "schema": "wepppy.features_export.feature_collection.v1",
        "layer_id": layer_id,
        "output_layer_id": output_layer_id,
        "scope": scope,
        "scope_class": scope_class,
        "feature_collection": feature_collection,
    }
    if isinstance(epsg_value, int):
        payload["crs_epsg"] = epsg_value

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _as_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, cabc.Mapping):
        return {}
    normalized: dict[str, object] = {}
    for key, item in value.items():
        key_text = _as_string(key)
        if not key_text:
            continue
        normalized[key_text] = item
    return normalized


def _layer_join_allows_non_unique_keys(catalog_layer_raw: cabc.Mapping[str, object]) -> bool:
    join_contract = _as_mapping(catalog_layer_raw.get("join"))
    allow_flag = join_contract.get("allow_non_unique_keys")
    return isinstance(allow_flag, bool) and allow_flag


def _as_string(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _as_string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        token = value.strip()
        return (token,) if token else ()
    if not isinstance(value, cabc.Sequence):
        return ()

    normalized: list[str] = []
    for item in value:
        token = _as_string(item)
        if token:
            normalized.append(token)
    return tuple(normalized)


def _request_uses_tabular_long_layout(plan: ResolvedExportPlan) -> bool:
    request = plan.request
    if request.format not in {"csv", "parquet"}:
        return False
    tabular = request.tabular
    if tabular is None:
        return False
    return str(tabular.temporal_layout or "").strip().lower() == "long"


def _request_uses_tabular_payload(plan: ResolvedExportPlan) -> bool:
    return plan.request.format in {"csv", "parquet"}


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
    return _artifact_metadata_from_cache_entry_helper(
        cache_entry,
        plan=plan,
        artifact_relpath=artifact_relpath,
        artifact_path=artifact_path,
    )


def _layer_outputs_from_cache_entry(
    cache_entry: dict[str, object],
    plan: ResolvedExportPlan,
    artifact_relpath: str,
    format_token: str,
) -> tuple[ExportedLayerArtifact, ...]:
    return _layer_outputs_from_cache_entry_helper(
        cache_entry,
        plan=plan,
        artifact_relpath=artifact_relpath,
        format_token=format_token,
    )


def _cache_entry_artifact_relpath(cache_entry: dict[str, object]) -> str | None:
    return _cache_entry_artifact_relpath_helper(cache_entry)


def _find_cache_entries_by_artifact_relpath(
    wd: Path,
    *,
    artifact_relpath: str,
) -> list[tuple[str, dict[str, object]]]:
    cache_index = load_cache_index(wd)
    entries_raw = cache_index.get("entries")
    if not isinstance(entries_raw, dict):
        return []

    matches: list[tuple[str, dict[str, object]]] = []
    for cache_key, raw_entry in entries_raw.items():
        if not isinstance(cache_key, str) or not cache_key:
            continue
        if not isinstance(raw_entry, dict):
            continue
        candidate_relpath = _cache_entry_artifact_relpath(raw_entry)
        if candidate_relpath != artifact_relpath:
            continue
        matches.append((cache_key, raw_entry))
    return matches


def _select_latest_cache_entry(
    matches: list[tuple[str, dict[str, object]]],
) -> tuple[str, dict[str, object]]:
    if not matches:
        raise ValueError("matches must be non-empty.")

    def _sort_key(item: tuple[str, dict[str, object]]) -> tuple[str, str]:
        cache_key, cache_entry = item
        updated_at_utc = str(cache_entry.get("updated_at_utc") or "").strip()
        return updated_at_utc, cache_key

    return max(matches, key=_sort_key)


def _parse_cache_key_components(cache_key: str) -> tuple[str, str]:
    request_hash, separator, dependency_fingerprint = cache_key.partition("+")
    request_hash_token = request_hash.strip()
    dependency_token = dependency_fingerprint.strip()
    if not separator or not request_hash_token or not dependency_token:
        return "", ""
    return request_hash_token, dependency_token


def _artifact_relpath_from_result(job_result: dict[str, object] | None) -> str | None:
    return _artifact_relpath_from_result_helper(job_result)


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
        return _is_valid_cached_geopackage_artifact(
            artifact_path=artifact_path,
            packaged_member_relpaths=_cache_entry_packaged_member_relpaths(cache_entry),
        )
    if normalized_format == "geodatabase":
        return _is_valid_cached_geodatabase_artifact(
            artifact_path=artifact_path,
        )
    if normalized_format == "csv":
        return _is_valid_cached_csv_artifact(
            artifact_path=artifact_path,
            packaged_member_relpaths=_cache_entry_packaged_member_relpaths(cache_entry),
        )

    return True


def _cache_entry_packaged_member_relpaths(cache_entry: dict[str, object]) -> tuple[str, ...]:
    raw = cache_entry.get("packaged_member_relpaths")
    if not isinstance(raw, list):
        return ()
    normalized: list[str] = []
    for entry in raw:
        if isinstance(entry, str) and entry.strip():
            normalized.append(entry.strip())
    return tuple(normalized)


def _is_valid_cached_geopackage_artifact(
    *,
    artifact_path: Path,
    packaged_member_relpaths: cabc.Sequence[str],
) -> bool:
    if artifact_path.suffix.lower() == ".zip":
        return _is_valid_cached_geopackage_zip(
            artifact_path=artifact_path,
            packaged_member_relpaths=packaged_member_relpaths,
        )
    return _is_valid_cached_geopackage_file(artifact_path)


def _is_valid_cached_geopackage_zip(
    *,
    artifact_path: Path,
    packaged_member_relpaths: cabc.Sequence[str],
) -> bool:
    try:
        with zipfile.ZipFile(artifact_path, mode="r") as zip_handle:
            names = tuple(zip_handle.namelist())
            if not names:
                return False

            candidate_members = [
                member
                for member in packaged_member_relpaths
                if member.lower().endswith(".gpkg") and member in names
            ]
            if not candidate_members:
                candidate_members = [
                    member for member in names if member.lower().endswith(".gpkg")
                ]
            if not candidate_members:
                return False

            with zip_handle.open(sorted(candidate_members)[0], mode="r") as handle:
                return handle.read(16).startswith(b"SQLite format 3\x00")
    except (OSError, zipfile.BadZipFile, KeyError):
        return False


def _is_valid_cached_geopackage_file(artifact_path: Path) -> bool:
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


def _is_valid_cached_geodatabase_artifact(
    *,
    artifact_path: Path,
) -> bool:
    if artifact_path.suffix.lower() != ".zip":
        return False
    return _is_valid_cached_geodatabase_zip(artifact_path)


def _is_valid_cached_geodatabase_zip(artifact_path: Path) -> bool:
    try:
        with zipfile.ZipFile(artifact_path, mode="r") as zip_handle:
            names = tuple(zip_handle.namelist())
            if not names:
                return False
            if artifact_path.name.lower().endswith(".gdb.zip"):
                return True
            lowered_names = tuple(name.lower() for name in names)
            if any(".gdb/" in name for name in lowered_names):
                return True
            if any(name.endswith(".gdbtable") for name in lowered_names):
                return True
            return False
    except (OSError, zipfile.BadZipFile):
        return False


def _is_valid_cached_csv_artifact(
    *,
    artifact_path: Path,
    packaged_member_relpaths: cabc.Sequence[str],
) -> bool:
    if artifact_path.suffix.lower() != ".zip":
        return artifact_path.suffix.lower() == ".csv"
    try:
        with zipfile.ZipFile(artifact_path, mode="r") as zip_handle:
            names = tuple(zip_handle.namelist())
            if not names:
                return False
            candidate_members = [
                member
                for member in packaged_member_relpaths
                if member.lower().endswith(".csv") and member in names
            ]
            if not candidate_members:
                candidate_members = [member for member in names if member.lower().endswith(".csv")]
            return bool(candidate_members)
    except (OSError, zipfile.BadZipFile):
        return False


def _bundle_filename(format_token: str) -> str:
    normalized = str(format_token or "").strip().lower()
    if normalized == "f_esri":
        normalized = "geodatabase"
    safe = _SAFE_TOKEN_PATTERN.sub("_", normalized).strip("._")
    if not safe:
        safe = "export"
    return f"features_export.{safe}.zip"


def _payload_member_sources(
    *,
    artifact: ExportArtifactMetadata,
    artifact_dir: Path,
) -> dict[str, Path]:
    if artifact.packaged_member_relpaths:
        member_sources: dict[str, Path] = {}
        artifact_path = Path(artifact.artifact_path).resolve()
        for member_relpath in artifact.packaged_member_relpaths:
            token = str(member_relpath or "").strip()
            if not token:
                continue
            source = (artifact_dir / token).resolve()
            if not source.exists() and artifact_path.name == Path(token).name and artifact_path.exists():
                source = artifact_path
            if not source.is_file():
                raise FeaturesExportServiceError(
                    "Writer output is missing an expected payload member file.",
                    status_code=500,
                    code="artifact_missing",
                    details=f"Missing payload member {token!r} for format {artifact.format!r}.",
                )
            member_sources[token] = source
        if member_sources:
            return member_sources

    artifact_path = Path(artifact.artifact_path).resolve()
    if not artifact_path.is_file():
        raise FeaturesExportServiceError(
            "Writer output artifact file is missing.",
            status_code=500,
            code="artifact_missing",
            details=f"Missing writer artifact at {artifact_path}.",
        )
    default_member = Path(str(artifact.artifact_relpath or artifact_path.name)).name
    if not default_member:
        default_member = artifact_path.name
    return {default_member: artifact_path}


def _cleanup_intermediate_writer_artifact(
    *,
    artifact: ExportArtifactMetadata,
    retained_sources: cabc.Sequence[Path],
) -> None:
    artifact_path = Path(artifact.artifact_path).resolve()
    retained = {Path(entry).resolve() for entry in retained_sources}
    if artifact_path in retained:
        return
    try:
        if artifact_path.is_file():
            artifact_path.unlink()
    except OSError:
        # Best-effort cleanup only; do not fail export completion.
        return


def _job_download_url(runid: str, config: str, job_id: str) -> str:
    return f"/rq-engine/api/runs/{runid}/{config}/export/features/job/{job_id}/download"


def _empty_publication_registry() -> dict[str, object]:
    return {
        "schema_version": FEATURES_EXPORT_PUBLICATION_SCHEMA_VERSION,
        "updated_at_utc": "",
        "profiles": {},
    }


def _normalize_publication_entry(
    canonical_profile: str,
    value: cabc.Mapping[str, object],
) -> dict[str, object]:
    return {
        "profile": canonical_profile,
        "job_id": str(value.get("job_id") or "").strip(),
        "artifact_id": str(value.get("artifact_id") or "").strip(),
        "artifact_relpath": str(value.get("artifact_relpath") or "").strip(),
        "manifest_relpath": str(value.get("manifest_relpath") or "").strip(),
        "format": str(value.get("format") or "").strip(),
        "request_hash": str(value.get("request_hash") or "").strip(),
        "dependency_fingerprint": str(value.get("dependency_fingerprint") or "").strip(),
        "cache_key": str(value.get("cache_key") or "").strip(),
        "published_at_utc": str(value.get("published_at_utc") or "").strip(),
    }


def _normalize_publication_registry(value: cabc.Mapping[str, object]) -> dict[str, object]:
    schema_version_raw = value.get("schema_version")
    try:
        schema_version = int(schema_version_raw)
    except (TypeError, ValueError) as exc:
        raise FeaturesExportServiceError(
            "Features export publication registry has invalid schema_version.",
            code="publication_registry_invalid",
            details=f"schema_version={schema_version_raw!r}",
        ) from exc

    if schema_version != FEATURES_EXPORT_PUBLICATION_SCHEMA_VERSION:
        raise FeaturesExportServiceError(
            "Unsupported features export publication registry schema version.",
            code="publication_registry_invalid",
            details=(
                f"Expected schema_version={FEATURES_EXPORT_PUBLICATION_SCHEMA_VERSION}, "
                f"received {schema_version}."
            ),
        )

    updated_at_utc_raw = value.get("updated_at_utc")
    updated_at_utc = (
        str(updated_at_utc_raw).strip()
        if isinstance(updated_at_utc_raw, str)
        else ""
    )

    normalized_profiles: dict[str, dict[str, object]] = {}
    profiles_raw = value.get("profiles")
    if isinstance(profiles_raw, cabc.Mapping):
        for raw_profile, raw_entry in profiles_raw.items():
            canonical_profile = normalize_published_profile_id(str(raw_profile))
            if canonical_profile is None:
                continue
            if not isinstance(raw_entry, cabc.Mapping):
                continue
            normalized_profiles[canonical_profile] = _normalize_publication_entry(
                canonical_profile,
                raw_entry,
            )

    return {
        "schema_version": FEATURES_EXPORT_PUBLICATION_SCHEMA_VERSION,
        "updated_at_utc": updated_at_utc,
        "profiles": normalized_profiles,
    }


def _write_publication_registry(wd: Path, registry: cabc.Mapping[str, object]) -> Path:
    normalized_registry = _normalize_publication_registry(registry)
    registry_path = _resolve_relpath(wd, FEATURES_EXPORT_PUBLISHED_INDEX_RELPATH)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = registry_path.with_name(f"{registry_path.name}.{uuid4().hex}.tmp")
    try:
        tmp_path.write_text(
            json.dumps(normalized_registry, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(registry_path)
    except OSError as exc:
        raise FeaturesExportServiceError(
            "Failed to write features export publication registry.",
            code="publication_registry_write_failed",
            details=str(exc),
        ) from exc
    return registry_path


def _stale_publication_error(profile: str, details: str) -> FeaturesExportServiceError:
    return FeaturesExportServiceError(
        "Published features export artifact is stale.",
        status_code=409,
        code="stale_publication",
        details=f"profile={profile}: {details}",
    )


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
    "FEATURES_EXPORT_ARTIFACT_README_NAME",
    "FEATURES_EXPORT_ARTIFACTS_RELPATH",
    "FEATURES_EXPORT_JOBS_RELPATH",
    "FEATURES_EXPORT_MANIFEST_NAME",
    "FEATURES_EXPORT_PUBLISHED_INDEX_RELPATH",
    "FEATURES_EXPORT_PUBLISHED_RELPATH",
    "FEATURES_EXPORT_PUBLICATION_SCHEMA_VERSION",
    "FEATURES_EXPORT_ROOT_RELPATH",
    "FeaturesExportServiceError",
    "FeaturesExportSubmission",
    "cache_entry_supports_cache_hit",
    "co_create_post_wepp_geodatabase_artifact",
    "execute_features_export",
    "load_publication_registry",
    "load_job_manifest",
    "normalize_published_profile_id",
    "publish_profile_execution_artifacts",
    "prepare_export_submission",
    "publish_profile_artifact",
    "resolve_download_artifact_path",
    "resolve_published_artifact_path",
    "resolve_published_profile_request",
]
