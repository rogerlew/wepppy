from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest

run_0_module = importlib.import_module(
    "wepppy.weppcloud.routes.run_0.run_0_bp"
)


pytestmark = pytest.mark.routes


def test_create_page_rq_token_uses_numeric_user_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issued: dict[str, object] = {}
    user = SimpleNamespace(
        id=42,
        email="viewer@example.test",
        roles=[SimpleNamespace(name="User")],
        get_id=lambda: "fs-uniquifier-must-not-be-the-subject",
    )

    def _issue_token(subject, **kwargs):
        issued["subject"] = subject
        issued.update(kwargs)
        return {"token": "rq-token"}

    monkeypatch.setattr(run_0_module, "current_user", user)
    monkeypatch.setattr(run_0_module.auth_tokens, "issue_token", _issue_token)

    assert run_0_module._issue_rq_engine_token() == "rq-token"
    assert issued["subject"] == "42"
    assert issued["extra_claims"]["email"] == user.email


@pytest.mark.parametrize("user_id", (None, 0, -1, True, "42"))
def test_create_page_rq_token_rejects_non_positive_numeric_user_id(
    monkeypatch: pytest.MonkeyPatch,
    user_id: object,
) -> None:
    user = SimpleNamespace(
        id=user_id,
        email="viewer@example.test",
        roles=[SimpleNamespace(name="User")],
    )

    def _unexpected_issue_token(*_args, **_kwargs):
        pytest.fail("token issuance must not run without a positive numeric user ID")

    monkeypatch.setattr(run_0_module, "current_user", user)
    monkeypatch.setattr(
        run_0_module.auth_tokens,
        "issue_token",
        _unexpected_issue_token,
    )

    with pytest.raises(RuntimeError, match="positive numeric user subject"):
        run_0_module._issue_rq_engine_token()
