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


def test_ensure_redis_lock_client_raises_when_reconnect_fails(monkeypatch):
    monkeypatch.setattr(base, "redis_lock_client", None, raising=False)

    def _fail_pool(**kwargs):
        raise base.redis.exceptions.RedisError("redis down")

    monkeypatch.setattr(base.redis, "ConnectionPool", _fail_pool)

    with pytest.raises(RuntimeError, match="Redis lock client is unavailable"):
        base._ensure_redis_lock_client()


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
