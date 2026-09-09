from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import project_routes
from wepppy.weppcloud.utils import auth_tokens
from wepppy.weppcloud.user_preferences import (
    CreationActor,
    PreferenceIdentityError,
)
from sqlalchemy.exc import SQLAlchemyError

pytestmark = pytest.mark.microservice

RUN_ID = "cap-run"
CONFIG = "disturbed9002"


class _FakeIdempotencyRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def set(self, key: str, value: str, *, nx: bool = False, xx: bool = False, ex: int) -> bool:
        if nx and key in self.values:
            return False
        if xx and key not in self.values:
            return False
        self.values[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def delete(self, key: str) -> int:
        return int(self.values.pop(key, None) is not None)


def _creation_actor() -> CreationActor:
    return CreationActor(
        user_id=42,
        email="tester@example.com",
    )


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
    request,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Tuple[Any, Dict[str, Any]]:
    monkeypatch.delenv("WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION", raising=False)
    if hasattr(request, "param"):
        monkeypatch.setenv("WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION", request.param)
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
    monkeypatch.delenv("WEPPPY_PROJECT_CONFIG_PRESET_WRITER_ENABLED", raising=False)
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


@pytest.mark.parametrize("create_client", ["true", "on"], indirect=True)
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


def test_create_api_alias_accepts_valid_cap_token(create_client, monkeypatch: pytest.MonkeyPatch):
    client, captured = create_client

    monkeypatch.setattr(
        project_routes,
        "_verify_cap_token",
        lambda request, token: {"success": True},
    )

    response = client.post(
        "/api/create/",
        data={"config": CONFIG, "cap_token": "good-token"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    location = response.headers["Location"].rstrip("/")
    assert location.endswith(f"/weppcloud/runs/{RUN_ID}/{CONFIG}")
    assert captured["cfg"] == f"{CONFIG}.cfg"


def test_flagged_create_materializes_before_ron_and_replays_original_redirect(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, captured = create_client
    idempotency = _FakeIdempotencyRedis()
    ron_observation: dict[str, bool] = {}

    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_PRESET_WRITER_ENABLED", "1")
    monkeypatch.setenv("RQ_ENGINE_DEPLOYMENT_REVISION", "test-revision")
    monkeypatch.setattr(project_routes, "_creation_idempotency_client", lambda: idempotency)
    monkeypatch.setattr(
        project_routes,
        "_verify_cap_token",
        lambda _request, _token: {"success": True},
    )

    class ObservingRon:
        def __init__(self, wd: str, cfg: str) -> None:
            captured["wd"] = wd
            captured["cfg"] = cfg
            run_root = Path(wd)
            ron_observation["config"] = (run_root / f"{CONFIG}.cfg").is_file()
            ron_observation["manifest"] = (run_root / "config-manifest.json").is_file()

        def config_get_bool(self, _section: str, _option: str, default: bool | None = None) -> bool:
            return bool(default)

    monkeypatch.setattr(project_routes, "Ron", ObservingRon)
    data = {
        "config": CONFIG,
        "cap_token": "good-token",
        "creation_idempotency_key": "12345678-1234-4234-9234-123456789abc",
        "unitizer:is_english": "true",
    }
    first = client.post("/create/", data=data, follow_redirects=False)
    replay = client.post("/create/", data=data, follow_redirects=False)

    assert first.status_code == replay.status_code == 303
    assert first.headers["Location"] == replay.headers["Location"]
    assert ron_observation == {"config": True, "manifest": True}
    assert captured["cfg"] == f"{CONFIG}.cfg"
    manifest = Path(captured["wd"]) / "config-manifest.json"
    assert '"source_preset":"disturbed9002"' in manifest.read_text(encoding="utf-8")


def test_flagged_create_same_key_different_input_conflicts(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _captured = create_client
    idempotency = _FakeIdempotencyRedis()
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_PRESET_WRITER_ENABLED", "1")
    monkeypatch.setattr(project_routes, "_creation_idempotency_client", lambda: idempotency)
    monkeypatch.setattr(
        project_routes,
        "_verify_cap_token",
        lambda _request, _token: {"success": True},
    )
    key = "abcdef12-1234-4234-9234-123456789abc"
    first = client.post(
        "/create/",
        data={"config": CONFIG, "cap_token": "good", "creation_idempotency_key": key},
        follow_redirects=False,
    )
    conflict = client.post(
        "/create/",
        data={
            "config": CONFIG,
            "cap_token": "good",
            "creation_idempotency_key": key,
            "watershed:delineation_backend": "wbt",
        },
        follow_redirects=False,
    )

    assert first.status_code == 303
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_key_conflict"


@pytest.mark.parametrize("create_client", ["true", "false"], indirect=True)
def test_create_accepts_rq_token(create_client, monkeypatch: pytest.MonkeyPatch):
    client, captured = create_client

    token = _issue_token(monkeypatch)
    owner_calls: Dict[str, Any] = {}

    monkeypatch.setattr(
        project_routes,
        "resolve_creation_actor",
        lambda claims: _creation_actor(),
    )

    def fake_register(runid: str, config: str, user_id: int) -> None:
        owner_calls["runid"] = runid
        owner_calls["config"] = config
        owner_calls["user_id"] = user_id

    monkeypatch.setattr(project_routes, "register_owned_run", fake_register)
    monkeypatch.setattr(project_routes, "_check_revocation", lambda jti: None)

    response = client.post(
        "/create/",
        data={"config": CONFIG, "rq_token": token, "unitizer:is_english": "true"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert owner_calls["runid"] == RUN_ID
    assert owner_calls["config"] == CONFIG
    assert owner_calls["user_id"] == 42


def test_create_does_not_apply_account_preferences_to_durable_config(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, captured = create_client
    token = _issue_token(monkeypatch)
    monkeypatch.setattr(project_routes, "_check_revocation", lambda _jti: None)
    monkeypatch.setattr(
        project_routes,
        "resolve_creation_actor",
        lambda _claims: _creation_actor(),
    )
    monkeypatch.setattr(project_routes, "register_owned_run", lambda *_args: None)

    response = client.post(
        "/create/",
        data={"config": CONFIG, "rq_token": token},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "unitizer:is_english" not in captured["cfg"]
    assert "watershed.wbt:boundary_touch_behavior" not in captured["cfg"]


def test_create_payload_unit_override_wins_query(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, captured = create_client
    token = _issue_token(monkeypatch)
    monkeypatch.setattr(project_routes, "_check_revocation", lambda _jti: None)
    monkeypatch.setattr(
        project_routes,
        "resolve_creation_actor",
        lambda _claims: _creation_actor(),
    )
    monkeypatch.setattr(project_routes, "register_owned_run", lambda *_args: None)

    response = client.post(
        "/create/?unitizer:is_english=true",
        data={
            "config": CONFIG,
            "rq_token": token,
            "unitizer:is_english": "false",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert captured["cfg"].count("unitizer:is_english=false") == 1
    assert "unitizer:is_english=true" not in captured["cfg"]


def test_create_rejects_locale_override_before_run_publication(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, captured = create_client
    token = _issue_token(monkeypatch)
    monkeypatch.setattr(project_routes, "_check_revocation", lambda _jti: None)

    response = client.post(
        '/create/?general:locales=["eu"]',
        data={"config": CONFIG, "rq_token": token},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "project_config_validation_failed"
    assert "general.locales" in response.json()["error"]["details"]
    assert "cfg" not in captured


def test_create_transport_idempotency_key_is_not_a_runtime_override(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, captured = create_client
    monkeypatch.setattr(
        project_routes,
        "_verify_cap_token",
        lambda _request, _token: {"success": True},
    )

    response = client.post(
        "/create/",
        data={
            "config": CONFIG,
            "cap_token": "good-token",
            "creation_idempotency_key": "12345678-1234-4234-9234-123456789abc",
            "unitizer:is_english": "true",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert captured["cfg"].endswith("?unitizer:is_english=true")
    assert "creation_idempotency_key" not in captured["cfg"]


def test_create_invalid_explicit_unit_fails_before_run_directory(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, captured = create_client
    monkeypatch.setattr(
        project_routes,
        "_verify_cap_token",
        lambda _request, _token: {"success": True},
    )

    response = client.post(
        "/create/",
        data={
            "config": CONFIG,
            "cap_token": "good-token",
            "unitizer:is_english": "yes",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_unitizer_override"
    assert captured == {}


def test_create_payload_failure_does_not_disclose_traceback_or_path(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, captured = create_client

    async def _raise_payload_error(_request):
        raise RuntimeError("Traceback at /private/parser.py")

    monkeypatch.setattr(project_routes, "parse_request_payload", _raise_payload_error)

    response = client.post("/create/", data={"config": CONFIG})

    assert response.status_code == 400
    assert response.json()["error_id"]
    assert "Traceback" not in response.text
    assert "/private/parser.py" not in response.text
    assert captured == {}


def test_create_run_directory_failure_does_not_disclose_path(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, captured = create_client
    monkeypatch.setattr(
        project_routes,
        "_verify_cap_token",
        lambda _request, _token: {"success": True},
    )
    monkeypatch.setattr(
        project_routes,
        "_create_run_dir",
        lambda _email: (_ for _ in ()).throw(
            RuntimeError("/private/runs/secret failed")
        ),
    )

    response = client.post(
        "/create/",
        data={"config": CONFIG, "cap_token": "good-token"},
    )

    assert response.status_code == 500
    assert response.json()["error_id"]
    assert "/private/runs" not in response.text
    assert captured == {}


def test_create_initialization_failure_returns_correlated_diagnostic(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _captured = create_client
    monkeypatch.setattr(
        project_routes,
        "_verify_cap_token",
        lambda _request, _token: {"success": True},
    )
    monkeypatch.setattr(
        project_routes,
        "Ron",
        lambda _wd, _cfg: (_ for _ in ()).throw(ValueError("/private/run path")),
    )

    response = client.post(
        "/create/",
        data={"config": CONFIG, "cap_token": "good-token"},
    )

    payload = response.json()
    assert response.status_code == 500
    assert payload["error"]["code"] == "run_initialization_failed"
    assert "Run initialization failed." in payload["error"]["details"]
    assert "cause could not be safely identified" in payload["error"]["details"]
    assert "/private/run" not in response.text


@pytest.mark.parametrize("auth_path", ("bearer", "session", "expired_reauth"))
def test_create_unexpected_auth_failure_is_sanitized(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
    auth_path: str,
) -> None:
    client, captured = create_client
    headers: dict[str, str] = {}
    data = {"config": CONFIG}

    if auth_path == "bearer":
        headers["Authorization"] = "Bearer opaque"
        monkeypatch.setattr(
            project_routes,
            "require_jwt",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("Traceback /private/bearer.py")
            ),
        )
    elif auth_path == "session":
        monkeypatch.setattr(
            project_routes,
            "_claims_from_session_cookie",
            lambda _request: (_ for _ in ()).throw(
                RuntimeError("Traceback /private/session.py")
            ),
        )
    else:
        data["rq_token"] = "expired"
        monkeypatch.setattr(
            project_routes,
            "_require_rq_token",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                project_routes.AuthError("Token has expired")
            ),
        )
        monkeypatch.setattr(
            project_routes,
            "_claims_from_session_cookie",
            lambda _request: (_ for _ in ()).throw(
                RuntimeError("Traceback /private/reauth.py")
            ),
        )

    response = client.post("/create/", data=data, headers=headers)

    assert response.status_code == 401
    assert response.json()["error_id"]
    assert "Traceback" not in response.text
    assert "/private/" not in response.text
    assert captured == {}


@pytest.mark.parametrize("create_client", ["true", "false"], indirect=True)
def test_create_actor_lookup_failure_creates_no_directory(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, captured = create_client
    token = _issue_token(monkeypatch)
    monkeypatch.setattr(project_routes, "_check_revocation", lambda _jti: None)
    monkeypatch.setattr(
        project_routes,
        "resolve_creation_actor",
        lambda _claims: (_ for _ in ()).throw(
            PreferenceIdentityError("unknown user")
        ),
    )

    response = client.post(
        "/create/",
        data={"config": CONFIG, "rq_token": token},
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "run_ownership_failed"
    assert response.json()["error_id"]
    assert captured == {}


def test_create_owner_failure_compensates_directory(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _captured = create_client
    token = _issue_token(monkeypatch)
    cleanups: list[tuple[str, str]] = []
    monkeypatch.setattr(project_routes, "_check_revocation", lambda _jti: None)
    monkeypatch.setattr(
        project_routes,
        "resolve_creation_actor",
        lambda _claims: _creation_actor(),
    )
    monkeypatch.setattr(
        project_routes,
        "register_owned_run",
        lambda *_args: (_ for _ in ()).throw(SQLAlchemyError("owner write failed")),
    )
    monkeypatch.setattr(
        project_routes,
        "cleanup_new_run_directory",
        lambda runid, wd: cleanups.append((runid, wd)),
    )

    response = client.post(
        "/create/",
        data={"config": CONFIG, "rq_token": token},
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "run_ownership_failed"
    assert cleanups and cleanups[0][0] == RUN_ID


@pytest.mark.parametrize(
    "cleanup_error",
    (
        OSError("cleanup failed"),
        project_routes.redis.RedisError("redis cleanup failed"),
    ),
)
def test_create_cleanup_failure_log_uses_response_error_id(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    cleanup_error: BaseException,
) -> None:
    client, _captured = create_client
    token = _issue_token(monkeypatch)
    monkeypatch.setattr(project_routes, "_check_revocation", lambda _jti: None)
    monkeypatch.setattr(
        project_routes,
        "resolve_creation_actor",
        lambda _claims: _creation_actor(),
    )
    monkeypatch.setattr(
        project_routes,
        "register_owned_run",
        lambda *_args: (_ for _ in ()).throw(SQLAlchemyError("owner failed")),
    )
    monkeypatch.setattr(
        project_routes,
        "cleanup_new_run_directory",
        lambda *_args: (_ for _ in ()).throw(cleanup_error),
    )

    with caplog.at_level("ERROR", logger=project_routes.__name__):
        response = client.post(
            "/create/",
            data={"config": CONFIG, "rq_token": token},
        )

    error_id = response.json()["error_id"]
    cleanup_records = [
        record
        for record in caplog.records
        if record.getMessage().startswith("rq-engine create directory cleanup failed")
    ]
    assert response.status_code == 500
    assert RUN_ID not in response.text
    assert len(cleanup_records) == 1
    assert cleanup_records[0].error_id == error_id
    assert cleanup_records[0].runid == RUN_ID


@pytest.mark.parametrize("create_client", ["true", "false"], indirect=True)
def test_create_reauths_expired_rq_token_with_session_cookie(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, _ = create_client
    owner_calls: Dict[str, Any] = {}

    def _raise_expired_token(*_args, **_kwargs):
        raise project_routes.AuthError("Invalid token: Token has expired")

    monkeypatch.setattr(
        project_routes,
        "_require_rq_token",
        _raise_expired_token,
    )
    monkeypatch.setattr(
        project_routes,
        "_claims_from_session_cookie",
        lambda request: {"sub": "42", "token_class": "user", "email": "tester@example.com"},
    )
    monkeypatch.setattr(
        project_routes,
        "resolve_creation_actor",
        lambda claims: _creation_actor(),
    )

    def fake_register(runid: str, config: str, user_id: int) -> None:
        owner_calls["runid"] = runid
        owner_calls["config"] = config
        owner_calls["user_id"] = user_id

    monkeypatch.setattr(project_routes, "register_owned_run", fake_register)

    response = client.post(
        "/create/",
        data={"config": CONFIG, "rq_token": "expired-token"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert owner_calls["runid"] == RUN_ID
    assert owner_calls["config"] == CONFIG
    assert owner_calls["user_id"] == 42


@pytest.mark.parametrize("create_client", ["true", "false"], indirect=True)
def test_create_non_expired_rq_token_error_does_not_reauth(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, captured = create_client

    def _raise_signature_error(*_args, **_kwargs):
        raise project_routes.AuthError("Invalid token: Token signature mismatch")

    monkeypatch.setattr(
        project_routes,
        "_require_rq_token",
        _raise_signature_error,
    )

    def _unexpected_cookie_reauth(_request):
        raise AssertionError("session-cookie reauth should not be attempted")

    monkeypatch.setattr(project_routes, "_claims_from_session_cookie", _unexpected_cookie_reauth)

    response = client.post(
        "/create/",
        data={"config": CONFIG, "rq_token": "bad-token"},
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid token: Token signature mismatch"
    assert "cfg" not in captured


def test_create_accepts_session_cookie_auth_without_rq_token(
    create_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, _ = create_client
    owner_calls: Dict[str, Any] = {}

    monkeypatch.setattr(
        project_routes,
        "_claims_from_session_cookie",
        lambda request: {"sub": "42", "token_class": "user", "email": "tester@example.com"},
    )
    monkeypatch.setattr(
        project_routes,
        "resolve_creation_actor",
        lambda claims: _creation_actor(),
    )

    def fake_register(runid: str, config: str, user_id: int) -> None:
        owner_calls["runid"] = runid
        owner_calls["config"] = config
        owner_calls["user_id"] = user_id

    monkeypatch.setattr(project_routes, "register_owned_run", fake_register)

    response = client.post(
        "/create/",
        data={"config": CONFIG},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert owner_calls["runid"] == RUN_ID
    assert owner_calls["config"] == CONFIG
    assert owner_calls["user_id"] == 42


def test_cookie_claims_use_migration_aware_session_selector(monkeypatch):
    request = object()
    payload = {"_user_id": "42", "roles": ["User"]}
    from wepppy.microservices.rq_engine import session_routes

    monkeypatch.setattr(
        session_routes,
        "_is_same_origin_cookie_request",
        lambda candidate: candidate is request,
    )
    monkeypatch.setattr(
        session_routes,
        "_resolve_session_from_cookie",
        lambda candidate: ("owned-sid", payload),
    )
    monkeypatch.setattr(
        session_routes,
        "_resolve_session_id_from_cookie",
        lambda _request: (_ for _ in ()).throw(AssertionError("legacy-only selector used")),
    )

    monkeypatch.setattr(session_routes, "_resolve_roles_for_user_id", lambda user_id: ["User"])
    claims = project_routes._claims_from_session_cookie(request)

    assert claims["sub"] == "42"


def test_rq_token_rejects_revoked_session_sid(monkeypatch):
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()
    token = auth_tokens.issue_token(
        "revoked-sid",
        scopes=["rq:enqueue"],
        audience="rq-engine",
        extra_claims={
            "jti": "session-jti",
            "token_class": "session",
            "session_id": "revoked-sid",
        },
    )["token"]
    monkeypatch.setattr(project_routes, "_check_revocation", lambda _jti: None)
    monkeypatch.setattr(
        project_routes,
        "_check_session_revocation",
        lambda sid: (_ for _ in ()).throw(project_routes.AuthError("Session token has been revoked."))
        if sid == "revoked-sid"
        else None,
    )

    with pytest.raises(project_routes.AuthError, match="revoked"):
        project_routes._require_rq_token(token, required_scopes=["rq:enqueue"])


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


@pytest.mark.parametrize("path", ["/create/", "/api/create/"])
@pytest.mark.parametrize("transport", ["data", "json"])
@pytest.mark.parametrize("writer", ["true", "false"])
def test_restricted_create_denies_captcha_before_side_effects(
    create_client, monkeypatch, path, transport, writer,
):
    client, captured = create_client
    monkeypatch.setenv("WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION", "false")
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_PRESET_WRITER_ENABLED", writer)
    monkeypatch.setattr(project_routes, "_claims_from_session_cookie", lambda request: None)

    def forbidden(*args, **kwargs):
        pytest.fail("Restricted anonymous creation reached a side effect")

    monkeypatch.setattr(project_routes, "_verify_cap_token", forbidden)
    monkeypatch.setattr(project_routes, "_creation_idempotency_client", forbidden)
    response = client.post(path, **{transport: {"config": CONFIG, "cap_token": "solved-token"}})
    assert response.status_code == 403
    assert response.json()["error"] == {
        "message": "Sign in to create a project.", "code": "anonymous_creation_disabled",
        "details": "Sign in to create a project.",
    }
    assert "cfg" not in captured


@pytest.mark.parametrize("raw", ["", " ", "treu", "2"])
def test_create_invalid_policy_is_unavailable(create_client, monkeypatch, raw):
    client, captured = create_client
    monkeypatch.setenv("WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION", raw)
    response = client.post("/create/", json={"config": CONFIG, "cap_token": "solved"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "creation_policy_configuration_error"
    assert captured == {}


@pytest.mark.parametrize("token_class", ["session", "unknown", "USER", ""])
@pytest.mark.parametrize("transport", ["rq_token", "bearer"])
@pytest.mark.parametrize("user_id", [None, 42])
def test_restricted_create_rejects_disallowed_signed_token_class(
    create_client, monkeypatch, token_class, transport, user_id,
):
    client, captured = create_client
    monkeypatch.setenv("WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION", "false")
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()
    token = auth_tokens.issue_token(
        "42", scopes=["rq:enqueue"], audience="rq-engine",
        extra_claims={"jti": "policy-jti", "token_class": token_class, "session_id": "policy-sid", "user_id": user_id},
    )["token"]
    monkeypatch.setattr(project_routes, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(project_routes, "_check_session_revocation", lambda sid: None)
    from wepppy.microservices.rq_engine import auth
    monkeypatch.setattr(auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(auth, "_check_session_revocation", lambda sid: None)
    body = {"config": CONFIG}
    headers = {}
    if transport == "rq_token":
        body["rq_token"] = token
    else:
        headers["Authorization"] = f"Bearer {token}"
    response = client.post("/create/", json=body, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "anonymous_creation_disabled"
    assert captured == {}


@pytest.mark.parametrize("cap_token", ["", "stale-solved-token"])
def test_restricted_create_accepts_cookie_with_or_without_captcha(create_client, monkeypatch, cap_token):
    client, captured = create_client
    monkeypatch.setenv("WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION", "false")
    monkeypatch.setattr(project_routes, "_claims_from_session_cookie", lambda request: {"sub": "42", "token_class": "user"})
    monkeypatch.setattr(project_routes, "resolve_creation_actor", lambda claims: _creation_actor())
    monkeypatch.setattr(project_routes, "register_owned_run", lambda *args: None)
    response = client.post("/create/", data={"config": CONFIG, "cap_token": cap_token}, follow_redirects=False)
    assert response.status_code == 303
    assert captured["email"] == "tester@example.com"


@pytest.mark.parametrize("token_class", ["service", "mcp"])
def test_restricted_create_preserves_service_callers(create_client, monkeypatch, token_class):
    client, captured = create_client
    monkeypatch.setenv("WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION", "false")
    monkeypatch.setattr(project_routes, "require_jwt", lambda *args, **kwargs: {"sub": "operator", "token_class": token_class})
    response = client.post("/create/", json={"config": CONFIG}, headers={"Authorization": "Bearer valid"}, follow_redirects=False)
    assert response.status_code == 303
    assert captured["email"] is None


@pytest.mark.parametrize("endpoint", ["/create/", "/api/create/"])
@pytest.mark.parametrize(
    "failure, expected",
    [
        (Exception("unknown mod portland"), "module 'portland' is unavailable"),
        (FileNotFoundError("/private/secret"), "required file or directory is missing"),
        (PermissionError("/private/secret"), "permission"),
        (OSError(28, "private token=secret"), "storage is full"),
        (ModuleNotFoundError("private token=secret"), "Python dependency"),
        (project_routes.redis.ConnectionError("private token=secret"), "state service"),
        (SQLAlchemyError("private token=secret"), "database operation"),
        (ValueError("/private/token=secret"), "could not be safely identified"),
    ],
)
def test_create_initialization_cause_and_formatted_correlation(
    create_client, monkeypatch, caplog, endpoint, failure, expected,
):
    client, _ = create_client
    monkeypatch.setattr(project_routes, "_verify_cap_token", lambda *_: {"success": True})
    monkeypatch.setattr(project_routes, "Ron", lambda *_: (_ for _ in ()).throw(failure))
    with caplog.at_level("WARNING", logger=project_routes.__name__):
        response = client.post(endpoint, data={"config": CONFIG, "cap_token": "good"})
    payload = response.json()
    assert response.status_code == 500
    assert payload["error"]["code"] == "run_initialization_failed"
    assert expected in payload["error"]["details"]
    assert "administrator" in payload["error"]["details"]
    assert any(action in payload["error"]["details"] for action in (
        "restore", "repair", "free storage", "check", "install or enable", "investigate",
    ))
    assert "private" not in response.text
    assert "token=secret" not in response.text
    assert payload["error_id"] in caplog.text
    assert any(r.exc_info and payload["error_id"] in r.getMessage() for r in caplog.records)
    assert any(
        payload["error_id"] in r.getMessage()
        and "status=500" in r.getMessage()
        and "code=run_initialization_failed" in r.getMessage()
        for r in caplog.records
    )


@pytest.mark.parametrize("diagnostic", [
    "unknown mod portland\n", "unknown mod portland extra", "unknown mod /private/path",
    "unknown mod <script>", "unknown mod pö rtland", "unknown mod " + "a" * 65,
    "unknown mod ", "unknown mod token=secret",
])
def test_create_rejects_unsafe_module_diagnostics(create_client, monkeypatch, diagnostic):
    client, _ = create_client
    monkeypatch.setattr(project_routes, "_verify_cap_token", lambda *_: {"success": True})
    monkeypatch.setattr(project_routes, "Ron", lambda *_: (_ for _ in ()).throw(Exception(diagnostic)))
    response = client.post("/create/", data={"config": CONFIG, "cap_token": "good"})
    assert response.status_code == 500
    assert "could not be safely identified" in response.json()["error"]["details"]
    assert diagnostic not in response.text


@pytest.mark.parametrize("endpoint", ["/create/", "/api/create/"])
@pytest.mark.parametrize("data", [{}, {"config": CONFIG}])
def test_create_validation_and_auth_response_ids_are_logged(create_client, caplog, endpoint, data):
    client, _ = create_client
    with caplog.at_level("WARNING", logger=project_routes.__name__):
        response = client.post(endpoint, data=data)
    payload = response.json()
    assert response.status_code in (400, 403)
    assert any(
        payload["error_id"] in r.getMessage()
        and f"status={response.status_code}" in r.getMessage()
        and f"code={payload['error']['code']}" in r.getMessage()
        for r in caplog.records
    )


@pytest.mark.parametrize("endpoint", ["/create/", "/api/create/"])
def test_create_uncaught_exception_is_canonical(create_client, monkeypatch, caplog, endpoint):
    client, captured = create_client
    monkeypatch.setattr(
        project_routes, "_require_rq_token",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("/private/token=secret")),
    )
    with caplog.at_level("ERROR", logger=project_routes.__name__):
        response = client.post(endpoint, data={"config": CONFIG, "rq_token": "opaque"})
    payload = response.json()
    assert response.status_code == 500
    assert payload["error"]["code"] == "run_creation_failed"
    assert "Project creation" in payload["error"]["details"]
    assert "private" not in response.text
    assert captured == {}
    assert any(r.exc_info and payload["error_id"] in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("boundary, failure, code, operation, cause", [
    ("_create_run_dir", PermissionError("/private/secret"), "run_directory_failed", "Run directory creation", "permission"),
    ("_create_run_dir", OSError(28, "secret"), "run_directory_failed", "Run directory creation", "storage is full"),
    ("resolve_creation_actor", PreferenceIdentityError("secret"), "run_ownership_failed", "Project owner resolution", "signed-in account"),
    ("resolve_creation_actor", SQLAlchemyError("secret"), "run_ownership_failed", "Project owner resolution", "database operation"),
    ("_verify_cap_token", project_routes.CapVerificationError("secret"), "internal_error", "CAPTCHA", "CAPTCHA service"),
])
def test_create_infrastructure_stage_diagnostics(
    create_client, monkeypatch, caplog, boundary, failure, code, operation, cause,
):
    client, _ = create_client
    monkeypatch.setattr(project_routes, "_verify_cap_token", lambda *_: {"success": True})
    monkeypatch.setattr(project_routes, boundary, lambda *_: (_ for _ in ()).throw(failure))
    with caplog.at_level("WARNING"):
        response = client.post("/create/", data={"config": CONFIG, "cap_token": "good"})
    payload = response.json()
    assert response.status_code == 500
    assert payload["error"]["code"] == code
    assert operation in payload["error"]["details"]
    assert cause in payload["error"]["details"]
    assert "secret" not in response.text
    assert "NAS" not in response.text
    assert any(r.exc_info and payload["error_id"] in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("boundary, expected_code, operation", [
    ("_creation_idempotency_client", "creation_idempotency_unavailable", "Creation reservation"),
    ("materialize_preset_snapshot", "project_config_materialization_failed", "Project configuration persistence"),
    ("complete_creation", "creation_idempotency_failed", "Project creation completion"),
])
def test_create_writer_failures_remain_observable_and_release_reservation(
    create_client, monkeypatch, caplog, boundary, expected_code, operation,
):
    client, _ = create_client
    state = _FakeIdempotencyRedis()
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_PRESET_WRITER_ENABLED", "1")
    monkeypatch.setattr(project_routes, "_creation_idempotency_client", lambda: state)
    monkeypatch.setattr(project_routes, "_verify_cap_token", lambda *_: {"success": True})

    def fail(*_args, **_kwargs):
        if boundary == "materialize_preset_snapshot":
            try:
                raise PermissionError("/private/secret")
            except PermissionError as exc:
                raise project_routes.PresetSnapshotError("secret") from exc
        raise project_routes.redis.ConnectionError("secret")

    monkeypatch.setattr(project_routes, boundary, fail)
    with caplog.at_level("WARNING"):
        response = client.post("/create/", data={
            "config": CONFIG, "cap_token": "good",
            "creation_idempotency_key": "12345678-1234-4234-9234-123456789abc",
        })
    payload = response.json()
    assert response.status_code == (503 if boundary == "_creation_idempotency_client" else 500)
    assert payload["error"]["code"] == expected_code
    assert operation in payload["error"]["details"]
    assert ("permission" if boundary == "materialize_preset_snapshot" else "state service") in payload["error"]["details"]
    assert "secret" not in response.text
    assert not state.values
    assert any(r.exc_info and payload["error_id"] in r.getMessage() for r in caplog.records)


def test_create_initialization_retains_original_failure_when_cleanup_fails(create_client, monkeypatch, caplog):
    client, _ = create_client
    monkeypatch.setattr(project_routes, "_verify_cap_token", lambda *_: {"success": True})
    monkeypatch.setattr(project_routes, "Ron", lambda *_: (_ for _ in ()).throw(Exception("unknown mod portland")))
    monkeypatch.setattr(project_routes, "cleanup_new_run_directory", lambda *_: (_ for _ in ()).throw(OSError("cleanup secret")))
    with caplog.at_level("ERROR"):
        response = client.post("/create/", data={"config": CONFIG, "cap_token": "good"})
    payload = response.json()
    assert "module 'portland' is unavailable" in payload["error"]["details"]
    assert "cleanup" not in response.text
    failures = [r for r in caplog.records if r.exc_info and payload["error_id"] in r.getMessage()]
    assert any(str(r.exc_info[1]) == "unknown mod portland" for r in failures)
    assert any(str(r.exc_info[1]) == "cleanup secret" for r in failures)


def test_create_unexpected_post_allocation_failure_does_not_add_cleanup(create_client, monkeypatch, caplog):
    client, captured = create_client
    state = _FakeIdempotencyRedis()
    cleanup = []
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_PRESET_WRITER_ENABLED", "1")
    monkeypatch.setattr(project_routes, "_creation_idempotency_client", lambda: state)
    monkeypatch.setattr(project_routes, "_verify_cap_token", lambda *_: {"success": True})
    monkeypatch.setattr(project_routes, "materialize_preset_snapshot", lambda *_: (_ for _ in ()).throw(RuntimeError("secret")))
    monkeypatch.setattr(project_routes, "cleanup_new_run_directory", lambda *_: cleanup.append(True))
    with caplog.at_level("WARNING"):
        response = client.post("/create/", data={
            "config": CONFIG, "cap_token": "good",
            "creation_idempotency_key": "12345678-1234-4234-9234-123456789abc",
        })
    payload = response.json()
    assert response.status_code == 500
    assert payload["error"]["code"] == "run_creation_failed"
    assert "secret" not in response.text
    assert "email" in captured
    assert cleanup == []
    assert state.values  # Existing unhandled-failure lifecycle is unchanged.
    assert any(r.exc_info and payload["error_id"] in r.getMessage() for r in caplog.records)


def test_create_release_failure_keeps_initialization_diagnosis(create_client, monkeypatch, caplog):
    client, _ = create_client
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_PRESET_WRITER_ENABLED", "1")
    monkeypatch.setattr(project_routes, "_creation_idempotency_client", _FakeIdempotencyRedis)
    monkeypatch.setattr(project_routes, "_verify_cap_token", lambda *_: {"success": True})
    monkeypatch.setattr(project_routes, "Ron", lambda *_: (_ for _ in ()).throw(Exception("unknown mod portland")))
    monkeypatch.setattr(project_routes, "release_creation", lambda *_: (_ for _ in ()).throw(project_routes.redis.RedisError("release secret")))
    with caplog.at_level("ERROR"):
        response = client.post("/create/", data={
            "config": CONFIG, "cap_token": "good",
            "creation_idempotency_key": "12345678-1234-4234-9234-123456789abc",
        })
    payload = response.json()
    assert "module 'portland' is unavailable" in payload["error"]["details"]
    assert "secret" not in response.text
    assert any(
        r.exc_info and str(r.exc_info[1]) == "release secret" and payload["error_id"] in r.getMessage()
        for r in caplog.records
    )


@pytest.mark.parametrize("boundary", ["ttl", "readme"])
def test_create_optional_failure_keeps_success(create_client, monkeypatch, caplog, boundary):
    from wepppy.weppcloud.utils import run_ttl

    client, _ = create_client
    monkeypatch.setattr(project_routes, "_verify_cap_token", lambda *_: {"success": True})
    target, name = (run_ttl, "initialize_ttl") if boundary == "ttl" else (project_routes, "ensure_readme_on_create")
    monkeypatch.setattr(target, name, lambda *_: (_ for _ in ()).throw(RuntimeError("optional failure")))
    with caplog.at_level("ERROR"):
        response = client.post("/create/", data={"config": CONFIG, "cap_token": "good"}, follow_redirects=False)
    assert response.status_code == 303
    assert RUN_ID in response.headers["location"]
    assert any(r.exc_info and str(r.exc_info[1]) == "optional failure" for r in caplog.records)


def test_create_in_progress_keeps_retry_header_and_correlation(create_client, monkeypatch, caplog):
    client, captured = create_client
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_PRESET_WRITER_ENABLED", "1")
    monkeypatch.setattr(project_routes, "_creation_idempotency_client", _FakeIdempotencyRedis)
    monkeypatch.setattr(project_routes, "_verify_cap_token", lambda *_: {"success": True})
    monkeypatch.setattr(project_routes, "reserve_creation", lambda *_a, **_k: project_routes.CreationReservation("in_progress", "test-key", "test-fingerprint"))
    with caplog.at_level("WARNING"):
        response = client.post("/create/", data={"config": CONFIG, "cap_token": "good"})
    payload = response.json()
    assert response.status_code == 409
    assert response.headers["retry-after"] == "2"
    assert payload["error"]["code"] == "creation_in_progress"
    assert captured == {}
    assert any(payload["error_id"] in r.getMessage() for r in caplog.records)


def test_create_legacy_mod_override_remains_accepted(create_client, monkeypatch):
    client, captured = create_client
    monkeypatch.setattr(project_routes, "_verify_cap_token", lambda *_: {"success": True})

    def initialize(_wd, cfg):
        captured['cfg'] = cfg
        raise Exception("unknown mod custom_mod")

    monkeypatch.setattr(project_routes, "Ron", initialize)
    response = client.post("/create/", data={
        "config": CONFIG, "cap_token": "good", "nodb:mods": '["custom_mod"]',
    })
    assert 'nodb:mods=["custom_mod"]' in captured['cfg']
    details = response.json()["error"]["details"]
    assert "module 'custom_mod' is unavailable" in details
    assert "Check the configured module name" in details
    assert "install or enable" in details


def test_create_preset_policy_failure_hides_private_policy_path(create_client, monkeypatch, caplog):
    client, captured = create_client
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_PRESET_WRITER_ENABLED", "1")
    monkeypatch.setattr(project_routes, "_verify_cap_token", lambda *_: {"success": True})
    monkeypatch.setattr(project_routes, "resolve_preset_snapshot", lambda *_a, **_k: (_ for _ in ()).throw(project_routes.PresetPolicyError("Unable to parse preset policies: /private/policy.toml")))
    with caplog.at_level("WARNING"):
        response = client.post("/create/", data={"config": CONFIG, "cap_token": "good"})
    payload = response.json()
    assert response.status_code == 400
    assert payload["error"]["code"] == "project_config_validation_failed"
    assert "administrator must repair the preset policy" in payload["error"]["details"]
    assert "/private/" not in response.text
    assert captured == {}
    assert payload["error_id"] in caplog.text
    assert "Traceback" in caplog.text
    assert "/private/policy.toml" in caplog.text
