"""Cache-entry rehydration helpers for features export artifacts."""

from __future__ import annotations

import collections.abc as cabc

from .contracts import ResolvedExportPlan
from .exporters import ExportArtifactMetadata, ExportedLayerArtifact


def artifact_metadata_from_cache_entry(
    cache_entry: cabc.Mapping[str, object],
    *,
    plan: ResolvedExportPlan,
    artifact_relpath: str,
    artifact_path: str,
) -> ExportArtifactMetadata:
    """Build artifact metadata from one cached index entry."""

    format_token = str(cache_entry.get("artifact_format") or plan.request.format)
    layer_outputs = layer_outputs_from_cache_entry(
        cache_entry,
        plan=plan,
        artifact_relpath=artifact_relpath,
        format_token=format_token,
    )
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


def layer_outputs_from_cache_entry(
    cache_entry: cabc.Mapping[str, object],
    *,
    plan: ResolvedExportPlan,
    artifact_relpath: str,
    format_token: str,
) -> tuple[ExportedLayerArtifact, ...]:
    """Parse cached layer outputs; fall back to plan-derived outputs when malformed."""

    raw_layer_outputs = cache_entry.get("layer_outputs")
    if isinstance(raw_layer_outputs, list):
        parsed_outputs: list[ExportedLayerArtifact] = []
        for raw_entry in raw_layer_outputs:
            parsed = _parse_layer_output_entry(
                raw_entry,
                artifact_relpath=artifact_relpath,
                format_token=format_token,
            )
            if parsed is not None:
                parsed_outputs.append(parsed)

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


def cache_entry_artifact_relpath(cache_entry: cabc.Mapping[str, object]) -> str | None:
    """Resolve artifact relpath from cache entry payload."""

    artifact_relpath = cache_entry.get("artifact_relpath")
    if isinstance(artifact_relpath, str) and artifact_relpath.strip():
        return artifact_relpath.strip()

    artifact_paths = cache_entry.get("artifact_paths")
    if isinstance(artifact_paths, list) and artifact_paths:
        first = artifact_paths[0]
        if isinstance(first, str) and first.strip():
            return first.strip()

    return None


def artifact_relpath_from_result(job_result: cabc.Mapping[str, object] | None) -> str | None:
    """Resolve artifact relpath from one job result payload."""

    if not isinstance(job_result, cabc.Mapping):
        return None

    value = job_result.get("artifact_relpath")
    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def _parse_layer_output_entry(
    raw_entry: object,
    *,
    artifact_relpath: str,
    format_token: str,
) -> ExportedLayerArtifact | None:
    if not isinstance(raw_entry, cabc.Mapping):
        return None

    layer_id = _as_nonempty_string(raw_entry.get("layer_id"))
    output_layer_id = _as_nonempty_string(raw_entry.get("output_layer_id"))
    if layer_id is None or output_layer_id is None:
        return None

    scope = _as_nonempty_string(raw_entry.get("scope")) or "shared"
    scope_class = _as_nonempty_string(raw_entry.get("scope_class")) or "scope_invariant"
    format_value = _as_nonempty_string(raw_entry.get("format")) or format_token
    relpath_value = _as_nonempty_string(raw_entry.get("relpath")) or artifact_relpath

    return ExportedLayerArtifact(
        layer_id=layer_id,
        output_layer_id=output_layer_id,
        scope=scope,
        scope_class=scope_class,
        format=format_value,
        relpath=relpath_value,
        row_count=_optional_int(raw_entry.get("row_count")),
        feature_count=_optional_int(raw_entry.get("feature_count")),
    )


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
    if isinstance(value, str):
        token = value.strip()
        return (token,) if token else ()
    if not isinstance(value, cabc.Sequence):
        return ()

    normalized: list[str] = []
    for item in value:
        token = _as_nonempty_string(item)
        if token is not None:
            normalized.append(token)
    return tuple(normalized)


def _as_nonempty_string(value: object) -> str | None:
    if isinstance(value, str):
        token = value.strip()
        return token if token else None
    return None


__all__ = [
    "artifact_metadata_from_cache_entry",
    "artifact_relpath_from_result",
    "cache_entry_artifact_relpath",
    "layer_outputs_from_cache_entry",
]
