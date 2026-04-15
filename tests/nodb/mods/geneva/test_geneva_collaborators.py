from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
from wepppy.nodb.mods.geneva.collaborators.config_service import GenevaConfigService
from wepppy.nodb.mods.geneva.collaborators.hru_preparation_service import GenevaHruPreparationService
from wepppy.nodb.mods.geneva.collaborators.kernel_gateway import GenevaKernelGateway
from wepppy.nodb.mods.geneva.errors import GenevaKernelError


pytestmark = pytest.mark.unit


def _fixture_paths() -> dict[str, str]:
    root = Path(__file__).resolve().parents[3] / "data" / "geneva" / "synthetic_small_watershed_v1"
    return {
        "bound_tif": str(root / "bound.tif"),
        "landuse_tif": str(root / "landuse.tif"),
        "hydgrpdcd_tif": str(root / "hydgrpdcd.tif"),
        "burn_severity_tif": str(root / "burn_severity.tif"),
    }


def test_config_service_initializes_defaults_and_merges_updates() -> None:
    service = GenevaConfigService()
    geneva = SimpleNamespace(_config={})

    initialized = service.initialize_config(geneva)
    assert initialized["schema_version"] == 1
    assert initialized["lambda_mode"] == "0.20"
    assert initialized["min_hru_area_ha"] == 2.0

    updated = service.update_config(geneva, {"lambda_mode": "0.05", "enabled": True})
    assert updated["lambda_mode"] == "0.05"
    assert updated["enabled"] is True


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
    artifact_io = GenevaArtifactIO()
    fixture_paths = _fixture_paths()

    class _FakeHsgService:
        @staticmethod
        def resolve_prepare_input_refs(_geneva, *, overrides=None):
            refs = dict(fixture_paths)
            refs.update(dict(overrides or {}))
            return refs

        @staticmethod
        def resolve_default_hsg(_config):
            return None, None

    class _FakeKernelGateway:
        @staticmethod
        def call_json_api(api_name: str, payload: dict[str, object]) -> dict[str, object]:
            assert api_name == "geneva_prepare_hrus"
            assert payload["kernel_schema_version"] == 1
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
                "warnings": [],
            }

    geneva = SimpleNamespace(
        wd=str(tmp_path),
        artifact_io=artifact_io,
        hsg_assignment_service=_FakeHsgService(),
        kernel_gateway=_FakeKernelGateway(),
        _config={
            "unresolved_hsg_policy": "error",
            "strict_burn_nodata": False,
            "allow_cross_hsg_merge": False,
            "min_hru_area_ha": 2.0,
            "hydrophobic_forest_high": True,
            "hydrophobic_forest_moderate": False,
            "hydrophobic_shrub_high": True,
            "hydrophobic_shrub_moderate": False,
        },
    )

    summary = service.prepare_hrus(geneva, force_rebuild=True)
    assert summary["hru_count"] == 1
    assert summary["artifacts"]["hru_table_relpath"] == "hru_table.parquet"
    assert (tmp_path / "geneva" / "hru_table.parquet").exists()
    assert (tmp_path / "geneva" / "hru_prepare_summary.json").exists()


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
