from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Tuple

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import project_routes
from wepppy.weppcloud.utils import auth_tokens

pytestmark = pytest.mark.microservice

RUN_ID = "cap-run"
CONFIG = "disturbed9002"


def _issue_token(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()
    payload = auth_tokens.issue_token(
        "42",
        scopes=["rq:enqueue"],
        audience="rq-engine",
        extra_claims={"jti": "test-jti", "token_class": "user", "email": "tester@example.com"},
    )
    return payload["token"]


@pytest.fixture()
def create_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Tuple[Any, Dict[str, Any]]:
    captured: Dict[str, Any] = {}

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    def fake_create_run_dir(user_email: str | None) -> Tuple[str, str]:
        captured["email"] = user_email
        return RUN_ID, str(run_dir)

    class DummyRon:
        def __init__(self, wd: str, cfg: str) -> None:
            captured["wd"] = wd
            captured["cfg"] = cfg
            self._cfg = cfg

        def config_get_bool(self, section: str, option: str, default: bool | None = None) -> bool:
            if section != "nodb" or option != "apply_nodir":
                return bool(default)
            if "?" not in self._cfg:
                return False if default is None else bool(default)
            _, query = self._cfg.split("?", 1)
            for pair in query.split("&"):
                if "=" not in pair:
                    continue
                key, value = pair.split("=", 1)
                if key != "nodb:apply_nodir":
                    continue
                return value.strip().lower().startswith("true")
            return False if default is None else bool(default)

    monkeypatch.setattr(project_routes, "_create_run_dir", fake_create_run_dir)
    monkeypatch.setattr(project_routes, "Ron", DummyRon)
    monkeypatch.setattr(project_routes, "ensure_readme_on_create", lambda runid, config: None)
    monkeypatch.delenv("WEPP_NODIR_DEFAULT_NEW_RUNS", raising=False)
    monkeypatch.setenv("SITE_PREFIX", "/weppcloud")

    with TestClient(rq_engine.app) as client:
        yield client, captured


def test_create_requires_cap_token(create_client):
    client, captured = create_client

    response = client.post("/create/", data={"config": CONFIG})

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "CAPTCHA token is required."
    assert "cfg" not in captured


def test_create_rejects_invalid_token(create_client, monkeypatch: pytest.MonkeyPatch):
    client, captured = create_client

    monkeypatch.setattr(
        project_routes,
        "_verify_cap_token",
        lambda request, token: {"success": False, "error-codes": ["invalid"]},
    )

    response = client.post("/create/", data={"config": CONFIG, "cap_token": "bad-token"})

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "CAPTCHA verification failed."
    assert "cfg" not in captured


def test_create_accepts_valid_cap_token(create_client, monkeypatch: pytest.MonkeyPatch):
    client, captured = create_client

    monkeypatch.setattr(
        project_routes,
        "_verify_cap_token",
        lambda request, token: {"success": True},
    )

    response = client.post(
        "/create/",
        data={"config": CONFIG, "cap_token": "good-token", "unitizer:is_english": ""},
        follow_redirects=False,
    )

    assert response.status_code == 303
    location = response.headers["Location"].rstrip("/")
    assert location.endswith(f"/weppcloud/runs/{RUN_ID}/{CONFIG}")
    assert captured["cfg"] == f"{CONFIG}.cfg"


def test_create_accepts_rq_token(create_client, monkeypatch: pytest.MonkeyPatch):
    client, captured = create_client

    token = _issue_token(monkeypatch)
    stub_user = SimpleNamespace(email="tester@example.com")
    owner_calls: Dict[str, Any] = {}

    monkeypatch.setattr(project_routes, "_resolve_user_from_claims", lambda claims: stub_user)

    def fake_register(runid: str, config: str, user: Any) -> None:
        owner_calls["runid"] = runid
        owner_calls["config"] = config
        owner_calls["user_email"] = getattr(user, "email", None)

    monkeypatch.setattr(project_routes, "_register_run_owner", fake_register)
    monkeypatch.setattr(project_routes, "_check_revocation", lambda jti: None)

    response = client.post(
        "/create/",
        data={"config": CONFIG, "rq_token": token, "unitizer:is_english": "true"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert owner_calls["runid"] == RUN_ID
    assert owner_calls["config"] == CONFIG
    assert owner_calls["user_email"] == "tester@example.com"


def test_create_does_not_enable_default_nodir_roots_marker_without_opt_in(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, captured = create_client

    monkeypatch.setattr(
        project_routes,
        "_verify_cap_token",
        lambda request, token: {"success": True},
    )

    response = client.post(
        "/create/",
        data={"config": CONFIG, "cap_token": "good-token"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    marker_path = Path(captured["wd"]) / ".nodir" / "default_archive_roots.json"
    assert not marker_path.exists()


def test_create_does_not_enable_default_nodir_roots_marker_with_opt_in_override(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, captured = create_client

    monkeypatch.setattr(
        project_routes,
        "_verify_cap_token",
        lambda request, token: {"success": True},
    )

    response = client.post(
        "/create/",
        data={"config": CONFIG, "cap_token": "good-token", "nodb:apply_nodir": "true"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert captured["cfg"] == f"{CONFIG}.cfg?nodb:apply_nodir=true"
    marker_path = Path(captured["wd"]) / ".nodir" / "default_archive_roots.json"
    assert not marker_path.exists()


def test_create_opt_in_respects_global_nodir_env_gate(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, captured = create_client

    monkeypatch.setattr(
        project_routes,
        "_verify_cap_token",
        lambda request, token: {"success": True},
    )
    monkeypatch.setenv("WEPP_NODIR_DEFAULT_NEW_RUNS", "0")

    response = client.post(
        "/create/",
        data={"config": CONFIG, "cap_token": "good-token", "nodb:apply_nodir": "true"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert captured["cfg"] == f"{CONFIG}.cfg?nodb:apply_nodir=true"
    marker_path = Path(captured["wd"]) / ".nodir" / "default_archive_roots.json"
    assert not marker_path.exists()
