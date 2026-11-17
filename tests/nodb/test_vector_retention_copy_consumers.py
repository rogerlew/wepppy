"""Copy/reset consumer evidence through the real retention lifecycle and Redis."""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import uuid

import pytest
import redis

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.microservices import vector_upload_normalization as retention
from wepppy.nodb import batch_runner as batch_module
from wepppy.nodb.mods.omni import omni_clone_contrast_service as clone_module
from wepppy.nodb.mods.omni.omni_state_contrast_mixin import OmniStateContrastMixin
from wepppy.rq import batch_rq
from tests.nodb.test_batch_runner import _runner_stub, _FeatureStub, _NoopLogger, _StopBeforeControllers

pytestmark = pytest.mark.integration

ROOTS = (
    'roads/vector_upload_attempts', 'ag_fields/vector_upload_attempts',
    '_pups/omni/contrasts/vector_upload_attempts', 'resources/vector_upload_attempts',
    'archives/private',
)


def evidence(project: Path, relative: str, *, label: str = 'source') -> Path:
    attempt = project / relative / label
    attempt.mkdir(parents=True)
    (attempt / 'original.upload').write_bytes(f'complete-{label}'.encode())
    (attempt / 'normalization.json').write_text(json.dumps({
        'schema': 'vector-normalization-v1', 'status': 'accepted',
        'actor': {'kind': 'human', 'user_id': 41}, 'project_identity': 'source-project',
        'attempt_id': label, 'source_sha256': hashlib.sha256(f'complete-{label}'.encode()).hexdigest(),
    }))
    return attempt


@pytest.fixture
def ledger_environment(tmp_path, monkeypatch):
    filesystem_id = f'copy-consumer-{uuid.uuid4().hex}'
    monkeypatch.setenv('VECTOR_UPLOAD_RUN_FILESYSTEM_ID', filesystem_id)
    monkeypatch.setenv('VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT', str(tmp_path))
    options = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    secret = Path(os.getenv('REDIS_PASSWORD_FILE', '/run/secrets/redis_password'))
    if secret.exists():
        options['password'] = secret.read_text().strip()
    connection = redis.client.Redis(**options)
    prefix = f'vector-upload-retention:{filesystem_id}'
    connection.hset(f'{prefix}:totals', mapping={'initialized': 1, 'committed': 0, 'reserved': 0, 'inflight': 0})
    real_maintenance = retention.acquire_retention_maintenance_lease
    real_factory = retention.RedisScopeLeaseFactory
    real_pending = retention.retention_rebuild_obligation_pending
    monkeypatch.setattr(retention, 'acquire_retention_maintenance_lease', lambda: real_maintenance(connection))
    monkeypatch.setattr(retention, 'RedisScopeLeaseFactory', lambda: real_factory(connection))
    def pending(root, **kwargs):
        kwargs.setdefault('connection', connection)
        return real_pending(root, **kwargs)
    monkeypatch.setattr(retention, 'retention_rebuild_obligation_pending', pending)
    monkeypatch.setattr(retention.shutil, 'disk_usage', lambda _: SimpleNamespace(
        total=30_000_000_000, used=1_000_000_000, free=29_000_000_000))
    yield SimpleNamespace(root=tmp_path, connection=connection, prefix=prefix)
    keys = list(connection.scan_iter(match=f'{prefix}:*'))
    if keys:
        connection.delete(*keys)
    connection.close()


def assert_exact_ledger(env):
    audit = retention.reconcile_retention(env.root, rebuild_ledger=True, connection=env.connection)
    totals = env.connection.hgetall(f'{env.prefix}:totals')
    assert int(totals['committed']) == audit['ledger_audit']['computed_committed']
    assert not env.connection.smembers(f'{env.prefix}:rebuild-pending')
    assert not list((env.root / '.vector-upload-rebuild-pending').glob('*.json'))


def initialize_ledger(env):
    retention.reconcile_retention(env.root, apply=True, rebuild_ledger=True, connection=env.connection)


def prepare_batch(env, monkeypatch, *, reset):
    runner = _runner_stub(env.root, rmtree_enabled=reset)
    target = Path(runner.wd) / 'runs' / 'leaf'
    base = Path(runner.base_wd)
    base.mkdir()
    for relative in ROOTS:
        evidence(base, relative)
    monkeypatch.setattr(batch_module, 'get_wd', lambda _: str(target))
    monkeypatch.setattr(batch_module.BatchRunner, '_get_run_logger', lambda *_: _NoopLogger())
    monkeypatch.setattr(batch_module, '_clear_batch_leaf_nodb_state', lambda *_: ())
    monkeypatch.setattr(batch_module.RedisPrep, 'getInstance', lambda *_: (_ for _ in ()).throw(_StopBeforeControllers()))
    return runner, base, target


def test_batch_leaf_copy_preserves_all_retained_roots_and_charges_copy(ledger_environment, monkeypatch):
    env = ledger_environment
    runner, base, target = prepare_batch(env, monkeypatch, reset=False)
    originals = {relative: (base / relative / 'source/original.upload').read_bytes() for relative in ROOTS}
    initialize_ledger(env)
    with pytest.raises(_StopBeforeControllers):
        runner._run_batch_hillslopes_owned(_FeatureStub('leaf'))
    for relative in ROOTS:
        assert (target / relative / 'source/original.upload').read_bytes() == originals[relative]
        assert (base / relative / 'source/original.upload').read_bytes() == originals[relative]
        copied = json.loads((target / relative / 'source/normalization.json').read_text())
        assert copied['actor'] == {'kind': 'human', 'user_id': 41}
        assert copied['retention_actor']['kind'] == 'unattributed'
        assert copied['project_identity'] == 'source-project'
        assert copied['copied_from']['receipt_sha256'] == hashlib.sha256((base / relative / 'source/normalization.json').read_bytes()).hexdigest()
    assert_exact_ledger(env)
    # A normal rerun without replacement is not another copy or provenance event.
    before = (target / ROOTS[0] / 'source/normalization.json').read_bytes()
    with pytest.raises(_StopBeforeControllers):
        runner._run_batch_hillslopes_owned(_FeatureStub('leaf'))
    assert (target / ROOTS[0] / 'source/normalization.json').read_bytes() == before
    assert_exact_ledger(env)


def test_partial_batch_copy_retry_recopies_when_reset_option_disabled(ledger_environment, monkeypatch):
    env = ledger_environment
    runner, base, target = prepare_batch(env, monkeypatch, reset=False)
    initialize_ledger(env)
    real_copy = shutil.copytree
    def interrupted(source, destination, *args, **kwargs):
        if Path(source) == base:
            Path(destination).mkdir(parents=True)
            (Path(destination) / 'partial').write_text('incomplete')
            raise OSError('injected copy interruption')
        return real_copy(source, destination, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(batch_module.shutil, 'copytree', interrupted)
        with pytest.raises(OSError, match='copy interruption'):
            runner._run_batch_hillslopes_owned(_FeatureStub('leaf'))
    assert env.connection.scard(f'{env.prefix}:rebuild-pending') == 1
    with pytest.raises(_StopBeforeControllers):
        runner._run_batch_hillslopes_owned(_FeatureStub('leaf'))
    assert not (target / 'partial').exists()
    assert (target / ROOTS[0] / 'source/original.upload').read_bytes() == b'complete-source'
    assert_exact_ledger(env)


def test_batch_copy_retry_requires_partial_removal_before_recopy(ledger_environment, monkeypatch):
    env = ledger_environment
    runner, base, target = prepare_batch(env, monkeypatch, reset=False)
    initialize_ledger(env)
    source_total = int(env.connection.hget(f'{env.prefix}:totals', 'committed'))
    real_copy = shutil.copytree
    copy_calls = []

    def copied_then_interrupted(source, destination, *args, **kwargs):
        result = real_copy(source, destination, *args, **kwargs)
        if Path(destination) == target:
            copy_calls.append(Path(destination))
            raise OSError('interrupted after source receipts copied')
        return result

    with monkeypatch.context() as patch:
        patch.setattr(shutil, 'copytree', copied_then_interrupted)
        with pytest.raises(OSError, match='source receipts copied'):
            runner._run_batch_hillslopes_owned(_FeatureStub('leaf'))
    copied_receipt = target / ROOTS[0] / 'source/normalization.json'
    assert 'retention_actor' not in json.loads(copied_receipt.read_text())
    unchanged_receipt = copied_receipt.read_bytes()
    assert env.connection.scard(f'{env.prefix}:rebuild-pending') == 1

    def record_copy(source, destination, *args, **kwargs):
        if Path(destination) == target:
            copy_calls.append(Path(destination))
        return real_copy(source, destination, *args, **kwargs)

    def failed_removal(*_args, **_kwargs):
        raise OSError('injected partial removal failure')

    with monkeypatch.context() as patch:
        patch.setattr(shutil, 'rmtree', failed_removal)
        patch.setattr(shutil, 'copytree', record_copy)
        with pytest.raises(OSError, match='partial removal failure'):
            runner._run_batch_hillslopes_owned(_FeatureStub('leaf'))
    assert copy_calls == [target]
    assert copied_receipt.read_bytes() == unchanged_receipt
    assert not list(target.parent.glob('leaf.stale.*'))
    assert env.connection.scard(f'{env.prefix}:rebuild-pending') == 1
    assert int(env.connection.hget(f'{env.prefix}:totals', 'committed')) == source_total

    with pytest.raises(_StopBeforeControllers):
        runner._run_batch_hillslopes_owned(_FeatureStub('leaf'))
    assert not list(target.parent.glob('leaf.stale.*'))
    copied_total = sum(
        path.stat().st_size
        for relative in ROOTS for path in (target / relative).rglob('*') if path.is_file()
    )
    for actor_key, expected in (('human:41', source_total), ('unattributed', copied_total)):
        bucket = hashlib.sha256(actor_key.encode()).hexdigest()
        assert int(env.connection.hget(f'{env.prefix}:principal:{bucket}', 'committed')) == expected
    assert int(env.connection.hget(f'{env.prefix}:totals', 'committed')) == source_total + copied_total
    assert_exact_ledger(env)


def test_batch_omni_subtree_reset_accounts_removed_and_copied_attempts(ledger_environment, monkeypatch):
    env = ledger_environment
    base = env.root / 'batch/_base'
    leaf = env.root / 'batch/runs/leaf'
    source = evidence(base, ROOTS[2])
    evidence(leaf, ROOTS[2], label='old')
    (base / 'omni.nodb').write_text(json.dumps({'wd': str(base)}))
    monkeypatch.setattr(batch_rq, 'clear_nodb_file_cache', lambda *_: None)
    initialize_ledger(env)
    batch_rq._reset_omni_nodb_from_base(base, leaf, 'batch;;batch;;leaf')
    assert not (leaf / ROOTS[2] / 'old').exists()
    assert (leaf / ROOTS[2] / 'source/original.upload').read_bytes() == (source / 'original.upload').read_bytes()
    assert json.loads((leaf / 'omni.nodb').read_text())['wd'] == str(leaf)
    assert_exact_ledger(env)


def test_batch_base_reinitialization_reconciles_removed_evidence(ledger_environment, monkeypatch):
    env = ledger_environment
    runner = _runner_stub(env.root, rmtree_enabled=False)
    runner._base_wd = runner.base_wd
    runner._base_config = 'test.cfg'
    evidence(Path(runner.base_wd), ROOTS[0])
    initialize_ledger(env)
    import wepppy.nodb.core as core
    monkeypatch.setattr(core, 'Ron', lambda *_args, **_kwargs: None)
    runner._init_base_project()
    assert not (Path(runner.base_wd) / ROOTS[0]).exists()
    assert_exact_ledger(env)


@pytest.mark.parametrize('operation', ['_clean_contrast_runs', '_clean_stale_contrast_runs'])
def test_omni_bulk_cleanup_retry_preserves_owner_evidence_and_repairs_absent_children(ledger_environment, monkeypatch, operation):
    env = ledger_environment
    project = env.root / 'run'
    original = evidence(project, ROOTS[2])
    contrasts = project / '_pups/omni/contrasts'
    child = contrasts / '1'
    evidence(child, ROOTS[0], label='child')
    sidecar = project / 'omni/contrasts'
    sidecar.mkdir(parents=True)
    controller = SimpleNamespace(wd=str(project), runid=f'run-{env.root.name}', _contrast_sidecar_dir=lambda: str(sidecar))
    initialize_ledger(env)
    real_remove = shutil.rmtree
    def removed_then_failed(path, *args, **kwargs):
        real_remove(path, *args, **kwargs)
        if Path(path) == child:
            raise OSError('injected post-removal failure')
    args = ([],) if operation == '_clean_stale_contrast_runs' else ()
    method = getattr(OmniStateContrastMixin, operation)
    with monkeypatch.context() as patch:
        patch.setattr(shutil, 'rmtree', removed_then_failed)
        with pytest.raises(OSError, match='post-removal'):
            method(controller, *args)
    assert not child.exists()
    assert env.connection.scard(f'{env.prefix}:rebuild-pending') == 1
    method(controller, *args)
    assert (original / 'original.upload').read_bytes() == b'complete-source'
    assert_exact_ledger(env)


def test_omni_workspace_reset_counts_deferred_stale_evidence(ledger_environment, monkeypatch):
    env = ledger_environment
    target = env.root / 'run/_pups/omni/scenarios/example'
    original = evidence(target, ROOTS[0])
    source_bytes = (original / 'original.upload').read_bytes()
    initialize_ledger(env)
    monkeypatch.setattr(clone_module, '_rmtree_with_retry', lambda *_: (_ for _ in ()).throw(OSError('deferred cleanup')))
    clone_module._reset_workspace(target, logger=logging.getLogger(__name__), project_key=f'run:{env.root.name}')
    assert not target.exists()
    stale = next(target.parent.glob('example.stale.*'))
    assert (stale / ROOTS[0] / 'source/original.upload').read_bytes() == source_bytes
    assert_exact_ledger(env)


@pytest.mark.parametrize('consumer', ['batch', 'omni'])
def test_workspace_retry_requires_identity_for_retained_stale_sibling(ledger_environment, monkeypatch, consumer):
    env = ledger_environment
    if consumer == 'batch':
        runner, base, target = prepare_batch(env, monkeypatch, reset=False)
        for relative in ROOTS:
            shutil.rmtree(base / relative)
    else:
        target = env.root / 'run/_pups/omni/scenarios/example'
    stale = target.with_name(f'{target.name}.stale.123.456')
    retained = evidence(stale, ROOTS[0]) / 'original.upload'
    expected = retained.read_bytes()
    initialize_ledger(env)
    monkeypatch.delenv('VECTOR_UPLOAD_RUN_FILESYSTEM_ID')
    with pytest.raises(retention.VectorUploadError, match='identity is not configured'):
        if consumer == 'batch':
            runner._run_batch_hillslopes_owned(_FeatureStub('leaf'))
        else:
            clone_module._reset_workspace(target, logger=logging.getLogger(__name__), project_key='run:example')
    assert not target.exists()
    assert retained.read_bytes() == expected


@pytest.mark.parametrize('kind', ['scenario', 'contrast'])
def test_omni_single_child_delete_repairs_after_child_is_absent(ledger_environment, monkeypatch, kind):
    env = ledger_environment
    project = env.root / 'run'
    child = project / '_pups/omni' / ('scenarios/example' if kind == 'scenario' else 'contrasts/1')
    evidence(child, ROOTS[0])
    controller = SimpleNamespace(
        wd=str(project), runid=f'run-{env.root.name}', logger=logging.getLogger(__name__),
        _clear_contrast_run_status=lambda *_: None,
    )
    monkeypatch.setattr(
        'wepppy.nodb.mods.omni.omni_state_contrast_mixin._clear_nodb_cache_and_locks',
        lambda *_: None,
    )
    initialize_ledger(env)
    real_remove = shutil.rmtree

    def removed_then_failed(path, *args, **kwargs):
        real_remove(path, *args, **kwargs)
        raise OSError('injected post-removal failure')

    def remove_child():
        if kind == 'scenario':
            OmniStateContrastMixin._remove_scenario_artifacts(controller, 'example', [], [])
        else:
            OmniStateContrastMixin._clean_contrast_run(controller, 1)

    with monkeypatch.context() as patch:
        patch.setattr(shutil, 'rmtree', removed_then_failed)
        if kind == 'scenario':
            remove_child()  # Existing scenario cleanup logs filesystem failures.
        else:
            with pytest.raises(OSError, match='post-removal'):
                remove_child()
    assert not child.exists()
    assert env.connection.scard(f'{env.prefix}:rebuild-pending') == 1
    remove_child()
    assert_exact_ledger(env)


def test_omni_cleanup_borrows_live_upload_scope_and_preserves_reservation(ledger_environment):
    import io
    from wepppy.nodb.mods.omni.omni import _omni_workflow_operation

    env = ledger_environment
    project = env.root / 'run'
    project.mkdir()
    contrasts = project / '_pups/omni/contrasts'
    evidence(contrasts / '1', ROOTS[0], label='child')
    sidecar = project / 'omni/contrasts'
    sidecar.mkdir(parents=True)
    runid = f'borrowed-{env.root.name}'
    key = f'run:{runid}'
    controller = SimpleNamespace(wd=str(project), runid=runid, _contrast_sidecar_dir=lambda: str(sidecar))
    initialize_ledger(env)
    payload = json.dumps({'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': {}, 'geometry': {
            'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 0]]],
        }},
    ]}).encode()
    attempt_root = project / ROOTS[2]
    prepared = retention.prepare_vector_upload(
        raw_filename='areas.geojson', stream=io.BytesIO(payload),
        endpoint_max_bytes=1024 * 1024, attempt_root=attempt_root,
        evidence_roots=(attempt_root,), filesystem_root=project,
        project_key=key, workflow='omni_contrasts', project_identity=runid,
        actor=retention.RetentionActor('human', 42),
        validator=lambda *_: {'valid': True},
        ledger=retention.RedisRetentionLedger(env.connection),
    )
    try:
        before = env.connection.hgetall(f'{env.prefix}:totals')
        with _omni_workflow_operation(str(project), runid, prepared.lease):
            OmniStateContrastMixin._clean_stale_contrast_runs(controller, [])
        after = env.connection.hgetall(f'{env.prefix}:totals')
        assert after['reserved'] == before['reserved']
        assert after['inflight'] == before['inflight']
        assert prepared.receipt['status'] == 'prepared'
        assert (prepared.attempt_dir / prepared.receipt['source_path']).read_bytes() == payload
        assert not (contrasts / '1').exists()
        assert not env.connection.smembers(f'{env.prefix}:rebuild-pending')
    finally:
        prepared.reject('test-complete')
    assert_exact_ledger(env)
