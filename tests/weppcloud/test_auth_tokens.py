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


def _configure_env(monkeypatch):
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    monkeypatch.setenv("WEPP_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("WEPP_AUTH_JWT_ISSUER", "weppcloud")
    monkeypatch.setenv("WEPP_AUTH_JWT_DEFAULT_AUDIENCE", "wepp-services")
    monkeypatch.setenv("WEPP_AUTH_JWT_DEFAULT_TTL_SECONDS", "600")
    auth_tokens.get_jwt_config.cache_clear()


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
    with pytest.raises(auth_tokens.JWTConfigurationError):
        auth_tokens.issue_token("user")
