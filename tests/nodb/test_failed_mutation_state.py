"""Held-reference and low-level retry coverage for failed NoDb mutation recovery."""
import logging
from types import SimpleNamespace

import pytest

import wepppy.nodb.base as base
from tests.nodb.test_base_boundary_characterization import _DummyNoDb, _RedisStub

pytestmark = pytest.mark.unit


class StatefulNoDb(_DummyNoDb):
    @base.nodb_setter
    def reject_nested_change(self):
        self.value = 'B'
        self.options.enabled = False
        self.nested['items'].append('B')
        self.introduced = 'B'
        del self.retained
        raise ValueError('rejected operation')


@pytest.fixture
def controller(tmp_path, monkeypatch):
    monkeypatch.setattr(base, 'redis_lock_client', _RedisStub())
    monkeypatch.setattr(base, 'redis_nodb_cache_client', None)
    initial = StatefulNoDb(str(tmp_path))
    with initial.locked():
        initial.value = 'A'
        initial.options = SimpleNamespace(enabled=True)
        initial.nested = {'items': ['A']}
        initial.retained = 'A'
    instance = StatefulNoDb.getInstance(str(tmp_path))
    instance.logger = logging.getLogger(__name__)
    yield instance
    StatefulNoDb._instances.pop(str(tmp_path), None)


def test_decorator_recovers_new_deleted_and_nested_state_through_held_refs(controller):
    held = StatefulNoDb.getInstance(controller.wd)
    alias = held.options
    with pytest.raises(ValueError, match='rejected operation'):
        controller.reject_nested_change()
    assert StatefulNoDb.getInstance(controller.wd) is held is controller
    assert controller.value == 'A'
    assert controller.options.enabled is True
    assert controller.nested == {'items': ['A']}
    assert controller.retained == 'A'
    assert not hasattr(controller, 'introduced')
    # External aliases are invalidated, not magically repaired/re-attached.
    assert alias.enabled is False
    assert alias is not controller.options
    with controller.locked():
        controller.unrelated = 'C'
    durable = StatefulNoDb.load_detached(controller.wd)
    assert durable.value == 'A' and durable.options.enabled is True
    assert durable.nested == {'items': ['A']}
    assert durable.unrelated == 'C'


def test_failed_acquire_does_not_touch_owners_live_state(controller):
    with controller.locked():
        controller.value = 'owner'
        signature = (controller._nodb_mtime, controller._nodb_size)
        token = base._get_local_lock_token(controller)
        with pytest.raises(base.NoDbAlreadyLockedError):
            with controller.locked():
                raise AssertionError('unreachable')
        assert controller.value == 'owner'
        assert (controller._nodb_mtime, controller._nodb_size) == signature
        assert base._get_local_lock_token(controller) == token
    assert StatefulNoDb.load_detached(controller.wd).value == 'owner'


def test_quarantine_rejects_direct_assignment_and_deletion(controller, monkeypatch):
    path = controller._nodb
    original = open(path).read()
    with pytest.raises(ValueError, match='primary'):
        with controller.locked():
            controller.value = 'B'
            with open(path, 'w') as stream:
                stream.write('{bad')
            raise ValueError('primary')
    with pytest.raises(RuntimeError):
        controller.value = 'C'
    with pytest.raises(RuntimeError):
        del controller.value
    with open(path, 'w') as stream:
        stream.write(original)
    controller.recover_mutation_state()
    assert controller.value == 'A'
    with controller.locked():
        controller.value = 'C'
    assert '_nodb_failed_mutation' not in open(path).read()


def test_direct_dump_retains_payload_for_explicit_replace_retry(controller, monkeypatch):
    real_replace = base.os.replace
    controller.lock()
    try:
        controller.value = 'intentional retry'
        signature = (controller._nodb_mtime, controller._nodb_size)
        with monkeypatch.context() as patch:
            def fail_replace(*args):
                raise OSError('replace failed')
            patch.setattr(base.os, 'replace', fail_replace)
            with pytest.raises(OSError, match='replace failed'):
                controller.dump()
        assert controller.value == 'intentional retry'
        assert (controller._nodb_mtime, controller._nodb_size) == signature
        assert base.os.replace is real_replace
        controller.dump()
    finally:
        controller.unlock()
    assert StatefulNoDb.load_detached(controller.wd).value == 'intentional retry'


def test_acquisition_mirror_failure_releases_only_new_token(controller, monkeypatch):
    client = base.redis_lock_client
    original_hset = client.hset
    with monkeypatch.context() as patch:
        def failed_mirror(name, key, value):
            if value == 'true':
                raise OSError('lock mirror unavailable')
            return original_hset(name, key, value)
        patch.setattr(client, 'hset', failed_mirror)
        with pytest.raises(OSError, match='lock mirror unavailable'):
            with controller.locked():
                raise AssertionError('acquisition must fail before mutation')
    assert controller.value == 'A'
    assert not controller.islocked()
    assert base._get_local_lock_token(controller) is None
    with controller.locked():
        controller.value = 'C'
    assert StatefulNoDb.load_detached(controller.wd).value == 'C'
