from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wepppy.nodb.mods.geneva.errors import GenevaValidationError
from wepppy.nodb.mods.geneva.schemas import (
    GENEVA_DATASOURCE_IDS,
    GENEVA_MEASURE_IDS,
    validate_measure_id,
)

if TYPE_CHECKING:
    from wepppy.nodb.mods.geneva.geneva import Geneva


_CANONICAL_DATASOURCE_OPTIONS: tuple[str, ...] = ("all", *GENEVA_DATASOURCE_IDS)
_DURATION_MARKER_LABELS: dict[int, str] = {
    5: "5m",
    10: "10m",
    30: "30m",
    60: "1h",
    120: "2h",
    180: "3h",
    360: "6h",
    720: "12h",
    1440: "24h",
}


class GenevaReportPayloadService:
    """Build query/report payloads for Geneva summary exploration."""

    def build_summary_payload(
        self,
        geneva: "Geneva",
        *,
        datasource_id: str = "all",
        ari_years: list[int] | tuple[int, ...] | None = None,
        measure: str = "peak_discharge",
        selected_storm_id: str | None = None,
    ) -> dict[str, Any]:
        panel = geneva.frequency_panel_service.get_frequency_panel(geneva)
        measure_id = self._validate_measure(measure)
        datasource_filter = self._validate_datasource_filter(datasource_id)

        event_table_all = self._build_event_table(geneva, panel)
        available_ari_years = sorted(
            {
                int(row["ari_years"])
                for row in event_table_all
                if isinstance(row.get("ari_years"), int) and int(row["ari_years"]) > 0
            }
        )

        selected_ari = self._normalize_ari_filter(
            ari_years=ari_years,
            available_ari_years=available_ari_years,
        )

        filtered_rows = [
            row
            for row in event_table_all
            if (datasource_filter == "all" or row["datasource_id"] == datasource_filter)
            and row["ari_years"] in selected_ari
        ]

        selected_storm = self._normalize_selected_storm_id(
            requested_storm_id=selected_storm_id,
            rows=filtered_rows,
        )
        chart = self._build_chart(filtered_rows, measure_id, selected_storm)
        filter_options = self._build_filter_options(panel=panel, event_rows=event_table_all)
        assumptions = self._build_assumptions(panel=panel, event_rows=event_table_all)
        warnings = self._build_warning_list(geneva=geneva, panel=panel)
        if assumptions.get("legacy_uniform_interim_artifact_count"):
            warnings.append(
                {
                    "code": "legacy_uniform_interim_artifacts",
                    "message": assumptions.get("stale_artifact_policy"),
                    "legacy_uniform_interim_artifact_count": assumptions.get(
                        "legacy_uniform_interim_artifact_count"
                    ),
                }
            )
        errors = list(getattr(geneva, "_errors", []) or [])

        return {
            "schema_version": int(panel.get("schema_version", 1) or 1),
            "filters": {
                "datasource_id": datasource_filter,
                "ari_years": selected_ari,
                "measure": measure_id,
            },
            "filter_options": filter_options,
            "assumptions": assumptions,
            "chart": chart,
            "selected_storm_id": selected_storm,
            "event_table": filtered_rows,
            "warnings": self._sanitize_message_entries(warnings),
            "errors": self._sanitize_message_entries(errors),
        }

    def _build_event_table(self, geneva: "Geneva", panel: dict[str, Any]) -> list[dict[str, Any]]:
        artifact_io = geneva.artifact_io
        wd = geneva.wd
        run_summary = dict(getattr(geneva, "_run_summary", {}) or {})
        failed_storm_ids = {
            str(storm_id)
            for storm_id in run_summary.get("failed_storm_ids", []) or []
            if str(storm_id).strip()
        }
        completed_storm_ids = {
            str(storm_id)
            for storm_id in run_summary.get("completed_storm_ids", []) or []
            if str(storm_id).strip()
        }
        run_warning_counts = self._storm_count_index(run_summary.get("warnings", []), key="storm_id")
        run_error_counts = self._storm_count_index(run_summary.get("errors", []), key="storm_id")

        rows: list[dict[str, Any]] = []
        for cell in panel.get("cells", []):
            if not isinstance(cell, dict):
                continue

            storm_id = str(cell.get("storm_id", "")).strip()
            if not storm_id:
                continue
            cell_distribution = str(
                cell.get("distribution_type")
                or panel.get("distribution_type")
                or "neh4_type_b"
            ).strip()

            summary_relpath = f"storms/{storm_id}/summary.json"
            summary_exists = artifact_io.exists(wd, summary_relpath)
            summary = artifact_io.read_json(wd, summary_relpath) if summary_exists else {}
            summary_assumptions = dict(summary.get("assumptions", {}) or {})
            summary_distribution = str(
                summary_assumptions.get("distribution_type")
                or summary_assumptions.get("storm_distribution_assumption")
                or ""
            ).strip()
            summary_matches_distribution = (
                not summary_distribution
                or summary_distribution == cell_distribution
            )
            status = self._resolve_row_status(
                cell=cell,
                summary=summary,
                failed_storm_ids=failed_storm_ids,
                completed_storm_ids=completed_storm_ids,
                summary_matches_distribution=summary_matches_distribution,
            )
            metrics = dict(summary.get("summary_metrics", {}) or {}) if status == "completed" else {}
            summary_warnings = list(summary.get("warnings", []) or []) if status == "completed" else []
            summary_errors = list(summary.get("errors", []) or []) if status == "completed" else []
            distribution_type = (
                summary_distribution
                if summary_matches_distribution and summary_distribution
                else cell_distribution
            )
            uniform_assumed = bool(
                summary_assumptions.get(
                    "uniform_rainfall_assumed",
                    distribution_type == "uniform",
                )
            ) if summary_matches_distribution else distribution_type == "uniform"
            legacy_uniform_interim = (
                summary_matches_distribution
                and
                distribution_type == "neh4_type_b"
                and uniform_assumed
                and not isinstance(summary.get("hyetograph"), dict)
            )

            rows.append(
                {
                    "storm_id": storm_id,
                    "status": status,
                    "datasource_id": str(cell.get("datasource_id", "")),
                    "duration_minutes": int(cell.get("duration_minutes", 0) or 0),
                    "depth_mm": self._to_float(cell.get("depth_mm")),
                    "intensity_mm_per_hr": self._to_float(cell.get("intensity_mm_per_hr")),
                    "distribution_type": distribution_type,
                    "uniform_rainfall_assumed": uniform_assumed,
                    "hyetograph_artifact_status": (
                        "legacy_uniform_interim" if legacy_uniform_interim else "current"
                    ),
                    "ari_years": int(cell.get("ari_years", 0) or 0),
                    "peak_discharge": {
                        "value": self._to_float(metrics.get("peak_discharge")),
                        "unit": "m3_s",
                    },
                    "time_to_peak_minutes": self._to_float(metrics.get("time_to_peak")),
                    "runoff_volume": {
                        "value": self._to_float(metrics.get("runoff_volume")),
                        "unit": "m3",
                    },
                    "runoff_depth": {
                        "value": self._to_float(metrics.get("runoff_depth")),
                        "unit": "mm",
                    },
                    "warning_count": int(len(summary_warnings)) + int(run_warning_counts.get(storm_id, 0)),
                    "error_count": int(len(summary_errors)) + int(run_error_counts.get(storm_id, 0)),
                }
            )

        rows.sort(
            key=lambda row: (
                row["datasource_id"],
                row["duration_minutes"],
                row["ari_years"],
                row["storm_id"],
            )
        )
        return rows

    def _build_assumptions(
        self,
        *,
        panel: dict[str, Any],
        event_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        completed_rows = [row for row in event_rows if row.get("status") == "completed"]
        source_rows = completed_rows or event_rows
        distribution_values = {
            str(row.get("distribution_type") or "").strip()
            for row in source_rows
            if str(row.get("distribution_type") or "").strip()
        }
        if not distribution_values:
            distribution_values = {str(panel.get("distribution_type") or "neh4_type_b")}

        if len(distribution_values) == 1:
            distribution_type = next(iter(distribution_values))
        else:
            distribution_type = "mixed"

        stale_count = sum(
            1
            for row in source_rows
            if row.get("hyetograph_artifact_status") == "legacy_uniform_interim"
        )
        assumptions = {
            "arc_condition": "arc_ii",
            "storm_distribution_assumption": distribution_type,
            "distribution_type": distribution_type,
            "uniform_rainfall_assumed": distribution_type == "uniform",
        }
        if stale_count:
            assumptions["legacy_uniform_interim_artifact_count"] = stale_count
            assumptions["stale_artifact_policy"] = (
                "Existing summaries that claim neh4_type_b while marking uniform rainfall are "
                "treated as legacy interim artifacts and should be regenerated before comparison."
            )
        return assumptions

    def _build_chart(
        self,
        rows: list[dict[str, Any]],
        measure: str,
        selected_storm_id: str | None,
    ) -> dict[str, Any]:
        grouped: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            if row.get("status") != "completed":
                continue
            measure_payload = row.get(measure) if isinstance(row.get(measure), dict) else {}
            measure_value = self._to_float(measure_payload.get("value"))
            intensity_mm_per_hr = self._to_float(row.get("intensity_mm_per_hr"))
            if measure_value is None or intensity_mm_per_hr is None:
                continue
            ari = int(row["ari_years"])
            grouped.setdefault(ari, []).append(
                {
                    "storm_id": str(row["storm_id"]),
                    "duration_minutes": int(row["duration_minutes"]),
                    "datasource_id": str(row["datasource_id"]),
                    "intensity_mm_per_hr": intensity_mm_per_hr,
                    "measure_value": measure_value,
                }
            )

        series: list[dict[str, Any]] = []
        for ari in sorted(grouped):
            points = sorted(
                grouped[ari],
                key=lambda row: (
                    row["duration_minutes"],
                    row["datasource_id"],
                    row["storm_id"],
                ),
            )
            series.append(
                {
                    "series_id": f"ari_{ari}",
                    "series_label": f"ARI {ari}-year",
                    "ari_years": ari,
                    "points": [
                        {
                            "storm_id": row["storm_id"],
                            "duration_minutes": row["duration_minutes"],
                            "datasource_id": row["datasource_id"],
                            "intensity_mm_per_hr": row["intensity_mm_per_hr"],
                            "measure_value": row["measure_value"],
                            "marker_label": self._duration_marker_label(int(row["duration_minutes"])),
                            "selected": selected_storm_id is not None
                            and str(row["storm_id"]) == selected_storm_id,
                            "x": row["intensity_mm_per_hr"],
                            "y": row["measure_value"],
                        }
                        for row in points
                    ],
                }
            )

        return {
            "x_axis": "intensity_mm_per_hr",
            "y_axis": "selected_measure",
            "series_grouping": "ari_years",
            "marker_grouping": "duration_minutes",
            "series": series,
        }

    def _build_filter_options(
        self,
        *,
        panel: dict[str, Any],
        event_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ari_years = self._sorted_positive_ints(
            panel.get("ari_years"),
            fallback=[row.get("ari_years") for row in event_rows],
        )
        durations_minutes = self._sorted_positive_ints(
            panel.get("durations_minutes"),
            fallback=[row.get("duration_minutes") for row in event_rows],
        )
        datasource_availability = self._datasource_availability(panel)
        return {
            "datasource_ids": list(_CANONICAL_DATASOURCE_OPTIONS),
            "datasource_availability": datasource_availability,
            "ari_years": ari_years,
            "measures": list(GENEVA_MEASURE_IDS),
            "duration_minutes": durations_minutes,
        }

    def _datasource_availability(self, panel: dict[str, Any]) -> dict[str, bool]:
        availability: dict[str, bool] = {datasource_id: False for datasource_id in GENEVA_DATASOURCE_IDS}
        for cell in panel.get("cells", []):
            if not isinstance(cell, dict):
                continue
            datasource_id = str(cell.get("datasource_id", "")).strip()
            if datasource_id not in availability:
                continue
            if str(cell.get("availability", "unavailable")).strip() == "available":
                availability[datasource_id] = True
        return availability

    def _build_warning_list(self, *, geneva: "Geneva", panel: dict[str, Any]) -> list[Any]:
        warnings: list[Any] = []
        warnings.extend(list(getattr(geneva, "_warnings", []) or []))
        warnings.extend(list(panel.get("warnings", []) or []))
        return warnings

    def _resolve_row_status(
        self,
        *,
        cell: dict[str, Any],
        summary: dict[str, Any],
        failed_storm_ids: set[str],
        completed_storm_ids: set[str],
        summary_matches_distribution: bool,
    ) -> str:
        availability = str(cell.get("availability", "unavailable")).strip()
        storm_id = str(cell.get("storm_id", "")).strip()
        if availability != "available":
            return "unavailable"
        if not summary_matches_distribution:
            return "unavailable"

        if storm_id and storm_id in failed_storm_ids:
            return "failed"

        if completed_storm_ids:
            if storm_id and storm_id in completed_storm_ids:
                return "completed"
            return "unavailable"

        summary_status = str(summary.get("status", "")).strip()
        if summary_status in {"completed", "failed"}:
            return summary_status
        return "unavailable"

    def _storm_count_index(self, rows: Any, *, key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        if not isinstance(rows, list):
            return counts
        for row in rows:
            if not isinstance(row, dict):
                continue
            storm_id = str(row.get(key, "")).strip()
            if not storm_id:
                continue
            counts[storm_id] = int(counts.get(storm_id, 0)) + 1
        return counts

    def _validate_measure(self, measure: str) -> str:
        try:
            return validate_measure_id(measure)
        except ValueError as exc:
            raise GenevaValidationError(
                str(exc),
                code="invalid_input",
                details=str(exc),
                status_code=400,
            ) from exc

    def _validate_datasource_filter(self, datasource_id: str) -> str:
        value = str(datasource_id or "all").strip() or "all"
        if value == "all":
            return value

        if value not in GENEVA_DATASOURCE_IDS:
            raise GenevaValidationError(
                "datasource_id must be one of all, cligen_freq, noaa14_pds",
                code="invalid_input",
                details={
                    "datasource_id": value,
                    "available_datasource_ids": list(_CANONICAL_DATASOURCE_OPTIONS),
                },
                status_code=400,
            )
        return value

    def _normalize_ari_filter(
        self,
        *,
        ari_years: list[int] | tuple[int, ...] | None,
        available_ari_years: list[int],
    ) -> list[int]:
        if not available_ari_years:
            return []
        if not ari_years:
            return list(available_ari_years)

        requested = [int(value) for value in ari_years]
        invalid = sorted(set(requested) - set(available_ari_years))
        if invalid:
            raise GenevaValidationError(
                "ari_years filter includes values outside available storm ARIs",
                code="invalid_input",
                details={
                    "invalid_ari_years": invalid,
                    "available_ari_years": available_ari_years,
                },
                status_code=400,
            )
        return sorted(set(requested))

    def _normalize_selected_storm_id(
        self,
        *,
        requested_storm_id: str | None,
        rows: list[dict[str, Any]],
    ) -> str | None:
        if not rows:
            return None

        requested = str(requested_storm_id or "").strip()
        if requested and any(str(row.get("storm_id", "")) == requested for row in rows):
            return requested

        for row in rows:
            if row.get("status") == "completed":
                return str(row.get("storm_id", ""))
        return str(rows[0].get("storm_id", "")) or None

    def _sorted_positive_ints(self, values: Any, *, fallback: list[Any]) -> list[int]:
        source = values if isinstance(values, list) else fallback
        normalized: set[int] = set()
        for value in source:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed > 0:
                normalized.add(parsed)
        return sorted(normalized)

    def _duration_marker_label(self, duration_minutes: int) -> str:
        if duration_minutes in _DURATION_MARKER_LABELS:
            return _DURATION_MARKER_LABELS[duration_minutes]
        if duration_minutes > 0 and duration_minutes % 60 == 0:
            return f"{duration_minutes // 60}h"
        return f"{duration_minutes}m"

    def _to_float(self, value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _sanitize_message_entries(self, rows: Any) -> list[dict[str, Any]]:
        if not isinstance(rows, list):
            return []

        allowed_keys = (
            "code",
            "message",
            "severity",
            "storm_id",
            "datasource_id",
            "duration_minutes",
            "ari_years",
            "reason_code",
            "wsarea_km2",
            "wsarea_mi2",
            "wsarea_acres",
            "threshold_km2",
            "thresholds_km2",
            "arf_method",
            "arf_value",
            "uniform_rainfall_assumed",
            "distribution_type",
            "legacy_uniform_interim_artifact_count",
            "stale_artifact_policy",
        )
        sanitized: list[dict[str, Any]] = []
        for row in rows:
            if isinstance(row, dict):
                cleaned = {key: row[key] for key in allowed_keys if key in row and row.get(key) not in (None, "")}
                if cleaned:
                    sanitized.append(cleaned)
                    continue
                row = str(row)

            text = str(row).strip()
            if text:
                sanitized.append({"message": text})
        return sanitized


__all__ = ["GenevaReportPayloadService"]
