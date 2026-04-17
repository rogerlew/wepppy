from __future__ import annotations

from types import SimpleNamespace

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import geneva_routes
from wepppy.nodb.mods.geneva.errors import GenevaValidationError


pytestmark = pytest.mark.microservice


class _GenevaRouteStub:
    def __init__(self) -> None:
        self.queued: list[tuple[str, str]] = []
        self.frequency_panel_service = SimpleNamespace(
            normalize_request=lambda payload: {
                "schema_version": 1,
                "durations_minutes": [30],
                "ari_years": [10],
                "rebuild": bool(payload.get("rebuild", False)),
            }
        )
        self.batch_run_service = SimpleNamespace(
            validate_request=lambda _geneva, _payload: None
        )

    def assert_task_guardrails(self) -> None:
        return None

    def mark_job_queued(self, job_id: str, *, status_message: str) -> None:
        self.queued.append((job_id, status_message))

    def state_payload(self) -> dict[str, object]:
        return {
            "state_version": 1,
            "enabled": True,
            "config_snapshot": {
                "schema_version": 1,
                "enabled": True,
                "lambda_mode": "0.20",
                "uh_method": "scs_triangular",
                "default_hsg_code": None,
                "unresolved_hsg_policy": "error",
                "strict_burn_nodata": False,
                "allow_cross_hsg_merge": False,
                "hydrophobic_forest_high": True,
                "hydrophobic_forest_moderate": False,
                "hydrophobic_shrub_high": True,
                "hydrophobic_shrub_moderate": False,
                "min_hru_area_ha": 2.0,
            },
            "status": "prepared",
            "status_message": "Frequency panel ready.",
            "progress": {
                "completed": 0,
                "total": 0,
                "unit": "storms",
                "percent": 0.0,
                "updated_at": "2026-04-16T00:00:00Z",
            },
            "active_job_id": None,
            "last_job_id": "geneva-last-7",
            "last_prepare_summary": {"hru_count": 4},
            "last_run_summary": {"storm_count_total": 3},
            "warnings": [],
            "errors": [],
            "artifacts": {
                "hru_table_ready": True,
                "frequency_panel_ready": True,
                "batch_summary_ready": False,
            },
            "updated_at": "2026-04-16T00:00:00Z",
        }


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        geneva_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"scope": "rq:enqueue rq:status rq:read"},
    )
    monkeypatch.setattr(geneva_routes, "authorize_run_access", lambda claims, runid: None)


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "geneva-job-1") -> dict[str, object]:
    captured: dict[str, object] = {}

    class DummyJob:
        id = job_id

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return DummyJob()

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(geneva_routes, "Queue", DummyQueue)
    monkeypatch.setattr(geneva_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    return captured


def test_prepare_hrus_enqueues_job_with_canonical_submission_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    captured = _stub_queue(monkeypatch, job_id="geneva-prepare-9")
    stub = _GenevaRouteStub()
    monkeypatch.setattr(geneva_routes, "_ensure_geneva_controller", lambda runid, config: stub)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/geneva/prepare-hrus",
            json={"schema_version": 1, "force_rebuild": True},
        )

    assert response.status_code == 202
    assert response.json() == {
        "job_id": "geneva-prepare-9",
        "status_url": "/rq-engine/api/jobstatus/geneva-prepare-9",
        "message": "Job enqueued.",
    }
    assert captured["kwargs"]["func"] is geneva_routes.run_geneva_prepare_hrus_rq
    assert captured["kwargs"]["args"] == (
        "run-1",
        "cfg",
        {"schema_version": 1, "force_rebuild": True},
    )
    assert stub.queued == [("geneva-prepare-9", "Geneva HRU preparation queued.")]


def test_state_route_returns_revisioned_geneva_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    stub = _GenevaRouteStub()
    monkeypatch.setattr(geneva_routes, "_ensure_geneva_controller", lambda runid, config: stub)

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/geneva/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract_version"] == geneva_routes.CONTRACT_VERSION
    assert payload["run_state_domain"] == "orchestration"
    assert payload["run_state_revision"].startswith("runstate:run-1:")
    assert payload["run_state_vector"]["orchestration_revision"] == payload["run_state_revision"]
    assert payload["state_version"] == 1
    assert payload["config_snapshot"]["lambda_mode"] == "0.20"
    assert payload["last_job_id"] == "geneva-last-7"
    assert payload["updated_at"] == "2026-04-16T00:00:00Z"
    assert payload["etag"].startswith('W/"geneva:run-1:')


def test_run_batch_validation_error_returns_canonical_error_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    stub = _GenevaRouteStub()
    stub.batch_run_service = SimpleNamespace(
        validate_request=lambda _geneva, _payload: (_ for _ in ()).throw(
            GenevaValidationError(
                "Exactly one of runoff_model.tc_hours or runoff_model.timing_method must be provided",
                code="invalid_input",
                details="Exactly one of runoff_model.tc_hours or runoff_model.timing_method must be provided",
                status_code=400,
            )
        )
    )
    monkeypatch.setattr(geneva_routes, "_ensure_geneva_controller", lambda runid, config: stub)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/geneva/run-batch",
            json={
                "schema_version": 1,
                "event_filter": {"datasource_ids": ["cligen_freq"]},
                "hyetograph": {"distribution_type": "neh4_type_b", "time_step_minutes": 1.0},
                "runoff_model": {"lambda_mode": "0.20", "uh_method": "scs_triangular"},
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_input"
    assert payload["error"]["details"] == (
        "Exactly one of runoff_model.tc_hours or runoff_model.timing_method must be provided"
    )


def test_prepare_internal_error_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    stub = _GenevaRouteStub()
    monkeypatch.setattr(geneva_routes, "_ensure_geneva_controller", lambda runid, config: stub)
    monkeypatch.setattr(
        geneva_routes,
        "_enqueue_geneva_job",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("queue exploded with traceback details")),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/geneva/prepare-hrus",
            json={"schema_version": 1, "force_rebuild": False},
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "internal_error"
    assert payload["error"]["details"] == "Unexpected server error while preparing Geneva HRUs."
    assert "Traceback" not in payload["error"]["details"]
    assert "queue exploded" not in payload["error"]["details"]
