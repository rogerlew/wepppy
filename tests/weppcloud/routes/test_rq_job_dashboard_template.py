from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.weppcloud.routes.rq.job_dashboard import routes

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


def test_dashboard_loads_controller_stale_check_and_qr_assets() -> None:
    template = _template_text()

    assert "static_url('js/controllers-gl.js')" in template
    assert "static_url('js/controllers_gl_stale_check.js')" in template
    assert "static_url('js/qrcode.js')" in template


@pytest.mark.parametrize(
    "job_id",
    [
        "b774ed39c0ef44f2bb0efbdc6dda2c84",
        "b774ed39-c0ef-44f2-bb0e-fbdc6dda2c84",
    ],
)
def test_dashboard_preserves_exact_rq_job_id(
    monkeypatch: pytest.MonkeyPatch,
    job_id: str,
) -> None:
    rendered: dict[str, str] = {}

    def fake_render_template(template_name: str, **context: str) -> str:
        rendered.update(context)
        return template_name

    monkeypatch.setattr(routes, "render_template", fake_render_template)

    result = routes.job_dashboard_route.__wrapped__(job_id)

    assert result == "dashboard_pure.htm"
    assert rendered["job_id"] == job_id
