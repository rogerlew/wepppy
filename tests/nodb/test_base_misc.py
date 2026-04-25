import importlib
import importlib.util
import logging
import pathlib
import sys
import types

import pytest

import wepppy


pytestmark = pytest.mark.unit


def _load_base_module():
    if 'wepppy.nodb.base' in sys.modules:
        return sys.modules['wepppy.nodb.base']

    nodb_path = pathlib.Path(wepppy.__file__).resolve().parent / 'nodb'

    if 'wepppy.nodb' not in sys.modules:
        nodb_pkg = types.ModuleType('wepppy.nodb')
        nodb_pkg.__path__ = [str(nodb_path)]
        nodb_pkg.__file__ = str(nodb_path / '__init__.py')
        nodb_pkg.__package__ = 'wepppy.nodb'
        sys.modules['wepppy.nodb'] = nodb_pkg

    spec = importlib.util.spec_from_file_location(
        'wepppy.nodb.base', nodb_path / 'base.py'
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    sys.modules['wepppy.nodb.base'] = module
    return module


base = _load_base_module()


def test_discover_legacy_module_redirects_includes_wepp():
    redirects = base._discover_legacy_module_redirects()

    assert 'wepp' in redirects
    assert redirects['wepp'] == 'wepppy.nodb.core.wepp'


def test_ensure_legacy_module_imports_registers_module(monkeypatch):
    stub_module = types.ModuleType('tests.fake_mod')
    monkeypatch.setattr(
        base.NoDbBase,
        '_legacy_module_redirects',
        {'fake': 'tests.fake_mod'},
    )

    real_import_module = importlib.import_module

    def _fake_import(name, package=None):
        if name == 'tests.fake_mod':
            sys.modules[name] = stub_module
            return stub_module
        return real_import_module(name, package)

    monkeypatch.setattr(base.importlib, 'import_module', _fake_import)

    legacy_name = 'wepppy.nodb.fake'
    sys.modules.pop(legacy_name, None)

    base.NoDbBase._ensure_legacy_module_imports(
        '{"py/object": "wepppy.nodb.fake.FakeClass"}'
    )

    assert sys.modules[legacy_name] is stub_module

    sys.modules.pop(legacy_name, None)


def test_try_redis_set_log_level_updates_client(monkeypatch):
    class _StubRedis:
        def __init__(self):
            self.calls = []

        def set(self, key, value):
            self.calls.append((key, value))

    client = _StubRedis()
    monkeypatch.setattr(base, 'redis_log_level_client', client, raising=False)

    logger_name = 'wepppy.run.unit-test'
    logger = logging.getLogger(logger_name)
    previous_level = logger.level

    try:
        base.try_redis_set_log_level('unit-test', 'DEBUG')
        assert client.calls == [('loglevel:unit-test', str(logging.DEBUG))]
        assert logger.level == logging.DEBUG
    finally:
        logger.setLevel(previous_level)


def test_try_redis_set_log_level_swallows_redis_errors(monkeypatch):
    class _StubRedis:
        def __init__(self):
            self.calls = []

        def set(self, key, value):
            self.calls.append((key, value))
            raise base.redis.exceptions.RedisError("boom")

    client = _StubRedis()
    monkeypatch.setattr(base, "redis_log_level_client", client, raising=False)

    logger_name = "wepppy.run.unit-test"
    logger = logging.getLogger(logger_name)
    previous_level = logger.level

    try:
        base.try_redis_set_log_level("unit-test", "DEBUG")
        assert client.calls == [("loglevel:unit-test", str(logging.DEBUG))]
        assert logger.level == logging.DEBUG
    finally:
        logger.setLevel(previous_level)


def test_try_redis_set_log_level_swallows_logger_setlevel_failures(monkeypatch):
    class _StubRedis:
        def __init__(self):
            self.calls = []

        def set(self, key, value):
            self.calls.append((key, value))

    client = _StubRedis()
    monkeypatch.setattr(base, "redis_log_level_client", client, raising=False)

    class _StubLogger:
        def setLevel(self, level):  # noqa: N802 - matches logging API
            raise TypeError("boom")

    original_get_logger = base.logging.getLogger

    def _fake_get_logger(name=None):
        if name == "wepppy.run.unit-test":
            return _StubLogger()
        return original_get_logger(name) if name is not None else original_get_logger()

    monkeypatch.setattr(base.logging, "getLogger", _fake_get_logger)

    base.try_redis_set_log_level("unit-test", "DEBUG")
    assert client.calls == [("loglevel:unit-test", str(logging.DEBUG))]


def test_try_redis_set_log_level_invalid_level_falls_back_to_info(monkeypatch):
    class _StubRedis:
        def __init__(self):
            self.calls = []

        def set(self, key, value):
            self.calls.append((key, value))

    client = _StubRedis()
    monkeypatch.setattr(base, "redis_log_level_client", client, raising=False)

    logger_name = "wepppy.run.unit-test"
    logger = logging.getLogger(logger_name)
    previous_level = logger.level

    try:
        base.try_redis_set_log_level("unit-test", "not-a-log-level")
        assert client.calls == [("loglevel:unit-test", str(logging.INFO))]
        assert logger.level == logging.INFO
    finally:
        logger.setLevel(previous_level)


def test_config_get_path_expands_locales_dir():
    class _StubNoDb:
        _expand_config_path_tokens = base.NoDbBase._expand_config_path_tokens

        def config_get_str(self, section, option, default=None):
            assert (section, option, default) == ("soils", "soils_map", None)
            return "LOCALES_DIR/tenerife/soils/tf_soil_25.tif"

    resolved = base.NoDbBase.config_get_path(_StubNoDb(), "soils", "soils_map")

    assert resolved.endswith("wepppy/locales/tenerife/soils/tf_soil_25.tif")


@pytest.mark.parametrize("raw_value", ["19 # requested by team", "19 ; requested by team"])
def test_config_get_int_ignores_inline_comment_suffix(raw_value):
    class _StubParser:
        def get(self, section, option):
            assert (section, option) == ("watershed", "mofe_max_ofes")
            return raw_value

    class _StubNoDb:
        _configparser = _StubParser()

    value = base.NoDbBase.config_get_int(_StubNoDb(), "watershed", "mofe_max_ofes")
    assert value == 19


@pytest.mark.parametrize("raw_value", ["2.5 # calibration", "2.5 ; calibration"])
def test_config_get_float_ignores_inline_comment_suffix(raw_value):
    class _StubParser:
        def get(self, section, option):
            assert (section, option) == ("climate", "factor")
            return raw_value

    class _StubNoDb:
        _configparser = _StubParser()

    value = base.NoDbBase.config_get_float(_StubNoDb(), "climate", "factor")
    assert value == 2.5


@pytest.mark.parametrize("raw_value", ["none # fallback", "null ; fallback"])
def test_config_get_numeric_respects_default_with_inline_comment(raw_value):
    class _StubParser:
        def get(self, section, option):
            assert (section, option) in {
                ("watershed", "mofe_max_ofes"),
                ("climate", "factor"),
            }
            return raw_value

    class _StubNoDb:
        _configparser = _StubParser()

    assert base.NoDbBase.config_get_int(
        _StubNoDb(), "watershed", "mofe_max_ofes", default=19
    ) == 19
    assert base.NoDbBase.config_get_float(
        _StubNoDb(), "climate", "factor", default=1.25
    ) == 1.25


def test_ensure_redis_lock_client_reconnects_when_unset(monkeypatch):
    class _StubRedisClient:
        def __init__(self, connection_pool):
            self.connection_pool = connection_pool
            self.ping_calls = 0

        def ping(self):
            self.ping_calls += 1
            return True

    pool_calls = []

    def _fake_pool(**kwargs):
        pool_calls.append(kwargs)
        return {"kwargs": kwargs}

    monkeypatch.setattr(base, "redis_lock_client", None, raising=False)
    monkeypatch.setattr(base.redis, "ConnectionPool", _fake_pool)
    monkeypatch.setattr(base.redis, "StrictRedis", _StubRedisClient)

    client = base._ensure_redis_lock_client()

    assert isinstance(client, _StubRedisClient)
    assert client.ping_calls == 1
    assert base.redis_lock_client is client
    assert pool_calls


def test_ensure_redis_lock_client_retries_after_failed_ping(monkeypatch):
    class _StubRedisClient:
        def __init__(self, connection_pool):
            self.connection_pool = connection_pool
            self.ping_calls = 0

        def ping(self):
            self.ping_calls += 1
            raise base.redis.exceptions.RedisError("redis down")

    pool_calls = []

    def _fake_pool(**kwargs):
        pool_calls.append(kwargs)
        return {"kwargs": kwargs}

    monkeypatch.setattr(base, "redis_lock_client", None, raising=False)
    monkeypatch.setattr(base, "redis_lock_pool", None, raising=False)
    monkeypatch.setattr(base.redis, "ConnectionPool", _fake_pool)
    monkeypatch.setattr(base.redis, "StrictRedis", _StubRedisClient)

    with pytest.raises(RuntimeError, match="Redis lock client is unavailable"):
        base._ensure_redis_lock_client()
    with pytest.raises(RuntimeError, match="Redis lock client is unavailable"):
        base._ensure_redis_lock_client()

    assert base.redis_lock_client is None
    assert base.redis_lock_pool is None
    assert len(pool_calls) == 2


def test_ensure_redis_lock_client_raises_when_reconnect_fails(monkeypatch):
    monkeypatch.setattr(base, "redis_lock_client", None, raising=False)

    def _fail_pool(**kwargs):
        raise base.redis.exceptions.RedisError("redis down")

    monkeypatch.setattr(base.redis, "ConnectionPool", _fail_pool)

    with pytest.raises(RuntimeError, match="Redis lock client is unavailable"):
        base._ensure_redis_lock_client()


def test_clear_locks_reconnects_lock_client_when_unset(monkeypatch):
    calls = {
        "hgetall": [],
        "scan_iter": [],
        "hset": [],
        "delete": [],
    }

    class _StubLockClient:
        def hgetall(self, runid):
            calls["hgetall"].append(runid)
            return {
                "locked:foo.nodb": "true",
                "locked:bar.nodb": "false",
                "last_modified": "123",
            }

        def scan_iter(self, match):
            calls["scan_iter"].append(match)
            return iter([f"{base.LOCK_KEY_PREFIX}:run-123:baz.nodb"])

        def hset(self, runid, key, value):
            calls["hset"].append((runid, key, value))
            return 1

        def delete(self, key):
            calls["delete"].append(key)
            return 1

    ensure_calls = []
    client = _StubLockClient()

    def _fake_ensure():
        ensure_calls.append(True)
        return client

    monkeypatch.setattr(base, "redis_lock_client", None, raising=False)
    monkeypatch.setattr(base, "_ensure_redis_lock_client", _fake_ensure)

    cleared = base.clear_locks("run-123")

    assert len(ensure_calls) == 1
    assert calls["hgetall"] == ["run-123"]
    assert calls["scan_iter"] == [f"{base.LOCK_KEY_PREFIX}:run-123:*"]
    assert calls["hset"] == [
        ("run-123", "locked:foo.nodb", "false"),
        ("run-123", "locked:baz.nodb", "false"),
    ]
    assert set(calls["delete"]) == {
        base._lock_key_for("run-123", "foo.nodb"),
        base._lock_key_for("run-123", "bar.nodb"),
        f"{base.LOCK_KEY_PREFIX}:run-123:baz.nodb",
    }
    assert set(cleared) == {"locked:foo.nodb", "locked:bar.nodb", "locked:baz.nodb"}


def test_lock_statuses_reconnects_lock_client_when_unset(monkeypatch):
    calls = {
        "scan_iter": [],
        "hgetall": [],
        "hset": [],
    }

    class _StubLockClient:
        def scan_iter(self, match):
            calls["scan_iter"].append(match)
            return iter(())

        def hgetall(self, runid):
            calls["hgetall"].append(runid)
            return {"locked:stale.nodb": "true"}

        def hset(self, runid, key, value):
            calls["hset"].append((runid, key, value))
            return 1

    ensure_calls = []
    client = _StubLockClient()

    def _fake_ensure():
        ensure_calls.append(True)
        return client

    monkeypatch.setattr(base, "redis_lock_client", None, raising=False)
    monkeypatch.setattr(base, "_ensure_redis_lock_client", _fake_ensure)

    statuses = base.lock_statuses("run-456")

    assert dict(statuses) == {"stale.nodb": False}
    assert len(ensure_calls) == 1
    assert calls["scan_iter"] == [f"{base.LOCK_KEY_PREFIX}:run-456:*"]
    assert calls["hgetall"] == ["run-456"]
    assert calls["hset"] == [("run-456", "locked:stale.nodb", "false")]


def test_ensure_redis_nodb_cache_client_reconnects_when_unset(monkeypatch):
    class _StubRedisClient:
        def __init__(self, connection_pool):
            self.connection_pool = connection_pool
            self.ping_calls = 0

        def ping(self):
            self.ping_calls += 1
            return True

    pool_calls = []

    def _fake_pool(**kwargs):
        pool_calls.append(kwargs)
        return {"kwargs": kwargs}

    monkeypatch.setattr(base, "redis_nodb_cache_client", None, raising=False)
    monkeypatch.setattr(base, "redis_nodb_cache_pool", None, raising=False)
    monkeypatch.setattr(base.redis, "ConnectionPool", _fake_pool)
    monkeypatch.setattr(base.redis, "StrictRedis", _StubRedisClient)

    client = base._ensure_redis_nodb_cache_client()

    assert isinstance(client, _StubRedisClient)
    assert client.ping_calls == 1
    assert base.redis_nodb_cache_client is client
    assert len(pool_calls) == 1
    pool_kwargs = pool_calls[0]
    assert pool_kwargs["max_connections"] == 50
    assert pool_kwargs["socket_timeout"] == 5
    assert pool_kwargs["socket_connect_timeout"] == 5
    assert pool_kwargs["socket_keepalive"] is True
    assert pool_kwargs["health_check_interval"] == 30
    assert pool_kwargs["retry_on_timeout"] is True


def test_ensure_redis_nodb_cache_client_retries_after_failed_ping(monkeypatch):
    class _StubRedisClient:
        def __init__(self, connection_pool):
            self.connection_pool = connection_pool
            self.ping_calls = 0

        def ping(self):
            self.ping_calls += 1
            raise base.redis.exceptions.RedisError("redis down")

    pool_calls = []

    def _fake_pool(**kwargs):
        pool_calls.append(kwargs)
        return {"kwargs": kwargs}

    monkeypatch.setattr(base, "redis_nodb_cache_client", None, raising=False)
    monkeypatch.setattr(base, "redis_nodb_cache_pool", None, raising=False)
    monkeypatch.setattr(base.redis, "ConnectionPool", _fake_pool)
    monkeypatch.setattr(base.redis, "StrictRedis", _StubRedisClient)

    with pytest.raises(RuntimeError, match="Redis NoDb cache client is unavailable"):
        base._ensure_redis_nodb_cache_client()
    with pytest.raises(RuntimeError, match="Redis NoDb cache client is unavailable"):
        base._ensure_redis_nodb_cache_client()

    assert base.redis_nodb_cache_client is None
    assert base.redis_nodb_cache_pool is None
    assert len(pool_calls) == 2
    for pool_kwargs in pool_calls:
        assert pool_kwargs["max_connections"] == 50
        assert pool_kwargs["socket_timeout"] == 5
        assert pool_kwargs["socket_connect_timeout"] == 5
        assert pool_kwargs["socket_keepalive"] is True
        assert pool_kwargs["health_check_interval"] == 30
        assert pool_kwargs["retry_on_timeout"] is True


def test_try_redis_get_log_level_missing_value_returns_default(monkeypatch):
    class _StubRedis:
        def get(self, key):
            return None

    client = _StubRedis()
    monkeypatch.setattr(base, 'redis_log_level_client', client, raising=False)

    level = base.try_redis_get_log_level('unit-test', default=logging.WARNING)
    assert level == logging.WARNING


def test_try_redis_get_log_level_swallows_redis_errors(monkeypatch):
    class _StubRedis:
        def get(self, key):
            raise base.redis.exceptions.RedisError("boom")

    client = _StubRedis()
    monkeypatch.setattr(base, "redis_log_level_client", client, raising=False)

    level = base.try_redis_get_log_level("unit-test", default=logging.WARNING)
    assert level == logging.WARNING


def test_try_redis_log_level_round_trip_with_numeric_storage(monkeypatch):
    class _StubRedis:
        def __init__(self):
            self.store = {}

        def set(self, key, value):
            self.store[key] = value

        def get(self, key):
            return self.store.get(key)

    client = _StubRedis()
    monkeypatch.setattr(base, "redis_log_level_client", client, raising=False)

    base.try_redis_set_log_level("unit-test", "DEBUG")
    level = base.try_redis_get_log_level("unit-test", default=logging.WARNING)
    assert level == logging.DEBUG


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ("debug", logging.DEBUG),
        ("DEBUG", logging.DEBUG),
        (" info ", logging.INFO),
        ("warning", logging.WARNING),
        ("error", logging.ERROR),
        ("critical", logging.CRITICAL),
        (str(logging.DEBUG), logging.DEBUG),
        (f" {logging.INFO} ", logging.INFO),
    ],
)
def test_try_redis_get_log_level_parses_valid_values(monkeypatch, stored, expected):
    class _StubRedis:
        def __init__(self, value):
            self.value = value

        def get(self, key):
            return self.value

    monkeypatch.setattr(base, "redis_log_level_client", _StubRedis(stored), raising=False)

    level = base.try_redis_get_log_level("unit-test", default=logging.WARNING)
    assert level == expected


@pytest.mark.parametrize("stored", ["verbose", "15", "-1", "0", "9999"])
def test_try_redis_get_log_level_invalid_values_return_default(monkeypatch, stored):
    class _StubRedis:
        def __init__(self, value):
            self.value = value

        def get(self, key):
            return self.value

    monkeypatch.setattr(base, "redis_log_level_client", _StubRedis(stored), raising=False)

    level = base.try_redis_get_log_level("unit-test", default=logging.WARNING)
    assert level == logging.WARNING


def test_try_redis_get_log_level_str_coercion_failures_return_default(monkeypatch):
    class _BadStr:
        def __str__(self):
            raise TypeError("boom")

    class _StubRedis:
        def get(self, key):
            return _BadStr()

    monkeypatch.setattr(base, "redis_log_level_client", _StubRedis(), raising=False)

    level = base.try_redis_get_log_level("unit-test", default=logging.WARNING)
    assert level == logging.WARNING


def test_try_redis_get_log_level_unexpected_errors_propagate(monkeypatch):
    class _StubRedis:
        def get(self, key):
            raise RuntimeError("boom")

    monkeypatch.setattr(base, "redis_log_level_client", _StubRedis(), raising=False)

    with pytest.raises(RuntimeError, match="boom"):
        base.try_redis_get_log_level("unit-test", default=logging.WARNING)


def test_try_redis_set_log_level_unexpected_redis_set_errors_propagate(monkeypatch):
    class _StubRedis:
        def set(self, key, value):
            raise RuntimeError("boom")

    monkeypatch.setattr(base, "redis_log_level_client", _StubRedis(), raising=False)

    with pytest.raises(RuntimeError, match="boom"):
        base.try_redis_set_log_level("unit-test", "DEBUG")


def test_try_redis_set_log_level_unexpected_logger_errors_propagate(monkeypatch):
    class _StubRedis:
        def __init__(self):
            self.calls = []

        def set(self, key, value):
            self.calls.append((key, value))

    client = _StubRedis()
    monkeypatch.setattr(base, "redis_log_level_client", client, raising=False)

    class _StubLogger:
        def setLevel(self, level):  # noqa: N802 - matches logging API
            raise RuntimeError("boom")

    original_get_logger = base.logging.getLogger

    def _fake_get_logger(name=None):
        if name == "wepppy.run.unit-test":
            return _StubLogger()
        return original_get_logger(name) if name is not None else original_get_logger()

    monkeypatch.setattr(base.logging, "getLogger", _fake_get_logger)

    with pytest.raises(RuntimeError, match="boom"):
        base.try_redis_set_log_level("unit-test", "DEBUG")

    assert client.calls == [("loglevel:unit-test", str(logging.DEBUG))]


def test_cleanup_all_instances_does_not_swallow_keyboard_interrupt():
    class _Controller(base.NoDbBase):
        filename = "cleanup.nodb"

        def _init_logging(self) -> None:
            return

    class _StubInstance:
        def _safe_stop_queue_listener(self) -> None:
            raise KeyboardInterrupt()

    with _Controller._instances_lock:
        _Controller._instances.clear()
        _Controller._instances["boom"] = _StubInstance()

    try:
        with pytest.raises(KeyboardInterrupt):
            _Controller.cleanup_all_instances()
    finally:
        with _Controller._instances_lock:
            _Controller._instances.clear()


def test_create_process_pool_executor_prefers_spawn_but_falls_back(monkeypatch):
    ctx_object = object()

    def _fake_get_context(method):
        assert method == 'spawn'
        return ctx_object

    monkeypatch.setattr(base.mp, 'get_context', _fake_get_context)

    calls = []

    def _fake_executor(*args, **kwargs):
        calls.append(kwargs)
        if 'mp_context' in kwargs:
            raise OSError('spawn unavailable')
        return 'fallback-executor'

    monkeypatch.setattr(base, 'ProcessPoolExecutor', _fake_executor)

    class _Logger:
        def __init__(self):
            self.records = []

        def warning(self, message, *args):
            self.records.append((message, args))

    logger = _Logger()

    result = base.createProcessPoolExecutor(2, logger=logger, prefer_spawn=True)

    assert result == 'fallback-executor'
    assert calls == [{'max_workers': 2, 'mp_context': ctx_object}, {'max_workers': 2}]
    assert logger.records


def test_create_process_pool_executor_requires_max_workers():
    with pytest.raises(ValueError):
        base.createProcessPoolExecutor(None)
