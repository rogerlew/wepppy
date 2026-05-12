"""Deterministic README generation for features export artifact bundles."""

from __future__ import annotations

import collections.abc as cabc
import json
import re

_WINDOWS_ABSOLUTE_PATH_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


def build_export_readme(
    *,
    manifest: cabc.Mapping[str, object],
    runid: str,
    config: str,
) -> str:
    """Build one deterministic artifact README from manifest metadata."""

    if not isinstance(manifest, cabc.Mapping):
        raise TypeError("manifest must be a mapping.")
    if not isinstance(runid, str) or not runid.strip():
        raise ValueError("runid must be a non-empty string.")
    if not isinstance(config, str) or not config.strip():
        raise ValueError("config must be a non-empty string.")

    normalized_manifest = _normalize_mapping(manifest)
    runid_token = runid.strip()
    config_token = config.strip()

    artifact = _mapping_value(normalized_manifest.get("artifact"))
    request = _mapping_value(normalized_manifest.get("request"))
    request_resolved = _mapping_value(request.get("resolved"))
    crs = _mapping_value(normalized_manifest.get("crs"))
    dependency_snapshot = _mapping_value(normalized_manifest.get("dependency_snapshot"))
    columns = _mapping_value(normalized_manifest.get("columns"))
    output_layer_metadata = _mapping_value(columns.get("output_layer_metadata"))

    layer_entries = _sorted_layer_entries(normalized_manifest.get("layers"))
    dependency_entries = _sorted_dependency_entries(dependency_snapshot.get("entries"))
    warnings = _sorted_warning_entries(normalized_manifest.get("warnings"))

    lines: list[str] = []
    lines.append("# Features Export Artifact Metadata")
    lines.append("")
    lines.extend(
        _render_export_summary(
            manifest=normalized_manifest,
            artifact=artifact,
            request_resolved=request_resolved,
            crs=crs,
            runid=runid_token,
            config=config_token,
        )
    )
    lines.append("")
    lines.extend(
        _render_standards_notes(
            artifact=artifact,
            crs=crs,
        )
    )
    lines.append("")
    lines.extend(_render_resolved_request_profile(request_resolved))
    lines.append("")
    lines.extend(
        _render_layer_inventory(
            layers=layer_entries,
            output_layer_metadata=output_layer_metadata,
        )
    )
    lines.append("")
    lines.extend(
        _render_column_and_unit_summary(
            layers=layer_entries,
            output_layer_metadata=output_layer_metadata,
        )
    )
    lines.append("")
    lines.extend(
        _render_dependency_lineage_summary(
            dependency_snapshot=dependency_snapshot,
            dependency_entries=dependency_entries,
        )
    )
    lines.append("")
    lines.extend(_render_warning_summary(warnings))
    lines.append("")
    lines.extend(_render_machine_readable_pointer())
    lines.append("")
    return "\n".join(lines)


def _render_export_summary(
    *,
    manifest: dict[str, object],
    artifact: dict[str, object],
    request_resolved: dict[str, object],
    crs: dict[str, object],
    runid: str,
    config: str,
) -> list[str]:
    packaged_member_relpaths = _string_list(artifact.get("packaged_member_relpaths"))
    member_summary = ", ".join(_sanitize_relpath(item) for item in packaged_member_relpaths)
    if not member_summary:
        member_summary = "(none)"

    rows = [
        ("Generated at (UTC)", _string_or_fallback(manifest.get("generated_at_utc"))),
        ("Run ID", runid),
        ("Config", config),
        ("Artifact ID", _string_or_fallback(manifest.get("artifact_id"))),
        ("Format", _string_or_fallback(artifact.get("format"))),
        ("Artifact bundle", _sanitize_relpath(_string_or_fallback(artifact.get("artifact_relpath")))),
        ("Cache hit", "true" if bool(manifest.get("cache_hit")) else "false"),
        ("Source job ID", _string_or_fallback(manifest.get("source_job_id"), fallback="(none)")),
        ("Units mode", _string_or_fallback(request_resolved.get("units"))),
        ("Requested CRS", _string_or_fallback(crs.get("requested_crs"))),
        ("Resolved CRS", _string_or_fallback(crs.get("resolved_crs"))),
        ("Resolved EPSG", _string_or_fallback(crs.get("resolved_epsg"), fallback="(unspecified)")),
        ("Packaged members", member_summary),
    ]

    lines = ["## Export summary", ""]
    lines.extend(_render_two_column_table(("Field", "Value"), rows))
    return lines


def _render_standards_notes(
    *,
    artifact: dict[str, object],
    crs: dict[str, object],
) -> list[str]:
    format_token = _string_or_fallback(artifact.get("format"), fallback="unknown").lower()
    resolved_crs = _string_or_fallback(crs.get("resolved_crs"), fallback="unknown").lower()

    notes = [
        "This README follows the features export metadata baseline aligned to FGDC CSDGM essentials and ISO 19115-1 orientation.",
        "Machine-readable provenance is defined by `manifest.json`; this README is a deterministic derivative for human review.",
    ]

    if format_token == "geojson":
        notes.append(
            "GeoJSON payload semantics follow RFC 7946; coordinate interpretation is longitude/latitude on WGS84."
        )
    elif format_token == "geoparquet":
        notes.append(
            "GeoParquet payload semantics follow GeoParquet metadata rules, including embedded CRS metadata in parquet schema metadata."
        )
    elif format_token == "geopackage":
        notes.append(
            "GeoPackage payload semantics follow OGC GeoPackage conventions and can be extended with `gpkg_metadata` tables."
        )
    elif format_token in {"csv", "parquet"}:
        notes.append(
            "Tabular payloads strip geometry and therefore rely on manifest CRS and layer metadata for spatial interpretation."
        )

    if resolved_crs == "wgs":
        notes.append("Resolved CRS mode is `wgs`.")
    elif resolved_crs == "utm":
        notes.append("Resolved CRS mode is `utm`.")

    lines = ["## Standards and interpretation notes", ""]
    for note in notes:
        lines.append(f"- {note}")
    return lines


def _render_resolved_request_profile(request_resolved: dict[str, object]) -> list[str]:
    lines = ["## Resolved request profile", ""]
    lines.append("Normalized request payload:")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(request_resolved, indent=2, sort_keys=True))
    lines.append("```")
    return lines


def _render_layer_inventory(
    *,
    layers: tuple[dict[str, object], ...],
    output_layer_metadata: dict[str, object],
) -> list[str]:
    rows: list[tuple[str, str, str, str, str, str]] = []
    for layer in layers:
        output_layer_id = _string_or_fallback(layer.get("output_layer_id"))
        metadata = _mapping_value(output_layer_metadata.get(output_layer_id))
        source_layer_ids = _string_list(metadata.get("source_layer_ids"))
        if not source_layer_ids:
            source_layer_ids = [_string_or_fallback(layer.get("layer_id"))]

        scope = _string_or_fallback(layer.get("scope"), fallback="shared")
        context = _string_or_fallback(layer.get("context"), fallback="base")
        scope_context = f"{scope} / {context}"

        rows.append(
            (
                output_layer_id,
                ", ".join(source_layer_ids),
                scope_context,
                _string_or_fallback(layer.get("row_count"), fallback="(n/a)"),
                _string_or_fallback(layer.get("feature_count"), fallback="(n/a)"),
                _sanitize_relpath(_string_or_fallback(layer.get("artifact_relpath"))),
            )
        )

    lines = ["## Layer inventory", ""]
    if not rows:
        lines.append("No layer metadata entries were recorded.")
        return lines

    lines.extend(
        _render_table(
            ("Output layer", "Source layer(s)", "Scope / context", "Rows", "Features", "Artifact member"),
            rows,
        )
    )
    return lines


def _render_column_and_unit_summary(
    *,
    layers: tuple[dict[str, object], ...],
    output_layer_metadata: dict[str, object],
) -> list[str]:
    lines = ["## Column and unit summary", ""]
    if not layers:
        lines.append("No column metadata entries were recorded.")
        return lines

    rendered_any = False
    for layer in layers:
        output_layer_id = _string_or_fallback(layer.get("output_layer_id"))
        metadata = _mapping_value(output_layer_metadata.get(output_layer_id))
        selected_columns = _string_list(metadata.get("selected_columns"))
        unit_mapping = _mapping_value(metadata.get("unit_mapping"))
        description_mapping = _mapping_value(metadata.get("description_mapping"))
        source_layer_ids = _string_list(metadata.get("source_layer_ids"))

        if (
            not selected_columns
            and not unit_mapping
            and not description_mapping
            and not source_layer_ids
        ):
            continue

        rendered_any = True
        lines.append(f"### {output_layer_id}")
        lines.append("")
        if source_layer_ids:
            lines.append(f"- Source layer ids: `{', '.join(source_layer_ids)}`")
            lines.append("")

        ordered_columns = _ordered_columns(selected_columns, unit_mapping)
        if not ordered_columns:
            lines.append("No selected columns were recorded.")
            lines.append("")
            continue

        rows = [
            (
                column_name,
                _string_or_fallback(unit_mapping.get(column_name), fallback="(unspecified)"),
                _string_or_fallback(description_mapping.get(column_name), fallback="(unspecified)"),
            )
            for column_name in ordered_columns
        ]
        lines.extend(_render_table(("Column", "Unit", "Description"), rows))
        lines.append("")

    if not rendered_any:
        lines.append("No column metadata entries were recorded.")

    return lines


def _render_dependency_lineage_summary(
    *,
    dependency_snapshot: dict[str, object],
    dependency_entries: tuple[dict[str, object], ...],
) -> list[str]:
    lines = ["## Dependency lineage summary", ""]
    snapshot_rows = [
        ("Dependency fingerprint", _string_or_fallback(dependency_snapshot.get("fingerprint"))),
        ("Catalog signature", _string_or_fallback(dependency_snapshot.get("catalog_signature"))),
    ]
    lines.extend(_render_two_column_table(("Field", "Value"), snapshot_rows))

    if not dependency_entries:
        lines.append("")
        lines.append("No dependency entries were recorded.")
        return lines

    grouped: dict[str, list[dict[str, object]]] = {}
    for entry in dependency_entries:
        role = _string_or_fallback(entry.get("dependency_role"), fallback="(unspecified)")
        grouped.setdefault(role, []).append(entry)

    for role in sorted(grouped):
        lines.append("")
        lines.append(f"### Role: {role}")
        lines.append("")
        rows: list[tuple[str, str, str, str, str, str, str]] = []
        for entry in grouped[role]:
            hash_marker = _string_or_fallback(entry.get("content_hash_marker"), fallback="")
            hash_value = _string_or_fallback(entry.get("content_hash_value"), fallback="")
            if hash_marker and hash_value:
                hash_summary = f"{hash_marker}:{hash_value}"
            elif hash_value:
                hash_summary = hash_value
            else:
                hash_summary = "(none)"

            rows.append(
                (
                    _string_or_fallback(entry.get("dependency_id"), fallback="(unspecified)"),
                    _string_or_fallback(entry.get("layer_id"), fallback="(unspecified)"),
                    _string_or_fallback(entry.get("output_layer_id"), fallback="(unspecified)"),
                    _sanitize_relpath(_string_or_fallback(entry.get("relpath"), fallback="(none)")),
                    "true" if bool(entry.get("exists")) else "false",
                    _string_or_fallback(entry.get("size"), fallback="(n/a)"),
                    hash_summary,
                )
            )

        lines.extend(
            _render_table(
                ("Dependency ID", "Layer", "Output layer", "Relpath", "Exists", "Size", "Hash"),
                rows,
            )
        )

    return lines


def _render_warning_summary(
    warnings: tuple[dict[str, object], ...],
) -> list[str]:
    lines = ["## Warning summary", ""]
    if not warnings:
        lines.append("No warnings were reported for this artifact.")
        return lines

    rows = [
        (
            _string_or_fallback(warning.get("code"), fallback="(unspecified)"),
            _string_or_fallback(warning.get("message")),
            _string_or_fallback(warning.get("layer_id"), fallback="(none)"),
            _string_or_fallback(warning.get("scope"), fallback="(none)"),
        )
        for warning in warnings
    ]
    lines.extend(_render_table(("Code", "Message", "Layer", "Scope"), rows))
    return lines


def _render_machine_readable_pointer() -> list[str]:
    return [
        "## Machine-readable contract pointer",
        "",
        "`manifest.json` is the canonical machine-readable provenance and metadata contract for this artifact.",
    ]


def _render_two_column_table(
    headers: tuple[str, str],
    rows: cabc.Sequence[tuple[str, str]],
) -> list[str]:
    return _render_table(headers, rows)


def _render_table(
    headers: cabc.Sequence[str],
    rows: cabc.Sequence[cabc.Sequence[str]],
) -> list[str]:
    rendered: list[str] = []
    rendered.append(f"| {' | '.join(_escape_markdown_cell(header) for header in headers)} |")
    rendered.append(f"| {' | '.join('---' for _ in headers)} |")
    for row in rows:
        rendered.append(f"| {' | '.join(_escape_markdown_cell(cell) for cell in row)} |")
    return rendered


def _normalize_mapping(value: cabc.Mapping[str, object]) -> dict[str, object]:
    serialized = json.dumps(dict(value), sort_keys=True, separators=(",", ":"))
    parsed = json.loads(serialized)
    if not isinstance(parsed, dict):
        raise TypeError("manifest must normalize to a dict.")
    return parsed


def _mapping_value(value: object) -> dict[str, object]:
    if not isinstance(value, cabc.Mapping):
        return {}
    serialized = json.dumps(dict(value), sort_keys=True, separators=(",", ":"))
    parsed = json.loads(serialized)
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _string_list(value: object) -> list[str]:
    if not isinstance(value, cabc.Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    resolved: list[str] = []
    for item in value:
        if isinstance(item, str):
            token = item.strip()
            if token:
                resolved.append(token)
    return resolved


def _string_or_fallback(value: object, *, fallback: str = "(unknown)") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        token = value.strip()
        return token if token else fallback
    return str(value)


def _ordered_columns(selected_columns: list[str], unit_mapping: dict[str, object]) -> tuple[str, ...]:
    ordered: list[str] = []
    for column_name in selected_columns:
        if column_name not in ordered:
            ordered.append(column_name)

    extras = sorted(
        column_name
        for column_name in unit_mapping
        if isinstance(column_name, str) and column_name not in ordered
    )
    ordered.extend(extras)
    return tuple(ordered)


def _sorted_layer_entries(value: object) -> tuple[dict[str, object], ...]:
    if not isinstance(value, cabc.Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    normalized = [_mapping_value(entry) for entry in value if isinstance(entry, cabc.Mapping)]
    ordered = sorted(
        normalized,
        key=lambda item: (
            _string_or_fallback(item.get("output_layer_id"), fallback=""),
            _string_or_fallback(item.get("layer_id"), fallback=""),
        ),
    )
    return tuple(ordered)


def _sorted_dependency_entries(value: object) -> tuple[dict[str, object], ...]:
    if not isinstance(value, cabc.Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    normalized = [_mapping_value(entry) for entry in value if isinstance(entry, cabc.Mapping)]
    ordered = sorted(
        normalized,
        key=lambda item: (
            _string_or_fallback(item.get("dependency_role"), fallback=""),
            _string_or_fallback(item.get("layer_id"), fallback=""),
            _string_or_fallback(item.get("output_layer_id"), fallback=""),
            _string_or_fallback(item.get("dependency_id"), fallback=""),
            _string_or_fallback(item.get("relpath"), fallback=""),
        ),
    )
    return tuple(ordered)


def _sorted_warning_entries(value: object) -> tuple[dict[str, object], ...]:
    if not isinstance(value, cabc.Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    normalized = [_mapping_value(entry) for entry in value if isinstance(entry, cabc.Mapping)]
    ordered = sorted(
        normalized,
        key=lambda item: (
            _string_or_fallback(item.get("code"), fallback=""),
            _string_or_fallback(item.get("message"), fallback=""),
            _string_or_fallback(item.get("layer_id"), fallback=""),
            _string_or_fallback(item.get("scope"), fallback=""),
        ),
    )
    return tuple(ordered)


def _sanitize_relpath(value: str) -> str:
    token = value.strip()
    if not token:
        return "(none)"
    if token.startswith("/") or token.startswith("\\") or _WINDOWS_ABSOLUTE_PATH_PATTERN.match(token):
        return "[redacted-absolute-path]"
    return token


def _escape_markdown_cell(value: object) -> str:
    text = _string_or_fallback(value, fallback="")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", "<br>")
    text = text.replace("|", "\\|")
    return text


__all__ = ["build_export_readme"]
