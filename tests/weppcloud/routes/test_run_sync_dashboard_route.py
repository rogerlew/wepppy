from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

import wepppy.weppcloud.routes.run_sync_dashboard.run_sync_dashboard as run_sync_module


pytestmark = pytest.mark.routes


def test_issue_token_preserves_admin_identity_and_enqueue_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issued: list[tuple[tuple, dict]] = []
    user = SimpleNamespace(
        get_id=lambda: "admin-7",
        id=7,
        email="admin@example.com",
        roles=[SimpleNamespace(name="Admin")],
    )
    monkeypatch.setattr(run_sync_module, "current_user", user)
    monkeypatch.setattr(
        run_sync_module.auth_tokens,
        "issue_token",
        lambda *args, **kwargs: (
            issued.append((args, kwargs)) or {"token": "rq-token"}
        ),
    )
    monkeypatch.setattr(run_sync_module.uuid, "uuid4", lambda: SimpleNamespace(hex="jti-1"))

    token = run_sync_module._issue_rq_engine_token()

    assert token == "rq-token"
    assert issued == [
        (
            ("admin-7",),
            {
                "scopes": ["rq:enqueue"],
                "audience": "rq-engine",
                "extra_claims": {
                    "roles": ["Admin"],
                    "token_class": "user",
                    "email": "admin@example.com",
                    "jti": "jti-1",
                },
            },
        )
    ]


def test_run_sync_dashboard_renders_exact_server_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_sync_module, "_issue_rq_engine_token", lambda: "rq-token")
    monkeypatch.setattr(
        run_sync_module,
        "render_template",
        lambda template, **context: {"template": template, **context},
    )
    route = inspect.unwrap(run_sync_module.run_sync_dashboard)

    context = route()

    assert context == {
        "template": "rq-run-sync-dashboard.htm",
        "default_target_root": run_sync_module.DEFAULT_TARGET_ROOT,
        "status_channel_suffix": run_sync_module.STATUS_CHANNEL_SUFFIX,
        "migrations_channel_suffix": run_sync_module.MIGRATIONS_CHANNEL_SUFFIX,
        "rq_engine_token": "rq-token",
    }
