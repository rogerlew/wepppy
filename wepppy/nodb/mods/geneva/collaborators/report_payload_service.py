from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wepppy.nodb.mods.geneva.errors import GenevaValidationError
from wepppy.nodb.mods.geneva.schemas import validate_measure_id

if TYPE_CHECKING:
    from wepppy.nodb.mods.geneva.geneva import Geneva


class GenevaReportPayloadService:
    """Build query/report payloads for Geneva summary exploration."""

    def build_summary_payload(
        self,
        geneva: "Geneva",
        *,
        datasource_id: str = "all",
        ari_years: list[int] | tuple[int, ...] | None = None,
        measure: str = "peak_discharge",
    ) -> dict[str, Any]:
        panel = geneva.frequency_panel_service.get_frequency_panel(geneva)
        measure_id = self._validate_measure(measure)

        event_table_all = self._build_event_table(geneva, panel)
        available_ari_years = sorted({int(row["ari_years"]) for row in event_table_all})

        datasource_filter = self._validate_datasource_filter(datasource_id, panel)
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

        chart = self._build_chart(filtered_rows, measure_id)
        warnings = list(geneva._warnings) + list(panel.get("warnings", []) or [])

        return {
            "filters": {
                "datasource_id": datasource_filter,
                "ari_years": selected_ari,
                "measure": measure_id,
            },
            "assumptions": {
                "arc_condition": "arc_ii",
                "storm_distribution_assumption": "neh4_type_b",
                "uniform_rainfall_assumed": True,
            },
            "chart": chart,
            "event_table": filtered_rows,
            "warnings": warnings,
        }

    def _build_event_table(self, geneva: "Geneva", panel: dict[str, Any]) -> list[dict[str, Any]]:
        artifact_io = geneva.artifact_io
        wd = geneva.wd

        rows: list[dict[str, Any]] = []
        for cell in panel.get("cells", []):
            if not isinstance(cell, dict):
                continue
            if str(cell.get("availability", "")) != "available":
                continue

            storm_id = str(cell.get("storm_id", "")).strip()
            if not storm_id:
                continue

            summary_relpath = f"storms/{storm_id}/summary.json"
            if not artifact_io.exists(wd, summary_relpath):
                continue

            summary = artifact_io.read_json(wd, summary_relpath)
            metrics = dict(summary.get("summary_metrics", {}) or {})

            rows.append(
                {
                    "storm_id": storm_id,
                    "datasource_id": str(cell.get("datasource_id", "")),
                    "duration_minutes": int(cell.get("duration_minutes", 0) or 0),
                    "depth_mm": self._to_float(cell.get("depth_mm")),
                    "intensity_mm_per_hr": self._to_float(cell.get("intensity_mm_per_hr")),
                    "distribution_type": str(
                        cell.get("distribution_type")
                        or summary.get("assumptions", {}).get("storm_distribution_assumption")
                        or "neh4_type_b"
                    ),
                    "ari_years": int(cell.get("ari_years", 0) or 0),
                    "peak_discharge": self._to_float(metrics.get("peak_discharge")),
                    "time_to_peak": self._to_float(metrics.get("time_to_peak")),
                    "runoff_volume": self._to_float(metrics.get("runoff_volume")),
                    "runoff_depth": self._to_float(metrics.get("runoff_depth")),
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

    def _build_chart(self, rows: list[dict[str, Any]], measure: str) -> dict[str, Any]:
        grouped: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            if row.get(measure) is None:
                continue
            ari = int(row["ari_years"])
            grouped.setdefault(ari, []).append(row)

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
                    "ari_years": ari,
                    "points": [
                        {
                            "storm_id": row["storm_id"],
                            "duration_minutes": row["duration_minutes"],
                            "datasource_id": row["datasource_id"],
                            "x": row["intensity_mm_per_hr"],
                            "y": row[measure],
                        }
                        for row in points
                    ],
                }
            )

        return {
            "x_axis": "intensity_mm_per_hr",
            "y_axis": "selected_measure",
            "series": series,
        }

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

    def _validate_datasource_filter(self, datasource_id: str, panel: dict[str, Any]) -> str:
        value = str(datasource_id or "all").strip() or "all"
        if value == "all":
            return value

        available = set(panel.get("datasource_ids", []))
        if value not in available:
            raise GenevaValidationError(
                "datasource_id must be one of panel datasource_ids or all",
                code="invalid_input",
                details={
                    "datasource_id": value,
                    "available_datasource_ids": sorted(available),
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

    def _to_float(self, value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


__all__ = ["GenevaReportPayloadService"]
