from __future__ import annotations

import time

import pytest

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "wepppy" / "weppcloud" / "utils" / "auth_tokens.py"
spec = importlib.util.spec_from_file_location("wepppy.weppcloud.utils.auth_tokens", MODULE_PATH)
auth_tokens = importlib.util.module_from_spec(spec)
sys.modules["wepppy.weppcloud.utils.auth_tokens"] = auth_tokens
assert spec.loader is not None
spec.loader.exec_module(auth_tokens)

pytestmark = pytest.mark.unit


def _configure_env(monkeypatch):
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    monkeypatch.setenv("WEPP_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("WEPP_AUTH_JWT_ISSUER", "weppcloud")
    monkeypatch.setenv("WEPP_AUTH_JWT_DEFAULT_AUDIENCE", "wepp-services")
    monkeypatch.setenv("WEPP_AUTH_JWT_DEFAULT_TTL_SECONDS", "600")
    auth_tokens.get_jwt_config.cache_clear()


def _configure_rotation_env(monkeypatch):
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRETS", "new-secret,old-secret")
    monkeypatch.setenv("WEPP_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("WEPP_AUTH_JWT_ISSUER", "weppcloud")
    monkeypatch.setenv("WEPP_AUTH_JWT_DEFAULT_AUDIENCE", "wepp-services")
    monkeypatch.setenv("WEPP_AUTH_JWT_DEFAULT_TTL_SECONDS", "600")
    monkeypatch.delenv("WEPP_AUTH_JWT_SECRET", raising=False)
    auth_tokens.get_jwt_config.cache_clear()


def _configure_secret_file_env(monkeypatch, tmp_path):
    secret_path = tmp_path / "jwt_secret"
    secret_path.write_text("file-secret\n", encoding="utf-8")

    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET_FILE", str(secret_path))
    monkeypatch.delenv("WEPP_AUTH_JWT_SECRET", raising=False)
    monkeypatch.delenv("WEPP_AUTH_JWT_SECRETS", raising=False)
    monkeypatch.setenv("WEPP_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("WEPP_AUTH_JWT_ISSUER", "weppcloud")
    monkeypatch.setenv("WEPP_AUTH_JWT_DEFAULT_AUDIENCE", "wepp-services")
    monkeypatch.setenv("WEPP_AUTH_JWT_DEFAULT_TTL_SECONDS", "600")
    auth_tokens.get_jwt_config.cache_clear()


def _issue_time_claim_token(claim_overrides: dict[str, object], *, now: int | None = None) -> str:
    config = auth_tokens.get_jwt_config()
    issued_at = int(time.time()) if now is None else int(now)
    claims = {
        "sub": "time-claims-user",
        "jti": "time-claims-jti",
        "iat": issued_at,
        "exp": issued_at + 300,
        "iss": config.issuer,
        "aud": config.default_audience,
    }
    claims.update(claim_overrides)
    return auth_tokens.encode_jwt(
        claims,
        config.secret,
        algorithm=config.algorithms[0],
    )


def test_issue_token_includes_claims(monkeypatch):
    _configure_env(monkeypatch)
    now = int(time.time())

    result = auth_tokens.issue_token(
        "user-123",
        scopes=["runs:read", "queries:execute"],
        runs=["run-1", "run-2"],
        audience=["service-a"],
        expires_in=120,
        extra_claims={"custom": "value"},
        issued_at=now,
    )

    token = result["token"]
    claims = result["claims"]
    assert token
    assert claims["sub"] == "user-123"
    assert claims["scope"] == "runs:read queries:execute"
    assert claims["runs"] == ["run-1", "run-2"]
    assert claims["custom"] == "value"
    assert claims["iss"] == "weppcloud"
    assert claims["aud"] == ["wepp-services", "service-a"]
    assert claims["exp"] == now + 120

    decoded = auth_tokens.decode_token(token, audience=["service-a", "wepp-services"])
    assert decoded["sub"] == "user-123"


def test_decode_token_rejects_mismatched_audience(monkeypatch):
    _configure_env(monkeypatch)
    result = auth_tokens.issue_token("user-456")
    token = result["token"]

    with pytest.raises(auth_tokens.JWTDecodeError):
        auth_tokens.decode_token(token, audience="other-service")


def test_missing_configuration_raises(monkeypatch):
    auth_tokens.get_jwt_config.cache_clear()
    monkeypatch.delenv("WEPP_AUTH_JWT_SECRET", raising=False)
    monkeypatch.delenv("WEPP_AUTH_JWT_SECRETS", raising=False)
    with pytest.raises(auth_tokens.JWTConfigurationError):
        auth_tokens.issue_token("user")


def test_decode_token_accepts_rotated_secret(monkeypatch):
    _configure_rotation_env(monkeypatch)
    result = auth_tokens.issue_token("user-789")
    claims = result["claims"]
    config = auth_tokens.get_jwt_config()

    rotated_token = auth_tokens.encode_jwt(
        claims,
        "old-secret",
        algorithm=config.algorithms[0],
    )
    decoded = auth_tokens.decode_token(rotated_token, audience="wepp-services")

    assert decoded["sub"] == "user-789"
    assert config.secret == "new-secret"
    assert config.validation_secrets == ("new-secret", "old-secret")

    bad_token = auth_tokens.encode_jwt(
        claims,
        "unknown-secret",
        algorithm=config.algorithms[0],
    )
    with pytest.raises(auth_tokens.JWTDecodeError):
        auth_tokens.decode_token(bad_token, audience="wepp-services")


def test_issue_token_uses_secret_file_env(monkeypatch, tmp_path):
    _configure_secret_file_env(monkeypatch, tmp_path)
    result = auth_tokens.issue_token("user-file")

    decoded = auth_tokens.decode_token(result["token"], audience="wepp-services")
    assert decoded["sub"] == "user-file"


def test_decode_token_rejects_expired_token(monkeypatch):
    _configure_env(monkeypatch)
    now = int(time.time())
    token = _issue_time_claim_token({"exp": now - 5}, now=now - 120)

    with pytest.raises(auth_tokens.JWTDecodeError, match="expired"):
        auth_tokens.decode_token(token, audience="wepp-services")


def test_decode_token_rejects_not_before_in_future(monkeypatch):
    _configure_env(monkeypatch)
    now = int(time.time())
    token = _issue_time_claim_token({"nbf": now + 60}, now=now)

    with pytest.raises(auth_tokens.JWTDecodeError, match="not yet valid"):
        auth_tokens.decode_token(token, audience="wepp-services")


def test_decode_token_rejects_issued_at_in_future(monkeypatch):
    _configure_env(monkeypatch)
    now = int(time.time())
    token = _issue_time_claim_token({"iat": now + 60, "exp": now + 120}, now=now)

    with pytest.raises(auth_tokens.JWTDecodeError, match="future"):
        auth_tokens.decode_token(token, audience="wepp-services")


def test_decode_token_allows_time_claims_with_leeway(monkeypatch):
    _configure_env(monkeypatch)
    monkeypatch.setenv("WEPP_AUTH_JWT_LEEWAY", "15")
    auth_tokens.get_jwt_config.cache_clear()

    now = int(time.time())
    token = _issue_time_claim_token(
        {"exp": now - 5, "nbf": now + 5, "iat": now + 5},
        now=now,
    )
    decoded = auth_tokens.decode_token(token, audience="wepp-services")

    assert decoded["sub"] == "time-claims-user"


@pytest.mark.parametrize("claim", ["exp", "nbf", "iat"])
def test_decode_token_rejects_non_numeric_time_claims(monkeypatch, claim):
    _configure_env(monkeypatch)
    token = _issue_time_claim_token({claim: "invalid"})

    with pytest.raises(auth_tokens.JWTDecodeError, match=f"'{claim}' claim must be numeric"):
        auth_tokens.decode_token(token, audience="wepp-services")
