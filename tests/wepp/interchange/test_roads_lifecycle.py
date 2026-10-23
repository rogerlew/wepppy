"""Filesystem evidence for Roads replacement, admission, and coordination."""
import json
import multiprocessing
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.wepp.interchange import _roads_lifecycle as lifecycle

pytestmark = pytest.mark.unit


def prepared(root):
    segment_dir = root / lifecycle.SEGMENTS
    segment_dir.mkdir(parents=True)
    (segment_dir / 'roads.inslope.monotonic.geojson').write_text(json.dumps({
        'features': [{'properties': {'segment_id': 'roads-seg-000001'}}]}))
    (segment_dir / 'roads.segment.pass.manifest.json').write_text(json.dumps([
        {'segment_id': 'roads-seg-000001', 'segment_run_id': 'profile-1', 'status': 'completed'}]))
    resources = {'required_relpaths': sorted(lifecycle.mandatory_paths(False))}
    for relative in resources['required_relpaths']:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == '.parquet':
            pq.write_table(pa.table({'value': [1.0]}), path)
        else:
            path.write_text('validated output')
    return resources


def publish(root):
    resources = prepared(root)
    with lifecycle.operation(root):
        lifecycle.publish(root, resources, single_storm=False)
    return resources


def _other_process_writer(root, queue):
    try:
        with lifecycle.operation(root):
            queue.put('acquired')
    except lifecycle.RoadsOperationBusy:
        queue.put('busy')


def test_replacement_retains_outputs_geometry_and_external_cache(tmp_path):
    publish(tmp_path)
    baseline = tmp_path / 'wepp/output/example'
    baseline.parent.mkdir()
    baseline.write_text('baseline')
    cache = tmp_path / lifecycle.CACHE / (lifecycle.CACHE_KEY + '.parquet')
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b'old cache')
    assert lifecycle.available(tmp_path)
    with lifecycle.operation(tmp_path):
        snapshot = lifecycle.retain(tmp_path, replace_segments=True)
    assert not lifecycle.available(tmp_path)
    assert (snapshot / lifecycle.RECEIPT).is_file()
    assert (snapshot / lifecycle.SEGMENTS / 'roads.inslope.monotonic.geojson').is_file()
    assert (snapshot / cache.relative_to(tmp_path)).read_bytes() == b'old cache'
    assert not cache.exists()
    assert baseline.read_text() == 'baseline'
    assert lifecycle.path_owner(snapshot / lifecycle.RECEIPT) is None
    publish(tmp_path)
    assert lifecycle.available(tmp_path)


def test_receipt_never_admits_missing_required_resource(tmp_path):
    publish(tmp_path)
    (tmp_path / next(iter(lifecycle.mandatory_paths(False)))).unlink()
    assert not lifecycle.available(tmp_path)


def test_legacy_files_are_not_current(tmp_path):
    prepared(tmp_path)
    assert not lifecycle.available(tmp_path)


def test_read_lock_blocks_other_process_mutation(tmp_path):
    publish(tmp_path)
    context = multiprocessing.get_context('spawn')
    queue = context.Queue()
    with lifecycle.current_read(tmp_path):
        process = context.Process(target=_other_process_writer, args=(tmp_path, queue))
        process.start()
        assert queue.get(timeout=20) == 'busy'
        process.join(timeout=20)
        assert process.exitcode == 0


def test_duplicate_geometry_cannot_publish(tmp_path):
    resources = prepared(tmp_path)
    path = tmp_path / lifecycle.SEGMENTS / 'roads.inslope.monotonic.geojson'
    data = json.loads(path.read_text())
    data['features'] *= 2
    path.write_text(json.dumps(data))
    with lifecycle.operation(tmp_path), pytest.raises(ValueError, match='Duplicate'):
        lifecycle.publish(tmp_path, resources, single_storm=False)
    assert not lifecycle.available(tmp_path)


def test_failed_restore_revokes_receipt_preserves_lock_inode(tmp_path):
    publish(tmp_path)
    inode = (tmp_path / lifecycle.LOCK).stat().st_ino
    with pytest.raises(RuntimeError), lifecycle.restore_operation(tmp_path):
        raise RuntimeError('interrupted extraction')
    assert not lifecycle.available(tmp_path)
    assert (tmp_path / lifecycle.LOCK).stat().st_ino == inode


def test_cached_query_source_is_rejected_after_replacement(tmp_path):
    from wepppy.query_engine.executor import DuckDBExecutor
    from wepppy.query_engine.payload import QuerySource

    publish(tmp_path)
    path = tmp_path / lifecycle.OUTPUT / 'interchange/H.wat.parquet'
    source = QuerySource('water', str(path))
    executor = DuckDBExecutor(tmp_path)
    assert executor.execute('SELECT * FROM water', sources=[source]).num_rows == 1
    with lifecycle.operation(tmp_path):
        lifecycle.retain(tmp_path)
    # Even surviving files must not make an old plan executable.
    path.parent.mkdir(parents=True)
    pq.write_table(pa.table({'value': [99.0]}), path)
    with pytest.raises(lifecycle.RoadsResultsUnavailable):
        executor.execute('SELECT * FROM water', sources=[source])


def test_retained_link_is_materialized_before_its_target_moves(tmp_path):
    publish(tmp_path)
    runs = tmp_path / lifecycle.RUNS
    runs.mkdir()
    (runs / 'input.run').write_text('old input')
    linked = tmp_path / lifecycle.OUTPUT / 'input.run'
    linked.symlink_to(runs / 'input.run')
    with lifecycle.operation(tmp_path):
        snapshot = lifecycle.retain(tmp_path)
    retained = snapshot / linked.relative_to(tmp_path)
    assert not retained.is_symlink()
    assert retained.read_text() == 'old input'


def test_stream_keeps_admission_until_send_finishes(tmp_path):
    import asyncio
    from starlette.responses import FileResponse
    from wepppy.microservices.browse._roads import guarded_response

    publish(tmp_path)
    path = tmp_path / lifecycle.OUTPUT / 'interchange/README.md'
    async def exercise():
        async def build():
            return FileResponse(path)
        response = await guarded_response(path, build)
        # Same-process different descriptor still contends with the shared lock.
        with pytest.raises(lifecycle.RoadsOperationBusy), lifecycle.operation(tmp_path):
            pass
        messages = []
        async def send(message):
            messages.append(message)
            with pytest.raises(lifecycle.RoadsOperationBusy), lifecycle.operation(tmp_path):
                pass
        async def receive():
            return {'type': 'http.request'}
        await response({'type': 'http', 'method': 'GET', 'headers': []}, receive, send)
        assert any(message['type'] == 'http.response.body' for message in messages)
        with lifecycle.operation(tmp_path):
            pass
    asyncio.run(exercise())


def test_single_storm_receipt_includes_pass_accounting_without_wat(tmp_path):
    from wepppy.wepp.interchange import roads_accounting
    prepared(tmp_path)
    for relative in lifecycle.mandatory_paths(False) - lifecycle.mandatory_paths(True):
        (tmp_path / relative).unlink()
    ledger = {'policy': roads_accounting.POLICY, 'state': 'routed', 'area_basis': 'pass',
              'sources': [], 'targets': [], 'inputs': {}, 'canonical_pass': {}}
    digest = roads_accounting._allocation_digest(ledger)
    ledger.update(composition_allocation_sha256=digest, routed_allocation_sha256=digest)
    relative = str(lifecycle.SEGMENTS / 'roads.accounting.json')
    (tmp_path / relative).write_text(json.dumps(ledger))
    resources = {'required_relpaths': sorted(lifecycle.mandatory_paths(True)) + [relative]}
    with lifecycle.operation(tmp_path):
        lifecycle.publish(tmp_path, resources, single_storm=True)
    assert lifecycle.available(tmp_path)
    with lifecycle.restore_operation(tmp_path):
        pass
    ledger['sources'].append({'changed': True})
    (tmp_path / relative).write_text(json.dumps(ledger))
    with pytest.raises(ValueError), lifecycle.restore_operation(tmp_path):
        pass
    assert not lifecycle.available(tmp_path)


@pytest.mark.parametrize('damage', ['geometry', 'footer', 'body'])
def test_restore_rejects_incomplete_or_corrupt_generated_set(tmp_path, damage):
    publish(tmp_path)
    path = tmp_path / lifecycle.OUTPUT / 'interchange/H.pass.parquet'
    if damage == 'geometry':
        (tmp_path / lifecycle.SEGMENTS / 'roads.inslope.monotonic.geojson').unlink()
    elif damage == 'footer':
        path.write_bytes(b'broken parquet')
    else:
        data = bytearray(path.read_bytes())
        data[4:16] = b'\xff' * 12
        path.write_bytes(data)
        assert pq.read_metadata(path).num_rows == 1
    with pytest.raises((OSError, ValueError)), lifecycle.restore_operation(tmp_path):
        pass
    assert not lifecycle.available(tmp_path)


def test_partial_failure_retains_diagnostics_without_current_receipt(tmp_path):
    publish(tmp_path)
    class Controller:
        wd = str(tmp_path)
        @lifecycle.mutation
        def fail(self):
            lifecycle.retain(self.wd)
            path = tmp_path / lifecycle.OUTPUT / 'partial.log'
            path.parent.mkdir(parents=True)
            path.write_text('failure evidence')
            raise ValueError('model failed')
    with pytest.raises(ValueError, match='model failed'):
        Controller().fail()
    assert not lifecycle.available(tmp_path)
    snapshots = list((tmp_path / lifecycle.HISTORY).iterdir())
    assert any((path/lifecycle.OUTPUT/'partial.log').is_file() for path in snapshots)
    assert any((path/lifecycle.RECEIPT).is_file() for path in snapshots)


def test_first_creation_guard_does_not_depend_on_roads_directory(tmp_path):
    with lifecycle.operation(tmp_path, shared=True, create=True):
        assert not (tmp_path/'wepp/roads').exists()
        with pytest.raises(lifecycle.RoadsOperationBusy), lifecycle.operation(tmp_path):
            pass


def test_readonly_failed_restore_revokes_before_unlock(tmp_path):
    publish(tmp_path)
    folder = tmp_path/lifecycle.OUTPUT
    folder.chmod(0o555)
    try:
        with pytest.raises(RuntimeError, match='extraction failed'), lifecycle.restore_operation(tmp_path):
            raise RuntimeError('extraction failed')
        assert not (tmp_path/lifecycle.RECEIPT).exists()
        assert folder.stat().st_mode & 0o777 == 0o555
        assert not lifecycle.available(tmp_path)
    finally:
        folder.chmod(0o755)


def test_readonly_mutation_preserves_current_artifacts(tmp_path):
    publish(tmp_path)
    before = (tmp_path / lifecycle.RECEIPT).read_bytes()
    (tmp_path / 'READONLY').touch()

    class Controller:
        wd = str(tmp_path)

        @lifecycle.mutation
        def replace(self):
            lifecycle.retain(self.wd, replace_segments=True)

    with pytest.raises(PermissionError, match='readonly'):
        Controller().replace()
    assert (tmp_path / lifecycle.RECEIPT).read_bytes() == before
    assert lifecycle.available(tmp_path)
    assert not (tmp_path / lifecycle.HISTORY).exists()
