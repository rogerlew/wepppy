from __future__ import annotations

import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.jobinfo as jobinfo_module


pytestmark = pytest.mark.routes


@pytest.fixture()
def jobinfo_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(jobinfo_module.rq_jobinfo_bp)
    return app


def test_jobstatus_returns_404_for_not_found(
    jobinfo_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_jobstatus(job_id: str) -> dict[str, str]:
        return {"id": job_id, "status": "not_found"}

    monkeypatch.setattr(jobinfo_module, "get_wepppy_rq_job_status", fake_jobstatus)

    with jobinfo_app.test_client() as client:
        response = client.get("/rq/api/jobstatus/job-missing")

    assert response.status_code == 404
    assert response.get_json() == {"id": "job-missing", "status": "not_found"}


def test_jobinfo_returns_404_for_not_found(
    jobinfo_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_jobinfo(job_id: str) -> dict[str, str]:
        return {"id": job_id, "status": "not_found"}

    monkeypatch.setattr(jobinfo_module, "get_wepppy_rq_job_info", fake_jobinfo)

    with jobinfo_app.test_client() as client:
        response = client.get("/rq/api/jobinfo/job-missing")

    assert response.status_code == 404
    assert response.get_json() == {"id": "job-missing", "status": "not_found"}
