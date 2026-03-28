"""WP-4 service orchestration for features export execution and cache handling."""

from __future__ import annotations

import collections.abc as cabc
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import string
import re
from urllib.parse import quote
from uuid import uuid4

import duckdb
import geopandas as gpd
import pandas as pd

from wepppy.nodb.core import Watershed
from wepppy.nodb.unitizer import Unitizer
from wepppy.runtime_paths.materialize import materialize_path_if_archive

from .carrier_layer_materializer import materialize_carrier_layer_core
from .cache_rehydration import (
    artifact_metadata_from_cache_entry as _artifact_metadata_from_cache_entry_helper,
    artifact_relpath_from_result as _artifact_relpath_from_result_helper,
    cache_entry_artifact_relpath as _cache_entry_artifact_relpath_helper,
    layer_outputs_from_cache_entry as _layer_outputs_from_cache_entry_helper,
)
from .cache_key import CacheKeyParts, build_cache_key, get_cache_index_entry, upsert_cache_index_entry
from .catalog_loader import LayerCatalog, load_layer_catalog
from .column_selection import (
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
from .geometry_carriers import attach_geometry_once, build_canonical_geometry_carrier
from .join_planner import JOIN_KEY_COLUMN, MaterializationContractError
from .legacy_source_materializer import build_legacy_merged_frame
from .manifest import build_export_manifest, write_export_manifest
from .manifest_builder import build_output_layer_column_metadata
from .output_column_naming import apply_unitized_column_suffixes
from .planner import resolve_export_plan
from .tabular_temporal_layout import reshape_temporal_wide_to_long

FEATURES_EXPORT_ROOT_RELPATH = "export/features"
FEATURES_EXPORT_ARTIFACTS_RELPATH = "export/features/artifacts"
FEATURES_EXPORT_JOBS_RELPATH = "export/features/jobs"
FEATURES_EXPORT_MANIFEST_NAME = "manifest.json"
_GPKG_APPLICATION_ID = 0x47504B47
_CONSOLIDATED_JOIN_KEY_COLUMN = JOIN_KEY_COLUMN
_SAFE_TOKEN_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


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
    artifact = writer.write(
        ExportWriterRequest(
            plan=materialized_plan,
            layer_payloads=layer_payloads,
            artifact_dir=artifact_dir,
            artifact_basename="features_export",
        )
    )

    artifact_relpath = _to_relpath(wd, Path(artifact.artifact_path))
    generation_timestamp_utc = _utcnow_iso()

    manifest = build_export_manifest(
        plan=materialized_plan,
        artifact=artifact,
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
        request_column_selection_by_layer_id=_request_column_selection_payload(submission.plan),
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
        layer_inputs.append(
            LayerCarrierInput(
                layer_id=result.layer.layer_id,
                dataframe=result.frame,
                selected_columns=result.selected_columns,
                unit_mapping=result.unit_mapping,
            )
        )

    carrier_core = materialize_carrier_core(
        carrier_label=layer.output_layer_id,
        layer_inputs=layer_inputs,
        allow_non_unique_keys=layer.temporal_mode == "event",
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
        merged_table = merged_table.drop(columns=[_CONSOLIDATED_JOIN_KEY_COLUMN], errors="ignore")

        projection_columns = [column for column in selected_columns if column in merged_table.columns]
        selected_columns = tuple(_dedupe_identity_selected_columns(projection_columns))
        table_frame = pd.DataFrame(merged_table[list(selected_columns)]).copy()

        row_count = int(len(table_frame.index))
        feature_count = row_count

        column_metadata = build_output_layer_column_metadata(
            source_layer_ids=carrier_core.source_layer_ids,
            selected_columns=selected_columns,
            unit_mapping=unit_mapping,
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
        allow_non_unique_keys=layer.temporal_mode == "event",
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

    merged = merged.drop(columns=[_CONSOLIDATED_JOIN_KEY_COLUMN], errors="ignore")
    geometry_name = merged.geometry.name
    projection_columns = [column for column in selected_columns if column in merged.columns and column != geometry_name]
    selected_columns = tuple(_dedupe_identity_selected_columns(projection_columns))
    merged = gpd.GeoDataFrame(
        merged[list(selected_columns) + [geometry_name]],
        geometry=geometry_name,
        crs=merged.crs,
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

    column_metadata = build_output_layer_column_metadata(
        source_layer_ids=carrier_core.source_layer_ids,
        selected_columns=selected_columns,
        unit_mapping=unit_mapping,
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

    column_metadata = {
        "source_layer_ids": source_layer_ids,
        "selected_columns": selected_columns,
        "unit_mapping": {
            column_name: unit_mapping.get(column_name, "non-unitized")
            for column_name in selected_columns
        },
    }
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
    merged, selected_columns, unit_mapping = apply_unitized_column_suffixes(
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
