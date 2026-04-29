from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from wepppy.nodb.mods.geneva.errors import GenevaKernelError, GenevaValidationError
from wepppy.nodb.mods.geneva.schemas import (
    validate_distribution_type,
    validate_hru_map_measure_id,
)
from wepppy.query_engine.activate import update_catalog_entry
from wepppy.query_engine.context import resolve_run_context
from wepppy.query_engine.core import run_query
from wepppy.query_engine.payload import QueryRequest

if TYPE_CHECKING:
    from wepppy.nodb.mods.geneva.geneva import Geneva


HRU_EVENT_MEASURE_SCHEMA_VERSION = 1
HRU_EVENT_MEASURE_ARTIFACT_RELPATH = "hru_event_measure_rows.parquet"
HRU_EVENT_MEASURE_DATASET_PATH = f"geneva/{HRU_EVENT_MEASURE_ARTIFACT_RELPATH}"
HRU_EVENT_MEASURE_COLUMNS = [
    "schema_version",
    "storm_id",
    "datasource_id",
    "duration_minutes",
    "ari_years",
    "distribution_type",
    "hru_id",
    "hru_value",
    "measure_id",
    "value",
    "unit",
]


class GenevaHruEventMeasureService:
    """Persist and query run-scoped Geneva HRU event-measure rows."""

    def materialize_from_batch(
        self,
        geneva: "Geneva",
        *,
        available_cells: list[dict[str, Any]],
        storm_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        completed_rows = [
            row
            for row in storm_results
            if isinstance(row, Mapping) and str(row.get("status", "")).strip() == "completed"
        ]

        artifact_io = geneva.artifact_io
        if not completed_rows:
            relpath = artifact_io.write_records_parquet(
                geneva.wd,
                HRU_EVENT_MEASURE_ARTIFACT_RELPATH,
                [],
                columns=HRU_EVENT_MEASURE_COLUMNS,
            )
            return {
                "schema_version": HRU_EVENT_MEASURE_SCHEMA_VERSION,
                "relpath": relpath,
                "path": f"geneva/{relpath}",
                "row_count": 0,
                "storm_count": 0,
                "measure_ids": ["runoff_depth", "runoff_volume"],
            }

        hru_value_by_id = self._load_hru_value_by_id(geneva)
        event_index = self._build_event_index(available_cells)

        rows: list[dict[str, Any]] = []
        seen_keys: set[tuple[str, str, str]] = set()

        for storm_row in completed_rows:
            storm_id = self._non_empty_text(
                storm_row.get("storm_id"),
                field="storm_results[].storm_id",
            )
            event_dims = event_index.get(storm_id)
            if event_dims is None:
                raise GenevaKernelError(
                    "Completed storm result is missing frequency-panel event dimensions.",
                    code="contract_violation",
                    details={"storm_id": storm_id},
                    status_code=500,
                )

            hru_excess_rows = storm_row.get("hru_excess")
            if not isinstance(hru_excess_rows, list):
                raise GenevaKernelError(
                    "run_batch storm result is missing hru_excess series rows.",
                    code="contract_violation",
                    details={"storm_id": storm_id, "type": type(hru_excess_rows).__name__},
                    status_code=500,
                )

            for hru_row in hru_excess_rows:
                if not isinstance(hru_row, Mapping):
                    raise GenevaKernelError(
                        "run_batch hru_excess row must be an object.",
                        code="contract_violation",
                        details={"storm_id": storm_id},
                        status_code=500,
                    )

                hru_id = self._non_empty_text(hru_row.get("hru_id"), field="hru_excess[].hru_id")
                if hru_id not in hru_value_by_id:
                    raise GenevaKernelError(
                        "hru_excess row has no legend crosswalk for hru_id.",
                        code="contract_violation",
                        details={"storm_id": storm_id, "hru_id": hru_id},
                        status_code=500,
                    )

                area_m2 = self._non_negative_float(hru_row.get("area_m2"), field="hru_excess[].area_m2")
                cumulative_excess_mm_raw = hru_row.get("cumulative_excess_mm")
                if not isinstance(cumulative_excess_mm_raw, list) or not cumulative_excess_mm_raw:
                    raise GenevaKernelError(
                        "hru_excess row must contain non-empty cumulative_excess_mm.",
                        code="contract_violation",
                        details={"storm_id": storm_id, "hru_id": hru_id},
                        status_code=500,
                    )

                runoff_depth_mm = self._non_negative_float(
                    cumulative_excess_mm_raw[-1],
                    field="hru_excess[].cumulative_excess_mm[-1]",
                )
                runoff_volume_m3 = (runoff_depth_mm / 1000.0) * area_m2

                base_row = {
                    "schema_version": HRU_EVENT_MEASURE_SCHEMA_VERSION,
                    "storm_id": storm_id,
                    "datasource_id": event_dims["datasource_id"],
                    "duration_minutes": event_dims["duration_minutes"],
                    "ari_years": event_dims["ari_years"],
                    "distribution_type": event_dims["distribution_type"],
                    "hru_id": hru_id,
                    "hru_value": hru_value_by_id[hru_id],
                }

                self._append_measure_row(
                    rows,
                    seen_keys,
                    base_row=base_row,
                    measure_id="runoff_depth",
                    value=runoff_depth_mm,
                    unit="mm",
                )
                self._append_measure_row(
                    rows,
                    seen_keys,
                    base_row=base_row,
                    measure_id="runoff_volume",
                    value=runoff_volume_m3,
                    unit="m3",
                )

        relpath = artifact_io.write_records_parquet(
            geneva.wd,
            HRU_EVENT_MEASURE_ARTIFACT_RELPATH,
            rows,
            columns=HRU_EVENT_MEASURE_COLUMNS,
        )
        return {
            "schema_version": HRU_EVENT_MEASURE_SCHEMA_VERSION,
            "relpath": relpath,
            "path": f"geneva/{relpath}",
            "row_count": len(rows),
            "storm_count": len(completed_rows),
            "measure_ids": ["runoff_depth", "runoff_volume"],
        }

    def query_rows(
        self,
        geneva: "Geneva",
        *,
        storm_id: str,
        measure_id: str,
        include_schema: bool = True,
        limit: int | None = None,
    ) -> dict[str, Any]:
        normalized_storm_id = self._require_non_empty_input_text(storm_id, field="storm_id")
        normalized_measure_id = self._validate_measure_scope(measure_id)

        normalized_limit = None
        if limit is not None:
            try:
                normalized_limit = int(limit)
            except (TypeError, ValueError) as exc:
                raise GenevaValidationError(
                    "limit must be a positive integer when provided",
                    code="invalid_input",
                    details="limit must be a positive integer when provided",
                    status_code=400,
                ) from exc
            if normalized_limit <= 0:
                raise GenevaValidationError(
                    "limit must be a positive integer when provided",
                    code="invalid_input",
                    details="limit must be a positive integer when provided",
                    status_code=400,
                )

        query_payload = self._query_payload(
            storm_id=normalized_storm_id,
            measure_id=normalized_measure_id,
            include_schema=bool(include_schema),
            limit=normalized_limit,
        )

        if not geneva.artifact_io.exists(geneva.wd, HRU_EVENT_MEASURE_ARTIFACT_RELPATH):
            return {
                "schema_version": HRU_EVENT_MEASURE_SCHEMA_VERSION,
                "filters": {
                    "storm_id": normalized_storm_id,
                    "measure_id": normalized_measure_id,
                },
                "availability": {
                    "status": "unavailable",
                    "reason_code": "legacy_hru_event_measures_missing",
                    "artifact_path": HRU_EVENT_MEASURE_DATASET_PATH,
                },
                "query": query_payload,
                "records": [],
                "schema": self._canonical_schema() if bool(include_schema) else None,
                "row_count": 0,
                "warnings": [
                    {
                        "code": "legacy_hru_event_measures_missing",
                        "message": "Legacy run is missing Geneva HRU event-measure artifact.",
                    }
                ],
                "errors": [],
            }

        try:
            update_catalog_entry(geneva.wd, HRU_EVENT_MEASURE_DATASET_PATH)
            context = resolve_run_context(
                geneva.wd,
                auto_activate=True,
                run_interchange=False,
            )
        except (FileNotFoundError, PermissionError, ValueError) as exc:
            raise GenevaKernelError(
                "Failed to prepare query-engine catalog for Geneva HRU event-measure dataset.",
                code="contract_violation",
                details=str(exc),
                status_code=500,
            ) from exc
        if not context.catalog.has(HRU_EVENT_MEASURE_DATASET_PATH):
            raise GenevaKernelError(
                "Query-engine catalog is missing Geneva HRU event-measure dataset.",
                code="contract_violation",
                details={"dataset": HRU_EVENT_MEASURE_DATASET_PATH},
                status_code=500,
            )

        try:
            query_request = QueryRequest(**query_payload)
            result = run_query(context, query_request)
        except ValueError as exc:
            raise GenevaValidationError(
                str(exc),
                code="invalid_input",
                details=str(exc),
                status_code=400,
            ) from exc
        except Exception as exc:
            # Boundary translation: normalize unexpected query-engine failures
            # into the canonical Geneva kernel-error envelope.
            raise GenevaKernelError(
                "Query-engine execution failed for Geneva HRU event-measure query.",
                code="contract_violation",
                details=str(exc),
                status_code=500,
            ) from exc

        hru_value_by_id = self._load_hru_value_by_id(geneva)
        self._validate_query_rows_crosswalk(result.records, hru_value_by_id)

        return {
            "schema_version": HRU_EVENT_MEASURE_SCHEMA_VERSION,
            "filters": {
                "storm_id": normalized_storm_id,
                "measure_id": normalized_measure_id,
            },
            "availability": {
                "status": "available",
                "reason_code": None,
                "artifact_path": HRU_EVENT_MEASURE_DATASET_PATH,
            },
            "query": query_payload,
            "records": result.records,
            "schema": result.schema,
            "row_count": result.row_count,
            "warnings": [],
            "errors": [],
        }

    def _append_measure_row(
        self,
        rows: list[dict[str, Any]],
        seen_keys: set[tuple[str, str, str]],
        *,
        base_row: Mapping[str, Any],
        measure_id: str,
        value: float,
        unit: str,
    ) -> None:
        key = (
            str(base_row["storm_id"]),
            str(base_row["hru_id"]),
            str(measure_id),
        )
        if key in seen_keys:
            raise GenevaKernelError(
                "Duplicate HRU event-measure row key encountered.",
                code="contract_violation",
                details={"storm_id": key[0], "hru_id": key[1], "measure_id": key[2]},
                status_code=500,
            )
        seen_keys.add(key)

        row = dict(base_row)
        row["measure_id"] = measure_id
        row["value"] = float(value)
        row["unit"] = unit
        rows.append(row)

    def _build_event_index(self, available_cells: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for cell in available_cells:
            storm_id = self._non_empty_text(cell.get("storm_id"), field="available_cells[].storm_id")
            if storm_id in index:
                raise GenevaKernelError(
                    "frequency_panel contains duplicate storm_id keys.",
                    code="contract_violation",
                    details={"storm_id": storm_id},
                    status_code=500,
                )

            try:
                distribution_type = validate_distribution_type(cell.get("distribution_type"))
            except ValueError as exc:
                raise GenevaKernelError(
                    "available_cells[].distribution_type is invalid.",
                    code="contract_violation",
                    details={"storm_id": storm_id, "distribution_type": cell.get("distribution_type")},
                    status_code=500,
                ) from exc

            index[storm_id] = {
                "datasource_id": self._non_empty_text(
                    cell.get("datasource_id"),
                    field="available_cells[].datasource_id",
                ),
                "duration_minutes": self._positive_int(
                    cell.get("duration_minutes"),
                    field="available_cells[].duration_minutes",
                ),
                "ari_years": self._positive_int(
                    cell.get("ari_years"),
                    field="available_cells[].ari_years",
                ),
                "distribution_type": distribution_type,
            }
        return index

    def _load_hru_value_by_id(self, geneva: "Geneva") -> dict[str, int]:
        if not geneva.artifact_io.exists(geneva.wd, "hru_map_legend.json"):
            raise GenevaKernelError(
                "hru_map_legend.json is required for Geneva HRU event-measure joins.",
                code="contract_violation",
                details={"artifact": "geneva/hru_map_legend.json"},
                status_code=500,
            )

        payload = geneva.artifact_io.read_json(geneva.wd, "hru_map_legend.json")
        rows = payload.get("rows")
        if not isinstance(rows, list):
            raise GenevaKernelError(
                "hru_map_legend.json rows payload must be a list.",
                code="contract_violation",
                details={"artifact": "geneva/hru_map_legend.json"},
                status_code=500,
            )

        index: dict[str, int] = {}
        used_values: set[int] = set()
        for entry in rows:
            if not isinstance(entry, Mapping):
                raise GenevaKernelError(
                    "hru_map_legend rows must be objects.",
                    code="contract_violation",
                    details={"artifact": "geneva/hru_map_legend.json"},
                    status_code=500,
                )

            hru_id = self._non_empty_text(entry.get("hru_id"), field="hru_map_legend.rows[].hru_id")
            hru_value = self._positive_int(entry.get("hru_value"), field="hru_map_legend.rows[].hru_value")
            if hru_id in index:
                raise GenevaKernelError(
                    "hru_map_legend contains duplicate hru_id values.",
                    code="contract_violation",
                    details={"hru_id": hru_id},
                    status_code=500,
                )
            if hru_value in used_values:
                raise GenevaKernelError(
                    "hru_map_legend contains duplicate hru_value values.",
                    code="contract_violation",
                    details={"hru_value": hru_value},
                    status_code=500,
                )

            index[hru_id] = hru_value
            used_values.add(hru_value)

        return index

    def _validate_query_rows_crosswalk(
        self,
        records: list[dict[str, Any]],
        hru_value_by_id: Mapping[str, int],
    ) -> None:
        for record in records:
            hru_id = self._non_empty_text(record.get("hru_id"), field="records[].hru_id")
            hru_value = self._positive_int(record.get("hru_value"), field="records[].hru_value")
            expected_value = hru_value_by_id.get(hru_id)
            if expected_value is None or expected_value != hru_value:
                raise GenevaKernelError(
                    "HRU row crosswalk validation failed for hru_id/hru_value.",
                    code="contract_violation",
                    details={
                        "hru_id": hru_id,
                        "hru_value": hru_value,
                        "expected_hru_value": expected_value,
                    },
                    status_code=500,
                )

    def _validate_measure_scope(self, measure_id: str) -> str:
        normalized = str(measure_id).strip()
        if normalized == "peak_discharge":
            raise GenevaValidationError(
                "peak_discharge is watershed-level only and is not supported for HRU map queries.",
                code="unsupported_measure_scope",
                details="measure_id=peak_discharge is not mapable at HRU scope",
                status_code=400,
            )
        try:
            return validate_hru_map_measure_id(normalized)
        except ValueError as exc:
            raise GenevaValidationError(
                str(exc),
                code="invalid_input",
                details=str(exc),
                status_code=400,
            ) from exc

    def _query_payload(
        self,
        *,
        storm_id: str,
        measure_id: str,
        include_schema: bool,
        limit: int | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "datasets": [HRU_EVENT_MEASURE_DATASET_PATH],
            "columns": list(HRU_EVENT_MEASURE_COLUMNS),
            "filters": [
                {"column": "storm_id", "operator": "=", "value": storm_id},
                {"column": "measure_id", "operator": "=", "value": measure_id},
            ],
            "order_by": ["hru_value", "hru_id"],
            "include_schema": include_schema,
        }
        if limit is not None:
            payload["limit"] = int(limit)
        return payload

    def _canonical_schema(self) -> list[dict[str, str]]:
        return [
            {"name": "schema_version", "type": "BIGINT"},
            {"name": "storm_id", "type": "VARCHAR"},
            {"name": "datasource_id", "type": "VARCHAR"},
            {"name": "duration_minutes", "type": "BIGINT"},
            {"name": "ari_years", "type": "BIGINT"},
            {"name": "distribution_type", "type": "VARCHAR"},
            {"name": "hru_id", "type": "VARCHAR"},
            {"name": "hru_value", "type": "BIGINT"},
            {"name": "measure_id", "type": "VARCHAR"},
            {"name": "value", "type": "DOUBLE"},
            {"name": "unit", "type": "VARCHAR"},
        ]

    def _require_non_empty_input_text(self, value: Any, *, field: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise GenevaValidationError(
                f"{field} must be a non-empty string.",
                code="invalid_input",
                details=f"{field} must be a non-empty string.",
                status_code=400,
            )
        return text

    def _non_empty_text(self, value: Any, *, field: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise GenevaKernelError(
                f"{field} must be a non-empty string.",
                code="contract_violation",
                details={"field": field, "value": value},
                status_code=500,
            )
        return text

    def _positive_int(self, value: Any, *, field: str) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise GenevaKernelError(
                f"{field} must be an integer.",
                code="contract_violation",
                details={"field": field, "value": value},
                status_code=500,
            ) from exc
        if parsed <= 0:
            raise GenevaKernelError(
                f"{field} must be > 0.",
                code="contract_violation",
                details={"field": field, "value": value},
                status_code=500,
            )
        return parsed

    def _non_negative_float(self, value: Any, *, field: str) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise GenevaKernelError(
                f"{field} must be numeric.",
                code="contract_violation",
                details={"field": field, "value": value},
                status_code=500,
            ) from exc
        if parsed < 0.0:
            raise GenevaKernelError(
                f"{field} must be >= 0.",
                code="contract_violation",
                details={"field": field, "value": value},
                status_code=500,
            )
        return parsed


__all__ = [
    "HRU_EVENT_MEASURE_SCHEMA_VERSION",
    "HRU_EVENT_MEASURE_ARTIFACT_RELPATH",
    "HRU_EVENT_MEASURE_DATASET_PATH",
    "HRU_EVENT_MEASURE_COLUMNS",
    "GenevaHruEventMeasureService",
]
