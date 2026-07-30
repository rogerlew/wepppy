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
    user = SimpleNamespace(
        get_id=lambda: "user-1",
        email="user@example.com",
        is_authenticated=True,
        roles={"PowerUser"},
    )
    user.has_role = lambda role: role in user.roles
    monkeypatch.setattr(module, "current_user", user)
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
        yield client, tmp_path, issue_token_calls, module, user


def test_query_engine_mcp_instructions_do_not_persist_token(command_bar_client) -> None:
    client, run_root, issue_token_calls, _module, _user = command_bar_client

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
    assert issue_token_calls[0]["scopes"] == [
        "runs:read",
        "queries:validate",
        "queries:execute",
    ]
    assert issue_token_calls[0]["runs"] == ["run-1"]
    assert issue_token_calls[0]["audience"] == ["query-engine"]
    assert issue_token_calls[0]["extra_claims"] == {"token_class": "mcp"}


def test_get_directory_locks_returns_runtime_lock_statuses(command_bar_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _run_root, _issue_token_calls, module, _user = command_bar_client
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
    client, _run_root, _issue_token_calls, module, _user = command_bar_client
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

    assert client.get("/runs/run-1/cfg/command_bar/clear_directory_locks").status_code == 405
    response = client.post("/runs/run-1/cfg/command_bar/clear_directory_locks")

    assert response.status_code == 200
    payload = response.get_json()["Content"]
    assert payload["cleared_count"] == 1
    assert payload["cleared_directory_locks"][0]["runid"] == "run-1"
    assert payload["cleared_directory_locks"][0]["key"].startswith("nodb-lock:path-scope:")


def test_directory_locks_service_unavailable_returns_503(command_bar_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _run_root, _issue_token_calls, module, _user = command_bar_client
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
    client, _run_root, _issue_token_calls, module, _user = command_bar_client
    monkeypatch.setattr(
        module,
        "clear_runtime_locks",
        lambda _runid: (_ for _ in ()).throw(RuntimeError("redis unavailable")),
    )

    response = client.post("/runs/run-1/cfg/command_bar/clear_directory_locks")

    assert response.status_code == 503
    payload = response.get_json()
    assert "Runtime lock service unavailable" in payload["error"]["message"]


def test_mutating_command_routes_enforce_authentication_and_privileged_role(command_bar_client) -> None:
    client, _run_root, issue_token_calls, _module, user = command_bar_client

    user.roles = {"User"}
    loglevel_response = client.post(
        "/runs/run-1/cfg/command_bar/loglevel",
        json={"level": "info"},
    )
    assert loglevel_response.status_code == 403
    assert "PowerUser" in loglevel_response.get_json()["error"]["message"]
    clear_response = client.post(
        "/runs/run-1/cfg/command_bar/clear_directory_locks",
    )
    assert clear_response.status_code == 403
    assert "PowerUser" in clear_response.get_json()["error"]["message"]

    user.is_authenticated = False
    response = client.post("/runs/run-1/cfg/command_bar/query_engine_mcp_token")

    assert response.status_code == 403
    assert response.get_json()["error"]["message"] == "Authentication is required."
    assert issue_token_calls == []


def test_poweruser_can_set_log_level(command_bar_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _run_root, _issue_token_calls, module, _user = command_bar_client
    stored: list[tuple[str, str]] = []
    monkeypatch.setattr(
        module,
        "try_redis_set_log_level",
        lambda runid, level: stored.append((runid, level)),
    )
    monkeypatch.setattr(module, "try_redis_get_log_level", lambda _runid: module.LogLevel.INFO.value)

    response = client.post(
        "/runs/run-1/cfg/command_bar/loglevel",
        json={"level": "INFO"},
    )

    assert response.status_code == 200
    assert stored == [("run-1", "info")]
    assert response.get_json()["Content"]["log_level"] == "info"
