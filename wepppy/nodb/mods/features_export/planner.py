"""Pure request normalization and deterministic planning for features export."""

from __future__ import annotations

import re
import collections.abc as cabc

from .catalog_loader import CatalogLayer, LayerCatalog
from .contracts import (
    DEFAULT_TABULAR_TEMPORAL_LAYOUT,
    DEFAULT_CRS,
    DEFAULT_OUTPUT_SCOPES,
    DEFAULT_SWAT_RUN_ID,
    FORMAT_ALIASES,
    ExportRequest,
    ExportWarning,
    FeaturesExportValidationError,
    LayerColumnSelection,
    NormalizedExportRequest,
    NormalizedSwatTables,
    NormalizedTabularRequest,
    NormalizedTemporalEvent,
    NormalizedTemporalRequest,
    ResolvedExportPlan,
    ResolvedLayerPlan,
    SUPPORTED_CRS,
    SUPPORTED_EVENT_SELECTORS,
    SUPPORTED_FORMATS,
    SUPPORTED_OUTPUT_SCOPES,
    SUPPORTED_TABULAR_TEMPORAL_LAYOUTS,
    SUPPORTED_TEMPORAL_MODES,
    SUPPORTED_UNITS,
    SUPPORTED_YEAR_SELECTIONS,
    TemporalLayerMode,
    ValidationIssue,
    WARNING_LAYER_UNAVAILABLE,
    WARNING_SCOPE_NOT_APPLICABLE,
)

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_OMNI_SCENARIO_LAYER_BY_BASE: dict[str, str] = {
    "wepp.summary.hillslopes": "omni.scenarios.hillslopes",
}
_OMNI_CONTRAST_LAYER_BY_BASE: dict[str, str] = {
    "wepp.summary.hillslopes": "omni.contrasts.hillslopes",
}


def normalize_export_request(
    request: ExportRequest | cabc.Mapping[str, object],
    catalog: LayerCatalog,
) -> NormalizedExportRequest:
    """Normalize request payload tokens and enforce planner validation contracts."""

    payload = _as_request_mapping(request)
    errors: list[ValidationIssue] = []

    format_token = _normalize_required_enum(
        payload.get("format"),
        path="format",
        allowed=SUPPORTED_FORMATS,
        errors=errors,
        aliases=FORMAT_ALIASES,
    )
    units_token = _normalize_required_enum(
        payload.get("units"),
        path="units",
        allowed=SUPPORTED_UNITS,
        errors=errors,
    )

    crs_token = DEFAULT_CRS
    if "crs" in payload and payload.get("crs") is not None:
        parsed_crs = _normalize_required_enum(
            payload.get("crs"),
            path="crs",
            allowed=SUPPORTED_CRS,
            errors=errors,
        )
        if parsed_crs is not None:
            crs_token = parsed_crs

    normalized_layers = _normalize_layers(payload.get("layers"), catalog, errors=errors)
    normalized_output_scopes = _normalize_output_scopes(payload.get("output_scopes"), errors=errors)

    scenarios = _normalize_selector_array(payload.get("scenarios"), path="scenarios", errors=errors)
    contrast_ids = _normalize_selector_array(payload.get("contrast_ids"), path="contrast_ids", errors=errors)

    scenario_alias = _optional_string(payload.get("scenario"), path="scenario", errors=errors)
    contrast_alias = _optional_string(payload.get("contrast_id"), path="contrast_id", errors=errors)
    if scenario_alias is not None:
        scenarios = sorted(set([*scenarios, scenario_alias]))
    if contrast_alias is not None:
        contrast_ids = sorted(set([*contrast_ids, contrast_alias]))

    if scenarios and contrast_ids:
        errors.append(
            ValidationIssue(
                code="mutually_exclusive",
                message="scenarios and contrast_ids are mutually exclusive.",
                path="scenarios",
            )
        )

    swat_run_id = _optional_string(payload.get("swat_run_id"), path="swat_run_id", errors=errors)
    if swat_run_id is None:
        swat_run_id = DEFAULT_SWAT_RUN_ID

    swat_tables = _normalize_swat_tables(payload.get("swat_tables"), errors=errors)
    temporal = _normalize_temporal(
        payload.get("temporal"),
        selected_layers=normalized_layers,
        catalog=catalog,
        errors=errors,
    )
    tabular = _normalize_tabular(
        payload.get("tabular"),
        format_token=format_token,
        selected_layers=normalized_layers,
        temporal=temporal,
        catalog=catalog,
        errors=errors,
    )
    column_selection = _normalize_column_selection(
        payload.get("column_selection"),
        selected_layers=normalized_layers,
        catalog=catalog,
        errors=errors,
    )

    _validate_omni_selector_rules(
        normalized_layers,
        scenarios=tuple(scenarios),
        contrast_ids=tuple(contrast_ids),
        catalog=catalog,
        errors=errors,
    )

    if errors:
        raise FeaturesExportValidationError(errors)

    return NormalizedExportRequest(
        format=format_token,
        units=units_token,
        layers=tuple(normalized_layers),
        crs=crs_token,
        output_scopes=tuple(normalized_output_scopes),
        scenarios=tuple(scenarios),
        contrast_ids=tuple(contrast_ids),
        swat_run_id=swat_run_id,
        swat_tables=swat_tables,
        temporal=temporal,
        column_selection=tuple(column_selection),
        tabular=tabular,
    )


def resolve_export_plan(
    request: ExportRequest | cabc.Mapping[str, object],
    catalog: LayerCatalog,
) -> ResolvedExportPlan:
    """Build a deterministic export plan from a normalized request and layer catalog."""

    normalized_request = normalize_export_request(request, catalog)
    warnings: list[ExportWarning] = []
    resolved_layers: list[ResolvedLayerPlan] = []

    for layer_id in normalized_request.layers:
        layer = catalog.layer_index[layer_id]
        effective_mode = _effective_temporal_mode_for_layer(
            layer_id,
            normalized_request.temporal,
            layer_temporal_supported_modes=layer.temporal_supported_modes,
        )
        if not _layer_supports_temporal(layer, effective_mode, normalized_request.temporal):
            warnings.append(
                ExportWarning(
                    code=WARNING_LAYER_UNAVAILABLE,
                    layer_id=layer.layer_id,
                    message=(
                        f"Layer {layer.layer_id!r} is incompatible with temporal mode "
                        f"{effective_mode!r}."
                    ),
                )
            )
            continue

        resolved_layers.extend(
            _resolve_layer_for_context(
                layer=layer,
                layer_id=layer.layer_id,
                effective_mode=effective_mode,
                context="base",
                selector_id=None,
                output_scopes=normalized_request.output_scopes,
                warnings=warnings,
            )
        )

    resolved_layers.extend(
        _resolve_omni_context_layers(
            request=normalized_request,
            catalog=catalog,
            warnings=warnings,
        )
    )

    if not resolved_layers:
        raise FeaturesExportValidationError(
            [
                ValidationIssue(
                    code="no_exportable_layers",
                    message=(
                        "No requested layers remain exportable after applying selector compatibility rules."
                    ),
                    path="layers",
                )
            ]
        )

    resolved_layers.sort(key=lambda item: item.output_layer_id)

    return ResolvedExportPlan(
        catalog_version=catalog.metadata.catalog_version,
        schema_version=catalog.metadata.schema_version,
        request=normalized_request,
        layers=tuple(resolved_layers),
        warnings=tuple(warnings),
    )


def _resolve_omni_context_layers(
    *,
    request: NormalizedExportRequest,
    catalog: LayerCatalog,
    warnings: list[ExportWarning],
) -> list[ResolvedLayerPlan]:
    resolved: list[ResolvedLayerPlan] = []

    if request.scenarios:
        omni_layer_ids = _resolve_omni_layer_ids(
            request=request,
            catalog=catalog,
            context="scenario",
        )
        for scenario_id in request.scenarios:
            for layer_id in omni_layer_ids:
                layer = catalog.layer_index[layer_id]
                effective_mode = _effective_temporal_mode_for_layer(
                    layer_id,
                    request.temporal,
                    layer_temporal_supported_modes=layer.temporal_supported_modes,
                )
                if not _layer_supports_temporal(layer, effective_mode, request.temporal):
                    warnings.append(
                        ExportWarning(
                            code=WARNING_LAYER_UNAVAILABLE,
                            layer_id=layer.layer_id,
                            message=(
                                f"Layer {layer.layer_id!r} is incompatible with temporal mode "
                                f"{effective_mode!r} for scenario {scenario_id!r}."
                            ),
                        )
                    )
                    continue
                resolved.extend(
                    _resolve_layer_for_context(
                        layer=layer,
                        layer_id=layer.layer_id,
                        effective_mode=effective_mode,
                        context="scenario",
                        selector_id=scenario_id,
                        output_scopes=request.output_scopes,
                        warnings=warnings,
                    )
                )

    if request.contrast_ids:
        omni_layer_ids = _resolve_omni_layer_ids(
            request=request,
            catalog=catalog,
            context="contrast",
        )
        for contrast_id in request.contrast_ids:
            for layer_id in omni_layer_ids:
                layer = catalog.layer_index[layer_id]
                effective_mode = _effective_temporal_mode_for_layer(
                    layer_id,
                    request.temporal,
                    layer_temporal_supported_modes=layer.temporal_supported_modes,
                )
                if not _layer_supports_temporal(layer, effective_mode, request.temporal):
                    warnings.append(
                        ExportWarning(
                            code=WARNING_LAYER_UNAVAILABLE,
                            layer_id=layer.layer_id,
                            message=(
                                f"Layer {layer.layer_id!r} is incompatible with temporal mode "
                                f"{effective_mode!r} for contrast {contrast_id!r}."
                            ),
                        )
                    )
                    continue
                resolved.extend(
                    _resolve_layer_for_context(
                        layer=layer,
                        layer_id=layer.layer_id,
                        effective_mode=effective_mode,
                        context="contrast",
                        selector_id=contrast_id,
                        output_scopes=request.output_scopes,
                        warnings=warnings,
                    )
                )

    return resolved


def _resolve_omni_layer_ids(
    *,
    request: NormalizedExportRequest,
    catalog: LayerCatalog,
    context: str,
) -> tuple[str, ...]:
    if context not in {"scenario", "contrast"}:
        return ()

    expected_family = "omni_scenarios" if context == "scenario" else "omni_contrasts"
    selected_direct = [
        layer_id
        for layer_id in request.layers
        if catalog.layer_index[layer_id].family == expected_family
    ]
    if selected_direct:
        return tuple(sorted(set(selected_direct)))

    mapping = _OMNI_SCENARIO_LAYER_BY_BASE if context == "scenario" else _OMNI_CONTRAST_LAYER_BY_BASE
    derived: list[str] = []
    for layer_id in request.layers:
        mapped = mapping.get(layer_id)
        if mapped and mapped in catalog.layer_index:
            derived.append(mapped)
    return tuple(sorted(set(derived)))


def _resolve_layer_for_context(
    *,
    layer: CatalogLayer,
    layer_id: str,
    effective_mode: str | None,
    context: str,
    selector_id: str | None,
    output_scopes: tuple[str, ...],
    warnings: list[ExportWarning],
) -> list[ResolvedLayerPlan]:
    resolved: list[ResolvedLayerPlan] = []

    if layer.scope_class == "scope_aware":
        scopes = output_scopes
    else:
        scopes = ("shared",)
        if "roads" in output_scopes:
            warnings.append(
                ExportWarning(
                    code=WARNING_SCOPE_NOT_APPLICABLE,
                    layer_id=layer.layer_id,
                    scope="roads",
                    message=(
                        f"Layer {layer.layer_id!r} is scope-invariant; "
                        "roads scope is not separately applicable."
                    ),
                )
            )

    for scope in scopes:
        output_layer_id = _resolved_output_layer_id(
            context=context,
            selector_id=selector_id,
            scope=scope,
            layer_id=layer_id,
        )
        resolved.append(
            ResolvedLayerPlan(
                layer_id=layer_id,
                family=layer.family,
                scope_class=layer.scope_class,
                scope=scope,
                output_layer_id=output_layer_id,
                temporal_mode=effective_mode,
                context=context,
                selector_id=selector_id,
                carrier_layer=_carrier_for_layer(layer),
            )
        )

    return resolved


def _resolved_output_layer_id(
    *,
    context: str,
    selector_id: str | None,
    scope: str,
    layer_id: str,
) -> str:
    if context == "base":
        return f"{scope}__{layer_id}"

    selector_token = selector_id if selector_id is not None else "unknown"
    return f"{context}-{selector_token}__{scope}__{layer_id}"


def _carrier_for_layer(layer: CatalogLayer) -> str | None:
    geometry = layer.raw.get("geometry") if isinstance(layer.raw, cabc.Mapping) else None
    if not isinstance(geometry, cabc.Mapping):
        return None

    locator = geometry.get("locator")
    locator_value = ""
    if isinstance(locator, cabc.Mapping):
        value = locator.get("value")
        if isinstance(value, str):
            locator_value = value.lower()

    geometry_type = str(geometry.get("type") or "").lower()
    if "channel" in locator_value or geometry_type == "line":
        return "chan_map-channels"
    if "subwta" in locator_value or geometry_type == "polygon":
        return "sbs_map-subcatchments"
    return None


def _effective_temporal_mode_for_layer(
    layer_id: str,
    temporal: NormalizedTemporalRequest | None,
    *,
    layer_temporal_supported_modes: cabc.Sequence[str] | None = None,
) -> str | None:
    if temporal is None:
        return None
    if not layer_temporal_supported_modes:
        return None
    return temporal.mode_for_layer(layer_id)


def _as_request_mapping(request: ExportRequest | cabc.Mapping[str, object]) -> cabc.Mapping[str, object]:
    if isinstance(request, cabc.Mapping):
        return request
    if isinstance(request, ExportRequest):
        payload: dict[str, object] = {
            "format": request.format,
            "units": request.units,
            "layers": list(request.layers),
        }
        if request.crs is not None:
            payload["crs"] = request.crs
        if request.output_scopes is not None:
            payload["output_scopes"] = list(request.output_scopes)
        if request.scenarios is not None:
            payload["scenarios"] = list(request.scenarios)
        if request.contrast_ids is not None:
            payload["contrast_ids"] = list(request.contrast_ids)
        if request.scenario is not None:
            payload["scenario"] = request.scenario
        if request.contrast_id is not None:
            payload["contrast_id"] = request.contrast_id
        if request.swat_run_id is not None:
            payload["swat_run_id"] = request.swat_run_id
        if request.swat_tables is not None:
            swat_tables: dict[str, object] = {}
            if request.swat_tables.include is not None:
                swat_tables["include"] = list(request.swat_tables.include)
            if request.swat_tables.exclude is not None:
                swat_tables["exclude"] = list(request.swat_tables.exclude)
            payload["swat_tables"] = swat_tables
        if request.temporal is not None:
            temporal: dict[str, object] = {}
            if request.temporal.mode is not None:
                temporal["mode"] = request.temporal.mode
            if request.temporal.layer_modes:
                temporal["layer_modes"] = {
                    item.layer_id: item.mode for item in request.temporal.layer_modes
                }
            if request.temporal.year_selection is not None:
                temporal["year_selection"] = request.temporal.year_selection
            if request.temporal.exclude_yr_indxs:
                temporal["exclude_yr_indxs"] = list(request.temporal.exclude_yr_indxs)
            if request.temporal.event is not None:
                temporal_event: dict[str, object] = {"selector": request.temporal.event.selector}
                if request.temporal.event.dates:
                    temporal_event["dates"] = list(request.temporal.event.dates)
                if request.temporal.event.return_periods:
                    temporal_event["return_periods"] = list(request.temporal.event.return_periods)
                temporal["event"] = temporal_event
            payload["temporal"] = temporal
        if request.column_selection is not None:
            payload["column_selection"] = {
                selection.layer_id: selection.to_mapping() for selection in request.column_selection
            }
        if request.tabular is not None:
            tabular: dict[str, object] = {}
            if request.tabular.concatenate_tables is not None:
                tabular["concatenate_tables"] = bool(request.tabular.concatenate_tables)
            if request.tabular.temporal_layout is not None:
                tabular["temporal_layout"] = request.tabular.temporal_layout
            payload["tabular"] = tabular
        return payload
    raise TypeError(
        "request must be a mapping payload or ExportRequest, "
        f"received {type(request).__name__}."
    )


def _normalize_layers(
    value: object,
    catalog: LayerCatalog,
    *,
    errors: list[ValidationIssue],
) -> list[str]:
    if not isinstance(value, list):
        errors.append(
            ValidationIssue(
                code="invalid_type",
                message="layers must be a non-empty array of layer identifiers.",
                path="layers",
            )
        )
        return []
    if not value:
        errors.append(
            ValidationIssue(code="missing_field", message="layers must not be empty.", path="layers")
        )
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for index, entry in enumerate(value):
        if not isinstance(entry, str) or not entry.strip():
            errors.append(
                ValidationIssue(
                    code="invalid_type",
                    message="layer id entries must be non-empty strings.",
                    path=f"layers[{index}]",
                )
            )
            continue
        layer_id = entry.strip()
        if layer_id not in seen:
            seen.add(layer_id)
            normalized.append(layer_id)

    unknown = sorted(layer_id for layer_id in normalized if layer_id not in catalog.layer_index)
    if unknown:
        errors.append(
            ValidationIssue(
                code="unknown_layer_id",
                message=f"Unknown layer id(s): {unknown}.",
                path="layers",
            )
        )
    return sorted(normalized)


def _normalize_output_scopes(
    value: object,
    *,
    errors: list[ValidationIssue],
) -> list[str]:
    if value is None:
        return list(DEFAULT_OUTPUT_SCOPES)
    if not isinstance(value, list):
        errors.append(
            ValidationIssue(
                code="invalid_type",
                message="output_scopes must be an array of scope tokens.",
                path="output_scopes",
            )
        )
        return list(DEFAULT_OUTPUT_SCOPES)
    if not value:
        errors.append(
            ValidationIssue(
                code="missing_field",
                message="output_scopes must not be empty when provided.",
                path="output_scopes",
            )
        )
        return list(DEFAULT_OUTPUT_SCOPES)

    seen: set[str] = set()
    for index, entry in enumerate(value):
        if not isinstance(entry, str) or not entry.strip():
            errors.append(
                ValidationIssue(
                    code="invalid_type",
                    message="output_scopes entries must be non-empty strings.",
                    path=f"output_scopes[{index}]",
                )
            )
            continue
        token = entry.strip().lower()
        if token not in SUPPORTED_OUTPUT_SCOPES:
            errors.append(
                ValidationIssue(
                    code="invalid_enum",
                    message=(
                        f"Unsupported output scope {entry!r}; supported values are "
                        f"{list(SUPPORTED_OUTPUT_SCOPES)!r}."
                    ),
                    path=f"output_scopes[{index}]",
                )
            )
            continue
        seen.add(token)

    if not seen:
        return list(DEFAULT_OUTPUT_SCOPES)
    return [scope for scope in SUPPORTED_OUTPUT_SCOPES if scope in seen]


def _normalize_selector_array(
    value: object,
    *,
    path: str,
    errors: list[ValidationIssue],
) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append(
            ValidationIssue(
                code="invalid_type",
                message=f"{path} must be an array of selector identifiers.",
                path=path,
            )
        )
        return []

    selectors = _normalize_string_list(value, path=path, errors=errors)
    if selectors is None:
        return []
    return sorted(set(selectors))


def _normalize_column_selection(
    value: object,
    *,
    selected_layers: list[str],
    catalog: LayerCatalog,
    errors: list[ValidationIssue],
) -> list[LayerColumnSelection]:
    if value is None:
        return []
    if not isinstance(value, cabc.Mapping):
        errors.append(
            ValidationIssue(
                code="invalid_type",
                message="column_selection must be an object keyed by layer id.",
                path="column_selection",
            )
        )
        return []

    selected_layer_set = set(selected_layers)
    normalized: list[LayerColumnSelection] = []

    for layer_id_raw, entry_value in value.items():
        if not isinstance(layer_id_raw, str) or not layer_id_raw.strip():
            errors.append(
                ValidationIssue(
                    code="invalid_type",
                    message="column_selection keys must be non-empty layer id strings.",
                    path="column_selection",
                )
            )
            continue

        layer_id = layer_id_raw.strip()
        if layer_id not in selected_layer_set:
            errors.append(
                ValidationIssue(
                    code="unknown_layer_id",
                    message=f"column_selection references unselected layer {layer_id!r}.",
                    path=f"column_selection.{layer_id}",
                )
            )
            continue

        if not isinstance(entry_value, cabc.Mapping):
            errors.append(
                ValidationIssue(
                    code="invalid_type",
                    message="column_selection entries must be objects.",
                    path=f"column_selection.{layer_id}",
                )
            )
            continue

        has_include = "include" in entry_value and entry_value.get("include") is not None
        has_exclude = "exclude" in entry_value and entry_value.get("exclude") is not None
        if has_include and has_exclude:
            errors.append(
                ValidationIssue(
                    code="mutually_exclusive",
                    message="include and exclude are mutually exclusive per layer.",
                    path=f"column_selection.{layer_id}",
                )
            )

        include = _normalize_string_list(
            entry_value.get("include"),
            path=f"column_selection.{layer_id}.include",
            errors=errors,
        )
        exclude = _normalize_string_list(
            entry_value.get("exclude"),
            path=f"column_selection.{layer_id}.exclude",
            errors=errors,
        )

        include_values = tuple(sorted(set(include or []))) if include is not None else None
        exclude_values = tuple(sorted(set(exclude or []))) if exclude is not None else None

        layer_catalog_entry = catalog.layer_index[layer_id]
        known_columns = _known_column_ids_for_layer(layer_catalog_entry)
        if known_columns and _layer_has_explicit_column_contract(layer_catalog_entry):
            unknown_columns: list[str] = []
            for column_id in list(include_values or ()) + list(exclude_values or ()):
                if column_id not in known_columns:
                    unknown_columns.append(column_id)
            if unknown_columns:
                errors.append(
                    ValidationIssue(
                        code="unknown_column_id",
                        message=(
                            f"Unknown column id(s) for {layer_id!r}: {sorted(set(unknown_columns))}."
                        ),
                        path=f"column_selection.{layer_id}",
                    )
                )

        if include_values is None and exclude_values is None:
            continue
        normalized.append(
            LayerColumnSelection(
                layer_id=layer_id,
                include=include_values,
                exclude=exclude_values,
            )
        )

    return sorted(normalized, key=lambda item: item.layer_id)


def _normalize_tabular(
    value: object,
    *,
    format_token: str,
    selected_layers: list[str],
    temporal: NormalizedTemporalRequest | None,
    catalog: LayerCatalog,
    errors: list[ValidationIssue],
) -> NormalizedTabularRequest | None:
    is_tabular_format = format_token in {"csv", "parquet"}
    default_tabular = NormalizedTabularRequest(
        concatenate_tables=False,
        temporal_layout=DEFAULT_TABULAR_TEMPORAL_LAYOUT,
    )

    if value is None:
        normalized = default_tabular if is_tabular_format else None
    else:
        if not isinstance(value, cabc.Mapping):
            errors.append(
                ValidationIssue(
                    code="invalid_type",
                    message="tabular must be an object when provided.",
                    path="tabular",
                )
            )
            return default_tabular if is_tabular_format else None

        if not is_tabular_format:
            errors.append(
                ValidationIssue(
                    code="invalid_selector_combo",
                    message="tabular options are only valid for format=csv|parquet.",
                    path="tabular",
                )
            )
            return None

        concatenate_tables = _normalize_bool(
            value.get("concatenate_tables"),
            path="tabular.concatenate_tables",
            errors=errors,
        )
        if concatenate_tables is None:
            concatenate_tables = False

        temporal_layout = DEFAULT_TABULAR_TEMPORAL_LAYOUT
        if "temporal_layout" in value and value.get("temporal_layout") is not None:
            raw_layout = _optional_string(
                value.get("temporal_layout"),
                path="tabular.temporal_layout",
                errors=errors,
            )
            if raw_layout is not None:
                candidate = raw_layout.lower()
                if candidate not in SUPPORTED_TABULAR_TEMPORAL_LAYOUTS:
                    errors.append(
                        ValidationIssue(
                            code="invalid_enum",
                            message=(
                                "Unsupported tabular.temporal_layout "
                                f"{raw_layout!r}; supported values are "
                                f"{list(SUPPORTED_TABULAR_TEMPORAL_LAYOUTS)!r}."
                            ),
                            path="tabular.temporal_layout",
                        )
                    )
                else:
                    temporal_layout = candidate

        normalized = NormalizedTabularRequest(
            concatenate_tables=bool(concatenate_tables),
            temporal_layout=temporal_layout,
        )

    if normalized is None:
        return None

    if normalized.temporal_layout == "long":
        effective_modes = _tabular_effective_temporal_modes(
            selected_layers=selected_layers,
            temporal=temporal,
            catalog=catalog,
        )
        if "event" in effective_modes and "yearly" in effective_modes:
            errors.append(
                ValidationIssue(
                    code="mixed_temporal_modes",
                    message=(
                        "tabular.temporal_layout=long does not support mixed event and yearly "
                        "layer modes in one export request."
                    ),
                    path="tabular.temporal_layout",
                )
            )

    return normalized


def _tabular_effective_temporal_modes(
    *,
    selected_layers: cabc.Sequence[str],
    temporal: NormalizedTemporalRequest | None,
    catalog: LayerCatalog,
) -> set[str]:
    if temporal is None:
        return set()

    resolved: set[str] = set()
    for layer_id in selected_layers:
        layer = catalog.layer_index.get(layer_id)
        if layer is None or not layer.temporal_supported_modes:
            continue
        mode = temporal.mode_for_layer(layer_id)
        if mode in {"event", "yearly"}:
            resolved.add(mode)
    return resolved


def _layer_has_explicit_column_contract(layer: CatalogLayer) -> bool:
    raw = layer.raw if isinstance(layer.raw, cabc.Mapping) else {}
    columns = raw.get("columns")
    if not isinstance(columns, list):
        return False
    for column in columns:
        if not isinstance(column, cabc.Mapping):
            continue
        token = column.get("column_id")
        if isinstance(token, str) and token.strip():
            return True
    return False


def _known_column_ids_for_layer(layer: CatalogLayer) -> set[str]:
    known: set[str] = set()
    raw = layer.raw if isinstance(layer.raw, cabc.Mapping) else {}

    columns = raw.get("columns")
    if isinstance(columns, list):
        for column in columns:
            if not isinstance(column, cabc.Mapping):
                continue
            token = column.get("column_id")
            if isinstance(token, str) and token.strip():
                known.add(token.strip())

    join = raw.get("join")
    if isinstance(join, cabc.Mapping):
        primary = join.get("primary_key")
        if isinstance(primary, str) and primary.strip():
            known.add(primary.strip())
        fallback_keys = join.get("fallback_keys")
        if isinstance(fallback_keys, list):
            for key in fallback_keys:
                if isinstance(key, str) and key.strip():
                    known.add(key.strip())

    geometry = raw.get("geometry")
    if isinstance(geometry, cabc.Mapping):
        feature_id_keys = geometry.get("feature_id_keys")
        if isinstance(feature_id_keys, list):
            for key in feature_id_keys:
                if isinstance(key, str) and key.strip():
                    known.add(key.strip())

    measures = raw.get("measures")
    if isinstance(measures, cabc.Mapping):
        required = measures.get("required")
        if isinstance(required, list):
            for key in required:
                if isinstance(key, str) and key.strip():
                    known.add(key.strip())

        optional = measures.get("optional")
        if isinstance(optional, list):
            for optional_measure in optional:
                if isinstance(optional_measure, str) and optional_measure.strip():
                    known.add(optional_measure.strip())
                elif isinstance(optional_measure, cabc.Mapping):
                    aliases = optional_measure.get("key_aliases")
                    if isinstance(aliases, list):
                        for key in aliases:
                            if isinstance(key, str) and key.strip():
                                known.add(key.strip())

    return known


def _normalize_swat_tables(
    value: object,
    *,
    errors: list[ValidationIssue],
) -> NormalizedSwatTables | None:
    if value is None:
        return None
    if not isinstance(value, cabc.Mapping):
        errors.append(
            ValidationIssue(
                code="invalid_type",
                message="swat_tables must be an object with include or exclude arrays.",
                path="swat_tables",
            )
        )
        return None

    has_include = "include" in value and value.get("include") is not None
    has_exclude = "exclude" in value and value.get("exclude") is not None
    if has_include and has_exclude:
        errors.append(
            ValidationIssue(
                code="mutually_exclusive",
                message="swat_tables.include and swat_tables.exclude are mutually exclusive.",
                path="swat_tables",
            )
        )

    include = _normalize_string_list(value.get("include"), path="swat_tables.include", errors=errors)
    exclude = _normalize_string_list(value.get("exclude"), path="swat_tables.exclude", errors=errors)

    if include is not None:
        include = sorted(set(include))
    if exclude is not None:
        exclude = sorted(set(exclude))

    if include is None and exclude is None:
        return None
    return NormalizedSwatTables(
        include=tuple(include) if include is not None else None,
        exclude=tuple(exclude) if exclude is not None else None,
    )


def _normalize_temporal(
    value: object,
    *,
    selected_layers: list[str],
    catalog: LayerCatalog,
    errors: list[ValidationIssue],
) -> NormalizedTemporalRequest | None:
    if value is None:
        return None
    if not isinstance(value, cabc.Mapping):
        errors.append(
            ValidationIssue(
                code="invalid_type",
                message="temporal must be an object when provided.",
                path="temporal",
            )
        )
        return None

    mode_token = _optional_string(value.get("mode"), path="temporal.mode", errors=errors)
    mode: str | None = None
    if mode_token is not None:
        mode = mode_token.lower()
        if mode == "daily":
            errors.append(
                ValidationIssue(
                    code="unsupported_temporal_mode",
                    message="Daily temporal mode is not supported for features export.",
                    path="temporal.mode",
                )
            )
            mode = None
        elif mode not in SUPPORTED_TEMPORAL_MODES:
            errors.append(
                ValidationIssue(
                    code="invalid_enum",
                    message=(
                        f"Unsupported temporal.mode {mode_token!r}; supported values are "
                        f"{list(SUPPORTED_TEMPORAL_MODES)!r}."
                    ),
                    path="temporal.mode",
                )
            )
            mode = None

    layer_modes = _normalize_layer_modes(
        value.get("layer_modes"),
        selected_layers=selected_layers,
        errors=errors,
    )

    validated_layer_modes: dict[str, str] = {}
    for layer_id, layer_mode in layer_modes.items():
        supported_modes = catalog.layer_index[layer_id].temporal_supported_modes
        if not supported_modes:
            errors.append(
                ValidationIssue(
                    code="unsupported_temporal_mode",
                    message=f"Layer {layer_id!r} does not support temporal modes.",
                    path=f"temporal.layer_modes.{layer_id}",
                )
            )
            continue
        if layer_mode not in supported_modes:
            errors.append(
                ValidationIssue(
                    code="unsupported_temporal_mode",
                    message=(
                        f"Layer {layer_id!r} does not support temporal mode {layer_mode!r}; "
                        f"supported values are {list(supported_modes)!r}."
                    ),
                    path=f"temporal.layer_modes.{layer_id}",
                )
            )
            continue
        validated_layer_modes[layer_id] = layer_mode
    layer_modes = validated_layer_modes

    selected_temporal_layers = [
        layer_id for layer_id in selected_layers if catalog.layer_index[layer_id].temporal_supported_modes
    ]
    if selected_temporal_layers and mode is None and not layer_modes:
        errors.append(
            ValidationIssue(
                code="missing_field",
                message=(
                    "temporal.mode or temporal.layer_modes is required when temporal-capable "
                    "layers are selected."
                ),
                path="temporal.mode",
            )
        )

    for layer_id in selected_temporal_layers:
        effective_mode = layer_modes.get(layer_id) or mode
        if effective_mode is None:
            errors.append(
                ValidationIssue(
                    code="missing_field",
                    message=f"No temporal mode resolved for layer {layer_id!r}.",
                    path="temporal.layer_modes",
                )
            )

    year_selection: str | None = None
    year_selection_explicit = False
    if "year_selection" in value and value.get("year_selection") is not None:
        raw_year_selection = _optional_string(
            value.get("year_selection"),
            path="temporal.year_selection",
            errors=errors,
        )
        if raw_year_selection is not None:
            candidate = raw_year_selection.lower()
            if candidate not in SUPPORTED_YEAR_SELECTIONS:
                errors.append(
                    ValidationIssue(
                        code="invalid_enum",
                        message=(
                            f"Unsupported temporal.year_selection {raw_year_selection!r}; "
                            f"supported values are {list(SUPPORTED_YEAR_SELECTIONS)!r}."
                        ),
                        path="temporal.year_selection",
                    )
                )
            else:
                year_selection = candidate
                year_selection_explicit = True

    exclude_year_indices_explicit = "exclude_yr_indxs" in value and value.get("exclude_yr_indxs") is not None
    exclude_year_indices = _normalize_non_negative_int_list(
        value.get("exclude_yr_indxs"),
        path="temporal.exclude_yr_indxs",
        errors=errors,
    )
    if exclude_year_indices is not None:
        exclude_year_indices = sorted(set(exclude_year_indices))
    else:
        exclude_year_indices = []

    resolved_layer_modes = [layer_modes.get(layer_id) or mode for layer_id in selected_temporal_layers]
    uses_year_selection = any(token in {"annual_average", "yearly"} for token in resolved_layer_modes if token)
    uses_event = any(token == "event" for token in resolved_layer_modes if token)

    if uses_year_selection and year_selection is None:
        year_selection = "all"

    if year_selection == "custom" and not exclude_year_indices:
        errors.append(
            ValidationIssue(
                code="missing_field",
                message="temporal.exclude_yr_indxs is required when year_selection=custom.",
                path="temporal.exclude_yr_indxs",
            )
        )

    event_selector: NormalizedTemporalEvent | None = None
    raw_event = value.get("event")
    if uses_event:
        if not isinstance(raw_event, cabc.Mapping):
            errors.append(
                ValidationIssue(
                    code="missing_field",
                    message="temporal.event is required when effective temporal mode includes event.",
                    path="temporal.event",
                )
            )
        else:
            selector_token = _optional_string(
                raw_event.get("selector"),
                path="temporal.event.selector",
                errors=errors,
            )
            selector = selector_token.lower() if selector_token is not None else None
            if selector is None:
                selector = None
            elif selector not in SUPPORTED_EVENT_SELECTORS:
                errors.append(
                    ValidationIssue(
                        code="invalid_enum",
                        message=(
                            f"Unsupported temporal.event.selector {selector_token!r}; "
                            f"supported values are {list(SUPPORTED_EVENT_SELECTORS)!r}."
                        ),
                        path="temporal.event.selector",
                    )
                )
                selector = None

            dates = _normalize_string_list(raw_event.get("dates"), path="temporal.event.dates", errors=errors)
            return_periods = _normalize_positive_float_list(
                raw_event.get("return_periods"),
                path="temporal.event.return_periods",
                errors=errors,
            )
            if dates is None:
                dates = []
            if return_periods is None:
                return_periods = []

            for index, date_token in enumerate(dates):
                if _DATE_PATTERN.match(date_token) is None:
                    errors.append(
                        ValidationIssue(
                            code="invalid_format",
                            message="temporal.event.dates values must use YYYY-MM-DD format.",
                            path=f"temporal.event.dates[{index}]",
                        )
                    )

            if selector == "date":
                if not dates:
                    errors.append(
                        ValidationIssue(
                            code="missing_field",
                            message="temporal.event.dates is required when selector=date.",
                            path="temporal.event.dates",
                        )
                    )
                if return_periods:
                    errors.append(
                        ValidationIssue(
                            code="mutually_exclusive",
                            message=(
                                "temporal.event.return_periods is not allowed when selector=date."
                            ),
                            path="temporal.event.return_periods",
                        )
                    )
                event_selector = NormalizedTemporalEvent(
                    selector="date",
                    dates=tuple(sorted(set(dates))),
                )
            elif selector == "return_period":
                if not return_periods:
                    errors.append(
                        ValidationIssue(
                            code="missing_field",
                            message=(
                                "temporal.event.return_periods is required when selector=return_period."
                            ),
                            path="temporal.event.return_periods",
                        )
                    )
                if dates:
                    errors.append(
                        ValidationIssue(
                            code="mutually_exclusive",
                            message="temporal.event.dates is not allowed when selector=return_period.",
                            path="temporal.event.dates",
                        )
                    )
                event_selector = NormalizedTemporalEvent(
                    selector="return_period",
                    return_periods=tuple(sorted(set(return_periods))),
                )
    elif raw_event is not None:
        errors.append(
            ValidationIssue(
                code="invalid_selector_combo",
                message="temporal.event is only valid when an effective temporal mode is event.",
                path="temporal.event",
            )
        )

    if uses_event and (year_selection_explicit or exclude_year_indices_explicit):
        errors.append(
            ValidationIssue(
                code="invalid_selector_combo",
                message=(
                    "temporal.year_selection and temporal.exclude_yr_indxs are not supported "
                    "when effective mode includes event."
                ),
                path="temporal",
            )
        )

    return NormalizedTemporalRequest(
        mode=mode,
        layer_modes=tuple(
            TemporalLayerMode(layer_id=layer_id, mode=layer_mode)
            for layer_id, layer_mode in sorted(layer_modes.items())
        ),
        year_selection=year_selection,
        exclude_yr_indxs=tuple(exclude_year_indices),
        event=event_selector,
    )


def _normalize_layer_modes(
    value: object,
    *,
    selected_layers: list[str],
    errors: list[ValidationIssue],
) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, cabc.Mapping):
        errors.append(
            ValidationIssue(
                code="invalid_type",
                message="temporal.layer_modes must be an object keyed by layer id.",
                path="temporal.layer_modes",
            )
        )
        return {}

    selected_layer_set = set(selected_layers)
    normalized: dict[str, str] = {}
    for layer_id_raw, mode_raw in value.items():
        if not isinstance(layer_id_raw, str) or not layer_id_raw.strip():
            errors.append(
                ValidationIssue(
                    code="invalid_type",
                    message="temporal.layer_modes keys must be layer ids.",
                    path="temporal.layer_modes",
                )
            )
            continue

        layer_id = layer_id_raw.strip()
        if layer_id not in selected_layer_set:
            errors.append(
                ValidationIssue(
                    code="unknown_layer_id",
                    message=f"temporal.layer_modes references unselected layer {layer_id!r}.",
                    path=f"temporal.layer_modes.{layer_id}",
                )
            )
            continue

        mode = _optional_string(mode_raw, path=f"temporal.layer_modes.{layer_id}", errors=errors)
        if mode is None:
            continue
        mode_token = mode.lower()
        if mode_token == "daily":
            errors.append(
                ValidationIssue(
                    code="unsupported_temporal_mode",
                    message="Daily temporal mode is not supported for features export.",
                    path=f"temporal.layer_modes.{layer_id}",
                )
            )
            continue
        if mode_token not in SUPPORTED_TEMPORAL_MODES:
            errors.append(
                ValidationIssue(
                    code="invalid_enum",
                    message=(
                        f"Unsupported temporal mode {mode!r}; supported values are "
                        f"{list(SUPPORTED_TEMPORAL_MODES)!r}."
                    ),
                    path=f"temporal.layer_modes.{layer_id}",
                )
            )
            continue
        normalized[layer_id] = mode_token

    return normalized


def _validate_omni_selector_rules(
    layer_ids: list[str],
    *,
    scenarios: tuple[str, ...],
    contrast_ids: tuple[str, ...],
    catalog: LayerCatalog,
    errors: list[ValidationIssue],
) -> None:
    families = {
        catalog.layer_index[layer_id].family
        for layer_id in layer_ids
        if layer_id in catalog.layer_index
    }

    has_omni_scenarios = "omni_scenarios" in families
    has_omni_contrasts = "omni_contrasts" in families

    if has_omni_scenarios and has_omni_contrasts:
        errors.append(
            ValidationIssue(
                code="invalid_selector_combo",
                message="Omni scenario and Omni contrast layer families cannot be mixed.",
                path="layers",
            )
        )
    if has_omni_scenarios and not scenarios:
        errors.append(
            ValidationIssue(
                code="missing_field",
                message="scenarios is required when Omni scenario layers are requested.",
                path="scenarios",
            )
        )
    if has_omni_contrasts and not contrast_ids:
        errors.append(
            ValidationIssue(
                code="missing_field",
                message="contrast_ids is required when Omni contrast layers are requested.",
                path="contrast_ids",
            )
        )


def _layer_supports_temporal(
    layer: CatalogLayer,
    effective_mode: str | None,
    temporal: NormalizedTemporalRequest | None,
) -> bool:
    if temporal is None:
        return True
    if not layer.temporal_supported_modes:
        return True
    if effective_mode is None:
        return False
    if effective_mode not in layer.temporal_supported_modes:
        return False
    if effective_mode != "event" or temporal.event is None:
        return True

    event_rule = layer.temporal_mode_rules.get("event", {})
    selector_support = event_rule.get("selector_support")
    if not isinstance(selector_support, list):
        return False
    return temporal.event.selector in selector_support


def _normalize_required_enum(
    value: object,
    *,
    path: str,
    allowed: tuple[str, ...],
    errors: list[ValidationIssue],
    aliases: cabc.Mapping[str, str] | None = None,
) -> str:
    token = _optional_string(value, path=path, errors=errors)
    if token is None:
        errors.append(ValidationIssue(code="missing_field", message=f"{path} is required.", path=path))
        return allowed[0]

    normalized = token.lower()
    if aliases is not None:
        normalized = aliases.get(normalized, normalized)
    if normalized not in allowed:
        errors.append(
            ValidationIssue(
                code="invalid_enum",
                message=f"Unsupported {path} {token!r}; supported values are {list(allowed)!r}.",
                path=path,
            )
        )
        return allowed[0]
    return normalized


def _optional_string(
    value: object,
    *,
    path: str,
    errors: list[ValidationIssue],
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(
            ValidationIssue(code="invalid_type", message=f"{path} must be a string.", path=path)
        )
        return None
    token = value.strip()
    if not token:
        return None
    return token


def _normalize_bool(
    value: object,
    *,
    path: str,
    errors: list[ValidationIssue],
) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    errors.append(
        ValidationIssue(
            code="invalid_type",
            message=f"{path} must be a boolean.",
            path=path,
        )
    )
    return None


def _normalize_string_list(
    value: object,
    *,
    path: str,
    errors: list[ValidationIssue],
) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        errors.append(
            ValidationIssue(code="invalid_type", message=f"{path} must be an array.", path=path)
        )
        return None
    if not value:
        errors.append(
            ValidationIssue(
                code="missing_field",
                message=f"{path} must not be empty when provided.",
                path=path,
            )
        )
        return []
    normalized: list[str] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, str) or not entry.strip():
            errors.append(
                ValidationIssue(
                    code="invalid_type",
                    message=f"{path} entries must be non-empty strings.",
                    path=f"{path}[{index}]",
                )
            )
            continue
        normalized.append(entry.strip())
    return normalized


def _normalize_non_negative_int_list(
    value: object,
    *,
    path: str,
    errors: list[ValidationIssue],
) -> list[int] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        errors.append(
            ValidationIssue(code="invalid_type", message=f"{path} must be an array.", path=path)
        )
        return None
    normalized: list[int] = []
    for index, entry in enumerate(value):
        if isinstance(entry, bool) or not isinstance(entry, int):
            errors.append(
                ValidationIssue(
                    code="invalid_type",
                    message=f"{path} entries must be non-negative integers.",
                    path=f"{path}[{index}]",
                )
            )
            continue
        if entry < 0:
            errors.append(
                ValidationIssue(
                    code="invalid_value",
                    message=f"{path} entries must be non-negative integers.",
                    path=f"{path}[{index}]",
                )
            )
            continue
        normalized.append(entry)
    return normalized


def _normalize_positive_float_list(
    value: object,
    *,
    path: str,
    errors: list[ValidationIssue],
) -> list[float] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        errors.append(
            ValidationIssue(code="invalid_type", message=f"{path} must be an array.", path=path)
        )
        return None
    normalized: list[float] = []
    for index, entry in enumerate(value):
        try:
            number = float(entry)
        except (TypeError, ValueError):
            errors.append(
                ValidationIssue(
                    code="invalid_type",
                    message=f"{path} entries must be numeric values.",
                    path=f"{path}[{index}]",
                )
            )
            continue
        if number <= 0:
            errors.append(
                ValidationIssue(
                    code="invalid_value",
                    message=f"{path} entries must be greater than zero.",
                    path=f"{path}[{index}]",
                )
            )
            continue
        normalized.append(number)
    return normalized


__all__ = ["normalize_export_request", "resolve_export_plan"]
