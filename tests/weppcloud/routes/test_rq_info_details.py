from __future__ import annotations

from datetime import datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path

import pytest

pytest.importorskip("flask")
pytest.importorskip("flask_security")
from flask import Flask

rq_info_details_module = import_module("wepppy.weppcloud.routes.rq.info_details.routes")

pytestmark = pytest.mark.routes

REPO_ROOT = Path(__file__).resolve().parents[3]
INFO_DETAILS_TEMPLATE = (
    REPO_ROOT / "wepppy" / "weppcloud" / "routes" / "rq" / "info_details" / "templates" / "info_details.htm"
)


def test_filter_failed_jobs_keeps_only_failed_entries() -> None:
    jobs = [
        {"job_id": "failed-status", "status": "failed", "registry": "finished"},
        {"job_id": "failed-registry", "status": "finished", "registry": "failed"},
        {"job_id": "uppercase-status", "status": "FAILED", "registry": "finished"},
        {"job_id": "finished", "status": "finished", "registry": "finished"},
        {"job_id": "stopped", "status": "stopped", "registry": "finished"},
    ]

    filtered = rq_info_details_module._filter_failed_jobs(jobs)

    assert [job["job_id"] for job in filtered] == [
        "failed-status",
        "failed-registry",
        "uppercase-status",
    ]


def test_template_includes_failed_jobs_panel() -> None:
    source = INFO_DETAILS_TEMPLATE.read_text(encoding="utf-8")

    assert "<h2>Failed Jobs (Last 24 Hours)</h2>" in source
    assert "{% if failed_jobs %}" in source
    assert "last {{ failed_lookback_seconds // 3600 }} hours" in source


def test_rq_info_details_route_wires_failed_jobs_context(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)
    completed_jobs = [
        {
            "job_id": "failed-recent",
            "status": "failed",
            "registry": "failed",
            "ended_at": (now - timedelta(hours=1)).isoformat(),
        },
        {
            "job_id": "finished-recent",
            "status": "finished",
            "registry": "finished",
            "ended_at": (now - timedelta(minutes=30)).isoformat(),
        },
        {
            "job_id": "failed-old",
            "status": "failed",
            "registry": "failed",
            "ended_at": (now - timedelta(hours=23)).isoformat(),
        },
        {
            "job_id": "finished-outside-recent",
            "status": "finished",
            "registry": "finished",
            "ended_at": (now - timedelta(hours=3)).isoformat(),
        },
    ]
    lookback_calls: list[int] = []
    captured_context: dict[str, object] = {}

    class _DummyRedis:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> object:
            return object()

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

    def _fake_recently_completed(
        _redis_conn: object,
        *,
        queue_names: tuple[str, ...],
        lookback_seconds: int,
    ) -> list[dict[str, str]]:
        assert queue_names == ("default", "batch")
        lookback_calls.append(lookback_seconds)
        return completed_jobs

    def _fake_render_template(_template_name: str, **context: object) -> str:
        captured_context.update(context)
        return "ok"

    app = Flask(__name__)

    monkeypatch.setattr(rq_info_details_module, "redis_connection_kwargs", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(rq_info_details_module.redis, "Redis", _DummyRedis)
    monkeypatch.setattr(rq_info_details_module, "list_recently_completed_jobs", _fake_recently_completed)
    monkeypatch.setattr(rq_info_details_module, "list_active_jobs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(rq_info_details_module, "render_template", _fake_render_template)
    monkeypatch.setattr(rq_info_details_module, "url_for_run", lambda endpoint, **_kwargs: f"/{endpoint}")

    with app.test_request_context("/rq/info-details"):
        response = rq_info_details_module.rq_info_details.__wrapped__.__wrapped__()

    assert response == "ok"
    assert lookback_calls == [rq_info_details_module.FAILED_JOBS_LOOKBACK_SECONDS]
    assert captured_context["failed_lookback_seconds"] == rq_info_details_module.FAILED_JOBS_LOOKBACK_SECONDS
    assert [job["job_id"] for job in captured_context["failed_jobs"]] == ["failed-recent", "failed-old"]
    assert [job["job_id"] for job in captured_context["recent_jobs"]] == ["failed-recent", "finished-recent"]
