import importlib
import importlib.util
import logging
import pathlib
import sys
import types

import pytest

import wepppy


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


def test_try_redis_get_log_level_missing_value_returns_default(monkeypatch):
    class _StubRedis:
        def get(self, key):
            return None

    client = _StubRedis()
    monkeypatch.setattr(base, 'redis_log_level_client', client, raising=False)

    level = base.try_redis_get_log_level('unit-test', default=logging.WARNING)
    assert level == logging.WARNING


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
