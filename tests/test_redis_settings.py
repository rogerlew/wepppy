import contextlib

import pytest

from wepppy.config import redis_settings


@pytest.fixture(autouse=True)
def reset_redis_env(monkeypatch):
    """Clear env vars and caches so tests can tweak configuration safely."""

    for key in (
        "REDIS_URL",
        "RQ_REDIS_URL",
        "SESSION_REDIS_URL",
        "REDIS_HOST",
        "REDIS_PORT",
    ):
        monkeypatch.delenv(key, raising=False)

    redis_settings._base_url.cache_clear()
    redis_settings.redis_host.cache_clear()
    redis_settings.redis_port.cache_clear()
    redis_settings.redis_url.cache_clear()
    yield
    redis_settings._base_url.cache_clear()
    redis_settings.redis_host.cache_clear()
    redis_settings.redis_port.cache_clear()
    redis_settings.redis_url.cache_clear()


def test_defaults_to_localhost_and_standard_port():
    assert redis_settings.redis_host() == "localhost"
    assert redis_settings.redis_port() == 6379
    assert (
        redis_settings.redis_url(redis_settings.RedisDB.RQ)
        == "redis://localhost:6379/9"
    )


def test_env_overrides_host_and_port(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "cache-node")
    monkeypatch.setenv("REDIS_PORT", "6385")

    assert redis_settings.redis_host() == "cache-node"
    assert redis_settings.redis_port() == 6385
    assert redis_settings.redis_url(4) == "redis://cache-node:6385/4"


def test_url_override_applies_to_host_port_and_db(monkeypatch):
    monkeypatch.setenv(
        "REDIS_URL", "redis://user:pass@redis.internal:6380/12?ssl=true"
    )

    assert redis_settings.redis_host() == "redis.internal"
    assert redis_settings.redis_port() == 6380
    # Database portion should update while preserving other components.
    assert (
        redis_settings.redis_url(redis_settings.RedisDB.STATUS)
        == "redis://user:pass@redis.internal:6380/2?ssl=true"
    )


def test_legacy_rq_url_used_when_primary_missing(monkeypatch):
    monkeypatch.setenv(
        "RQ_REDIS_URL", "redis://legacy-host:6390/5?retry_on_timeout=true"
    )

    assert redis_settings.redis_host() == "legacy-host"
    assert redis_settings.redis_port() == 6390
    assert (
        redis_settings.redis_url(redis_settings.RedisDB.NODB_CACHE)
        == "redis://legacy-host:6390/13?retry_on_timeout=true"
    )


def test_invalid_url_falls_back_to_env_defaults(monkeypatch):
    # Missing hostname should invalidate the parsed URL.
    monkeypatch.setenv("REDIS_URL", "redis:///4")
    monkeypatch.setenv("REDIS_HOST", "fallback-host")
    monkeypatch.setenv("REDIS_PORT", "6391")

    assert redis_settings.redis_host() == "fallback-host"
    assert redis_settings.redis_port() == 6391
    assert (
        redis_settings.redis_url(redis_settings.RedisDB.LOG_LEVEL)
        == "redis://fallback-host:6391/15"
    )


def test_connection_kwargs_merge_extra(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "config-host")
    monkeypatch.setenv("REDIS_PORT", "6370")

    kwargs = redis_settings.redis_connection_kwargs(
        redis_settings.RedisDB.SESSION,
        decode_responses=True,
        extra={"socket_timeout": 5, "host": "override-host"},
    )

    assert kwargs["db"] == 11
    assert kwargs["decode_responses"] is True
    assert kwargs["host"] == "override-host"
    assert kwargs["port"] == 6370
    assert kwargs["socket_timeout"] == 5


def test_redis_client_uses_default_class(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "app-cache")
    client = redis_settings.redis_client(
        redis_settings.RedisDB.LOCK,
        decode_responses=False,
        extra_kwargs={"socket_keepalive": True},
    )

    # The stub installed by tests/conftest.py tracks kwargs for assertions.
    assert isinstance(client, redis_settings.redis.Redis)
    assert client.kwargs["db"] == int(redis_settings.RedisDB.LOCK)
    assert client.kwargs["host"] == "app-cache"
    assert client.kwargs["socket_keepalive"] is True


def test_redis_client_accepts_custom_class(monkeypatch):
    captured_kwargs = {}

    class DummyClient:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

    monkeypatch.setenv("REDIS_HOST", "custom-cache")
    result = redis_settings.redis_client(
        redis_settings.RedisDB.WD_CACHE,
        decode_responses=True,
        client_cls=DummyClient,
        extra_kwargs={"foo": "bar"},
    )

    assert isinstance(result, DummyClient)
    assert captured_kwargs["db"] == 11
    assert captured_kwargs["decode_responses"] is True
    assert captured_kwargs["foo"] == "bar"
    assert captured_kwargs["host"] == "custom-cache"


def test_redis_client_requires_redis_library(monkeypatch):
    monkeypatch.setattr(redis_settings, "redis", None)

    with pytest.raises(RuntimeError):
        redis_settings.redis_client(redis_settings.RedisDB.README)


def test_async_url_matches_sync_url(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "async-cache")
    monkeypatch.setenv("REDIS_PORT", "6400")

    db = redis_settings.RedisDB.NODB_CACHE
    assert redis_settings.redis_async_url(db) == redis_settings.redis_url(db)
