from datetime import datetime, timezone
import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def events():
    path = Path(__file__).parents[2] / "wepppy/nodb/persistence_events.py"
    spec = importlib.util.spec_from_file_location("portable_project_events", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_disabled_is_inert(events, monkeypatch):
    monkeypatch.delenv("WEPPPY_PROJECT_COMMIT_MODE", raising=False)
    events.initialize_project_commits()
    events.notify_committed("/not/a/real/project", "test", "nodb", "ron.nodb")
    assert events.notification_failures == 0


def test_portable_module_import_and_disabled_notify_block_web_and_sql(monkeypatch):
    import builtins
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith(("flask", "sqlalchemy", "psycopg", "wepppy.weppcloud")):
            pytest.fail("Portable seam imported deployment dependency " + name)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setenv("WEPPPY_PROJECT_COMMIT_MODE", "disabled")
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_WRITE_MODE", "timestamp_only")
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_READ_MODE", "legacy")
    path = Path(__file__).parents[2] / "wepppy/nodb/persistence_events.py"
    spec = importlib.util.spec_from_file_location("independent_events", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.initialize_project_commits()
    module.notify_committed("/does/not/exist", "test", "nodb", "ron.nodb")


def test_observer_failure_cannot_undo_commit(events, caplog):
    def fail(event):
        raise RuntimeError("private-database-credential")
    events.register_project_commit_observer(fail)
    events.notify_committed("/tmp/test", "test", "nodb", "ron.nodb")
    assert events.notification_failures == 1
    assert "project_commit_mirror_failed" in caplog.text
    assert "private-database-credential" not in caplog.text


def test_grouped_event_preserves_child_identity(events):
    collected = []
    events.register_project_commit_observer(collected.append)
    events.notify_committed("/wc1/runs/te/test/_pups/omni/scenarios/burned", "test", "nodb", "ron.nodb")
    assert collected[0].runid == "test;;omni;;burned"
    assert collected[0].committed_at.tzinfo is not None


@pytest.mark.parametrize("name", ["omni", "omni-contrast"])
def test_batch_named_omni_child_identity(events, name):
    collected = []
    events.register_project_commit_observer(collected.append)
    parent = "batch;;" + name + ";;leaf"
    path = "/wc1/batch/" + name + "/runs/leaf/_pups/omni/scenarios/burned"
    events.notify_committed(path, parent, "nodb", "ron.nodb")
    events.notify_committed(path, parent + ";;omni;;burned", "nodb", "ron.nodb")
    assert [event.runid for event in collected] == [parent + ";;omni;;burned"] * 2


@pytest.mark.parametrize("failure", ["replace", "ancillary", "observer"])
def test_actual_commit_boundary(tmp_path, monkeypatch, failure):
    from tests.nodb.test_base_boundary_characterization import _DummyNoDb, _RedisStub
    from wepppy.nodb import base, persistence_events
    monkeypatch.setattr(base, "redis_lock_client", _RedisStub())
    monkeypatch.setattr(base, "redis_nodb_cache_client", None)
    collected = []

    def observer(event):
        collected.append(event)
        if failure == "observer":
            raise ConnectionError("database unavailable")

    def fail(*args, **kwargs):
        raise OSError("injected commit boundary")

    monkeypatch.setattr(persistence_events, "_observer", observer)
    controller = _DummyNoDb(str(tmp_path))
    if failure == "replace":
        monkeypatch.setattr(base.os, "replace", fail)
    elif failure == "ancillary":
        monkeypatch.setattr(base, "write_version", fail)
    if failure == "observer":
        with controller.locked(validate_on_success=False):
            controller.value = 12
    else:
        with pytest.raises(OSError), controller.locked(validate_on_success=False):
            controller.value = 12
    assert len(collected) == (0 if failure == "replace" else 1)
    assert (tmp_path / "dummy.nodb").exists() == (failure != "replace")


def test_static_configuration_rejects_missing_driver_without_connecting(monkeypatch):
    from sqlalchemy.exc import NoSuchModuleError
    from wepppy.weppcloud.run_catalog import adapter
    monkeypatch.setenv("WEPPPY_PROJECT_COMMIT_MODE", "postgres")
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_WRITE_MODE", "timestamp_only")
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_READ_MODE", "legacy")
    monkeypatch.setattr(adapter, "_engines", {})
    monkeypatch.setenv("DATABASE_URL", "postgresql+nosuchdriver://localhost/missing")
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    with pytest.raises(NoSuchModuleError):
        adapter.initialize()
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost:1/unreachable")
    monkeypatch.setattr(adapter, "_engines", {})
    from wepppy.nodb import persistence_events
    monkeypatch.setattr(persistence_events, "_observer", None)
    adapter.initialize()
    assert persistence_events._observer is not None


def test_standalone_save_does_not_import_deployment_adapter(tmp_path):
    import os
    import subprocess
    import sys
    source = '''
import importlib.abc
import sys
class DenyDeployment(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'sqlalchemy', 'psycopg2', 'flask_sqlalchemy'} or fullname in {'wepppy.weppcloud.app', 'wepppy.weppcloud.db_api', 'wepppy.weppcloud.run_catalog.adapter'}:
            raise AssertionError('standalone loaded deployment dependency: ' + fullname)
sys.meta_path.insert(0, DenyDeployment())
from tests.nodb.test_base_boundary_characterization import _DummyNoDb, _RedisStub
from wepppy.nodb import base, persistence_events
base.redis_lock_client = _RedisStub()
base.redis_nodb_cache_client = None
persistence_events.initialize_project_commits()
controller = _DummyNoDb(sys.argv[1])
with controller.locked(validate_on_success=False):
    controller.value = 42
print('standalone saved')
'''
    environment = dict(os.environ, WEPPPY_PROJECT_COMMIT_MODE="disabled", WEPPCLOUD_RUN_CATALOG_WRITE_MODE="timestamp_only", WEPPCLOUD_RUN_CATALOG_READ_MODE="legacy")
    result = subprocess.run([sys.executable, "-c", source, str(tmp_path)], env=environment, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert "standalone saved" in result.stdout
