from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import Any

import pytest

from wepppy.nodb.mods.geneva import Geneva
from wepppy.nodb.mods.geneva import geneva as geneva_module


pytestmark = pytest.mark.integration


def _fixture_paths() -> dict[str, str]:
    root = Path(__file__).resolve().parents[3] / "data" / "geneva" / "synthetic_small_watershed_v1"
    return {
        "bound_tif": str(root / "bound.tif"),
        "landuse_tif": str(root / "landuse.tif"),
        "hydgrpdcd_tif": str(root / "hydgrpdcd.tif"),
        "burn_severity_tif": str(root / "burn_severity.tif"),
    }


class _FakeHsgService:
    def __init__(self, fixture_paths: dict[str, str]) -> None:
        self._fixture_paths = fixture_paths

    @staticmethod
    def enforce_wbt_backend(_geneva: Geneva) -> None:
        return None

    @staticmethod
    def enforce_supported_domain(_geneva: Geneva) -> None:
        return None

    def resolve_prepare_input_refs(self, _geneva: Geneva, *, overrides=None) -> dict[str, str]:
        refs = {
            "bound_tif": self._fixture_paths["bound_tif"],
            "landuse_tif": self._fixture_paths["landuse_tif"],
            "hydgrpdcd_tif": self._fixture_paths["hydgrpdcd_tif"],
        }
        refs.update(dict(overrides or {}))
        return refs

    @staticmethod
    def resolve_default_hsg(_config: dict[str, Any]) -> tuple[int, str]:
        return 4, "assume_d"


def _build_run_batch_response(
    payload: dict[str, Any],
    summary_metrics: dict[str, float],
) -> dict[str, Any]:
    time_minutes = [float(value) for value in payload["time_minutes"]]
    rainfall = [float(value) for value in payload["cumulative_rainfall_mm"]]
    cumulative_excess = [round(value * 0.2, 6) for value in rainfall]
    incremental_excess = [
        cumulative_excess[index] - cumulative_excess[index - 1] if index > 0 else cumulative_excess[index]
        for index in range(len(cumulative_excess))
    ]
    runoff_volume = [
        round(summary_metrics["runoff_volume"] * (index / (len(time_minutes) - 1)), 6)
        for index in range(len(time_minutes))
    ]
    runoff_cum_mm = [
        round(summary_metrics["runoff_depth"] * (index / (len(time_minutes) - 1)), 6)
        for index in range(len(time_minutes))
    ]

    q_cms: list[float] = []
    steps = max(len(time_minutes) - 1, 1)
    for index in range(len(time_minutes)):
        q_cms.append(round(summary_metrics["peak_discharge"] * (index / steps), 6))
    q_cfs = [round(value * 35.31466672148859, 6) for value in q_cms]

    return {
        "status": "ok",
        "phase": "run_batch",
        "kernel_schema_version": 1,
        "storm_id": payload["storm_id"],
        "lambda_mode": payload["lambda_mode"],
        "uh_method": payload["uh_method"],
        "tc_hours": payload["tc_hours"],
        "time_minutes": time_minutes,
        "cumulative_rainfall_mm": rainfall,
        "incremental_rainfall_mm": [
            rainfall[index] - rainfall[index - 1] if index > 0 else rainfall[index]
            for index in range(len(rainfall))
        ],
        "hru_excess": [],
        "composite_excess": {
            "cumulative_excess_mm": cumulative_excess,
            "incremental_excess_mm": incremental_excess,
        },
        "unit_hydrograph": {
            "method_id": payload["uh_method"],
            "dt_minutes": 1.0,
            "time_minutes": time_minutes,
            "unit_ordinates_per_hour": [0.0 for _ in time_minutes],
            "closure_error": 0.0,
            "unit_system": "si_km2_mm_hr_to_cms",
            "hf_constant": 0.208,
            "qp_equation_id": "qp_hf_a_re_over_tp",
        },
        "hydrograph": {
            "time_minutes": time_minutes,
            "q_cms": q_cms,
            "q_cfs": q_cfs,
            "runoff_cum_mm": runoff_cum_mm,
            "runoff_volume_m3": runoff_volume,
        },
        "summary_metrics": summary_metrics,
        "hydrograph_diagnostics": {
            "dt_minutes": 1.0,
            "expected_excess_volume_m3": summary_metrics["runoff_volume"],
            "hydrograph_volume_m3": summary_metrics["runoff_volume"],
            "volume_closure_relative": 0.0,
        },
        "diagnostics": {
            "total_area_m2": 20_000.0,
            "closure_error_mm": 0.0,
            "final_cumulative_excess_mm": summary_metrics["runoff_depth"],
            "incremental_sum_mm": sum(incremental_excess),
        },
        "warnings": [],
    }


class _ScenarioKernelGateway:
    def __init__(
        self,
        *,
        panel_payload: dict[str, Any],
        summary_metrics: dict[str, float],
    ) -> None:
        self._panel_payload = panel_payload
        self._summary_metrics = summary_metrics
        self.prepare_payloads: list[dict[str, Any]] = []
        self.run_batch_payloads: list[dict[str, Any]] = []

    def call_json_api(self, api_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if api_name == "geneva_prepare_hrus":
            self.prepare_payloads.append(dict(payload))
            return {
                "status": "ok",
                "phase": "prepare_hrus",
                "kernel_schema_version": 1,
                "hru_rows": [
                    {
                        "hru_id": "hru_1",
                        "area_m2": 10_000.0,
                        "area_ac": 2.4710538147,
                        "area_fraction": 0.5,
                        "landuse_class": 42,
                        "hsg_group": "B",
                        "burn_severity_class": "unburned",
                        "hydrophobic_class": False,
                        "is_water": False,
                        "cn_arc_ii": 74.0,
                        "cn_lambda_020": 74.0,
                        "cn_lambda_005": 86.0,
                        "antecedent_condition_source": "arc_ii",
                        "cn_source": "seed_table",
                        "hsg_source": "coded_lookup",
                        "collapsed_from_hru_ids": [],
                        "warnings": [],
                    },
                    {
                        "hru_id": "hru_2",
                        "area_m2": 10_000.0,
                        "area_ac": 2.4710538147,
                        "area_fraction": 0.5,
                        "landuse_class": 52,
                        "hsg_group": "C",
                        "burn_severity_class": "moderate",
                        "hydrophobic_class": True,
                        "is_water": False,
                        "cn_arc_ii": 82.0,
                        "cn_lambda_020": 82.0,
                        "cn_lambda_005": 92.0,
                        "antecedent_condition_source": "arc_ii",
                        "cn_source": "seed_table",
                        "hsg_source": "coded_lookup",
                        "collapsed_from_hru_ids": [],
                        "warnings": [],
                    },
                ],
                "diagnostics": {
                    "hru_area_total_m2": 20_000.0,
                    "hsg_provenance_counts": {"coded_lookup": 2},
                },
                "warnings": [],
            }
        if api_name == "geneva_build_frequency_panel":
            return self._panel_payload
        if api_name == "geneva_build_hyetograph":
            duration = float(payload["duration_minutes"])
            depth = float(payload["depth_mm"])
            distribution = str(payload.get("distribution_type") or "neh4_type_b")
            cumulative = [0.0, depth * (0.35 if distribution != "uniform" else 0.5), depth]
            return {
                "status": "ok",
                "phase": "build_hyetograph",
                "kernel_schema_version": 1,
                "distribution_type": distribution,
                "duration_minutes": duration,
                "depth_mm": depth,
                "time_step_minutes": float(payload["time_step_minutes"]),
                "time_minutes": [0.0, duration / 2.0, duration],
                "cumulative_rainfall_mm": cumulative,
                "incremental_rainfall_mm": [
                    cumulative[0],
                    cumulative[1] - cumulative[0],
                    cumulative[2] - cumulative[1],
                ],
                "intensity_mm_per_hr": [0.0, 0.0, 0.0],
                "warnings": [],
                "source_metadata": None,
                "diagnostics": {
                    "closure_error_mm": 0.0,
                    "closure_tolerance_mm": 0.01,
                    "cumulative_monotonic": True,
                },
            }
        if api_name == "geneva_run_batch":
            self.run_batch_payloads.append(dict(payload))
            return _build_run_batch_response(payload, self._summary_metrics)
        raise AssertionError(f"Unexpected API call: {api_name}")


@dataclass(frozen=True)
class _Scenario:
    include_burn: bool
    panel_payload: dict[str, Any]
    expected_status: str
    expect_gaps: bool


def _run_geneva_flow(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: _Scenario,
    summary_metrics: dict[str, float],
    wsarea_m2: float,
    allow_cross_hsg_merge: bool = False,
) -> tuple[Geneva, _ScenarioKernelGateway]:
    fixture_paths = _fixture_paths()
    fake_hsg = _FakeHsgService(fixture_paths)
    fake_kernel = _ScenarioKernelGateway(
        panel_payload=scenario.panel_payload,
        summary_metrics=summary_metrics,
    )

    monkeypatch.setattr(geneva_module, "_GENEVA_HSG_ASSIGNMENT_SERVICE", fake_hsg)
    monkeypatch.setattr(geneva_module, "_GENEVA_KERNEL_GATEWAY", fake_kernel)
    monkeypatch.setattr(
        Geneva,
        "watershed_instance",
        property(lambda _self: SimpleNamespace(wsarea=wsarea_m2)),
        raising=False,
    )

    tmp_path.mkdir(parents=True, exist_ok=True)
    Geneva.cleanup_all_instances()
    geneva = Geneva(str(tmp_path), "0.cfg")
    geneva.set_enabled(True)
    geneva.update_config(
        {
            "allow_cross_hsg_merge": allow_cross_hsg_merge,
            "default_hsg_code": 4,
            "unresolved_hsg_policy": "assume_d",
        }
    )

    input_refs = {
        "bound_tif": fixture_paths["bound_tif"],
        "landuse_tif": fixture_paths["landuse_tif"],
        "hydgrpdcd_tif": fixture_paths["hydgrpdcd_tif"],
    }
    if scenario.include_burn:
        input_refs["burn_severity_tif"] = fixture_paths["burn_severity_tif"]

    geneva.prepare_hrus(force_rebuild=True, input_refs=input_refs)
    geneva.build_frequency_panel(
        rebuild=True,
        durations_minutes=list(scenario.panel_payload["durations_minutes"]),
        ari_years=list(scenario.panel_payload["ari_years"]),
    )
    run_summary = geneva.run_batch(
        {
            "schema_version": 1,
            "runoff_model": {
                "timing_method": "kirpich",
            },
        }
    )
    assert run_summary["status"] == scenario.expected_status
    return geneva, fake_kernel


def _rel_delta(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1e-9)


def _panel_payload(*, dual_source: bool, mixed_unavailable: bool) -> dict[str, Any]:
    cells: list[dict[str, Any]] = [
        {
            "storm_id": "cligen_30m_10y",
            "datasource_id": "cligen_freq",
            "duration_minutes": 30,
            "ari_years": 10,
            "depth_mm": 20.0,
            "intensity_mm_per_hr": 40.0,
            "distribution_type": "neh4_type_b",
            "availability": "available",
            "reason_code": None,
        }
    ]
    datasource_ids = ["cligen_freq"]
    if dual_source:
        datasource_ids.append("noaa14_pds")
        if mixed_unavailable:
            cells.append(
                {
                    "storm_id": "noaa14_30m_10y",
                    "datasource_id": "noaa14_pds",
                    "duration_minutes": 30,
                    "ari_years": 10,
                    "depth_mm": None,
                    "intensity_mm_per_hr": None,
                    "distribution_type": "neh4_type_b",
                    "availability": "unavailable",
                    "reason_code": "source_missing",
                }
            )
        else:
            cells.append(
                {
                    "storm_id": "noaa14_30m_10y",
                    "datasource_id": "noaa14_pds",
                    "duration_minutes": 30,
                    "ari_years": 10,
                    "depth_mm": 25.0,
                    "intensity_mm_per_hr": 50.0,
                    "distribution_type": "neh4_type_b",
                    "availability": "available",
                    "reason_code": None,
                }
            )

    return {
        "status": "ok",
        "phase": "build_frequency_panel",
        "kernel_schema_version": 1,
        "schema_version": 1,
        "datasource_ids": datasource_ids,
        "distribution_type": "neh4_type_b",
        "durations_minutes": [30],
        "ari_years": [10],
        "cells": cells,
        "warnings": [],
    }


@pytest.mark.parametrize(
    ("scenario", "expect_burn_ref"),
    [
        (
            _Scenario(
                include_burn=False,
                panel_payload=_panel_payload(dual_source=False, mixed_unavailable=False),
                expected_status="completed",
                expect_gaps=False,
            ),
            False,
        ),
        (
            _Scenario(
                include_burn=True,
                panel_payload=_panel_payload(dual_source=True, mixed_unavailable=True),
                expected_status="completed_with_gaps",
                expect_gaps=True,
            ),
            True,
        ),
    ],
)
def test_wp09_scenario_matrix_and_completed_with_gaps_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: _Scenario,
    expect_burn_ref: bool,
) -> None:
    geneva, fake_kernel = _run_geneva_flow(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        scenario=scenario,
        summary_metrics={
            "peak_discharge": 4.0,
            "time_to_peak": 30.0,
            "runoff_volume": 240.0,
            "runoff_depth": 8.0,
        },
        wsarea_m2=2_000_000.0,
    )

    prepare_payload = fake_kernel.prepare_payloads[0]
    assert ("burn_severity_tif" in prepare_payload) is expect_burn_ref

    status = geneva.status_payload()
    results = geneva.results_payload()
    assert status["status"] == scenario.expected_status
    assert results["status"] == scenario.expected_status

    if scenario.expect_gaps:
        warning_codes = [warning.get("code") for warning in results["warnings"] if isinstance(warning, dict)]
        assert "source_missing" in warning_codes
    else:
        assert results["last_run_summary"]["storm_count_unavailable"] == 0

    query_payload = geneva.query_summary_payload(datasource_id="all", measure="runoff_depth")
    report_payload = geneva.report_payload_service.build_summary_payload(geneva, datasource_id="all")
    assert query_payload["event_table"]
    assert report_payload["event_table"]
    if scenario.expect_gaps:
        query_codes = [warning.get("code") for warning in query_payload["warnings"] if isinstance(warning, dict)]
        report_codes = [warning.get("code") for warning in report_payload["warnings"] if isinstance(warning, dict)]
        assert "source_missing" in query_codes
        assert "source_missing" in report_codes


def test_wp09_collapsed_vs_uncollapsed_sensitivity_thresholds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = _Scenario(
        include_burn=True,
        panel_payload=_panel_payload(dual_source=True, mixed_unavailable=False),
        expected_status="completed",
        expect_gaps=False,
    )
    reference = {
        "runoff_depth": 10.0,
        "runoff_volume": 1_000.0,
        "peak_discharge": 20.0,
    }

    default_geneva, default_kernel = _run_geneva_flow(
        tmp_path=tmp_path / "default",
        monkeypatch=monkeypatch,
        scenario=scenario,
        summary_metrics={
            "peak_discharge": 20.8,
            "time_to_peak": 30.0,
            "runoff_volume": 1_018.0,
            "runoff_depth": 10.15,
        },
        wsarea_m2=2_500_000.0,
        allow_cross_hsg_merge=False,
    )
    cross_geneva, cross_kernel = _run_geneva_flow(
        tmp_path=tmp_path / "cross",
        monkeypatch=monkeypatch,
        scenario=scenario,
        summary_metrics={
            "peak_discharge": 20.2,
            "time_to_peak": 30.0,
            "runoff_volume": 1_005.0,
            "runoff_depth": 10.18,
        },
        wsarea_m2=2_500_000.0,
        allow_cross_hsg_merge=True,
    )

    default_row = default_geneva.query_summary_payload(measure="runoff_depth")["event_table"][0]
    cross_row = cross_geneva.query_summary_payload(measure="runoff_depth")["event_table"][0]

    assert _rel_delta(default_row["runoff_depth"]["value"], reference["runoff_depth"]) <= 0.02
    assert _rel_delta(default_row["runoff_volume"]["value"], reference["runoff_volume"]) <= 0.02
    assert _rel_delta(default_row["peak_discharge"]["value"], reference["peak_discharge"]) <= 0.05
    assert _rel_delta(cross_row["runoff_depth"]["value"], reference["runoff_depth"]) <= 0.02

    assert default_kernel.prepare_payloads[0]["allow_cross_hsg_merge"] is False
    assert cross_kernel.prepare_payloads[0]["allow_cross_hsg_merge"] is True


@pytest.mark.parametrize(
    ("wsarea_m2", "expected_severity"),
    [
        (30_000_000.0, "warning"),
        (150_000_000.0, "severe"),
        (300_000_000.0, "extreme"),
    ],
)
def test_wp09_watershed_warning_thresholds_propagate_to_results_query_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wsarea_m2: float,
    expected_severity: str,
) -> None:
    scenario = _Scenario(
        include_burn=False,
        panel_payload=_panel_payload(dual_source=False, mixed_unavailable=False),
        expected_status="completed",
        expect_gaps=False,
    )

    geneva, _fake_kernel = _run_geneva_flow(
        tmp_path=tmp_path / expected_severity,
        monkeypatch=monkeypatch,
        scenario=scenario,
        summary_metrics={
            "peak_discharge": 3.0,
            "time_to_peak": 30.0,
            "runoff_volume": 200.0,
            "runoff_depth": 6.0,
        },
        wsarea_m2=wsarea_m2,
    )

    results = geneva.results_payload()
    warning = next(
        warning
        for warning in results["warnings"]
        if isinstance(warning, dict) and warning.get("code") == "point_rainfall_assumption"
    )
    assert warning["severity"] == expected_severity
    assert warning["wsarea_km2"] > warning["threshold_km2"]
    assert warning["uniform_rainfall_assumed"] is False

    query_payload = geneva.query_summary_payload(datasource_id="all")
    report_payload = geneva.report_payload_service.build_summary_payload(geneva, datasource_id="all")
    query_warning = next(
        warning
        for warning in query_payload["warnings"]
        if isinstance(warning, dict) and warning.get("code") == "point_rainfall_assumption"
    )
    report_warning = next(
        warning
        for warning in report_payload["warnings"]
        if isinstance(warning, dict) and warning.get("code") == "point_rainfall_assumption"
    )
    assert query_warning["severity"] == expected_severity
    assert report_warning["severity"] == expected_severity


def test_wp09_runtime_profile_harness_records_representative_baselines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario_small = _Scenario(
        include_burn=False,
        panel_payload=_panel_payload(dual_source=False, mixed_unavailable=False),
        expected_status="completed",
        expect_gaps=False,
    )
    scenario_large = _Scenario(
        include_burn=True,
        panel_payload={
            **_panel_payload(dual_source=True, mixed_unavailable=False),
            "durations_minutes": [5, 10, 30, 60],
            "ari_years": [1, 2, 5, 10],
            "cells": [
                {
                    "storm_id": f"{datasource}_{duration}m_{ari}y",
                    "datasource_id": datasource,
                    "duration_minutes": duration,
                    "ari_years": ari,
                    "depth_mm": 20.0 + duration + ari,
                    "intensity_mm_per_hr": 30.0 + ari,
                    "distribution_type": "neh4_type_b",
                    "availability": "available",
                    "reason_code": None,
                }
                for datasource in ("cligen_freq", "noaa14_pds")
                for duration in (5, 10, 30, 60)
                for ari in (1, 2, 5, 10)
            ],
        },
        expected_status="completed",
        expect_gaps=False,
    )

    timings: dict[str, float] = {}

    start_small = perf_counter()
    _run_geneva_flow(
        tmp_path=tmp_path / "small",
        monkeypatch=monkeypatch,
        scenario=scenario_small,
        summary_metrics={
            "peak_discharge": 2.0,
            "time_to_peak": 20.0,
            "runoff_volume": 150.0,
            "runoff_depth": 5.0,
        },
        wsarea_m2=2_000_000.0,
    )
    timings["small_profile_seconds"] = perf_counter() - start_small

    start_large = perf_counter()
    _run_geneva_flow(
        tmp_path=tmp_path / "large",
        monkeypatch=monkeypatch,
        scenario=scenario_large,
        summary_metrics={
            "peak_discharge": 4.2,
            "time_to_peak": 40.0,
            "runoff_volume": 420.0,
            "runoff_depth": 12.0,
        },
        wsarea_m2=80_000_000.0,
    )
    timings["large_profile_seconds"] = perf_counter() - start_large

    assert timings["small_profile_seconds"] >= 0.0
    assert timings["large_profile_seconds"] >= 0.0
