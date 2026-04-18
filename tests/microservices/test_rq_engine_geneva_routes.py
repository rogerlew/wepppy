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


def _stub_queue(
    monkeypatch: pytest.MonkeyPatch,
    *,
    job_id: str = "geneva-job-1",
    job_ids: list[str] | None = None,
) -> dict[str, object]:
    captured: dict[str, object] = {"job_ids": list(job_ids or [job_id])}

    class DummyJob:
        def __init__(self, id_value: str) -> None:
            self.id = id_value

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            self._job_ids: list[str] = list(captured.get("job_ids", [job_id]))

        def enqueue_call(self, *args, **kwargs):
            call_index = len(captured.setdefault("calls", []))
            next_job_id = self._job_ids[min(call_index, len(self._job_ids) - 1)]
            call = {"args": args, "kwargs": kwargs, "job_id": next_job_id}
            captured["calls"].append(call)
            captured["args"] = args
            captured["kwargs"] = kwargs
            return DummyJob(next_job_id)

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


def test_run_workflow_enqueues_chained_jobs_with_forced_rebuild(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    captured = _stub_queue(
        monkeypatch,
        job_ids=["geneva-prepare-1", "geneva-panel-2", "geneva-batch-3"],
    )
    stub = _GenevaRouteStub()
    monkeypatch.setattr(geneva_routes, "_ensure_geneva_controller", lambda runid, config: stub)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/geneva/run-workflow",
            json={
                "schema_version": 1,
                "prepare": {"schema_version": 1, "force_rebuild": False},
                "panel": {"schema_version": 1, "durations_minutes": [30], "ari_years": [10], "rebuild": False},
                "run_batch": {
                    "schema_version": 1,
                    "event_filter": {"datasource_ids": ["cligen_freq"]},
                    "hyetograph": {"distribution_type": "neh4_type_b", "time_step_minutes": 1.0},
                    "runoff_model": {"lambda_mode": "0.20", "uh_method": "scs_triangular", "timing_method": "kent"},
                },
            },
        )

    assert response.status_code == 202
    assert response.json() == {
        "job_id": "geneva-prepare-1",
        "job_ids": {
            "prepare_hrus": "geneva-prepare-1",
            "build_frequency_panel": "geneva-panel-2",
            "run_batch": "geneva-batch-3",
        },
        "status_url": "/rq-engine/api/jobstatus/geneva-prepare-1",
        "message": "Workflow enqueued.",
    }
    calls = captured["calls"]
    assert len(calls) == 3

    prepare_call = calls[0]["kwargs"]
    assert prepare_call["func"] is geneva_routes.run_geneva_prepare_hrus_rq
    assert prepare_call["args"] == (
        "run-1",
        "cfg",
        {"schema_version": 1, "force_rebuild": True},
    )

    panel_call = calls[1]["kwargs"]
    assert panel_call["func"] is geneva_routes.run_geneva_build_frequency_panel_rq
    assert panel_call["depends_on"].id == "geneva-prepare-1"
    assert panel_call["args"] == (
        "run-1",
        "cfg",
        {"schema_version": 1, "durations_minutes": [30], "ari_years": [10], "rebuild": True},
    )

    run_call = calls[2]["kwargs"]
    assert run_call["func"] is geneva_routes.run_geneva_run_batch_rq
    assert run_call["depends_on"].id == "geneva-panel-2"
    assert run_call["args"] == (
        "run-1",
        "cfg",
        {
            "schema_version": 1,
            "event_filter": {"datasource_ids": "cligen_freq"},
            "hyetograph": {"distribution_type": "neh4_type_b", "time_step_minutes": 1.0},
            "runoff_model": {"lambda_mode": "0.20", "uh_method": "scs_triangular", "timing_method": "kent"},
        },
    )
    assert stub.queued == [
        (
            "geneva-prepare-1",
            "Geneva workflow queued. Preparing HRUs, building frequency panel, then running Geneva batch.",
        )
    ]


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
