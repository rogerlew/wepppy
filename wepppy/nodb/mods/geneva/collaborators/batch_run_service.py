from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Mapping

from wepppy.nodb.mods.geneva.errors import GenevaKernelError, GenevaNoDbError, GenevaValidationError
from wepppy.nodb.mods.geneva.schemas import (
    GenevaRunBatchRequest,
    parse_run_batch_request,
    validate_distribution_type,
)

if TYPE_CHECKING:
    from wepppy.nodb.mods.geneva.geneva import Geneva

WARNING_AREA_KM2 = 25.0
SEVERE_WARNING_AREA_KM2 = 100.0
EXTREME_WARNING_AREA_KM2 = 250.0

_M2_TO_ACRES = 0.0002471053814671653
_KM2_TO_MI2 = 0.3861021585424458


class GenevaBatchRunService:
    """Run Geneva batch storms and persist per-storm artifacts."""

    def validate_request(
        self,
        geneva: "Geneva",
        payload: Mapping[str, Any],
    ) -> GenevaRunBatchRequest:
        config = dict(geneva._config)
        try:
            return parse_run_batch_request(
                payload,
                default_lambda_mode=str(config["lambda_mode"]),
                default_uh_method=str(config["uh_method"]),
            )
        except ValueError as exc:
            raise GenevaValidationError(
                str(exc),
                code="invalid_input",
                details=str(exc),
                status_code=400,
            ) from exc

    def run_batch(
        self,
        geneva: "Geneva",
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        request = self.validate_request(geneva, payload)

        artifact_io = geneva.artifact_io
        if not artifact_io.exists(geneva.wd, "frequency_panel.json"):
            raise GenevaValidationError(
                "Frequency panel is required before running Geneva batch.",
                code="invalid_input",
                details="Run build_frequency_panel before run_batch.",
            )
        if not artifact_io.exists(geneva.wd, "hru_table.parquet"):
            raise GenevaValidationError(
                "HRU table is required before running Geneva batch.",
                code="invalid_input",
                details="Run prepare_hrus before run_batch.",
            )

        frequency_panel = artifact_io.read_json(geneva.wd, "frequency_panel.json")
        panel_distribution = validate_distribution_type(
            frequency_panel.get("distribution_type")
        )
        if request.hyetograph.distribution_type != panel_distribution:
            raise GenevaValidationError(
                "hyetograph.distribution_type must match frequency panel distribution_type. Rebuild frequency panel with the selected storm shape before run_batch.",
                code="invalid_input",
                details={
                    "run_batch_distribution_type": request.hyetograph.distribution_type,
                    "frequency_panel_distribution_type": panel_distribution,
                },
                status_code=400,
            )

        hru_rows = artifact_io.read_records_parquet(geneva.wd, "hru_table.parquet")
        if not hru_rows:
            raise GenevaValidationError(
                "HRU table is empty.",
                code="invalid_input",
                details="prepare_hrus produced no rows.",
            )

        available_cells, unavailable_cells = _select_cells(frequency_panel, request.event_filter)
        incompatible_durations = _non_uniform_duration_minutes(
            available_cells,
            request.hyetograph.time_step_minutes,
        )
        if incompatible_durations:
            raise GenevaValidationError(
                "hyetograph.time_step_minutes must evenly divide selected duration_minutes for Geneva run_batch.",
                code="invalid_input",
                details={
                    "time_step_minutes": request.hyetograph.time_step_minutes,
                    "incompatible_durations_minutes": incompatible_durations,
                },
                status_code=400,
            )

        storm_inputs = {
            "schema_version": 1,
            "batch_id": request.batch_id,
            "runoff_model": {
                "lambda_mode": request.runoff_model.lambda_mode,
                "uh_method": request.runoff_model.uh_method,
                "timing_method": request.runoff_model.timing_method,
                "tc_hours": request.runoff_model.tc_hours,
            },
            "hyetograph": {
                "distribution_type": request.hyetograph.distribution_type,
                "time_step_minutes": request.hyetograph.time_step_minutes,
                "assumption": "selected_storm_shape",
                "uniform_rainfall_assumed": request.hyetograph.distribution_type == "uniform",
            },
            "selected_storm_ids": [str(cell["storm_id"]) for cell in available_cells],
            "source_artifact_hashes": {
                "frequency_panel_sha256": artifact_io.sha256(geneva.wd, "frequency_panel.json"),
                "hru_table_sha256": artifact_io.sha256(geneva.wd, "hru_table.parquet"),
                "hru_map_legend_sha256": artifact_io.sha256(geneva.wd, "hru_map_legend.json")
                if artifact_io.exists(geneva.wd, "hru_map_legend.json")
                else None,
            },
        }
        storm_inputs_relpath = artifact_io.write_json(geneva.wd, "storm_inputs.json", storm_inputs)

        storm_results: list[dict[str, Any]] = []
        failed_storm_ids: list[str] = []

        for cell in available_cells:
            storm_id = str(cell["storm_id"])
            duration_minutes = int(cell["duration_minutes"])
            depth_mm = float(cell["depth_mm"])
            tc_hours = _resolve_tc_hours(geneva, request.runoff_model.tc_hours, request.runoff_model.timing_method)
            hyetograph_response = _build_selected_hyetograph(
                geneva,
                duration_minutes=duration_minutes,
                depth_mm=depth_mm,
                time_step_minutes=request.hyetograph.time_step_minutes,
                distribution_type=request.hyetograph.distribution_type,
            )
            time_minutes = [float(value) for value in hyetograph_response["time_minutes"]]
            cumulative_rainfall_mm = [
                float(value) for value in hyetograph_response["cumulative_rainfall_mm"]
            ]

            kernel_request = {
                "kernel_schema_version": 1,
                "storm_id": storm_id,
                "lambda_mode": request.runoff_model.lambda_mode,
                "uh_method": request.runoff_model.uh_method,
                "tc_hours": tc_hours,
                "time_minutes": time_minutes,
                "cumulative_rainfall_mm": cumulative_rainfall_mm,
                "hru_rows": [
                    {
                        "hru_id": row["hru_id"],
                        "area_m2": float(row["area_m2"]),
                        "cn_lambda_020": float(row["cn_lambda_020"]),
                    }
                    for row in hru_rows
                ],
            }

            try:
                kernel_response = geneva.kernel_gateway.call_json_api(
                    "geneva_run_batch",
                    kernel_request,
                )
                storm_result = self._persist_storm_artifacts(
                    geneva,
                    storm_id=storm_id,
                    cell=cell,
                    hyetograph_response=hyetograph_response,
                    kernel_response=kernel_response,
                )
                storm_result["hru_excess"] = list(kernel_response.get("hru_excess", []) or [])
                storm_results.append(storm_result)
            except GenevaNoDbError as exc:
                failed_storm_ids.append(storm_id)
                storm_results.append(
                    {
                        "storm_id": storm_id,
                        "status": "failed",
                        "datasource_id": cell.get("datasource_id"),
                        "duration_minutes": cell.get("duration_minutes"),
                        "ari_years": cell.get("ari_years"),
                        "error": str(exc),
                    }
                )

        hru_event_measure_artifact = geneva.hru_event_measure_service.materialize_from_batch(
            geneva,
            available_cells=available_cells,
            storm_results=storm_results,
        )

        run_warnings = _watershed_area_warnings(geneva, request.hyetograph.distribution_type)

        return {
            "schema_version": 1,
            "batch_id": request.batch_id,
            "storm_inputs_relpath": storm_inputs_relpath,
            "storm_results": storm_results,
            "available_cells": available_cells,
            "unavailable_cells": unavailable_cells,
            "failed_storm_ids": failed_storm_ids,
            "run_warnings": run_warnings,
            "hru_event_measure_artifact": hru_event_measure_artifact,
            "completed_storm_ids": [
                result["storm_id"] for result in storm_results if result.get("status") == "completed"
            ],
        }

    def _persist_storm_artifacts(
        self,
        geneva: "Geneva",
        *,
        storm_id: str,
        cell: Mapping[str, Any],
        hyetograph_response: Mapping[str, Any],
        kernel_response: Mapping[str, Any],
    ) -> dict[str, Any]:
        artifact_io = geneva.artifact_io

        distribution_type = str(hyetograph_response.get("distribution_type") or "neh4_type_b")
        source_metadata = dict(hyetograph_response.get("source_metadata") or {})
        time_minutes = [float(value) for value in hyetograph_response.get("time_minutes", [])]
        cumulative_rainfall_mm = [
            float(value) for value in hyetograph_response.get("cumulative_rainfall_mm", [])
        ]
        incremental_rainfall_mm = [
            float(value) for value in hyetograph_response.get("incremental_rainfall_mm", [])
        ]
        if len(incremental_rainfall_mm) != len(cumulative_rainfall_mm):
            incremental_rainfall_mm = _incremental_from_cumulative(cumulative_rainfall_mm)
        intensity_mm_per_hr = [
            float(value) for value in hyetograph_response.get("intensity_mm_per_hr", [])
        ]
        if len(intensity_mm_per_hr) != len(cumulative_rainfall_mm):
            intensity_mm_per_hr = _intensity_series(time_minutes, incremental_rainfall_mm)

        hyetograph_records = [
            {
                "t_minutes": float(t),
                "p_cum_mm": float(p_cum),
                "p_inc_mm": float(p_inc),
                "intensity_mm_per_hr": float(intensity),
                "distribution_type": distribution_type,
                "source_distribution_type": source_metadata.get("source_distribution_type"),
                "extraction_start_hours": source_metadata.get("extraction_start_hours"),
                "extraction_end_hours": source_metadata.get("extraction_end_hours"),
                "extraction_ratio_to_24h": source_metadata.get("extraction_ratio_to_24h"),
            }
            for t, p_cum, p_inc, intensity in zip(
                time_minutes,
                cumulative_rainfall_mm,
                incremental_rainfall_mm,
                intensity_mm_per_hr,
            )
        ]

        hydrograph = kernel_response.get("hydrograph", {})
        hydro_time = [float(value) for value in hydrograph.get("time_minutes", [])]
        q_cms = [float(value) for value in hydrograph.get("q_cms", [])]
        q_cfs = [float(value) for value in hydrograph.get("q_cfs", [])]
        runoff_cum_mm = [float(value) for value in hydrograph.get("runoff_cum_mm", [])]
        runoff_volume_m3 = [float(value) for value in hydrograph.get("runoff_volume_m3", [])]

        composite = kernel_response.get("composite_excess", {})
        qex_cum_mm = [float(value) for value in composite.get("cumulative_excess_mm", [])]
        qex_inc_mm = [float(value) for value in composite.get("incremental_excess_mm", [])]

        storm_prefix = f"storms/{storm_id}"
        hyetograph_relpath = artifact_io.write_records_parquet(
            geneva.wd,
            f"{storm_prefix}/hyetograph.parquet",
            hyetograph_records,
            columns=[
                "t_minutes",
                "p_cum_mm",
                "p_inc_mm",
                "intensity_mm_per_hr",
                "distribution_type",
                "source_distribution_type",
                "extraction_start_hours",
                "extraction_end_hours",
                "extraction_ratio_to_24h",
            ],
        )
        excess_relpath = artifact_io.write_records_parquet(
            geneva.wd,
            f"{storm_prefix}/excess_hyetograph.parquet",
            [
                {
                    "t_minutes": float(t),
                    "qex_cum_mm": float(q_cum),
                    "qex_inc_mm": float(q_inc),
                }
                for t, q_cum, q_inc in zip(time_minutes, qex_cum_mm, qex_inc_mm)
            ],
            columns=["t_minutes", "qex_cum_mm", "qex_inc_mm"],
        )
        hydrograph_relpath = artifact_io.write_records_parquet(
            geneva.wd,
            f"{storm_prefix}/hydrograph.parquet",
            [
                {
                    "t_minutes": float(t),
                    "q_cms": float(cms),
                    "q_cfs": float(cfs),
                    "runoff_cum_mm": float(cum),
                    "runoff_volume_m3": float(vol),
                }
                for t, cms, cfs, cum, vol in zip(
                    hydro_time,
                    q_cms,
                    q_cfs,
                    runoff_cum_mm,
                    runoff_volume_m3,
                )
            ],
            columns=["t_minutes", "q_cms", "q_cfs", "runoff_cum_mm", "runoff_volume_m3"],
        )

        summary = {
            "storm_id": storm_id,
            "status": "completed",
            "datasource_id": cell.get("datasource_id"),
            "duration_minutes": cell.get("duration_minutes"),
            "ari_years": cell.get("ari_years"),
            "summary_metrics": kernel_response.get("summary_metrics", {}),
            "warnings": list(kernel_response.get("warnings", []) or []),
            "assumptions": {
                "arc_condition": "arc_ii",
                "storm_distribution_assumption": distribution_type,
                "distribution_type": distribution_type,
                "uniform_rainfall_assumed": distribution_type == "uniform",
                "arf_method": "constant_1.0",
                "arf_value": 1.0,
                "hyetograph_source_metadata": source_metadata,
            },
            "hyetograph": {
                "distribution_type": distribution_type,
                "time_step_minutes": hyetograph_response.get("time_step_minutes"),
                "duration_minutes": hyetograph_response.get("duration_minutes"),
                "depth_mm": hyetograph_response.get("depth_mm"),
                "source_metadata": source_metadata,
                "diagnostics": dict(hyetograph_response.get("diagnostics") or {}),
                "warnings": list(hyetograph_response.get("warnings", []) or []),
            },
            "artifacts": {
                "hyetograph_relpath": hyetograph_relpath,
                "excess_hyetograph_relpath": excess_relpath,
                "hydrograph_relpath": hydrograph_relpath,
            },
        }
        summary_relpath = artifact_io.write_json(geneva.wd, f"{storm_prefix}/summary.json", summary)
        summary["artifacts"]["summary_relpath"] = summary_relpath
        return summary


def _select_cells(
    panel_payload: Mapping[str, Any],
    event_filter: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cells_raw = panel_payload.get("cells", [])
    if not isinstance(cells_raw, list):
        raise GenevaValidationError(
            "frequency_panel.json has invalid cells payload.",
            code="contract_violation",
        )

    datasource_filter = set(event_filter.datasource_ids)
    duration_filter = set(event_filter.durations_minutes)
    ari_filter = set(event_filter.ari_years)

    available: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []

    for raw in cells_raw:
        if not isinstance(raw, dict):
            continue
        datasource_id = str(raw.get("datasource_id", ""))
        duration = int(raw.get("duration_minutes", 0) or 0)
        ari = int(raw.get("ari_years", 0) or 0)

        if datasource_filter and datasource_id not in datasource_filter:
            continue
        if duration_filter and duration not in duration_filter:
            continue
        if ari_filter and ari not in ari_filter:
            continue

        availability = str(raw.get("availability", "unavailable"))
        storm = {
            "storm_id": str(raw.get("storm_id", "")),
            "datasource_id": datasource_id,
            "duration_minutes": duration,
            "ari_years": ari,
            "depth_mm": raw.get("depth_mm"),
            "intensity_mm_per_hr": raw.get("intensity_mm_per_hr"),
            "distribution_type": raw.get("distribution_type") or panel_payload.get("distribution_type"),
            "reason_code": raw.get("reason_code"),
        }

        if availability == "available" and storm["depth_mm"] not in (None, ""):
            available.append(storm)
        else:
            unavailable.append(storm)

    available.sort(key=_storm_sort_key)
    unavailable.sort(key=_storm_sort_key)
    return available, unavailable


def _non_uniform_duration_minutes(
    available_cells: list[dict[str, Any]],
    time_step_minutes: float,
) -> list[int]:
    incompatible: set[int] = set()
    for cell in available_cells:
        duration_minutes = int(cell.get("duration_minutes", 0) or 0)
        if duration_minutes <= 0:
            continue
        ratio = float(duration_minutes) / float(time_step_minutes)
        nearest = round(ratio)
        if abs(ratio - float(nearest)) > 1e-9:
            incompatible.add(duration_minutes)
    return sorted(incompatible)


def _storm_sort_key(cell: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(cell.get("datasource_id", "")),
        int(cell.get("duration_minutes", 0) or 0),
        int(cell.get("ari_years", 0) or 0),
        str(cell.get("storm_id", "")),
    )


def _resolve_tc_hours(geneva: "Geneva", tc_hours: float | None, timing_method: str | None) -> float:
    if tc_hours is not None:
        return float(tc_hours)

    wsarea = float(getattr(geneva.watershed_instance, "wsarea", 1.0) or 1.0)
    area_km2 = max(wsarea / 1_000_000.0, 0.01)
    method = (timing_method or "kirpich").lower()

    if method == "kirpich":
        return max(0.25, min(6.0, 0.6 * math.sqrt(area_km2)))
    if method == "kent":
        return max(0.25, min(6.0, 0.8 * math.sqrt(area_km2)))
    if method == "simas":
        return max(0.25, min(6.0, 1.0 * math.sqrt(area_km2)))

    raise GenevaValidationError(
        "Unsupported timing_method.",
        code="invalid_input",
        details={"timing_method": timing_method},
    )


def _build_selected_hyetograph(
    geneva: "Geneva",
    *,
    duration_minutes: int,
    depth_mm: float,
    time_step_minutes: float,
    distribution_type: str,
) -> dict[str, Any]:
    if duration_minutes <= 0:
        raise GenevaValidationError(
            "duration_minutes must be > 0.",
            code="invalid_input",
            details={"duration_minutes": duration_minutes},
        )
    if depth_mm <= 0.0:
        raise GenevaValidationError(
            "depth_mm must be > 0.",
            code="invalid_input",
            details={"depth_mm": depth_mm},
        )

    payload = {
        "kernel_schema_version": 1,
        "duration_minutes": float(duration_minutes),
        "depth_mm": float(depth_mm),
        "time_step_minutes": float(time_step_minutes),
        "distribution_type": distribution_type,
    }
    response = geneva.kernel_gateway.call_json_api("geneva_build_hyetograph", payload)
    if str(response.get("status")) != "ok":
        raise GenevaKernelError(
            "geneva_build_hyetograph returned non-ok status.",
            code="contract_violation",
            details=response,
            status_code=500,
        )
    for field in ("time_minutes", "cumulative_rainfall_mm"):
        if not isinstance(response.get(field), list) or not response[field]:
            raise GenevaKernelError(
                "geneva_build_hyetograph returned invalid hyetograph series.",
                code="contract_violation",
                details={"field": field},
                status_code=500,
            )

    return response


def _incremental_from_cumulative(cumulative: list[float]) -> list[float]:
    incremental: list[float] = []
    previous = 0.0
    for value in cumulative:
        delta = float(value) - previous
        incremental.append(max(delta, 0.0))
        previous = float(value)
    return incremental


def _intensity_series(time_minutes: list[float], incremental_mm: list[float]) -> list[float]:
    if len(time_minutes) != len(incremental_mm):
        return [0.0 for _ in incremental_mm]
    intensities = [0.0]
    for index in range(1, len(time_minutes)):
        delta_t = max(time_minutes[index] - time_minutes[index - 1], 1e-6)
        intensity = (incremental_mm[index] / delta_t) * 60.0
        intensities.append(float(intensity))
    return intensities


def _watershed_area_warnings(geneva: "Geneva", distribution_type: str) -> list[dict[str, Any]]:
    try:
        watershed = geneva.watershed_instance
    except FileNotFoundError:
        return []

    wsarea_m2 = float(getattr(watershed, "wsarea", 0.0) or 0.0)
    if wsarea_m2 <= 0.0:
        return []

    wsarea_km2 = wsarea_m2 / 1_000_000.0
    if wsarea_km2 > EXTREME_WARNING_AREA_KM2:
        severity = "extreme"
        threshold_km2 = EXTREME_WARNING_AREA_KM2
    elif wsarea_km2 > SEVERE_WARNING_AREA_KM2:
        severity = "severe"
        threshold_km2 = SEVERE_WARNING_AREA_KM2
    elif wsarea_km2 > WARNING_AREA_KM2:
        severity = "warning"
        threshold_km2 = WARNING_AREA_KM2
    else:
        return []

    wsarea_mi2 = wsarea_km2 * _KM2_TO_MI2
    wsarea_acres = wsarea_m2 * _M2_TO_ACRES

    return [
        {
            "code": "point_rainfall_assumption",
            "severity": severity,
            "message": "Point rainfall assumption may under-represent watershed-scale variability.",
            "wsarea_km2": round(wsarea_km2, 4),
            "wsarea_mi2": round(wsarea_mi2, 4),
            "wsarea_acres": round(wsarea_acres, 4),
            "threshold_km2": threshold_km2,
            "thresholds_km2": {
                "warning": WARNING_AREA_KM2,
                "severe": SEVERE_WARNING_AREA_KM2,
                "extreme": EXTREME_WARNING_AREA_KM2,
            },
            "arf_method": "constant_1.0",
            "arf_value": 1.0,
            "uniform_rainfall_assumed": distribution_type == "uniform",
        }
    ]


__all__ = ["GenevaBatchRunService"]
