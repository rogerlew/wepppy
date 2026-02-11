from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask


pytestmark = pytest.mark.routes


@pytest.fixture()
def command_bar_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    module = importlib.reload(importlib.import_module("wepppy.weppcloud.routes.command_bar.command_bar"))

    app = Flask(__name__)
    app.config.update(SECRET_KEY="command-bar-test", TESTING=True)
    app.register_blueprint(module.command_bar_bp)

    monkeypatch.setattr(module, "authorize", lambda runid, config: None)
    monkeypatch.setattr(
        module,
        "load_run_context",
        lambda runid, config: SimpleNamespace(active_root=str(tmp_path)),
    )
    monkeypatch.setattr(
        module,
        "current_user",
        SimpleNamespace(get_id=lambda: "user-1", email="user@example.com"),
    )
    issue_token_calls: list[dict[str, object]] = []

    def _issue_token(*_args, **kwargs):
        issue_token_calls.append(dict(kwargs))
        return {
            "token": "super-secret-token",
            "claims": {
                "exp": 1_700_000_000,
                "scope": "runs:read queries:validate queries:execute",
            },
        }

    monkeypatch.setattr(
        module.auth_tokens,
        "issue_token",
        _issue_token,
    )
    monkeypatch.setattr(module.auth_tokens, "get_jwt_config", lambda: SimpleNamespace(scope_separator=" "))

    with app.test_client() as client:
        yield client, tmp_path, issue_token_calls


def test_query_engine_mcp_instructions_do_not_persist_token(command_bar_client) -> None:
    client, run_root, issue_token_calls = command_bar_client

    response = client.post(
        "/runs/run-1/cfg/command_bar/query_engine_mcp_token",
        headers={"Host": "example.test"},
    )

    assert response.status_code == 200
    payload = response.get_json()["Content"]
    assert payload["token"] == "super-secret-token"

    instructions_relpath = payload["instructions_path"]
    instructions_path = run_root / instructions_relpath
    assert instructions_path.exists()

    markdown = instructions_path.read_text(encoding="utf-8")
    assert "super-secret-token" not in markdown
    assert "Authorization: Bearer <paste-token-from-command-bar-response>" in markdown
    assert issue_token_calls[0]["extra_claims"] == {"token_class": "mcp"}
