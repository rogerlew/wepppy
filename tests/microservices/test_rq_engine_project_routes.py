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
    assert payload["error"]["details"] == (
        f"Run initialization failed (ValueError). "
        f"Search server logs for error_id {payload['error_id']}."
    )
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
        if record.getMessage() == "rq-engine create directory cleanup failed"
    ]
    assert response.status_code == 500
    assert RUN_ID not in response.text
    assert len(cleanup_records) == 1
    assert cleanup_records[0].error_id == error_id
    assert cleanup_records[0].runid == RUN_ID


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
