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
        yield client, tmp_path, issue_token_calls, module


def test_query_engine_mcp_instructions_do_not_persist_token(command_bar_client) -> None:
    client, run_root, issue_token_calls, _module = command_bar_client

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


def test_get_directory_locks_returns_runtime_lock_statuses(command_bar_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _run_root, _issue_token_calls, module = command_bar_client
    monkeypatch.setattr(
        module,
        "runtime_lock_statuses",
        lambda runid: [
            {
                "key": "nodb-lock:run-1:runtime-paths/landuse",
                "root": "landuse",
                "owner": "host:123",
                "runid": runid,
                "scope": "legacy_runid",
                "purpose": "unit-test",
                "expires_at": 1_700_000_000,
                "acquired_at": 1_699_999_900,
                "ttl_seconds": 100,
            }
        ],
    )

    response = client.get("/runs/run-1/cfg/command_bar/directory_locks")

    assert response.status_code == 200
    payload = response.get_json()["Content"]["directory_locks"]
    assert payload == [
        {
            "key": "nodb-lock:run-1:runtime-paths/landuse",
            "root": "landuse",
            "owner": "host:123",
            "runid": "run-1",
            "scope": "legacy_runid",
            "purpose": "unit-test",
            "expires_at": 1_700_000_000,
            "acquired_at": 1_699_999_900,
            "ttl_seconds": 100,
        }
    ]


def test_clear_directory_locks_returns_cleared_payload(command_bar_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _run_root, _issue_token_calls, module = command_bar_client
    monkeypatch.setattr(
        module,
        "clear_runtime_locks",
        lambda runid: [
            {
                "key": "nodb-lock:path-scope:abc123:runtime-paths/landuse",
                "root": "landuse",
                "owner": "host:321",
                "runid": runid,
                "scope": "effective_root_path_compat",
                "purpose": "clear-test",
                "expires_at": 1_700_000_100,
                "acquired_at": 1_700_000_000,
                "ttl_seconds": 100,
            }
        ],
    )

    response = client.get("/runs/run-1/cfg/command_bar/clear_directory_locks")

    assert response.status_code == 200
    payload = response.get_json()["Content"]
    assert payload["cleared_count"] == 1
    assert payload["cleared_directory_locks"][0]["runid"] == "run-1"
    assert payload["cleared_directory_locks"][0]["key"].startswith("nodb-lock:path-scope:")


def test_directory_locks_service_unavailable_returns_503(command_bar_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _run_root, _issue_token_calls, module = command_bar_client
    monkeypatch.setattr(
        module,
        "runtime_lock_statuses",
        lambda _runid: (_ for _ in ()).throw(RuntimeError("redis unavailable")),
    )

    response = client.get("/runs/run-1/cfg/command_bar/directory_locks")

    assert response.status_code == 503
    payload = response.get_json()
    assert "Runtime lock service unavailable" in payload["error"]["message"]


def test_clear_directory_locks_service_unavailable_returns_503(command_bar_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _run_root, _issue_token_calls, module = command_bar_client
    monkeypatch.setattr(
        module,
        "clear_runtime_locks",
        lambda _runid: (_ for _ in ()).throw(RuntimeError("redis unavailable")),
    )

    response = client.get("/runs/run-1/cfg/command_bar/clear_directory_locks")

    assert response.status_code == 503
    payload = response.get_json()
    assert "Runtime lock service unavailable" in payload["error"]["message"]
