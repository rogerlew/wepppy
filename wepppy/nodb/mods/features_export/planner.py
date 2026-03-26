"""Pure request normalization and deterministic planning for features export."""

from __future__ import annotations

import re
import collections.abc as cabc

from .catalog_loader import CatalogLayer, LayerCatalog
from .contracts import (
    DEFAULT_CRS,
    DEFAULT_OUTPUT_SCOPES,
    DEFAULT_SWAT_RUN_ID,
    FORMAT_ALIASES,
    ExportRequest,
    ExportWarning,
    FeaturesExportValidationError,
    NormalizedExportRequest,
    NormalizedSwatTables,
    NormalizedTemporalEvent,
    NormalizedTemporalRequest,
    ResolvedExportPlan,
    ResolvedLayerPlan,
    SUPPORTED_CRS,
    SUPPORTED_EVENT_SELECTORS,
    SUPPORTED_FORMATS,
    SUPPORTED_OUTPUT_SCOPES,
    SUPPORTED_TEMPORAL_MODES,
    SUPPORTED_UNITS,
    SUPPORTED_YEAR_SELECTIONS,
    ValidationIssue,
    WARNING_LAYER_UNAVAILABLE,
    WARNING_SCOPE_NOT_APPLICABLE,
)

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def normalize_export_request(
    request: ExportRequest | cabc.Mapping[str, object],
    catalog: LayerCatalog,
) -> NormalizedExportRequest:
    """Normalize request payload tokens and enforce WP-1 validation contracts."""

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

    scenario = _optional_string(payload.get("scenario"), path="scenario", errors=errors)
    contrast_id = _optional_string(payload.get("contrast_id"), path="contrast_id", errors=errors)
    if scenario is not None and contrast_id is not None:
        errors.append(
            ValidationIssue(
                code="mutually_exclusive",
                message="scenario and contrast_id are mutually exclusive.",
                path="scenario",
            )
        )

    swat_run_id = _optional_string(payload.get("swat_run_id"), path="swat_run_id", errors=errors)
    if swat_run_id is None:
        swat_run_id = DEFAULT_SWAT_RUN_ID

    swat_tables = _normalize_swat_tables(payload.get("swat_tables"), errors=errors)
    temporal = _normalize_temporal(payload.get("temporal"), errors=errors)

    _validate_omni_selector_rules(
        normalized_layers,
        scenario=scenario,
        contrast_id=contrast_id,
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
        scenario=scenario,
        contrast_id=contrast_id,
        swat_run_id=swat_run_id,
        swat_tables=swat_tables,
        temporal=temporal,
    )


def resolve_export_plan(
    request: ExportRequest | cabc.Mapping[str, object],
    catalog: LayerCatalog,
) -> ResolvedExportPlan:
    """Build a deterministic export plan from a normalized request and layer catalog."""

    normalized_request = normalize_export_request(request, catalog)
    warnings: list[ExportWarning] = []
    resolved_layers: list[ResolvedLayerPlan] = []
    requested_temporal_mode = (
        normalized_request.temporal.mode
        if normalized_request.temporal is not None
        else None
    )

    for layer_id in normalized_request.layers:
        layer = catalog.layer_index[layer_id]
        if not _layer_supports_temporal(layer, normalized_request.temporal):
            warnings.append(
                ExportWarning(
                    code=WARNING_LAYER_UNAVAILABLE,
                    layer_id=layer.layer_id,
                    message=(
                        f"Layer {layer.layer_id!r} is incompatible with temporal mode "
                        f"{requested_temporal_mode!r}."
                    ),
                )
            )
            continue

        if layer.scope_class == "scope_aware":
            for scope in normalized_request.output_scopes:
                resolved_layers.append(
                    ResolvedLayerPlan(
                        layer_id=layer.layer_id,
                        family=layer.family,
                        scope_class=layer.scope_class,
                        scope=scope,
                        output_layer_id=f"{scope}__{layer.layer_id}",
                        temporal_mode=requested_temporal_mode,
                    )
                )
        else:
            resolved_layers.append(
                ResolvedLayerPlan(
                    layer_id=layer.layer_id,
                    family=layer.family,
                    scope_class=layer.scope_class,
                    scope="shared",
                    output_layer_id=f"shared__{layer.layer_id}",
                    temporal_mode=requested_temporal_mode,
                )
            )
            if "roads" in normalized_request.output_scopes:
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
    has_other_temporal_fields = any(key in value for key in ("year_selection", "exclude_yr_indxs", "event"))
    if mode_token is None:
        if has_other_temporal_fields:
            errors.append(
                ValidationIssue(
                    code="missing_field",
                    message="temporal.mode is required when temporal selectors are provided.",
                    path="temporal.mode",
                )
            )
        return None

    mode = mode_token.lower()
    if mode == "daily":
        errors.append(
            ValidationIssue(
                code="unsupported_temporal_mode",
                message="Daily temporal mode is not supported for features export.",
                path="temporal.mode",
            )
        )
        return None
    if mode not in SUPPORTED_TEMPORAL_MODES:
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
        return None

    year_selection: str | None = None
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

    exclude_year_indices = _normalize_non_negative_int_list(
        value.get("exclude_yr_indxs"),
        path="temporal.exclude_yr_indxs",
        errors=errors,
    )
    if exclude_year_indices is not None:
        exclude_year_indices = sorted(set(exclude_year_indices))
    else:
        exclude_year_indices = []

    if mode in {"annual_average", "yearly"} and year_selection is None:
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
    if mode == "event":
        if not isinstance(raw_event, cabc.Mapping):
            errors.append(
                ValidationIssue(
                    code="missing_field",
                    message="temporal.event is required when temporal.mode=event.",
                    path="temporal.event",
                )
            )
            return None

        selector_token = _optional_string(
            raw_event.get("selector"),
            path="temporal.event.selector",
            errors=errors,
        )
        if selector_token is None:
            return None
        selector = selector_token.lower()
        if selector not in SUPPORTED_EVENT_SELECTORS:
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
            return None

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
            event_selector = NormalizedTemporalEvent(selector=selector, dates=tuple(sorted(set(dates))))
        else:
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
                selector=selector,
                return_periods=tuple(sorted(set(return_periods))),
            )

        if year_selection is not None or exclude_year_indices:
            errors.append(
                ValidationIssue(
                    code="invalid_selector_combo",
                    message=(
                        "temporal.year_selection and temporal.exclude_yr_indxs are not "
                        "supported when temporal.mode=event."
                    ),
                    path="temporal",
                )
            )
    elif raw_event is not None:
        errors.append(
            ValidationIssue(
                code="invalid_selector_combo",
                message="temporal.event is only valid when temporal.mode=event.",
                path="temporal.event",
            )
        )

    return NormalizedTemporalRequest(
        mode=mode,
        year_selection=year_selection,
        exclude_yr_indxs=tuple(exclude_year_indices),
        event=event_selector,
    )


def _validate_omni_selector_rules(
    layer_ids: list[str],
    *,
    scenario: str | None,
    contrast_id: str | None,
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
    if has_omni_scenarios and scenario is None:
        errors.append(
            ValidationIssue(
                code="missing_field",
                message="scenario is required when Omni scenario layers are requested.",
                path="scenario",
            )
        )
    if has_omni_contrasts and contrast_id is None:
        errors.append(
            ValidationIssue(
                code="missing_field",
                message="contrast_id is required when Omni contrast layers are requested.",
                path="contrast_id",
            )
        )


def _layer_supports_temporal(
    layer: CatalogLayer,
    temporal: NormalizedTemporalRequest | None,
) -> bool:
    if temporal is None:
        return True
    if temporal.mode not in layer.temporal_supported_modes:
        return False
    if temporal.mode != "event" or temporal.event is None:
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
