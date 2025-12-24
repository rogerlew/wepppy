import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine


pytestmark = pytest.mark.microservice


def test_health_returns_expected_payload() -> None:
    with TestClient(rq_engine.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "scope": "rq-engine"}


def test_jobstatus_returns_stubbed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_jobstatus(job_id: str) -> dict[str, str]:
        seen["job_id"] = job_id
        return {"status": "ok", "job_id": job_id}

    monkeypatch.setattr(rq_engine, "get_wepppy_rq_job_status", fake_jobstatus)

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/jobstatus/job-123")

    assert response.json() == {"status": "ok", "job_id": "job-123"}
    assert seen["job_id"] == "job-123"


def test_jobinfo_returns_stubbed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_jobinfo(job_id: str) -> dict[str, str]:
        seen["job_id"] = job_id
        return {"id": job_id, "status": "finished"}

    monkeypatch.setattr(rq_engine, "get_wepppy_rq_job_info", fake_jobinfo)

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/jobinfo/job-abc")

    assert response.json() == {"id": "job-abc", "status": "finished"}
    assert seen["job_id"] == "job-abc"


def test_jobinfo_batch_preserves_order_and_filters_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_jobs_info(job_ids: list[str]) -> dict[str, dict[str, str]]:
        seen["job_ids"] = list(job_ids)
        return {"a": {"id": "a"}, "c": {"id": "c"}}

    monkeypatch.setattr(rq_engine, "get_wepppy_rq_jobs_info", fake_jobs_info)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/jobinfo", json={"job_ids": ["a", "b", "c"]})

    payload = response.json()
    assert seen["job_ids"] == ["a", "b", "c"]
    assert payload["jobs"] == {"a": {"id": "a"}, "c": {"id": "c"}}
    assert payload["job_ids"] == ["a", "c"]


def test_jobinfo_batch_uses_query_args_when_payload_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_jobs_info(job_ids: list[str]) -> dict[str, dict[str, str]]:
        return {job_id: {"id": job_id} for job_id in job_ids}

    monkeypatch.setattr(rq_engine, "get_wepppy_rq_jobs_info", fake_jobs_info)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/jobinfo?job_id=job-99",
            data="{not-json}",
            headers={"content-type": "application/json"},
        )

    assert response.json() == {"jobs": {"job-99": {"id": "job-99"}}, "job_ids": ["job-99"]}


def test_jobinfo_error_returns_500_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(job_id: str) -> dict[str, str]:
        raise RuntimeError("boom")

    monkeypatch.setattr(rq_engine, "get_wepppy_rq_job_info", explode)

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/jobinfo/job-err")

    payload = response.json()
    assert response.status_code == 500
    assert payload["Success"] is False
    assert isinstance(payload["Error"], str)
    assert isinstance(payload["StackTrace"], list)
