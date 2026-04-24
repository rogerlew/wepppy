from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
from wepppy.nodb.mods.geneva.collaborators.batch_run_service import GenevaBatchRunService
from wepppy.nodb.mods.geneva.collaborators.cn_table_service import GenevaCnTableService
from wepppy.nodb.mods.geneva.collaborators.config_service import GenevaConfigService
from wepppy.nodb.mods.geneva.collaborators.hru_preparation_service import GenevaHruPreparationService
from wepppy.nodb.mods.geneva.collaborators.kernel_gateway import GenevaKernelGateway
from wepppy.nodb.mods.geneva.errors import GenevaKernelError, GenevaValidationError
from wepppy.nodb.mods.geneva.schemas import default_geneva_config


pytestmark = pytest.mark.unit


def _fixture_paths() -> dict[str, str]:
    root = Path(__file__).resolve().parents[3] / "data" / "geneva" / "synthetic_small_watershed_v1"
    return {
        "bound_tif": str(root / "bound.tif"),
        "landuse_tif": str(root / "landuse.tif"),
        "hydgrpdcd_tif": str(root / "hydgrpdcd.tif"),
        "burn_severity_tif": str(root / "burn_severity.tif"),
    }


def _geneva_config() -> dict[str, object]:
    config = default_geneva_config().to_payload()
    config["lambda_mode"] = "0.20"
    config["uh_method"] = "scs_triangular"
    return config


def _kernel_hru_row(
    *,
    landuse_class: int = 42,
    hsg_group: str = "B",
    burn_severity_class: str = "unburned",
    hydrophobic_class: bool = False,
    cn_arc_ii: float = 74.0,
) -> dict[str, object]:
    return {
        "hru_id": "hru_1",
        "area_m2": 900.0,
        "area_ac": 0.22239484332044878,
        "area_fraction": 1.0,
        "landuse_class": landuse_class,
        "hsg_group": hsg_group,
        "burn_severity_class": burn_severity_class,
        "hydrophobic_class": hydrophobic_class,
        "is_water": False,
        "cn_arc_ii": cn_arc_ii,
        "cn_lambda_020": cn_arc_ii,
        "cn_lambda_005": 86.0,
        "antecedent_condition_source": "arc_ii_seed",
        "cn_source": "geneva_proxy_cn_v1",
        "hsg_source": "coded_lookup",
        "collapsed_from_hru_ids": [],
        "warnings": [],
    }


class _FakeHsgService:
    def __init__(self, fixture_paths: dict[str, str]) -> None:
        self._fixture_paths = fixture_paths

    def resolve_prepare_input_refs(self, _geneva, *, overrides=None):
        refs = dict(self._fixture_paths)
        refs.update(dict(overrides or {}))
        return refs

    @staticmethod
    def resolve_default_hsg(_config):
        return None, None


class _RecordingKernelGateway:
    def __init__(self, *, prepare_rows: list[dict[str, object]]) -> None:
        self.prepare_rows = [dict(row) for row in prepare_rows]
        self.prepare_calls = 0
        self.run_batch_payloads: list[dict[str, object]] = []

    def call_json_api(self, api_name: str, payload: dict[str, object]) -> dict[str, object]:
        if api_name == "geneva_prepare_hrus":
            self.prepare_calls += 1
            return {
                "status": "ok",
                "phase": "prepare_hrus",
                "kernel_schema_version": 1,
                "hru_rows": [dict(row) for row in self.prepare_rows],
                "diagnostics": {
                    "hru_area_total_m2": 900.0,
                    "hsg_provenance_counts": {"coded_lookup": 1},
                },
                "warnings": [],
            }

        if api_name == "geneva_run_batch":
            self.run_batch_payloads.append(json.loads(json.dumps(payload)))
            time_minutes = [0.0, 30.0]
            cumulative_rainfall_mm = [0.0, 20.0]
            cumulative_excess_mm = [0.0, 4.0]
            return {
                "status": "ok",
                "phase": "run_batch",
                "kernel_schema_version": 1,
                "storm_id": payload["storm_id"],
                "summary_metrics": {
                    "peak_discharge": 1.2,
                    "time_to_peak": 30.0,
                    "runoff_volume": 40.0,
                    "runoff_depth": 4.0,
                },
                "composite_excess": {
                    "cumulative_excess_mm": cumulative_excess_mm,
                    "incremental_excess_mm": [0.0, 4.0],
                },
                "hydrograph": {
                    "time_minutes": time_minutes,
                    "q_cms": [0.0, 1.2],
                    "q_cfs": [0.0, 42.37760006578631],
                    "runoff_cum_mm": cumulative_excess_mm,
                    "runoff_volume_m3": [0.0, 40.0],
                },
                "warnings": [],
            }

        raise AssertionError(f"Unexpected API call: {api_name}")


def _geneva_stub(
    tmp_path: Path,
    *,
    kernel_gateway: object,
) -> SimpleNamespace:
    return SimpleNamespace(
        wd=str(tmp_path),
        artifact_io=GenevaArtifactIO(),
        cn_table_service=GenevaCnTableService(),
        hsg_assignment_service=_FakeHsgService(_fixture_paths()),
        kernel_gateway=kernel_gateway,
        watershed_instance=SimpleNamespace(wsarea=1_000_000.0),
        _config=_geneva_config(),
    )


def _update_cn_table_row(
    geneva: SimpleNamespace,
    *,
    nlcd_class: str,
    hsg: str,
    burn_severity: str,
    hydrophobic: str,
    cn_arc_ii: str,
    antecedent_condition_source: str = "user_override",
) -> dict[str, object]:
    snapshot = geneva.cn_table_service.snapshot(geneva)
    rows = [dict(row) for row in snapshot["rows"]]
    for row in rows:
        if (
            row["nlcd_class"] == nlcd_class
            and row["hsg"] == hsg
            and row["burn_severity"] == burn_severity
            and row["hydrophobic"] == hydrophobic
        ):
            row["cn_arc_ii"] = cn_arc_ii
            row["antecedent_condition_source"] = antecedent_condition_source
            break
    else:
        raise AssertionError("Expected CN-table row was not found in seed data.")

    return geneva.cn_table_service.modify(
        geneva,
        rows,
        if_match_sha256=snapshot["lookup_sha256"],
    )


def test_config_service_initializes_defaults_and_merges_updates() -> None:
    service = GenevaConfigService()
    geneva = SimpleNamespace(_config={})

    initialized = service.initialize_config(geneva)
    assert initialized["schema_version"] == 1
    assert initialized["lambda_mode"] == "0.20"
    assert initialized["unresolved_hsg_policy"] == "assume_d"
    assert initialized["min_hru_area_ha"] == 2.0

    updated = service.update_config(geneva, {"lambda_mode": "0.05", "enabled": True})
    assert updated["lambda_mode"] == "0.05"
    assert updated["enabled"] is True


def test_config_service_migrates_legacy_unresolved_hsg_default_for_unedited_runs() -> None:
    service = GenevaConfigService()
    legacy = default_geneva_config().to_payload()
    legacy["unresolved_hsg_policy"] = "error"
    geneva = SimpleNamespace(_config=legacy, _config_user_modified=False)

    initialized = service.initialize_config(geneva)

    assert initialized["unresolved_hsg_policy"] == "assume_d"


def test_config_service_preserves_legacy_unresolved_hsg_when_user_modified() -> None:
    service = GenevaConfigService()
    legacy = default_geneva_config().to_payload()
    legacy["unresolved_hsg_policy"] = "error"
    geneva = SimpleNamespace(_config=legacy, _config_user_modified=True)

    initialized = service.initialize_config(geneva)

    assert initialized["unresolved_hsg_policy"] == "error"


def test_artifact_io_writes_and_reads_json_and_parquet(tmp_path: Path) -> None:
    io = GenevaArtifactIO()
    wd = str(tmp_path)

    io.write_json(wd, "batch_summary.json", {"storm_count_total": 2, "status": "completed"})
    payload = io.read_json(wd, "batch_summary.json")
    assert payload["storm_count_total"] == 2

    records = [{"hru_id": "h1", "area_m2": 900.0}, {"hru_id": "h2", "area_m2": 450.0}]
    io.write_records_parquet(wd, "hru_table.parquet", records)
    roundtrip = io.read_records_parquet(wd, "hru_table.parquet")
    assert len(roundtrip) == 2
    assert roundtrip[0]["hru_id"] == "h1"


def test_kernel_gateway_maps_typed_value_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeKernelModule:
        @staticmethod
        def geneva_prepare_hrus(_payload_json: str) -> str:
            raise ValueError("invalid_input: malformed payload")

    monkeypatch.setattr(
        "importlib.import_module",
        lambda _name: _FakeKernelModule,
    )

    gateway = GenevaKernelGateway()
    with pytest.raises(GenevaKernelError) as exc_info:
        gateway.call_json_api("geneva_prepare_hrus", {"kernel_schema_version": 1})

    assert exc_info.value.code == "invalid_input"
    assert "malformed payload" in json.dumps(exc_info.value.details)


def test_hru_preparation_service_persists_hru_artifacts(tmp_path: Path) -> None:
    service = GenevaHruPreparationService()
    kernel_gateway = _RecordingKernelGateway(prepare_rows=[_kernel_hru_row()])
    geneva = _geneva_stub(tmp_path, kernel_gateway=kernel_gateway)

    summary = service.prepare_hrus(geneva, force_rebuild=True)
    assert summary["hru_count"] == 1
    assert summary["artifacts"]["hru_table_relpath"] == "hru_table.parquet"
    assert summary["cn_table"]["runtime_source"] == "geneva_cn_table_csv_v1"
    assert (tmp_path / "geneva" / "hru_table.parquet").exists()
    assert (tmp_path / "geneva" / "hru_prepare_summary.json").exists()


def test_hru_preparation_service_rebuilds_when_cn_table_changes_and_persists_runtime_cn(
    tmp_path: Path,
) -> None:
    service = GenevaHruPreparationService()
    kernel_gateway = _RecordingKernelGateway(prepare_rows=[_kernel_hru_row()])
    geneva = _geneva_stub(tmp_path, kernel_gateway=kernel_gateway)

    service.prepare_hrus(geneva, force_rebuild=True)
    baseline_rows = geneva.artifact_io.read_records_parquet(geneva.wd, "hru_table.parquet")
    baseline_cn = float(baseline_rows[0]["cn_arc_ii"])
    assert baseline_rows[0]["cn_source"] == "geneva_cn_table_csv_v1"

    modify_result = _update_cn_table_row(
        geneva,
        nlcd_class="42",
        hsg="B",
        burn_severity="unburned",
        hydrophobic="false",
        cn_arc_ii="89",
    )

    rebuilt_summary = service.prepare_hrus(geneva, force_rebuild=False)
    rebuilt_rows = geneva.artifact_io.read_records_parquet(geneva.wd, "hru_table.parquet")

    assert kernel_gateway.prepare_calls == 2
    assert baseline_cn != 89.0
    assert rebuilt_rows[0]["cn_arc_ii"] == 89.0
    assert rebuilt_rows[0]["cn_lambda_020"] == 89.0
    assert rebuilt_rows[0]["antecedent_condition_source"] == "user_override"
    assert rebuilt_rows[0]["cn_source"] == "geneva_cn_table_csv_v1"
    assert rebuilt_summary["cn_table"]["lookup_sha256"] == modify_result["sha256"]


def test_batch_run_uses_updated_cn_values_from_hru_table_parquet(tmp_path: Path) -> None:
    prepare_service = GenevaHruPreparationService()
    batch_service = GenevaBatchRunService()
    kernel_gateway = _RecordingKernelGateway(prepare_rows=[_kernel_hru_row()])
    geneva = _geneva_stub(tmp_path, kernel_gateway=kernel_gateway)

    _update_cn_table_row(
        geneva,
        nlcd_class="42",
        hsg="B",
        burn_severity="unburned",
        hydrophobic="false",
        cn_arc_ii="89",
    )
    prepare_service.prepare_hrus(geneva, force_rebuild=True)

    geneva.artifact_io.write_json(
        geneva.wd,
        "frequency_panel.json",
        {
            "cells": [
                {
                    "storm_id": "cligen_30m_10y",
                    "datasource_id": "cligen_freq",
                    "duration_minutes": 30,
                    "ari_years": 10,
                    "depth_mm": 20.0,
                    "intensity_mm_per_hr": 40.0,
                    "availability": "available",
                    "reason_code": None,
                }
            ]
        },
    )

    batch_service.run_batch(
        geneva,
        {
            "schema_version": 1,
            "runoff_model": {"tc_hours": 1.0},
        },
    )

    assert kernel_gateway.run_batch_payloads
    batch_hru_row = kernel_gateway.run_batch_payloads[0]["hru_rows"][0]
    assert batch_hru_row["cn_lambda_020"] == 89.0


def test_hru_preparation_service_marks_missing_cn_table_rows_with_explicit_fallback(
    tmp_path: Path,
) -> None:
    service = GenevaHruPreparationService()
    kernel_gateway = _RecordingKernelGateway(
        prepare_rows=[
            _kernel_hru_row(
                landuse_class=71,
                hsg_group="B",
                burn_severity_class="high",
                hydrophobic_class=False,
                cn_arc_ii=81.0,
            )
        ]
    )
    geneva = _geneva_stub(tmp_path, kernel_gateway=kernel_gateway)

    service.prepare_hrus(geneva, force_rebuild=True)
    hru_rows = geneva.artifact_io.read_records_parquet(geneva.wd, "hru_table.parquet")

    assert hru_rows[0]["cn_arc_ii"] == 81.0
    assert hru_rows[0]["cn_source"] == "geneva_proxy_cn_v1_fallback_missing_row"
    assert "cn_table_missing_exact_row" in hru_rows[0]["warnings"]


def test_hru_preparation_service_rejects_invalid_runtime_cn_rows(tmp_path: Path) -> None:
    service = GenevaHruPreparationService()
    kernel_gateway = _RecordingKernelGateway(prepare_rows=[_kernel_hru_row()])
    geneva = _geneva_stub(tmp_path, kernel_gateway=kernel_gateway)

    _update_cn_table_row(
        geneva,
        nlcd_class="42",
        hsg="B",
        burn_severity="unburned",
        hydrophobic="false",
        cn_arc_ii="not-a-number",
    )

    with pytest.raises(GenevaValidationError) as exc_info:
        service.prepare_hrus(geneva, force_rebuild=True)

    assert exc_info.value.code == "invalid_cn_table_schema"


def test_kernel_gateway_falls_back_to_cli_revision_rust_when_nested_module_lacks_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _LegacyModule:
        pass

    class _FallbackModule:
        @staticmethod
        def geneva_prepare_hrus(_payload_json: str) -> str:
            return '{"status":"ok","phase":"prepare_hrus","kernel_schema_version":1}'

    def _import_module(name: str):
        if name == "wepppyo3.climate.cli_revision_rust":
            return _LegacyModule
        if name == "cli_revision_rust":
            return _FallbackModule
        raise ImportError(name)

    monkeypatch.setattr("importlib.import_module", _import_module)

    gateway = GenevaKernelGateway()
    payload = gateway.call_json_api("geneva_prepare_hrus", {"kernel_schema_version": 1})
    assert payload["status"] == "ok"
    assert payload["phase"] == "prepare_hrus"
