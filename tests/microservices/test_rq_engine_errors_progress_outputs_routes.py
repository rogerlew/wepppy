from __future__ import annotations

from typing import Any

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import (
    job_routes,
    orchestration_read_routes,
    schema_defaults_routes,
)

pytestmark = pytest.mark.microservice

RUNID = "run-1"
CONFIG = "disturbed9002_wbt"
RUN_ENDPOINT_ERRORS_PATH = f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_build_climate/errors"
OUTPUTS_PATH = f"/api/runs/{RUNID}/{CONFIG}/outputs"
PIPELINE_PATH = f"/api/runs/{RUNID}/{CONFIG}/pipeline"


def _stub_schema_auth(monkeypatch: pytest.MonkeyPatch, scope: str = "rq:status") -> None:
    monkeypatch.setattr(
        schema_defaults_routes,
        "require_jwt",
        lambda request: {"sub": "svc", "token_class": "service", "scope": scope},
    )
    monkeypatch.setattr(schema_defaults_routes, "authorize_run_access", lambda claims, runid: None)


def _stub_orchestration_auth(monkeypatch: pytest.MonkeyPatch, scope: str = "rq:status") -> None:
    monkeypatch.setattr(
        orchestration_read_routes,
        "require_jwt",
        lambda request: {"sub": "svc", "token_class": "service", "scope": scope},
    )
    monkeypatch.setattr(orchestration_read_routes, "authorize_run_access", lambda claims, runid: None)


def _sample_schema_runtime() -> schema_defaults_routes.RuntimeState:
    return schema_defaults_routes.RuntimeState(
        runid=RUNID,
        config=CONFIG,
        active_mods=("disturbed", "wepp"),
        region="conus",
        states={
            "has_dem": True,
            "watershed_has_channels": True,
            "watershed_has_outlet": True,
            "watershed_is_abstracted": True,
            "watershed_subcatchment_count": 42,
            "watershed_csa": 10.0,
            "watershed_mcl": 75.0,
            "delineation_backend": "taudem",
            "climate_built": False,
            "climate_mode_code": 11,
            "climate_mode": "gridmet_prism",
            "climate_has_station": True,
            "climate_station_required": True,
            "landuse_built": True,
            "landuse_mode": "nlcd",
            "soils_built": True,
            "soils_mode": "ssurgo",
            "initial_sat": 0.75,
            "wepp_has_run": False,
            "disturbed_enabled": True,
            "sbs_upload_supported": True,
            "disturbed_sbs_uploaded": True,
            "disturbed_sol_ver": 2018.0,
            "map_center": [-116.8, 46.8],
            "map_bounds": [-117.1, 46.5, -116.4, 47.2],
            "map_zoom": 11.0,
            "map_zoom_resolution_m_per_px": 30.0,
            "dem_coverage_source": "wbt",
            "uploaded_dem_filename": "dem.tif",
        },
        generated_at="2026-04-10T22:13:00Z",
        run_state_revision="runstate:run-1:deadbeefcafe",
    )


def _sample_orchestration_runtime() -> dict[str, Any]:
    return {
        "runid": RUNID,
        "config": CONFIG,
        "active_mods": ("disturbed", "debris_flow", "ash"),
        "states": {
            "has_dem": True,
            "watershed_has_channels": True,
            "watershed_has_outlet": True,
            "watershed_is_abstracted": True,
            "watershed_subcatchment_count": 42,
            "climate_built": False,
            "climate_station_ready": True,
            "climate_mode": None,
            "landuse_built": True,
            "landuse_mode": "nlcd",
            "soils_built": True,
            "soils_mode": "ssurgo",
            "wepp_has_run": False,
            "wepp_hillslopes_run": False,
            "wepp_watershed_run": False,
            "disturbed_enabled": True,
            "disturbed_sbs_uploaded": True,
            "disturbed_sol_ver_selected": True,
        },
        "step_completion_ts": {
            "fetch-dem-and-build-channels": 100,
            "set-outlet": 110,
            "build-subcatchments-and-abstract-watershed": 120,
            "upload-sbs": 200,
            "build-climate": None,
            "build-landuse": 150,
            "build-soils": 140,
            "prep-wepp-watershed": 130,
            "run-wepp": 160,
            "run-wepp-watershed": 170,
            "build-rusle": 125,
            "run-ash": None,
            "run-debris-flow": None,
        },
        "step_job": {
            "build-climate": {
                "job_id": "rq-222",
                "status": "started",
                "ended_at": None,
                "exc_info": None,
                "progress": {
                    "completed": 3,
                    "total": 10,
                    "unit": "subcatchments",
                    "percent": 30.0,
                    "updated_at": "2026-04-10T10:22:30Z",
                },
            }
        },
        "generated_at": "2026-04-10T10:22:31Z",
    }


def test_run_endpoint_errors_catalog_includes_machine_actionable_codes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_schema_auth(monkeypatch)
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_schema_runtime())

    with TestClient(rq_engine.app) as client:
        response = client.get(RUN_ENDPOINT_ERRORS_PATH)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "contract_version",
        "deployment_revision",
        "run_state_revision",
        "operation_id",
        "errors",
    }
    assert payload["operation_id"] == "rq_engine_build_climate"

    by_code = {entry["error_code"]: entry for entry in payload["errors"]}
    assert {"unauthorized", "forbidden", "validation_error"}.issubset(by_code)
    assert {"missing_station_selection", "climate_mode_unavailable_for_region"}.issubset(by_code)

    missing_station = by_code["missing_station_selection"]
    assert missing_station["recoverable"] is True
    assert 400 in missing_station["http_statuses"]
    assert missing_station["recovery_actions"][0]["operation_id"] == "rq_engine_build_climate"
    assert missing_station["recovery_actions"][0]["required_fields"] == ["climatestation"]


def test_run_endpoint_errors_returns_404_for_unknown_operation(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_schema_auth(monkeypatch)
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_schema_runtime())

    with TestClient(rq_engine.app) as client:
        response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_unknown/errors")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_outputs_payload_includes_trust_provenance_and_retrieval_handles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_schema_auth(monkeypatch)
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_schema_runtime())

    def _fake_feature_artifact(runtime: schema_defaults_routes.RuntimeState, *, wd: str) -> dict[str, Any]:
        return {
            "id": "features_export_latest",
            "kind": "zip",
            "producer_operation_id": "rq_engine_export_features_submit",
            "producer_step_id": "export-features",
            "producer_job_id": "rq-998",
            "produced_at": "2026-04-10T10:20:02Z",
            "source_run_state_revision": runtime.run_state_revision,
            "expires_at": None,
            "content_type": "application/zip",
            "size_bytes": 1834247,
            "sha256": "9c6c8f2de1d0fa4b92d3fa2f60f5f376fa2b36286f7496cff57d4c4555d52d7e",
            "result_source": "jobinfo.result",
            "download_url": f"/rq-engine/api/runs/{runtime.runid}/{runtime.config}/export/features/job/rq-998/download",
            "download_url_params": {
                "runid": runtime.runid,
                "config": runtime.config,
                "job_id": "rq-998",
            },
            "download_url_template": "/rq-engine/api/runs/{runid}/{config}/export/features/job/{job_id}/download",
        }

    monkeypatch.setattr(schema_defaults_routes, "_build_features_export_artifact", _fake_feature_artifact)

    with TestClient(rq_engine.app) as client:
        response = client.get(OUTPUTS_PATH)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "contract_version",
        "deployment_revision",
        "run_state_revision",
        "updated_at",
        "etag",
        "artifacts",
        "exports",
    }
    assert payload["etag"].startswith('W/"outputs:')
    assert payload["updated_at"] == "2026-04-10T10:20:02Z"

    artifacts = payload["artifacts"]
    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact["producer_job_id"] == "rq-998"
    assert artifact["source_run_state_revision"].startswith("runstate:run-1:")
    assert artifact["download_url_params"] == {"runid": RUNID, "config": CONFIG, "job_id": "rq-998"}
    assert artifact["result_source"] == "jobinfo.result"

    exports = payload["exports"]
    export_operation_ids = {entry["operation_id"] for entry in exports}
    assert "rq_engine_export_ermit" in export_operation_ids
    assert "rq_engine_export_features_submit" in export_operation_ids


def test_outputs_payload_uses_empty_defaults_when_no_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_schema_auth(monkeypatch)
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_schema_runtime())
    monkeypatch.setattr(schema_defaults_routes, "_build_features_export_artifact", lambda runtime, wd: None)

    with TestClient(rq_engine.app) as client:
        response = client.get(OUTPUTS_PATH)

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifacts"] == []
    assert payload["updated_at"] == schema_defaults_routes.UNKNOWN_UPDATED_AT


def test_jobstatus_surface_adds_progress_from_job_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        job_routes,
        "get_wepppy_rq_job_status",
        lambda job_id: {
            "job_id": job_id,
            "status": "started",
            "started_at": "2026-04-10T10:00:00Z",
            "ended_at": None,
            "progress": {
                "completed": 1,
                "total": 3,
                "unit": "jobs",
                "percent": 33.33,
                "updated_at": "2026-04-10T10:01:00Z",
            },
        },
    )
    monkeypatch.setattr(
        job_routes,
        "get_wepppy_rq_job_info",
        lambda job_id: (_ for _ in ()).throw(AssertionError("jobstatus should not fetch job tree")),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/jobstatus/job-progress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "started"
    assert payload["progress"]["completed"] == 1
    assert payload["progress"]["total"] == 3
    assert payload["progress"]["unit"] == "jobs"
    assert payload["progress"]["percent"] == pytest.approx(33.33, abs=0.001)
    assert payload["progress"]["updated_at"] == "2026-04-10T10:01:00Z"


def test_pipeline_surface_exposes_progress_for_running_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_orchestration_auth(monkeypatch)
    monkeypatch.setattr(orchestration_read_routes, "_load_runtime_state", lambda runid, config: _sample_orchestration_runtime())

    with TestClient(rq_engine.app) as client:
        response = client.get(PIPELINE_PATH)

    assert response.status_code == 200
    payload = response.json()
    build_climate = next(step for step in payload["steps"] if step["step_id"] == "build-climate")
    assert build_climate["status"] == "running"
    assert build_climate["active_job_id"] == "rq-222"
    assert build_climate["progress"] == {
        "completed": 3,
        "total": 10,
        "unit": "subcatchments",
        "percent": 30.0,
        "updated_at": "2026-04-10T10:22:30Z",
    }


def test_orchestration_progress_payload_uses_stable_unknown_timestamp_when_unset() -> None:
    progress = orchestration_read_routes._job_progress_payload(
        {
            "status": "started",
            "started_at": None,
            "ended_at": None,
            "children": {"0": [{"status": "queued", "started_at": None, "ended_at": None, "children": {}}]},
        }
    )

    assert progress == {
        "completed": 0,
        "total": 2,
        "unit": "jobs",
        "percent": 0.0,
        "updated_at": orchestration_read_routes.UNKNOWN_UPDATED_AT,
    }


def test_outputs_operation_descriptor_requires_snapshot_fields() -> None:
    runtime = _sample_schema_runtime()
    operations = schema_defaults_routes._build_run_operations(runtime)
    outputs_id = schema_defaults_routes.rq_operation_id("get_outputs")
    outputs_docs = operations[outputs_id]

    required_result_fields = outputs_docs["descriptor"]["result_contract"]["required_response_fields"]
    required_success_fields = outputs_docs["schema"]["responses"]["success"]["required"]
    assert required_result_fields == ["updated_at", "etag", "artifacts", "exports"]
    assert required_success_fields == ["updated_at", "etag", "artifacts", "exports"]


def test_outputs_artifact_source_run_revision_uses_unknown_sentinel_when_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    runtime = _sample_schema_runtime()

    class _FakePrep:
        def get_rq_job_id(self, key: str) -> str | None:
            return "rq-998"

        def get_rq_job_ids(self) -> dict[str, str]:
            return {}

    artifact_path = tmp_path / "features_export.zip"
    artifact_path.write_bytes(b"abc123")

    monkeypatch.setattr(schema_defaults_routes.RedisPrep, "getInstance", lambda wd: _FakePrep())
    monkeypatch.setattr(
        schema_defaults_routes,
        "get_wepppy_rq_job_info",
        lambda job_id: {
            "job_id": job_id,
            "runid": runtime.runid,
            "status": "finished",
            "ended_at": "2026-04-10T10:20:02Z",
            "result": {"artifact_id": "features_export_latest"},
        },
    )
    monkeypatch.setattr(
        schema_defaults_routes,
        "resolve_download_artifact_path",
        lambda wd, job_id, job_result: (artifact_path, "export/features/artifacts/features_export_latest/features_export.zip"),
    )
    monkeypatch.setattr(schema_defaults_routes, "load_job_manifest", lambda wd, job_id: {"generated_at_utc": "2026-04-10T10:20:02Z"})

    artifact = schema_defaults_routes._build_features_export_artifact(runtime, wd=str(tmp_path))

    assert artifact is not None
    assert artifact["source_run_state_revision"] == schema_defaults_routes.UNKNOWN_SOURCE_RUN_STATE_REVISION


def test_outputs_artifact_accepts_legacy_missing_job_runid_when_artifact_is_run_scoped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    runtime = _sample_schema_runtime()

    class _FakePrep:
        def get_rq_job_id(self, key: str) -> str | None:
            return "rq-999"

        def get_rq_job_ids(self) -> dict[str, str]:
            return {}

    artifact_path = tmp_path / "features_export_legacy.zip"
    artifact_path.write_bytes(b"legacy")

    monkeypatch.setattr(schema_defaults_routes.RedisPrep, "getInstance", lambda wd: _FakePrep())
    monkeypatch.setattr(
        schema_defaults_routes,
        "get_wepppy_rq_job_info",
        lambda job_id: {
            "job_id": job_id,
            "runid": None,
            "status": "finished",
            "ended_at": "2026-04-10T10:20:02Z",
            "result": {"artifact_id": "features_export_legacy"},
        },
    )
    monkeypatch.setattr(
        schema_defaults_routes,
        "resolve_download_artifact_path",
        lambda wd, job_id, job_result: (artifact_path, "export/features/artifacts/features_export_legacy/features_export.zip"),
    )
    monkeypatch.setattr(schema_defaults_routes, "load_job_manifest", lambda wd, job_id: {"generated_at_utc": "2026-04-10T10:20:02Z"})

    artifact = schema_defaults_routes._build_features_export_artifact(runtime, wd=str(tmp_path))

    assert artifact is not None
    assert artifact["producer_job_id"] == "rq-999"
