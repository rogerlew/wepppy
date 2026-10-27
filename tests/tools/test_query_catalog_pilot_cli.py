"""Owned fixture and artifact-truth checks for the trusted pilot controller."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tools import query_catalog_pilot as pilot
from wepppy.query_engine import catalog_refresh as cr

pytestmark = pytest.mark.integration
PILOT_ID = 'test-pilot-1234'


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    root = tmp_path / 'runs' / 'qc'
    source = tmp_path / 'source'
    root.mkdir(parents=True)
    source.mkdir()
    for name in ['watershed/channels.parquet', 'wepp/output/interchange/H.pass.parquet', 'climate/example.parquet']:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.table({'id': [1, 2], 'value': [3.0, 4.0]}), path)
    monkeypatch.setattr(pilot, 'ROOT', root)
    monkeypatch.setattr(pilot, 'SOURCE', source)
    monkeypatch.setattr(pilot, 'SOURCE_FILES', 3)
    monkeypatch.setattr(pilot, 'SOURCE_BYTES', sum(path.stat().st_size for path in source.rglob('*.parquet')))
    monkeypatch.setenv('QUERY_CATALOG_ROOTS_JSON', json.dumps([dict(path=str(root.parent), namespace='test:runs',
                       coordination=str(tmp_path / 'locks'), layout='sharded')]))
    monkeypatch.setenv('QUERY_CATALOG_REFRESH_ENABLED', 'false')
    evidence = tmp_path / 'evidence'
    evidence.mkdir(mode=0o700)
    return evidence, pilot.prepare(PILOT_ID, evidence, cr)


def publish(setup):
    for path in setup['paths']:
        cr.refresh_catalog(path)


def test_exclusive_independent_copies_and_sentinel(prepared):
    evidence, setup = prepared
    assert pilot.load_setup(evidence, PILOT_ID) == setup
    for path in setup['paths']:
        target = Path(path) / setup['files'][0]['path']
        assert target.stat().st_ino != (pilot.SOURCE / setup['files'][0]['path']).stat().st_ino
    assert len(cr.pending_catalog_requests(setup['sentinel'])) == 1
    with pytest.raises(FileExistsError):
        pilot.prepare(PILOT_ID, evidence, cr)


def test_actual_raw_publication_and_duckdb_consumer(prepared):
    _, setup = prepared
    publish(setup)
    result = pilot.verify_artifacts(setup, cr)
    assert result['status'] == 'passed'
    assert len(result['queries']) == 24
    assert all(row['rows'] == row['source_rows'] == 2 for row in result['queries'])
    assert len(cr.pending_catalog_requests(setup['sentinel'])) == 1


def test_pending_receipt_cannot_be_repaired_into_acceptance(prepared, monkeypatch):
    _, setup = prepared
    publish(setup)
    receipt = cr.record_catalog_refresh(setup['paths'][0])
    from wepppy.query_engine import core
    monkeypatch.setattr(core, 'run_query', lambda *args, **kwargs: pytest.fail('consumer ran before raw gate'))
    with pytest.raises(ValueError, match='Raw publication incomplete'):
        pilot.verify_artifacts(setup, cr)
    assert cr.pending_catalog_requests(setup['paths'][0])[0]['request_id'] == receipt['request_id']


def test_changed_catalog_digest_rejected_before_consumer(prepared):
    _, setup = prepared
    publish(setup)
    catalog = Path(setup['paths'][0]) / '_query_engine/catalog.json'
    catalog.write_text(catalog.read_text() + '\n')
    with pytest.raises(ValueError, match='identity/digest'):
        pilot.verify_artifacts(setup, cr)


def test_excluded_sentinel_change_is_failure(prepared):
    _, setup = prepared
    publish(setup)
    (Path(setup['sentinel']) / 'unexpected').write_text('changed')
    with pytest.raises(ValueError, match='sentinel changed'):
        pilot.verify_artifacts(setup, cr)


def test_setup_path_tampering_rejected(prepared):
    evidence, setup = prepared
    setup['paths'][0] = setup['sentinel']
    (evidence / 'setup.json').write_text(json.dumps(setup))
    with pytest.raises(ValueError, match='locators'):
        pilot.load_setup(evidence, PILOT_ID)


def test_symlink_fixture_rejected(prepared):
    _, setup = prepared
    path = Path(setup['paths'][0])
    moved = path.with_name(path.name + '-moved')
    path.rename(moved)
    path.symlink_to(moved, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        pilot.assert_owned(path, PILOT_ID)


def test_interrupted_receipt_wave_never_replayed():
    runtime = SimpleNamespace(status=lambda _: {'phases': {'receipt_wave_started': True}})
    with pytest.raises(RuntimeError, match='operator reconciliation'):
        pilot.receipt_wave(runtime, {}, PILOT_ID, 'token')


def test_completed_wave_is_idempotent():
    runtime = SimpleNamespace(status=lambda _: {'phases': {'receipt_wave_complete': []}})
    pilot.receipt_wave(runtime, {}, PILOT_ID, 'token')


def test_observer_failure_stops_without_blind_renewal(tmp_path, monkeypatch):
    calls = []
    def failed(*args):
        calls.append('observe')
        raise ConnectionError('read unavailable')
    runtime = SimpleNamespace(observe=failed)
    observer = pilot.Observer(runtime, PILOT_ID, 'token', tmp_path)
    monkeypatch.setattr(pilot, 'OBSERVE_SECONDS', 0.001)
    observer.thread.start()
    observer.thread.join(timeout=1)
    with pytest.raises(RuntimeError, match='observation failed'):
        observer.check()
    assert calls == ['observe']
    assert observer.stop.is_set()


class ControllerRuntime:
    """Only queue execution is simulated; artifacts/receipts use the real core."""
    def __init__(self, setup):
        import copy
        self.copy = copy.deepcopy
        self.setup, self.cr, self.connection, self.queue = setup, cr, object(), object()
        scopes = [dict(path=name, directory_identity={'inode': Path(name).stat().st_ino},
                       **cr.resolve_scope(name).as_dict()) for name in setup['paths']]
        self.data = dict(manifest={'scopes': scopes}, phases={}, jobs={}, counters={'refresh': 0, 'inventory': 0},
                         state='paused', failures=[], outstanding=0, global_outstanding=0, global_uncertain=0)
        self.calls = []
        self.pilot = SimpleNamespace(acquire_controller=lambda *args: 'owned-token',
                                     resume_pilot=self.resume, authorize_receipt=self.authorize)
        self.cq = SimpleNamespace(reconcile_query_catalogs=self.reconcile, enqueue_catalog_refresh=self.enqueue)

    def preflight(self, **kwargs):
        return {'consumers': {'compatible': 8, 'incompatible': [], 'suspended': False}}

    def status(self, _):
        return self.copy(self.data)

    def observe(self, *_):
        self.calls.append('observe')
        return self.status(PILOT_ID)

    def pause(self, _, reason):
        self.data['state'] = 'paused'
        self.calls.append(('pause', reason))

    def phase(self, _, token, phase, value):
        assert token == 'owned-token'
        if phase in self.data['phases']:
            assert self.data['phases'][phase] == value
        self.data['phases'][phase] = value

    def raw_jobs(self, status):
        return {}

    def raw_ordinary(self, status):
        return {}

    def public_jobs(self, status):
        return {job_id: {'job_id': job_id, 'children': {}} for job_id in status['jobs']}

    def resume(self, *args):
        self.data['state'] = 'active'

    def authorize(self, connection, identifier, name, token):
        if identifier != PILOT_ID:
            raise ValueError('Pilot authority is absent')
        if name not in self.setup['paths']:
            raise ValueError('Scope is not approved')

    def add_job(self, kind, scope=None):
        from uuid import uuid4
        job_id = 'query_catalog_refresh_' + str(uuid4())
        self.data['jobs'][job_id] = dict(kind=kind, scope=scope, status='finished')
        self.data['counters'][kind] += 1
        return job_id

    def reconcile(self, **kwargs):
        self.calls.append('reconcile')
        if not self.data['jobs']:
            self.add_job('inventory')
            for name in self.setup['paths']:
                cr.refresh_catalog(name)
                self.add_job('refresh', cr.resolve_scope(name).as_dict())

    def enqueue(self, name, *, queue, pilot_id=None, controller_token=None):
        if pilot_id is None:
            return {'state': 'pending', 'error_code': 'query_catalog_refresh_disabled'}
        self.authorize(self.connection, pilot_id, name, controller_token)
        cr.refresh_catalog(name)
        return {'state': 'queued', 'job_id': self.add_job('refresh', cr.resolve_scope(name).as_dict())}


def test_controller_two_waves_actual_artifacts_and_lineage(prepared):
    evidence, setup = prepared
    runtime = ControllerRuntime(setup)
    result = pilot.run_controller(runtime, PILOT_ID, evidence, monitor_seconds=30)
    assert result['outcome'] == 'completed'
    assert result['status']['counters'] == {'refresh': 16, 'inventory': 1}
    assert result['status']['phases']['artifact_verified']
    assert len(result['status']['phases']['receipt_wave_complete']) == 8
    assert runtime.calls[-2:] == [('pause', 'acceptance_readback_complete'), 'observe']
    assert (evidence / 'inventory-readback.json').exists()
    assert (evidence / 'receipt-readback.json').exists()


def test_controller_bound_stops_admissions_without_discarding_work(prepared):
    evidence, setup = prepared
    runtime = ControllerRuntime(setup)
    runtime.data['outstanding'] = 1
    runtime.data['global_outstanding'] = 1
    result = pilot.run_controller(runtime, PILOT_ID, evidence, monitor_seconds=0)
    assert result['outcome'] == 'incomplete_drain'
    assert runtime.data['state'] == 'paused'
    assert 'reconcile' not in runtime.calls


def test_retained_failure_cannot_resume_into_pass(prepared):
    evidence, setup = prepared
    runtime = ControllerRuntime(setup)
    runtime.data['phases']['acceptance_failure'] = {'error_type': 'ValueError'}
    with pytest.raises(RuntimeError, match='cannot become a passed pilot'):
        pilot.run_controller(runtime, PILOT_ID, evidence, resume=True)
    assert not runtime.calls


def test_catalog_presence_without_job_lineage_cannot_pass(prepared):
    evidence, setup = prepared
    publish(setup)
    runtime = ControllerRuntime(setup)
    runtime.cq.reconcile_query_catalogs = lambda **kwargs: None
    with pytest.raises(ValueError, match='job/budget lineage'):
        pilot.run_controller(runtime, PILOT_ID, evidence, monitor_seconds=10)
    assert 'acceptance_failure' in runtime.data['phases']
    assert runtime.data['state'] == 'paused'


def test_started_ordinary_job_retains_wait_crossing_between_polls():
    rows = {'ordinary': {'enqueued_at': '2026-10-27T00:00:00Z', 'started_at': '2026-10-27T00:05:01Z'}}
    result = pilot.ordinary_waits(rows, [], 0)
    assert result['max_observed_wait_seconds'] == 301
    assert result['unavailable_timestamps'] == []


def test_missing_ordinary_metadata_is_not_zero_wait_evidence():
    result = pilot.ordinary_waits({'missing': {}}, ['missing'], 0)
    assert result['unavailable_timestamps'] == ['missing']


def test_drain_does_not_resume_or_require_valid_artifact_setup(prepared):
    evidence, setup = prepared
    runtime = ControllerRuntime(setup)
    runtime.data['phases']['acceptance_failure'] = {'error_type': 'ValueError'}
    (evidence / 'setup.json').write_text('invalid')
    result = pilot.run_controller(runtime, PILOT_ID, evidence, drain_only=True, monitor_seconds=1)
    assert result['outcome'] == 'failed'
    assert runtime.data['state'] == 'paused'
    assert 'reconcile' not in runtime.calls


def test_observer_missing_global_ledger_pauses_and_keeps_observing(tmp_path):
    pauses = []
    state = {'global_outstanding': None, 'global_uncertain': True, 'counters': {'refresh': 0, 'inventory': 0}, 'jobs': {}}
    runtime = SimpleNamespace(observe=lambda *args: state, pause=lambda *args: pauses.append(args),
                              preflight=lambda **kwargs: {'consumers': {'compatible': 8, 'incompatible': [], 'suspended': False}},
                              raw_jobs=lambda *_: {}, raw_ordinary=lambda *_: {})
    observer = pilot.Observer(runtime, PILOT_ID, 'token', tmp_path)
    assert observer.once() is state
    assert pauses == [(PILOT_ID, 'accounting_failure')]
    assert not observer.stop.is_set()


def test_receipt_wave_capacity_deferred_scope_retried_after_inventory_complete(prepared):
    _, setup = prepared
    runtime = ControllerRuntime(setup)
    runtime.reconcile()
    runtime.resume()
    original = runtime.cq.enqueue_catalog_refresh
    calls = []
    def bounded(name, **kwargs):
        calls.append(name)
        if len(calls) == 8:
            return {'state': 'pending', 'error_code': 'query_catalog_capacity_pending'}
        return original(name, **kwargs)
    runtime.cq.enqueue_catalog_refresh = bounded
    pilot.receipt_wave(runtime, setup, PILOT_ID, 'owned-token')
    assert cr.pending_catalog_requests(setup['paths'][-1])
    assert runtime.data['counters']['refresh'] == 15
    pilot.retry_receipt_wave(runtime, setup, PILOT_ID, 'owned-token')
    assert not cr.pending_catalog_requests(setup['paths'][-1])
    assert runtime.data['counters']['refresh'] == 16
    assert len(calls) == 9


def test_unknown_prefix_jobs_remain_ordinary_for_raw_wait_evidence(monkeypatch):
    import rq.registry
    known = 'query_catalog_refresh_known'
    unknown = 'query_catalog_refresh_unowned'
    connection = SimpleNamespace(lrange=lambda *args: [known.encode(), unknown.encode()], zrange=lambda *args: [])
    monkeypatch.setattr(rq.registry, 'StartedJobRegistry', lambda *args, **kwargs: SimpleNamespace(get_job_ids=lambda **kwargs: []))
    runtime = pilot.Runtime.__new__(pilot.Runtime)
    runtime.connection, runtime.queue, runtime.ordinary_seen = connection, SimpleNamespace(key='batch'), set()
    runtime.raw_jobs = lambda state: {jid: {'enqueued_at': '2026-10-27T00:00:00Z'} for jid in state['jobs']}
    result = runtime.raw_ordinary({'jobs': {}, 'global_job_ids': [known]})
    assert set(result['jobs']) == {unknown}
    assert unknown in result['wait_seconds']


def test_post_renewal_raw_read_failure_pauses_in_observer_thread(tmp_path, monkeypatch):
    import threading
    paused = threading.Event()
    state = {'global_outstanding': 0, 'global_uncertain': False, 'counters': {'refresh': 0, 'inventory': 0}, 'jobs': {}}
    def failed(_):
        raise OSError('raw job metadata unavailable')
    runtime = SimpleNamespace(observe=lambda *args: state, pause=lambda *args: paused.set(),
                              preflight=lambda **kwargs: {'consumers': {'compatible': 8, 'incompatible': [], 'suspended': False}},
                              raw_jobs=lambda *_: {}, raw_ordinary=failed)
    observer = pilot.Observer(runtime, PILOT_ID, 'token', tmp_path)
    monkeypatch.setattr(pilot, 'OBSERVE_SECONDS', 0.001)
    observer.thread.start()
    assert paused.wait(1), 'pause must not wait for main-thread artifact readback'
    observer.thread.join(timeout=1)
    with pytest.raises(RuntimeError, match='observation failed'):
        observer.check()


def test_initial_observation_failure_is_latched_and_paused(prepared):
    evidence, setup = prepared
    runtime = ControllerRuntime(setup)
    def failed(*args):
        raise OSError('initial observation unavailable')
    runtime.observe = failed
    with pytest.raises(OSError, match='initial observation'):
        pilot.run_controller(runtime, PILOT_ID, evidence)
    assert runtime.data['state'] == 'paused'
    assert 'acceptance_failure' in runtime.data['phases']
    assert ('pause', 'controller_observation_failure') in runtime.calls


def test_prepare_creates_missing_canonical_shard_parent(prepared, tmp_path, monkeypatch):
    new_root = tmp_path / 'newruns'
    new_root.mkdir()
    shard = new_root / 'qc'
    monkeypatch.setattr(pilot, 'ROOT', shard)
    monkeypatch.setenv('QUERY_CATALOG_ROOTS_JSON', json.dumps([dict(path=str(new_root), namespace='other:runs',
                       coordination=str(tmp_path / 'newlocks'), layout='sharded')]))
    evidence = tmp_path / 'new-evidence'
    evidence.mkdir()
    assert not shard.exists()
    setup = pilot.prepare(PILOT_ID, evidence, cr)
    assert shard.is_dir()
    assert len(setup['paths']) == 8


def test_republished_new_incarnation_cannot_pass_old_admission_binding(prepared, monkeypatch):
    _, setup = prepared
    runtime = ControllerRuntime(setup)
    bindings = runtime.status(PILOT_ID)['manifest']['scopes']
    publish(setup)
    cr.invalidate_catalog_incarnation(setup['paths'][0])
    cr.refresh_catalog(setup['paths'][0])
    from wepppy.query_engine import core
    monkeypatch.setattr(core, 'run_query', lambda *args, **kwargs: pytest.fail('consumer ran with replaced authority'))
    with pytest.raises(ValueError, match='differs from admitted manifest'):
        pilot.verify_artifacts(setup, cr, bindings=bindings)


def test_raw_ordinary_uses_public_started_ids_without_cleanup(monkeypatch):
    import rq.registry

    calls = []
    def get_job_ids(*, cleanup):
        calls.append(cleanup)
        return ["ordinary", "query_catalog_refresh_known"]
    connection = SimpleNamespace(lrange=lambda *args: [])
    monkeypatch.setattr(rq.registry, "StartedJobRegistry", lambda *args, **kwargs: SimpleNamespace(
        get_job_ids=get_job_ids
    ))
    runtime = pilot.Runtime.__new__(pilot.Runtime)
    runtime.connection, runtime.queue, runtime.ordinary_seen = connection, SimpleNamespace(key="batch"), set()
    runtime.raw_jobs = lambda state: {job_id: {
        "enqueued_at": "2026-10-27T00:00:00Z", "started_at": "2026-10-27T00:01:00Z"
    } for job_id in state["jobs"]}
    result = runtime.raw_ordinary({"global_job_ids": ["query_catalog_refresh_known"]})
    assert calls == [False]
    assert result["started_ids"] == ["ordinary", "query_catalog_refresh_known"]
    assert set(result["jobs"]) == {"ordinary"}
    assert result["wait_seconds"] == {"ordinary": 60.0}
