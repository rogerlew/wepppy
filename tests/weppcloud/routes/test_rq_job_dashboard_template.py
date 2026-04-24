from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.routes


TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3]
    / "wepppy"
    / "weppcloud"
    / "routes"
    / "rq"
    / "job_dashboard"
    / "templates"
    / "dashboard_pure.htm"
)


def _template_text() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def test_cancel_job_uses_rq_engine_token_fallback_when_runid_missing() -> None:
    template = _template_text()

    assert 'errors.push("Run ID unavailable for session token");' in template
    assert "return await fetchSessionToken();" in template
    assert "return await fetchRqEngineToken();" in template
    assert "prefixedUrl(\"/api/auth/rq-engine-token\")" in template


def test_cancel_job_surfaces_response_message_and_refreshes_dashboard() -> None:
    template = _template_text()

    assert "const token = await getCancelAuthToken();" in template
    assert "alert(message);" in template
    assert "fetchJobStatus();" in template
