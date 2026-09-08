"""Receipt updates preserve concurrent fields through real NoDb disk transactions."""
import os

import pytest

import wepppy.nodb.base as base
from wepppy.nodb.batch_runner import BatchRunner
from tests.nodb.test_base_boundary_characterization import _DummyNoDb, _RedisStub

pytestmark = pytest.mark.unit


class ReceiptRunner(_DummyNoDb):
    filename = 'batch_runner.nodb'
    set_rq_job_id = BatchRunner.set_rq_job_id
    set_rq_job_id_fresh = BatchRunner.set_rq_job_id_fresh


@pytest.fixture
def runner(tmp_path, monkeypatch):
    monkeypatch.setattr(base, 'redis_lock_client', _RedisStub())
    monkeypatch.setattr(base, 'redis_nodb_cache_client', None)
    instance = ReceiptRunner(str(tmp_path))
    instance._rq_job_ids = {}
    for _ in range(3):
        with instance.locked():
            instance.value = 'before'
        # Fixed timestamp precision stabilizes serialized signature length.
        os.utime(instance._nodb, ns=(1_700_000_000_125_000_000, 1_700_000_000_125_000_000))
        instance = hydrate(instance)
    return instance


def hydrate(runner):
    return ReceiptRunner._hydrate_instance(runner.wd, False, False, False, use_redis_cache=False)


@pytest.mark.parametrize('key', ['run_batch_rq', 'final_batch_complete_rq'])
def test_same_size_child_commit_preserves_receipts(runner, key, caplog):
    parent = hydrate(runner); child = hydrate(runner)
    before = os.stat(child._nodb)
    with child.locked():
        child.value = 'after!'
    assert os.stat(child._nodb).st_size == before.st_size
    # Force distinct mtime even on filesystems with coarse timestamps.
    os.utime(child._nodb, ns=(before.st_atime_ns, before.st_mtime_ns + 2_000_000_000))
    with pytest.raises(base.NoDbStaleWriteError):
        parent.set_rq_job_id(key, 'job-id')
    caplog.clear()
    parent.set_rq_job_id_fresh('run_batch_rq', 'root-job')
    parent.set_rq_job_id_fresh('final_batch_complete_rq', 'final-job')
    durable = hydrate(runner)
    assert durable.value == 'after!'
    assert durable._rq_job_ids == {'run_batch_rq': 'root-job', 'final_batch_complete_rq': 'final-job'}
    assert 'stale' not in caplog.text.lower()


def test_remove_receipt_and_empty_key(runner):
    runner.set_rq_job_id_fresh('root', 'job')
    runner.set_rq_job_id_fresh('root', None)
    runner.set_rq_job_id_fresh('', 'ignored')
    assert hydrate(runner)._rq_job_ids == {}


def test_failed_dump_forces_singleton_refresh(runner, monkeypatch):
    ReceiptRunner._instances[os.path.abspath(runner.wd)] = runner
    def fail(_self):
        raise OSError('injected dump failure')
    with monkeypatch.context() as scoped:
        scoped.setattr(ReceiptRunner, 'dump', fail)
        with pytest.raises(OSError, match='injected dump failure'):
            runner.set_rq_job_id_fresh('root', 'uncommitted')
    assert runner._nodb_mtime is None
    current = ReceiptRunner.getInstance(runner.wd)
    assert current._rq_job_ids == {}
    assert not current.islocked()


def test_lost_lock_cannot_publish_or_unlock_new_owner(runner, monkeypatch):
    original = ReceiptRunner._hydrate_instance
    def expire(*args, **kwargs):
        fresh = original(*args, **kwargs)
        base.redis_lock_client.set(runner._distributed_lock_key, 'another-owner')
        return fresh
    monkeypatch.setattr(ReceiptRunner, '_hydrate_instance', expire)
    with pytest.raises(RuntimeError):
        runner.set_rq_job_id_fresh('root', 'uncommitted')
    assert base.redis_lock_client.get(runner._distributed_lock_key) == 'another-owner'
    durable = original(runner.wd, False, False, False, use_redis_cache=False)
    assert durable._rq_job_ids == {}


def test_rejected_nested_receipt_does_not_poison_outer_writer(runner):
    with runner.locked():
        signature = runner._nodb_mtime
        runner.value = 'outer!'
        with pytest.raises(base.NoDbAlreadyLockedError):
            runner.set_rq_job_id_fresh('root', 'rejected')
        assert runner._nodb_mtime == signature
    assert hydrate(runner).value == 'outer!'
    assert hydrate(runner)._rq_job_ids == {}
