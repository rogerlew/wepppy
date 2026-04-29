from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from wepppy.nodb.mods.geneva import Geneva
from wepppy.nodb.mods.geneva import geneva as geneva_module
from wepppy.nodb.mods.geneva.errors import GenevaKernelError


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

    def resolve_prepare_input_refs(self, _geneva: Geneva, *, overrides=None):
        refs = dict(self._fixture_paths)
        refs.update(dict(overrides or {}))
        return refs

    @staticmethod
    def resolve_default_hsg(_config: dict[str, Any]):
        return None, None


class _FakeKernelGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call_json_api(self, api_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((api_name, dict(payload)))

        if api_name == "geneva_prepare_hrus":
            self._materialize_hru_map_artifacts(payload)
            return {
                "status": "ok",
                "phase": "prepare_hrus",
                "kernel_schema_version": 1,
                "hru_rows": [
                    {
                        "hru_id": "hru_1",
                        "area_m2": 900.0,
                        "area_ac": 0.22239484332044878,
                        "area_fraction": 1.0,
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
                    }
                ],
                "diagnostics": {
                    "hru_area_total_m2": 900.0,
                    "hsg_provenance_counts": {"coded_lookup": 1},
                },
                "hru_map": {
                    "nodata_value": 0,
                    "hru_value_count": 1,
                    "fallback_id_match_count": 0,
                    "mapping_status": "complete",
                    "active_cell_count": 1,
                    "mapped_cell_count": 1,
                    "unmapped_cell_count": 0,
                    "unresolved_component_count": 0,
                    "unresolved_component_samples": [],
                },
                "warnings": [],
            }

        if api_name == "geneva_build_frequency_panel":
            distribution = str(payload.get("distribution_type") or "neh4_type_b")
            return {
                "status": "ok",
                "phase": "build_frequency_panel",
                "kernel_schema_version": 1,
                "datasource_ids": ["cligen_freq", "noaa14_pds"],
                "distribution_type": distribution,
                "durations_minutes": [30],
                "ari_years": [10],
                "cells": [
                    {
                        "storm_id": "cligen_30m_10y",
                        "datasource_id": "cligen_freq",
                        "duration_minutes": 30,
                        "ari_years": 10,
                        "depth_mm": 20.0,
                        "intensity_mm_per_hr": 40.0,
                        "distribution_type": distribution,
                        "availability": "available",
                        "reason_code": None,
                    },
                    {
                        "storm_id": "noaa14_30m_10y",
                        "datasource_id": "noaa14_pds",
                        "duration_minutes": 30,
                        "ari_years": 10,
                        "depth_mm": None,
                        "intensity_mm_per_hr": None,
                        "distribution_type": distribution,
                        "availability": "unavailable",
                        "reason_code": "source_missing",
                    },
                ],
                "warnings": [],
            }

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
            time_minutes = [float(v) for v in payload["time_minutes"]]
            rainfall = [float(v) for v in payload["cumulative_rainfall_mm"]]
            incremental_rainfall = [
                rainfall[idx] - rainfall[idx - 1] if idx > 0 else rainfall[idx]
                for idx in range(len(rainfall))
            ]
            cumulative_excess = [round(v * 0.2, 6) for v in rainfall]
            incremental_excess = [
                cumulative_excess[idx] - cumulative_excess[idx - 1] if idx > 0 else cumulative_excess[idx]
                for idx in range(len(cumulative_excess))
            ]
            q_cms = [round(idx * 0.12, 6) for idx in range(len(time_minutes))]
            q_cfs = [round(value * 35.31466672148859, 6) for value in q_cms]
            runoff_volume = [round(value * 3.0, 6) for value in cumulative_excess]

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
                "incremental_rainfall_mm": incremental_rainfall,
                "hru_excess": [
                    {
                        "hru_id": "hru_1",
                        "area_m2": 900.0,
                        "area_fraction": 1.0,
                        "cn_lambda_020": 74.0,
                        "cn_lambda_005": 86.0,
                        "selected_cn": 74.0,
                        "storage_mm": 89.0,
                        "initial_abstraction_mm": 17.8,
                        "cumulative_excess_mm": cumulative_excess,
                        "incremental_excess_mm": incremental_excess,
                    }
                ],
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
                    "runoff_cum_mm": cumulative_excess,
                    "runoff_volume_m3": runoff_volume,
                },
                "summary_metrics": {
                    "peak_discharge": max(q_cms),
                    "time_to_peak": time_minutes[q_cms.index(max(q_cms))],
                    "runoff_volume": runoff_volume[-1],
                    "runoff_depth": cumulative_excess[-1],
                },
                "hydrograph_diagnostics": {
                    "dt_minutes": 1.0,
                    "expected_excess_volume_m3": runoff_volume[-1],
                    "hydrograph_volume_m3": runoff_volume[-1],
                    "volume_closure_relative": 0.0,
                },
                "diagnostics": {
                    "total_area_m2": 900.0,
                    "closure_error_mm": 0.0,
                    "final_cumulative_excess_mm": cumulative_excess[-1],
                    "incremental_sum_mm": sum(incremental_excess),
                },
                "warnings": [],
            }

        raise AssertionError(f"Unexpected API call: {api_name}")

    def _materialize_hru_map_artifacts(self, payload: dict[str, Any]) -> None:
        map_path = str(payload.get("hru_map_output_tif") or "").strip()
        legend_path = str(payload.get("hru_map_legend_output_json") or "").strip()
        if map_path:
            path = Path(map_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fake-geotiff")
        if legend_path:
            path = Path(legend_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "hru_map_relpath": "hru_map.tif",
                        "nodata_value": 0,
                        "mapping_status": "complete",
                        "active_cell_count": 1,
                        "mapped_cell_count": 1,
                        "unmapped_cell_count": 0,
                        "unresolved_component_count": 0,
                        "unresolved_component_samples": [],
                        "rows": [
                            {
                                "hru_value": 1,
                                "hru_id": "hru_1",
                                "landuse_class": 42,
                                "hsg_group": "B",
                                "burn_severity_class": "unburned",
                                "hydrophobic_class": False,
                                "is_water": False,
                                "collapsed_from_hru_ids": [],
                            }
                        ],
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )


class _FailingPrepareKernelGateway(_FakeKernelGateway):
    def call_json_api(self, api_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((api_name, dict(payload)))
        if api_name == "geneva_prepare_hrus":
            raise GenevaKernelError(
                "Prepare failed",
                code="invalid_input",
                details="synthetic prepare failure",
            )
        return super().call_json_api(api_name, payload)


def test_geneva_auto_enables_on_first_initialization(tmp_path: Path) -> None:
    geneva = Geneva(str(tmp_path), "0.cfg")

    assert geneva.enabled is True
    assert geneva.get_config()["enabled"] is True
    assert "enabled" in geneva._timestamps


def test_geneva_reenables_on_reload_when_mod_is_present(tmp_path: Path) -> None:
    geneva = Geneva(str(tmp_path), "0.cfg")
    geneva.set_enabled(False)

    Geneva.cleanup_all_instances()
    reloaded = Geneva.getInstance(str(tmp_path))
    assert reloaded.enabled is True
    assert reloaded.get_config()["enabled"] is True


def test_prepare_hrus_facade_delegates_to_collaborator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_paths = _fixture_paths()
    fake_hsg = _FakeHsgService(fixture_paths)

    calls: list[dict[str, Any]] = []

    class _SpyHruService:
        def prepare_hrus(self, _geneva: Geneva, *, force_rebuild: bool, input_refs=None):
            calls.append({"force_rebuild": force_rebuild, "input_refs": dict(input_refs or {})})
            return {
                "status": "ok",
                "phase": "prepare_hrus",
                "hru_count": 1,
                "hru_area_total_m2": 900.0,
                "hru_area_total_acres": 0.222,
                "hsg_provenance_counts": {"coded_lookup": 1},
                "warnings": [],
                "input_refs": dict(fixture_paths),
                "artifacts": {
                    "hru_table_relpath": "hru_table.parquet",
                    "hru_prepare_summary_relpath": "hru_prepare_summary.json",
                    "hru_map_relpath": "hru_map.tif",
                    "hru_map_legend_relpath": "hru_map_legend.json",
                },
            }

    monkeypatch.setattr(geneva_module, "_GENEVA_HSG_ASSIGNMENT_SERVICE", fake_hsg)
    monkeypatch.setattr(geneva_module, "_GENEVA_HRU_PREPARATION_SERVICE", _SpyHruService())

    geneva = Geneva(str(tmp_path), "0.cfg")
    geneva.set_enabled(True)
    result = geneva.prepare_hrus(force_rebuild=True, input_refs={"bound_tif": fixture_paths["bound_tif"]})

    assert result["hru_count"] == 1
    assert geneva.status_payload()["status"] == "prepared"
    assert len(calls) == 1
    assert calls[0]["force_rebuild"] is True


def test_geneva_lifecycle_transitions_and_persistence_roundtrip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_paths = _fixture_paths()
    fake_hsg = _FakeHsgService(fixture_paths)
    fake_kernel = _FakeKernelGateway()

    monkeypatch.setattr(geneva_module, "_GENEVA_HSG_ASSIGNMENT_SERVICE", fake_hsg)
    monkeypatch.setattr(geneva_module, "_GENEVA_KERNEL_GATEWAY", fake_kernel)

    geneva = Geneva(str(tmp_path), "0.cfg")
    assert geneva.status_payload()["status"] == "idle"

    geneva.set_enabled(True)
    geneva.prepare_hrus(force_rebuild=True)
    assert geneva.status_payload()["status"] == "prepared"
    state_after_prepare = geneva.state_payload()
    assert state_after_prepare["artifacts"]["hru_table_ready"] is True
    assert state_after_prepare["artifacts"]["hru_map_ready"] is True
    assert state_after_prepare["artifacts"]["hru_map_legend_ready"] is True
    assert state_after_prepare["artifacts"]["hru_event_measure_rows_ready"] is False

    panel = geneva.build_frequency_panel(rebuild=True)
    assert len(panel["cells"]) == 2
    assert (tmp_path / "geneva" / "frequency_panel.json").exists()

    run_summary = geneva.run_batch(
        {
            "schema_version": 1,
            "runoff_model": {
                "tc_hours": 1.1,
            },
        }
    )
    assert run_summary["status"] == "completed_with_gaps"
    status_payload = geneva.status_payload()
    assert status_payload["status"] == "completed_with_gaps"
    assert status_payload["progress"]["completed"] == 1
    assert status_payload["progress"]["total"] == 2
    assert run_summary["artifacts"]["hru_event_measure_relpath"] == "geneva/hru_event_measure_rows.parquet"

    assert (tmp_path / "geneva" / "batch_summary.json").exists()
    assert (tmp_path / "geneva" / "hru_event_measure_rows.parquet").exists()
    assert (tmp_path / "geneva" / "storms" / "cligen_30m_10y" / "summary.json").exists()

    Geneva.cleanup_all_instances()
    reloaded = Geneva.getInstance(str(tmp_path))
    assert reloaded.status_payload()["status"] == "completed_with_gaps"
    assert reloaded.results_payload()["last_run_summary"]["storm_count_total"] == 2


def test_build_frequency_panel_shape_change_rebuilds_cache_and_clears_run_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_paths = _fixture_paths()
    fake_hsg = _FakeHsgService(fixture_paths)
    fake_kernel = _FakeKernelGateway()

    monkeypatch.setattr(geneva_module, "_GENEVA_HSG_ASSIGNMENT_SERVICE", fake_hsg)
    monkeypatch.setattr(geneva_module, "_GENEVA_KERNEL_GATEWAY", fake_kernel)

    geneva = Geneva(str(tmp_path), "0.cfg")
    geneva.set_enabled(True)
    geneva.prepare_hrus(force_rebuild=True)

    panel_type_b = geneva.build_frequency_panel(rebuild=True, distribution_type="neh4_type_b")
    assert panel_type_b["distribution_type"] == "neh4_type_b"

    run_summary = geneva.run_batch(
        {
            "schema_version": 1,
            "runoff_model": {
                "tc_hours": 1.1,
            },
        }
    )
    assert run_summary["storm_count_completed"] == 1
    assert geneva.results_payload()["last_run_summary"]["storm_count_completed"] == 1

    panel_type_ii = geneva.build_frequency_panel(
        rebuild=False,
        distribution_type="type_ii",
    )
    assert panel_type_ii["distribution_type"] == "type_ii"

    frequency_panel_calls = [api_name for api_name, _payload in fake_kernel.calls if api_name == "geneva_build_frequency_panel"]
    assert len(frequency_panel_calls) == 2
    assert geneva.results_payload()["last_run_summary"] == {}


def test_prepare_kernel_failure_sets_failed_state_and_error_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_paths = _fixture_paths()
    fake_hsg = _FakeHsgService(fixture_paths)
    failing_kernel = _FailingPrepareKernelGateway()

    monkeypatch.setattr(geneva_module, "_GENEVA_HSG_ASSIGNMENT_SERVICE", fake_hsg)
    monkeypatch.setattr(geneva_module, "_GENEVA_KERNEL_GATEWAY", failing_kernel)

    geneva = Geneva(str(tmp_path), "0.cfg")
    geneva.set_enabled(True)

    with pytest.raises(GenevaKernelError) as exc_info:
        geneva.prepare_hrus(force_rebuild=True)

    assert exc_info.value.code == "invalid_input"
    assert geneva.status_payload()["status"] == "failed"
    errors = geneva.results_payload()["errors"]
    assert errors and errors[0]["code"] == "invalid_input"
