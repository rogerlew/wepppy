"""Typed contracts for features export request normalization and planning."""

from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_FORMATS: tuple[str, ...] = (
    "geojson",
    "geoparquet",
    "kmz",
    "geopackage",
    "geodatabase",
)
FORMAT_ALIASES: dict[str, str] = {"f_esri": "geodatabase"}

SUPPORTED_UNITS: tuple[str, ...] = ("si", "english", "project")
SUPPORTED_CRS: tuple[str, ...] = ("wgs", "utm")
SUPPORTED_OUTPUT_SCOPES: tuple[str, ...] = ("baseline", "roads")
SUPPORTED_TEMPORAL_MODES: tuple[str, ...] = ("annual_average", "yearly", "event")
SUPPORTED_YEAR_SELECTIONS: tuple[str, ...] = (
    "all",
    "exclude_first",
    "exclude_first_two",
    "exclude_first_five",
    "custom",
)
SUPPORTED_EVENT_SELECTORS: tuple[str, ...] = ("date", "return_period")

DEFAULT_CRS = "wgs"
DEFAULT_OUTPUT_SCOPES: tuple[str, ...] = ("baseline",)
DEFAULT_SWAT_RUN_ID = "latest"

WARNING_SCOPE_MISSING_LAYER = "scope_missing_layer"
WARNING_SCOPE_NOT_APPLICABLE = "scope_not_applicable"
WARNING_LAYER_UNAVAILABLE = "layer_unavailable"
WARNING_TABLE_UNAVAILABLE = "table_unavailable"
WARNING_MEASURE_UNAVAILABLE = "measure_unavailable"
WARNING_UNIT_PASS_THROUGH = "unit_pass_through"
WARNING_SELECTOR_DEFAULTED = "selector_defaulted"
WARNING_LEGACY_FLAGS_IGNORED = "legacy_flags_ignored"

WARNING_CODES: tuple[str, ...] = (
    WARNING_SCOPE_MISSING_LAYER,
    WARNING_SCOPE_NOT_APPLICABLE,
    WARNING_LAYER_UNAVAILABLE,
    WARNING_TABLE_UNAVAILABLE,
    WARNING_MEASURE_UNAVAILABLE,
    WARNING_UNIT_PASS_THROUGH,
    WARNING_SELECTOR_DEFAULTED,
    WARNING_LEGACY_FLAGS_IGNORED,
)


@dataclass(frozen=True)
class ValidationIssue:
    """Machine-readable validation issue entry."""

    code: str
    message: str
    path: str

    def to_mapping(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "path": self.path}


class FeaturesExportValidationError(ValueError):
    """Validation error for planner/normalizer input contracts."""

    status_code = 400
    error_code = "validation_error"

    def __init__(
        self,
        issues: list[ValidationIssue] | tuple[ValidationIssue, ...],
        *,
        message: str = "Validation failed",
    ) -> None:
        normalized_issues = tuple(issues)
        if not normalized_issues:
            normalized_issues = (
                ValidationIssue(code="validation_error", message=message, path="$"),
            )
        self.issues: tuple[ValidationIssue, ...] = normalized_issues
        self.summary = message
        super().__init__(message)

    def to_error_payload(self) -> dict[str, object]:
        details = self.issues[0].message if self.issues else self.summary
        return {
            "error": {
                "message": self.summary,
                "code": self.error_code,
                "details": details,
            },
            "errors": [issue.to_mapping() for issue in self.issues],
        }


@dataclass(frozen=True)
class SwatTablesRequest:
    """Requested SWAT table selector object."""

    include: tuple[str, ...] | None = None
    exclude: tuple[str, ...] | None = None


@dataclass(frozen=True)
class TemporalEventRequest:
    """Requested temporal event selector payload."""

    selector: str
    dates: tuple[str, ...] = ()
    return_periods: tuple[float, ...] = ()


@dataclass(frozen=True)
class TemporalRequest:
    """Requested temporal selection payload."""

    mode: str | None = None
    year_selection: str | None = None
    exclude_yr_indxs: tuple[int, ...] = ()
    event: TemporalEventRequest | None = None


@dataclass(frozen=True)
class ExportRequest:
    """Typed incoming request payload before canonical normalization."""

    format: str
    units: str
    layers: tuple[str, ...]
    crs: str | None = None
    output_scopes: tuple[str, ...] | None = None
    scenario: str | None = None
    contrast_id: str | None = None
    swat_run_id: str | None = None
    swat_tables: SwatTablesRequest | None = None
    temporal: TemporalRequest | None = None


@dataclass(frozen=True)
class NormalizedSwatTables:
    """Canonicalized SWAT include/exclude selector."""

    include: tuple[str, ...] | None = None
    exclude: tuple[str, ...] | None = None

    def to_mapping(self) -> dict[str, list[str]]:
        payload: dict[str, list[str]] = {}
        if self.include is not None:
            payload["include"] = list(self.include)
        if self.exclude is not None:
            payload["exclude"] = list(self.exclude)
        return payload


@dataclass(frozen=True)
class NormalizedTemporalEvent:
    """Canonical temporal event selector."""

    selector: str
    dates: tuple[str, ...] = ()
    return_periods: tuple[float, ...] = ()

    def to_mapping(self) -> dict[str, object]:
        payload: dict[str, object] = {"selector": self.selector}
        if self.dates:
            payload["dates"] = list(self.dates)
        if self.return_periods:
            payload["return_periods"] = list(self.return_periods)
        return payload


@dataclass(frozen=True)
class NormalizedTemporalRequest:
    """Canonical temporal selector bundle."""

    mode: str
    year_selection: str | None = None
    exclude_yr_indxs: tuple[int, ...] = ()
    event: NormalizedTemporalEvent | None = None

    def to_mapping(self) -> dict[str, object]:
        payload: dict[str, object] = {"mode": self.mode}
        if self.year_selection is not None:
            payload["year_selection"] = self.year_selection
        if self.exclude_yr_indxs:
            payload["exclude_yr_indxs"] = list(self.exclude_yr_indxs)
        if self.event is not None:
            payload["event"] = self.event.to_mapping()
        return payload


@dataclass(frozen=True)
class NormalizedExportRequest:
    """Canonical request payload used for planning and cache-key inputs."""

    format: str
    units: str
    layers: tuple[str, ...]
    crs: str = DEFAULT_CRS
    output_scopes: tuple[str, ...] = DEFAULT_OUTPUT_SCOPES
    scenario: str | None = None
    contrast_id: str | None = None
    swat_run_id: str = DEFAULT_SWAT_RUN_ID
    swat_tables: NormalizedSwatTables | None = None
    temporal: NormalizedTemporalRequest | None = None

    def to_mapping(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "format": self.format,
            "units": self.units,
            "crs": self.crs,
            "layers": list(self.layers),
            "output_scopes": list(self.output_scopes),
            "swat_run_id": self.swat_run_id,
        }
        if self.scenario is not None:
            payload["scenario"] = self.scenario
        if self.contrast_id is not None:
            payload["contrast_id"] = self.contrast_id
        if self.swat_tables is not None:
            payload["swat_tables"] = self.swat_tables.to_mapping()
        if self.temporal is not None:
            payload["temporal"] = self.temporal.to_mapping()
        return payload


@dataclass(frozen=True)
class ExportWarning:
    """Warning entry emitted during plan resolution."""

    code: str
    message: str
    layer_id: str | None = None
    scope: str | None = None

    def to_mapping(self) -> dict[str, object]:
        payload: dict[str, object] = {"code": self.code, "message": self.message}
        if self.layer_id is not None:
            payload["layer_id"] = self.layer_id
        if self.scope is not None:
            payload["scope"] = self.scope
        return payload


@dataclass(frozen=True)
class ResolvedLayerPlan:
    """Resolved export target for one layer and one scope context."""

    layer_id: str
    family: str
    scope_class: str
    scope: str
    output_layer_id: str
    temporal_mode: str | None = None

    def to_mapping(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "layer_id": self.layer_id,
            "family": self.family,
            "scope_class": self.scope_class,
            "scope": self.scope,
            "output_layer_id": self.output_layer_id,
        }
        if self.temporal_mode is not None:
            payload["temporal_mode"] = self.temporal_mode
        return payload


@dataclass(frozen=True)
class ResolvedExportPlan:
    """Deterministic resolved plan used by later exporter phases."""

    catalog_version: str
    schema_version: int | str
    request: NormalizedExportRequest
    layers: tuple[ResolvedLayerPlan, ...]
    warnings: tuple[ExportWarning, ...] = ()

    def to_mapping(self) -> dict[str, object]:
        return {
            "catalog": {
                "catalog_version": self.catalog_version,
                "schema_version": self.schema_version,
            },
            "request": self.request.to_mapping(),
            "layers": [layer.to_mapping() for layer in self.layers],
            "warnings": [warning.to_mapping() for warning in self.warnings],
        }


__all__ = [
    "DEFAULT_CRS",
    "DEFAULT_OUTPUT_SCOPES",
    "DEFAULT_SWAT_RUN_ID",
    "FORMAT_ALIASES",
    "FeaturesExportValidationError",
    "ExportRequest",
    "ExportWarning",
    "NormalizedExportRequest",
    "NormalizedSwatTables",
    "NormalizedTemporalEvent",
    "NormalizedTemporalRequest",
    "ResolvedExportPlan",
    "ResolvedLayerPlan",
    "SUPPORTED_CRS",
    "SUPPORTED_EVENT_SELECTORS",
    "SUPPORTED_FORMATS",
    "SUPPORTED_OUTPUT_SCOPES",
    "SUPPORTED_TEMPORAL_MODES",
    "SUPPORTED_UNITS",
    "SUPPORTED_YEAR_SELECTIONS",
    "SwatTablesRequest",
    "TemporalEventRequest",
    "TemporalRequest",
    "ValidationIssue",
    "WARNING_CODES",
    "WARNING_LAYER_UNAVAILABLE",
    "WARNING_LEGACY_FLAGS_IGNORED",
    "WARNING_MEASURE_UNAVAILABLE",
    "WARNING_SCOPE_MISSING_LAYER",
    "WARNING_SCOPE_NOT_APPLICABLE",
    "WARNING_SELECTOR_DEFAULTED",
    "WARNING_TABLE_UNAVAILABLE",
    "WARNING_UNIT_PASS_THROUGH",
]
