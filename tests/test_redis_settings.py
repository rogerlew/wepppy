import pytest

pytestmark = pytest.mark.unit

from wepppy.config import redis_settings


@pytest.fixture(autouse=True)
def reset_redis_env(monkeypatch):
    """Clear env vars and caches so tests can tweak configuration safely."""

    for key in (
        "REDIS_URL",
        "RQ_REDIS_URL",
        "SESSION_REDIS_URL",
        "SESSION_REDIS_DB",
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_PASSWORD",
        "REDIS_PASSWORD_FILE",
    ):
        monkeypatch.delenv(key, raising=False)

    redis_settings._base_url.cache_clear()
    redis_settings._session_base_url.cache_clear()
    redis_settings.redis_host.cache_clear()
    redis_settings.redis_port.cache_clear()
    redis_settings.redis_url.cache_clear()
    redis_settings.session_redis_url.cache_clear()
    yield
    redis_settings._base_url.cache_clear()
    redis_settings._session_base_url.cache_clear()
    redis_settings.redis_host.cache_clear()
    redis_settings.redis_port.cache_clear()
    redis_settings.redis_url.cache_clear()
    redis_settings.session_redis_url.cache_clear()


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
        "REDIS_URL", "redis://user:pass@redis.internal:6380/12?socket_timeout=2"
    )

    assert redis_settings.redis_host() == "redis.internal"
    assert redis_settings.redis_port() == 6380
    # Database portion should update while preserving other components.
    assert (
        redis_settings.redis_url(redis_settings.RedisDB.STATUS)
        == "redis://redis.internal:6380/2?socket_timeout=2"
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


def test_invalid_url_fails_without_echoing_input(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis:///4")
    with pytest.raises(ValueError, match="Invalid or conflicting"):
        redis_settings.redis_host()


def test_password_stays_out_of_url(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "secure-cache")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_PASSWORD", "sekret")

    assert (
        redis_settings.redis_url(redis_settings.RedisDB.WD_CACHE)
        == "redis://secure-cache:6379/11"
    )


def test_password_stays_out_of_url_override(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://redis.internal:6380/12?socket_timeout=2")
    monkeypatch.setenv("REDIS_PASSWORD", "sekret")

    assert (
        redis_settings.redis_url(redis_settings.RedisDB.STATUS)
        == "redis://redis.internal:6380/2?socket_timeout=2"
    )


def test_file_password_separated_from_endpoint(monkeypatch, tmp_path):
    password_path = tmp_path / "redis_password"
    password_path.write_text("sekret\n", encoding="utf-8")

    monkeypatch.setenv("REDIS_HOST", "secure-cache")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_PASSWORD_FILE", str(password_path))
    monkeypatch.delenv("REDIS_PASSWORD", raising=False)

    assert (
        redis_settings.redis_url(redis_settings.RedisDB.WD_CACHE)
        == "redis://secure-cache:6379/11"
    )

    kwargs = redis_settings.redis_connection_kwargs(redis_settings.RedisDB.LOCK)
    assert kwargs["password"] == "sekret"


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


def test_connection_kwargs_include_password(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "secure-cache")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_PASSWORD", "sekret")

    kwargs = redis_settings.redis_connection_kwargs(redis_settings.RedisDB.LOCK)

    assert kwargs["password"] == "sekret"


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


def test_session_url_uses_session_override_db(monkeypatch):
    monkeypatch.setenv("SESSION_REDIS_URL", "redis://session-cache:6380/5")
    monkeypatch.setenv("SESSION_REDIS_DB", "11")

    assert redis_settings.session_redis_url() == "redis://session-cache:6380/11"


def test_session_url_preserves_session_url_path(monkeypatch):
    monkeypatch.setenv("SESSION_REDIS_URL", "redis://session-cache:6380/5")
    monkeypatch.delenv("SESSION_REDIS_DB", raising=False)

    assert redis_settings.session_redis_url() == "redis://session-cache:6380/5"


def test_session_url_overrides_base_url_db(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://cache:6379/0")
    monkeypatch.delenv("SESSION_REDIS_URL", raising=False)
    monkeypatch.delenv("SESSION_REDIS_DB", raising=False)

    assert redis_settings.session_redis_url() == "redis://cache:6379/11"


@pytest.mark.parametrize('endpoint', [
    'redis://user:p%40ss%3Aword@[::1]:6380/3?db=4&socket_timeout=2',
    'rediss://user:p%40ss%3Aword@[::1]:6380/3?db=4&socket_timeout=2',
])
def test_native_credentials_options_db_and_safe_repr(monkeypatch, endpoint):
    monkeypatch.setenv('REDIS_URL', endpoint)
    kwargs = redis_settings.redis_connection_kwargs(9)
    assert kwargs['username'] == 'user'
    assert kwargs['password'].encode() == b'p@ss:word'
    assert kwargs['db'] == 9
    assert kwargs['socket_timeout'] == 2
    assert kwargs['host'] == '::1'
    assert 'p@ss:word' not in repr(kwargs)
    assert 'p@ss:word' not in repr(dict(kwargs))
    assert 'p@ss:word' not in str(kwargs['password'])
    assert '@' not in redis_settings.redis_url(9)
    pool = redis_settings.redis_connection_kwargs(9, for_pool=True)
    if endpoint.startswith('rediss:'):
        assert kwargs['ssl'] is True
        assert pool['connection_class'] is redis_settings.redis.SSLConnection
        assert 'ssl' not in pool


def test_unix_client_and_pool_arguments(monkeypatch):
    monkeypatch.setenv('REDIS_URL', 'unix:///tmp/redis.sock?db=4')
    assert redis_settings.redis_connection_kwargs(9)['unix_socket_path'] == '/tmp/redis.sock'
    assert redis_settings.redis_connection_kwargs(9, for_pool=True)['path'] == '/tmp/redis.sock'
    assert redis_settings.redis_url(9) == 'unix:///tmp/redis.sock?db=9'


@pytest.mark.parametrize('content', [b'', b'\n', b' secret\n', b'secret \n', b'secret\r\n', b'a\x00b', b'\xff'])
def test_invalid_secret_files_fail_closed(monkeypatch, tmp_path, content):
    path = tmp_path / 'redis-password'
    path.write_bytes(content)
    monkeypatch.setenv('REDIS_PASSWORD_FILE', str(path))
    monkeypatch.setenv('REDIS_URL', 'redis://:legacy@cache/9')
    with pytest.raises(ValueError) as error:
        redis_settings.redis_connection_kwargs(9)
    assert 'legacy' not in str(error.value)


def test_conflicting_credentials_fail_without_echo(monkeypatch, tmp_path):
    path = tmp_path / 'redis-password'
    path.write_text('file-canary\n')
    monkeypatch.setenv('REDIS_PASSWORD_FILE', str(path))
    monkeypatch.setenv('REDIS_URL', 'redis://:url-canary@cache/9')
    with pytest.raises(ValueError) as error:
        redis_settings.redis_connection_kwargs(9)
    assert 'canary' not in str(error.value)


def test_session_native_kwargs_keep_override(monkeypatch):
    monkeypatch.setenv('REDIS_URL', 'redis://base/0')
    monkeypatch.setenv('SESSION_REDIS_URL', 'redis://session:6380/5?socket_timeout=3')
    monkeypatch.setenv('SESSION_REDIS_DB', '11')
    kwargs = redis_settings.session_redis_connection_kwargs()
    assert (kwargs['host'], kwargs['port'], kwargs['db'], kwargs['socket_timeout']) == ('session', 6380, 11, 3)


@pytest.mark.parametrize('endpoint', ['redis://cache/0?ssl_password=canary', 'redis://cache/0?PASSWORD=canary'])
def test_endpoint_helpers_reject_credential_query_options(monkeypatch, endpoint):
    monkeypatch.setenv('REDIS_URL', endpoint)
    with pytest.raises(ValueError) as error:
        redis_settings.redis_url(9)
    assert 'canary' not in str(error.value)


@pytest.mark.parametrize('host', ['user@cache', 'cache?password=canary', 'cache/path', 'cache#fragment'])
def test_host_only_input_cannot_inject_endpoint_fields(monkeypatch, host):
    monkeypatch.setenv('REDIS_HOST', host)
    with pytest.raises(ValueError):
        redis_settings.redis_url(9)


def test_native_missing_url_port_preserves_environment_fallback(monkeypatch):
    monkeypatch.setenv('REDIS_URL', 'redis://cache/0')
    monkeypatch.setenv('REDIS_PORT', '6385')
    assert redis_settings.redis_port() == 6385
    assert redis_settings.redis_connection_kwargs(9)['port'] == 6385
    assert redis_settings.session_redis_connection_kwargs()['port'] == 6379


def test_rq_adapter_preserves_supplied_native_pool(monkeypatch):
    # Subprocess bypasses the suite's autouse redis.Redis recorder.
    import subprocess
    import sys
    subprocess.run([sys.executable, '-c', "from wepppy.config.rq_redis import Connection\nimport redis\npool = redis.ConnectionPool(host='bounded-cache', db=9, socket_timeout=0.25)\nconnection = Connection(connection_pool=pool)\nassert connection.connection_pool is pool\nassert connection.connection_pool.connection_kwargs['socket_timeout'] == 0.25\n"], check=True)


def test_password_format_specifiers_are_safe(monkeypatch):
    monkeypatch.setenv('REDIS_PASSWORD', 'format-canary')
    password = redis_settings.redis_connection_kwargs(9)['password']
    assert 'format-canary' not in f'{password:s} {password:>30}'
    assert password.encode() == b'format-canary'


def test_explicit_url_port_ignores_invalid_environment_port(monkeypatch):
    monkeypatch.setenv('REDIS_URL', 'redis://cache:6380/0')
    monkeypatch.setenv('REDIS_PORT', 'invalid-port-canary')
    assert redis_settings.redis_port() == 6380
    assert redis_settings.redis_connection_kwargs(9)['port'] == 6380
