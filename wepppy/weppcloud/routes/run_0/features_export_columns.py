"""Discover and describe source columns for the run-page Features Export control."""

import pathlib
import re

try:
    import pyarrow.lib as _pyarrow_lib
    import pyarrow.parquet as _pyarrow_parquet
except ModuleNotFoundError:  # pragma: no cover - runtime image normally includes pyarrow
    _pyarrow_lib = None
    _pyarrow_parquet = None


if _pyarrow_lib is not None:
    _FEATURES_EXPORT_PARQUET_SCHEMA_EXCEPTIONS: tuple[type[Exception], ...] = (
        OSError,
        ValueError,
        _pyarrow_lib.ArrowException,
    )
else:  # pragma: no cover - pyarrow missing in non-runtime contexts
    _FEATURES_EXPORT_PARQUET_SCHEMA_EXCEPTIONS = (OSError, ValueError)


_FEATURES_EXPORT_INTERCHANGE_HEADING_RE = re.compile(r"^###\s+`([^`]+\.parquet)`\s*$")


def _infer_features_export_display_unit(column_id: str) -> str:
    token = str(column_id or "").strip().lower()
    if not token:
        return "non-unitized"

    suffix_units = [
        ("_mm", "mm"),
        ("_cm", "cm"),
        ("_m", "m"),
        ("_m2", "m2"),
        ("_m3", "m3"),
        ("_kg_ha", "kg/ha"),
        ("_kg_m2", "kg/m2"),
        ("_kg", "kg"),
        ("_ha", "ha"),
        ("_c", "C"),
        ("_cms", "cms"),
        ("_pct", "%"),
    ]
    for suffix, unit in suffix_units:
        if token.endswith(suffix):
            return unit

    if token.startswith("pct_") or token.endswith("_percent") or token.endswith("_percentage"):
        return "%"
    return "non-unitized"


def _features_export_column_label(column_id: str) -> str:
    token = str(column_id or "").strip()
    if not token:
        return ""
    if any(ch in token for ch in (" ", "-", "/", "%", ".")):
        return token
    return token.replace("_", " ")


def _features_export_column_match_key(column_id: str) -> str:
    token = str(column_id or "").strip().lower()
    if not token:
        return ""
    return re.sub(r"[^a-z0-9]+", "", token)


def _features_export_decode_metadata_value(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore").strip()
    if isinstance(value, str):
        return value.strip()
    return ""


def _features_export_metadata_lookup(metadata: dict, *keys: str) -> str:
    if not isinstance(metadata, dict):
        return ""
    for key in keys:
        byte_key = key.encode("utf-8")
        if byte_key in metadata:
            resolved = _features_export_decode_metadata_value(metadata.get(byte_key))
            if resolved:
                return resolved
        if key in metadata:
            resolved = _features_export_decode_metadata_value(metadata.get(key))
            if resolved:
                return resolved
    return ""


def _features_export_parse_markdown_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return []
    return [cell.strip() for cell in stripped.split("|")[1:-1]]


def _features_export_parse_interchange_readme(
    readme_path: pathlib.Path,
) -> dict[str, dict[str, dict[str, dict[str, str]]]]:
    if not readme_path.is_file():
        return {}

    try:
        lines = readme_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    parsed: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
    current_file = ""
    in_table = False
    for raw_line in lines:
        line = raw_line.strip()
        heading_match = _FEATURES_EXPORT_INTERCHANGE_HEADING_RE.match(line)
        if heading_match:
            current_file = heading_match.group(1).strip().lower()
            parsed.setdefault(current_file, {"exact": {}, "match": {}})
            in_table = False
            continue

        if not current_file:
            continue
        if line.lower() == "| column | type | units | description |":
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            in_table = False
            continue

        cells = _features_export_parse_markdown_table_row(line)
        if len(cells) < 4:
            continue
        if all(not cell or set(cell) <= {"-", ":"} for cell in cells):
            continue

        column_name = cells[0].strip()
        if not column_name or column_name.lower() == "column":
            continue

        doc: dict[str, str] = {"label": column_name}
        units = cells[2].strip()
        description = cells[3].strip()
        if units:
            doc["display_unit"] = units
        if description:
            doc["description"] = description

        file_docs = parsed[current_file]
        exact = file_docs.setdefault("exact", {})
        match = file_docs.setdefault("match", {})
        exact.setdefault(column_name, doc)
        match_key = _features_export_column_match_key(column_name)
        if match_key:
            match.setdefault(match_key, doc)
    return parsed


def _features_export_find_source_readme(source_path: pathlib.Path, wd_path: pathlib.Path) -> pathlib.Path | None:
    current = source_path.parent
    while True:
        candidate = current / "README.md"
        if candidate.is_file():
            return candidate
        if current == wd_path:
            return None
        if wd_path not in current.parents and current != wd_path:
            return None
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _features_export_lookup_readme_column_doc(
    readme_columns: dict[str, dict[str, dict[str, str]]] | None,
    column_id: str,
) -> dict[str, str]:
    if not isinstance(readme_columns, dict):
        return {}

    exact = readme_columns.get("exact")
    if isinstance(exact, dict):
        exact_doc = exact.get(column_id)
        if isinstance(exact_doc, dict):
            return dict(exact_doc)

    match = readme_columns.get("match")
    if isinstance(match, dict):
        key = _features_export_column_match_key(column_id)
        match_doc = match.get(key)
        if isinstance(match_doc, dict):
            return dict(match_doc)
    return {}


def _features_export_parquet_source_columns(
    path: pathlib.Path,
    *,
    readme_columns: dict[str, dict[str, dict[str, str]]] | None = None,
) -> list[dict]:
    if _pyarrow_parquet is None:
        return []

    try:
        schema = _pyarrow_parquet.read_schema(path)
    except _FEATURES_EXPORT_PARQUET_SCHEMA_EXCEPTIONS:
        return []

    columns: list[dict] = []
    for field in schema:
        column_id = str(field.name or "").strip()
        if not column_id:
            continue
        metadata = field.metadata if isinstance(field.metadata, dict) else {}
        readme_doc = _features_export_lookup_readme_column_doc(readme_columns, column_id)
        metadata_label = _features_export_metadata_lookup(metadata, "label", "display_name", "long_name")
        metadata_description = _features_export_metadata_lookup(metadata, "description", "desc")
        metadata_unit = _features_export_metadata_lookup(metadata, "units", "unit")
        readme_label = str(readme_doc.get("label") or "").strip()
        readme_description = str(readme_doc.get("description") or "").strip()
        readme_unit = str(readme_doc.get("display_unit") or "").strip()
        display_unit = metadata_unit or readme_unit or _infer_features_export_display_unit(column_id)
        columns.append(
            {
                "column_id": column_id,
                "label": metadata_label or readme_label or _features_export_column_label(column_id),
                "display_unit": display_unit,
                "description": metadata_description or readme_description,
                "default_selected": True,
            }
        )
    return columns


def _features_export_resolve_source_path(
    *,
    wd: pathlib.Path,
    source: dict,
    scenarios: list[dict],
    contrasts: list[dict],
    swat_catalog: dict,
) -> pathlib.Path | None:
    locator = source.get("locator") if isinstance(source.get("locator"), dict) else {}
    kind = str(locator.get("kind") or "").strip()
    value = str(locator.get("value") or "").strip()
    if not kind or not value:
        return None

    if kind == "relpath":
        return wd / value
    if kind != "path_template":
        return None

    latest_swat_run = str(swat_catalog.get("latest_run_id") or "latest").strip() or "latest"
    all_swat_tables = swat_catalog.get("all_tables", [])
    swat_table = ""
    if isinstance(all_swat_tables, list) and all_swat_tables:
        swat_table = str(all_swat_tables[0] or "").strip()

    context = {
        "scope_root": "output",
        "scenario_id": str(scenarios[0].get("id")) if scenarios else "",
        "contrast_id": str(contrasts[0].get("id")) if contrasts else "",
        "swat_run_id": latest_swat_run,
        "table_name": swat_table,
        "crs_token": "WGS",
    }
    try:
        resolved = value.format_map(context)
    except KeyError:
        return None
    return wd / resolved


def _features_export_discover_layer_columns(
    *,
    wd: str | None,
    raw_layer: dict,
    scenarios: list[dict],
    contrasts: list[dict],
    swat_catalog: dict,
) -> list[dict]:
    if not wd:
        return []

    wd_path = pathlib.Path(wd)
    if not wd_path.exists():
        return []

    discovered_by_id: dict[str, dict] = {}
    discovered_order: list[str] = []
    readme_cache: dict[pathlib.Path, dict[str, dict[str, dict[str, dict[str, str]]]]] = {}
    for source_entry in raw_layer.get("sources", []):
        if not isinstance(source_entry, dict):
            continue
        if str(source_entry.get("kind") or "").strip() != "parquet":
            continue
        source_path = _features_export_resolve_source_path(
            wd=wd_path,
            source=source_entry,
            scenarios=scenarios,
            contrasts=contrasts,
            swat_catalog=swat_catalog,
        )
        if source_path is None or not source_path.exists():
            continue
        readme_columns: dict[str, dict[str, dict[str, str]]] = {}
        readme_path = _features_export_find_source_readme(source_path, wd_path)
        if readme_path is not None:
            parsed_readme = readme_cache.get(readme_path)
            if parsed_readme is None:
                parsed_readme = _features_export_parse_interchange_readme(readme_path)
                readme_cache[readme_path] = parsed_readme
            readme_columns = parsed_readme.get(source_path.name.lower(), {})
        for column in _features_export_parquet_source_columns(source_path, readme_columns=readme_columns):
            column_id = str(column.get("column_id") or "").strip()
            if not column_id:
                continue
            existing = discovered_by_id.get(column_id)
            if existing is None:
                discovered_by_id[column_id] = dict(column)
                discovered_order.append(column_id)
                continue

            existing_description = str(existing.get("description") or "").strip()
            incoming_description = str(column.get("description") or "").strip()
            if not existing_description and incoming_description:
                existing["description"] = incoming_description

            existing_unit = str(existing.get("display_unit") or "").strip()
            incoming_unit = str(column.get("display_unit") or "").strip()
            if (
                (not existing_unit or existing_unit == "non-unitized")
                and incoming_unit
                and incoming_unit != "non-unitized"
            ):
                existing["display_unit"] = incoming_unit

            fallback_label = _features_export_column_label(column_id)
            existing_label = str(existing.get("label") or "").strip()
            incoming_label = str(column.get("label") or "").strip()
            if (
                (not existing_label or existing_label == fallback_label)
                and incoming_label
                and incoming_label != fallback_label
            ):
                existing["label"] = incoming_label
    return [discovered_by_id[column_id] for column_id in discovered_order]


def _features_export_column_contract(
    raw_layer: dict,
    *,
    discovered_columns: list[dict] | None = None,
) -> tuple[list[dict], set[str]]:
    join_contract = raw_layer.get("join") if isinstance(raw_layer.get("join"), dict) else {}
    geometry_contract = raw_layer.get("geometry") if isinstance(raw_layer.get("geometry"), dict) else {}
    measures = raw_layer.get("measures") if isinstance(raw_layer.get("measures"), dict) else {}
    explicit_columns = raw_layer.get("columns") if isinstance(raw_layer.get("columns"), list) else []
    columns = discovered_columns if discovered_columns else explicit_columns

    required_columns: set[str] = set()
    required_seen_keys: set[str] = set()

    def _add_required_column(candidate: str) -> None:
        token = str(candidate or "").strip()
        if not token:
            return
        dedupe_key = _features_export_column_match_key(token) or token.lower()
        if dedupe_key in required_seen_keys:
            return
        required_seen_keys.add(dedupe_key)
        required_columns.add(token)

    primary_key = str(join_contract.get("primary_key") or "").strip()
    if primary_key:
        _add_required_column(primary_key)
    for feature_key in geometry_contract.get("feature_id_keys", []):
        _add_required_column(str(feature_key or ""))

    normalized_columns: list[dict] = []
    seen_column_keys: set[str] = set()
    required_keys = {
        key
        for key in (_features_export_column_match_key(column_id) for column_id in required_columns)
        if key
    }
    for entry in columns:
        if not isinstance(entry, dict):
            continue
        column_id = str(entry.get("column_id") or "").strip()
        dedupe_key = _features_export_column_match_key(column_id) or column_id
        if not column_id or dedupe_key in seen_column_keys:
            continue
        seen_column_keys.add(dedupe_key)
        unit_meta = entry.get("unit") if isinstance(entry.get("unit"), dict) else {}
        is_required = column_id in required_columns or dedupe_key in required_keys
        display_unit = (
            str(entry.get("display_unit") or "").strip()
            or
            str(unit_meta.get("display_unit") or "").strip()
            or _infer_features_export_display_unit(column_id)
        )
        normalized_columns.append(
            {
                "column_id": column_id,
                "label": str(entry.get("label") or _features_export_column_label(column_id)),
                "description": str(entry.get("description") or "").strip(),
                "display_unit": display_unit,
                "required": is_required,
                "default_selected": bool(entry.get("default_selected", True) or is_required),
            }
        )

    if not normalized_columns:
        derived_columns: set[str] = set(required_columns)
        for measure in measures.get("optional", []):
            if isinstance(measure, str):
                token = measure.strip()
                if token:
                    derived_columns.add(token)
                continue
            if not isinstance(measure, dict):
                continue
            aliases = measure.get("key_aliases", [])
            if isinstance(aliases, list):
                for alias in aliases:
                    token = str(alias or "").strip()
                    if token:
                        derived_columns.add(token)
        for column_id in sorted(derived_columns):
            dedupe_key = _features_export_column_match_key(column_id) or column_id
            if dedupe_key in seen_column_keys:
                continue
            seen_column_keys.add(dedupe_key)
            is_required = column_id in required_columns or dedupe_key in required_keys
            normalized_columns.append(
                {
                    "column_id": column_id,
                    "label": _features_export_column_label(column_id),
                    "description": "",
                    "display_unit": _infer_features_export_display_unit(column_id),
                    "required": is_required,
                    "default_selected": is_required,
                }
            )

    for required_column in sorted(required_columns):
        dedupe_key = _features_export_column_match_key(required_column) or required_column
        if dedupe_key in seen_column_keys:
            continue
        seen_column_keys.add(dedupe_key)
        normalized_columns.append(
            {
                "column_id": required_column,
                "label": _features_export_column_label(required_column),
                "description": "",
                "display_unit": _infer_features_export_display_unit(required_column),
                "required": True,
                "default_selected": True,
            }
        )

    normalized_columns.sort(
        key=lambda item: (
            0 if item["required"] else 1,
            str(item["label"]).lower(),
            str(item["column_id"]).lower(),
        )
    )
    return normalized_columns, required_columns
