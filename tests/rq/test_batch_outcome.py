"""Real Redis, RQ timeout and filesystem publication, without running WEPP science."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import zipfile
from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from rq import Queue, SimpleWorker
from rq.job import Job

from tests.rq.test_batch_task_boundary import isolated_rq
from wepppy.rq import batch_outcome as outcome
from wepppy.rq import culvert_rq
from wepppy.rq.job_info import recursive_get_job_details

pytestmark = pytest.mark.integration


def write_outputs(root, run_id, job_id):
    run = root / 'runs' / run_id
    (run / 'wepp/output/interchange').mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({'value': list(range(11))}), run / 'wepp/output/interchange/loss_pw0.out.parquet')
    (run / 'dem/wbt').mkdir(parents=True, exist_ok=True)
    for name in ['subcatchments', 'channels']:
        (run / f'dem/wbt/{name}.WGS.geojson').write_text(json.dumps({'type':'FeatureCollection','features':[
            {'type':'Feature','properties':{'Point_ID':run_id}, 'geometry':{'type':'Point','coordinates':[1,2]}}]}))
    (run / 'run_metadata.json').write_text(json.dumps({'status':'success','rq_job_id':job_id}))


@pytest.fixture
def attempt(isolated_rq, tmp_path, monkeypatch, request):
    monkeypatch.setenv('CULVERTS_ROOT', str(tmp_path))
    root = tmp_path / 'project'
    root.mkdir()
    job = Job.create('wepppy.rq.culvert_rq.run_culvert_batch_rq', args=('project',), connection=isolated_rq)
    job.meta['culvert_batch_uuid'] = 'project'
    job.save()
    job.set_status('started')
    run_ids = ['good', *[f'good-{i}' for i in range(1, getattr(request, 'param', 1))], 'bad']
    outcome.enroll(job, run_ids)
    leaves = []
    for rid in run_ids:
        leaf = Job.create('wepppy.rq.culvert_rq.run_culvert_run_rq', args=(f'culvert;;project;;{rid}','project',rid), connection=isolated_rq)
        leaf.save()
        leaf.set_status('failed' if rid == 'bad' else 'finished')
        outcome.register(job, member=rid, jobs=[leaf.id])
        write_outputs(root, rid, leaf.id)
        leaves.append(leaf)
    finalizer = Job.create('wepppy.rq.culvert_rq._final_culvert_batch_complete_rq',args=('project',),connection=isolated_rq,meta={'batch_outcome_root_id':job.id})
    finalizer.save()
    finalizer.set_status('started')
    outcome.register(job, finalizer=finalizer.id)
    job.set_status('finished')
    return job, finalizer, leaves, root


def test_partial_archive_and_polling(attempt):
    job, finalizer, leaves, root = attempt
    result = outcome.publish(finalizer)
    assert result['outcome'] == 'partial_success'
    assert result['succeeded'] == result['failed'] == 1
    assert outcome.poll(job) == result
    detail = recursive_get_job_details(job, job.connection, datetime.now(timezone.utc))
    assert detail['batch'] == result
    with zipfile.ZipFile(root / 'batch_results' / job.id / 'results.zip') as archive:
        assert not any(name.startswith('runs/bad/') for name in archive.namelist())
        manifest = json.loads(archive.read('runs.json'))
        assert {row['run_id']:row['status'] for row in manifest['runs']} == {'good':'success','bad':'failed'}
        pq.read_table(pa.BufferReader(archive.read('runs/good/wepp/output/interchange/loss_pw0.out.parquet')))
    assert (root / 'runs/bad/run_metadata.json').exists()


def test_dispatch_registration_race_is_nonterminal(attempt):
    job, finalizer, _, root = attempt
    job.set_status('started')
    finalizer.delete()
    assert outcome.poll(job)['state'] == 'running'
    assert not (root / 'batch_results' / job.id / 'summary.json').exists()


def test_corrupt_success_and_stale_receipt_excluded(attempt):
    job, finalizer, _, root = attempt
    (root / 'runs/good/wepp/output/interchange/loss_pw0.out.parquet').write_bytes(b'corrupt')
    assert outcome.publish(finalizer)['results_available'] is False


def test_packaging_failure_and_crash_settles(attempt, monkeypatch):
    job, finalizer, _, root = attempt
    def fail(*args, **kwargs):
        raise OSError('disk full')
    monkeypatch.setattr(zipfile.ZipFile, 'writestr', fail)
    with pytest.raises(OSError, match="disk full"):
        outcome.publish(finalizer)
    finalizer.set_status('failed')
    assert outcome.poll(job)['reason'] == 'finalization_failed'


def test_foreign_symlink_not_bundled(attempt, tmp_path):
    job, finalizer, _, root = attempt
    target = tmp_path / 'private.parquet'
    target.write_bytes(b'private')
    (root / 'runs/good/wepp/output/interchange/foreign.parquet').symlink_to(target)
    assert outcome.publish(finalizer)['results_available'] is False


def test_stale_finalizer_cannot_publish(attempt):
    job, finalizer, _, root = attempt
    outcome.invalidate_culvert('project')
    with pytest.raises(ValueError, match='Superseded'):
        outcome.publish(finalizer)


def test_summary_cannot_inject_url(attempt):
    job, finalizer, _, root = attempt
    result = outcome.publish(finalizer)
    result['download_url'] = 'https://attacker.invalid/'
    outcome.atomic_json(root / 'batch_results' / job.id / 'summary.json', result)
    with pytest.raises(outcome.BatchReconciliationUnavailable):
        outcome.poll(job)


def timeout_leaf(*args):
    time.sleep(3)


def publish_current_finalizer(*args):
    from rq import get_current_job
    return outcome.publish(get_current_job())


@pytest.mark.parametrize('attempt', [32], indirect=True)
def test_real_timeout_retains_success_and_publishes(attempt, monkeypatch):
    job, finalizer, leaves, root = attempt
    monkeypatch.setattr(culvert_rq, 'run_culvert_run_rq', timeout_leaf)
    queue = Queue('batch', connection=job.connection)
    timed = queue.enqueue_call('wepppy.rq.culvert_rq.run_culvert_run_rq', args=('culvert;;project;;bad','project','bad'), timeout=1, result_ttl=-1)
    outcome.register(job, member='bad', jobs=[timed.id])
    monkeypatch.setattr(culvert_rq, '_final_culvert_batch_complete_rq', publish_current_finalizer)
    from rq.job import Dependency
    finalizer = queue.enqueue_call('wepppy.rq.culvert_rq._final_culvert_batch_complete_rq',
        args=('project',), depends_on=Dependency(jobs=[*leaves[:-1], timed], allow_failure=True),
        meta={'batch_outcome_root_id': job.id}, result_ttl=-1)
    outcome.register(job, finalizer=finalizer.id)
    assert finalizer.get_status() == 'deferred'
    SimpleWorker([queue], connection=job.connection).work(burst=True)
    assert finalizer.get_status(refresh=True) == 'finished'
    timed.refresh()
    assert timed.get_status() == 'failed'
    assert 'JobTimeoutException' in timed.exc_info
    result = outcome.poll(job)
    assert result['outcome'] == 'partial_success'
    assert result['succeeded'] == 32 and result['failed'] == 1


def test_canceled_with_unused_retries_settles(attempt):
    job, finalizer, _, _ = attempt
    finalizer.retries_left = 3
    finalizer.save()
    finalizer.set_status('canceled')
    assert outcome.poll(job)['reason'] == 'canceled'


def test_stale_success_receipt_is_not_reused(attempt):
    job, finalizer, _, root = attempt
    (root / 'runs/good/run_metadata.json').write_text(json.dumps({'status':'success','rq_job_id':'old'}))
    assert outcome.publish(finalizer)['succeeded'] == 0


def test_old_enrollment_cannot_reclaim_pointer(attempt):
    job, finalizer, _, root = attempt
    outcome.publish(finalizer)
    outcome.atomic_json(root / 'batch_results/current.json', {'attempt_id':'successor'})
    with pytest.raises(ValueError, match='Superseded'):
        outcome.enroll(job, ['good','bad'])
    assert json.loads((root / 'batch_results/current.json').read_text())['attempt_id'] == 'successor'


def test_safe_logical_components():
    for value in ['_culvert', 'site 1', 'échantillon']:
        assert outcome.component(value) == value
    for value in ['..','a/b','a\\b','a\x00b']:
        with pytest.raises(ValueError):
            outcome.component(value)


@pytest.fixture
def ordinary_graph(isolated_rq, tmp_path, monkeypatch):
    monkeypatch.setenv('BATCH_RUNNER_ROOT', str(tmp_path))
    root = tmp_path / 'ordinary'
    root.mkdir()
    connection = isolated_rq
    queue = Queue('batch', connection=connection)
    job = Job.create('wepppy.rq.batch_rq.run_batch_rq', args=('ordinary',), connection=connection)
    job.save()
    job.set_status('finished')
    outcome.enroll(job, ['good','bad'])
    leaves = []
    for rid in ['good','bad']:
        leaf = Job.create('wepppy.rq.batch_rq.run_batch_watershed_rq',args=('ordinary', SimpleNamespace(runid=rid), 'upstream'),connection=connection,
                          meta={'batch_root_job_id':job.id,'runid':f'batch;;ordinary;;{rid}'})
        leaf.save()
        leaf.set_status('finished')
        outcome.register(job, member=rid, jobs=[leaf.id])
        write_outputs(root, rid, leaf.id)
        leaves.append(leaf)
    scenario = Job.create('wepppy.rq.omni_rq.run_omni_scenario_rq', args=('batch;;ordinary;;bad', {}), connection=connection,
                          meta={'batch_root_job_id':job.id})
    scenario.save()
    scenario.set_status('failed')
    compile_job = queue.enqueue_call('wepppy.rq.omni_rq._compile_hillslope_summaries_rq',args=('batch;;ordinary;;bad',),depends_on=scenario,
                                    meta={'batch_root_job_id':job.id})
    omni_final = queue.enqueue_call('wepppy.rq.omni_rq._finalize_omni_scenarios_rq',args=('batch;;ordinary;;bad',),depends_on=compile_job,
                                   meta={'batch_root_job_id':job.id})
    leaves[1].meta.update({'jobs:1,scenario':scenario.id,'jobs:2,compile':compile_job.id,'jobs:3,final':omni_final.id})
    leaves[1].save_meta()
    from rq.job import Dependency
    finalizer = queue.enqueue_call('wepppy.rq.batch_rq._final_batch_complete_rq', args=('ordinary',),
                                   depends_on=Dependency(jobs=[*leaves,omni_final],allow_failure=True),
                                   meta={'batch_root_job_id':job.id})
    outcome.register(job, finalizer=finalizer.id)
    return job, finalizer, scenario, compile_job, omni_final, root


def test_ordinary_omni_failure_releases_batch(ordinary_graph):
    job, finalizer, scenario, compile_job, omni_final, root = ordinary_graph
    assert finalizer.get_status() == 'deferred'
    assert outcome.poll(job)['results_available'] is False
    assert compile_job.get_status(refresh=True) == 'canceled'
    assert omni_final.get_status(refresh=True) == 'canceled'
    assert finalizer.get_status(refresh=True) == 'queued'
    assert outcome.publish(finalizer)['outcome'] == 'partial_success'


def test_missing_culvert_execution_settles(attempt):
    job, finalizer, leaves, _ = attempt
    leaves[0].delete()
    assert outcome.poll(job)['reason'] == 'execution_record_missing'


def test_copied_enrollment_rejected(attempt):
    job, finalizer, _, root = attempt
    path = root / 'batch_results' / job.id / 'enrollment.json'
    enrollment = json.loads(path.read_text())
    enrollment['resource'] = 'foreign'
    outcome.atomic_json(path, enrollment)
    with pytest.raises(outcome.BatchReconciliationUnavailable):
        outcome.poll(job)


def test_optional_empty_parquet_is_valid(attempt):
    job, finalizer, _, root = attempt
    pq.write_table(pa.table({'event': pa.array([],type=pa.int32())}), root / 'runs/good/wepp/output/interchange/events.parquet')
    assert outcome.publish(finalizer)['succeeded'] == 1


def test_source_swap_never_enters_working_archive(attempt, monkeypatch, tmp_path):
    job, finalizer, _, root = attempt
    original = outcome.output_files
    private = tmp_path / 'private.parquet'
    private.write_bytes(b'PRIVATE_CANARY')
    def swap(*args, **kwargs):
        files = original(*args, **kwargs)
        path = files[0][1]
        path.unlink()
        path.symlink_to(private)
        return files
    monkeypatch.setattr(outcome, 'output_files', swap)
    with pytest.raises(ValueError):
        outcome.publish(finalizer)
    working = next((root / 'batch_results' / job.id).glob('results.working-*.zip'))
    with zipfile.ZipFile(working) as archive:
        assert all(b'PRIVATE_CANARY' not in archive.read(name) for name in archive.namelist())


from tests.microservices.test_browse_auth_routes import load_secure_browse, _issue_service_token


def test_http_poll_download_and_project_inspection(attempt, monkeypatch, load_secure_browse):
    from fastapi import FastAPI
    from starlette.testclient import TestClient
    from wepppy.rq import job_info
    from wepppy.microservices.rq_engine import job_routes
    import wepppy.config.redis_settings as settings
    job, finalizer, leaves, root = attempt
    job.meta.update({'jobs:0,good': leaves[0].id, 'jobs:0,bad': leaves[1].id, 'jobs:1,final': finalizer.id})
    job.save_meta()
    expected = outcome.publish(finalizer)
    finalizer.set_status('finished')
    kwargs = {'unix_socket_path': job.connection.connection_pool.connection_kwargs['path']}
    monkeypatch.setattr(job_info, 'redis_connection_kwargs', lambda *args: kwargs)
    monkeypatch.setattr(settings, 'redis_connection_kwargs', lambda *args: kwargs)
    monkeypatch.setenv('RQ_ENGINE_POLL_AUTH_MODE','open')
    app = FastAPI()
    app.include_router(job_routes.router)
    with TestClient(app) as client:
        for route in ['jobinfo', 'jobstatus']:
            response = client.get(f'/{route}/{job.id}')
            assert response.status_code == 200, response.text
            assert response.json()['batch'] == expected
        assert client.get(f'/jobstatus/{job.id}').json()['status'] == 'failed'
    browse = load_secure_browse({}, CULVERTS_ROOT=str(root.parent))
    from wepppy.microservices.browse import auth as browse_auth
    monkeypatch.setattr(browse_auth, 'redis_connection_kwargs', lambda *args: kwargs)
    token = _issue_service_token('project',service_groups=['culverts'])
    with TestClient(browse.create_app()) as client:
        response = client.get(expected['download_url'], headers={'Authorization':f'Bearer {token}'})
        assert response.status_code == 200, response.text
        import io
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert not any(name.startswith('runs/bad/') for name in archive.namelist())
        foreign = _issue_service_token('foreign', service_groups=['culverts'])
        assert client.get(expected['download_url'],headers={'Authorization':f'Bearer {foreign}'}).status_code == 403
        view = client.get('/weppcloud/culverts/project/browse/batch_results/',headers={'Authorization':f'Bearer {token}'})
        assert view.status_code == 200, view.text
        status_view = client.get(f'/weppcloud/culverts/project/download/batch_results/{job.id}/summary.json',headers={'Authorization':f'Bearer {token}'})
        assert status_view.json() == expected


from tests.rq.test_project_rq_archive import archive_rq_environment


def test_canonical_archive_restore_preserves_attempt(attempt, archive_rq_environment):
    job, finalizer, _, root = attempt
    outcome.publish(finalizer)
    directory = root / 'batch_results' / job.id
    expected = {path.name:path.read_bytes() for path in directory.iterdir() if path.is_file()}
    project, _, _, _ = archive_rq_environment
    project.archive_rq('project',comment='batch outcome acceptance')
    archive = next((root / 'archives').glob('*.zip'))
    for name in expected:
        (directory / name).unlink()
    project.restore_archive_rq('project',archive.name)
    assert {name:(directory / name).read_bytes() for name in expected} == expected


def test_existing_working_symlink_is_not_followed(attempt, tmp_path):
    job, finalizer, _, root = attempt
    target = tmp_path / 'keep.txt'
    target.write_text('KEEP')
    (root / 'batch_results' / job.id / 'results.working.zip').symlink_to(target)
    assert outcome.publish(finalizer)['results_available']
    assert target.read_text() == 'KEEP'


@pytest.mark.parametrize('corruption',['foreign_root','foreign_dependent','dependency_set'])
def test_omni_foreign_graph_has_no_mutation(ordinary_graph, corruption):
    job, finalizer, scenario, compile_job, omni_final, _ = ordinary_graph
    if corruption == 'foreign_root':
        scenario.meta['batch_root_job_id'] = 'foreign'
        scenario.save_meta()
    elif corruption == 'foreign_dependent':
        job.connection.sadd(compile_job.dependents_key,'foreign')
    else:
        job.connection.sadd(compile_job.dependencies_key,'foreign')
    with pytest.raises(outcome.BatchReconciliationUnavailable):
        outcome.poll(job)
    assert compile_job.get_status(refresh=True) == 'deferred'
    assert omni_final.get_status(refresh=True) == 'deferred'
    assert finalizer.get_status(refresh=True) == 'deferred'


@pytest.mark.parametrize('single_storm',[False,True])
def test_ordinary_climate_appropriate_hillslope_output(ordinary_graph, monkeypatch, single_storm):
    from wepppy.nodb.core import Climate
    job, finalizer, _, _, _, root = ordinary_graph
    path = root / 'batch_results' / job.id / 'enrollment.json'
    enrollment = json.loads(path.read_text())
    enrollment['hillslopes'] = True
    outcome.atomic_json(path,enrollment)
    monkeypatch.setattr(Climate,'getInstance',lambda *args: SimpleNamespace(is_single_storm=single_storm))
    from wepppy.wepp.interchange.hill_pass_interchange import SCHEMA
    row = {field.name: 'EVENT' if pa.types.is_string(field.type) else 1 for field in SCHEMA}
    pq.write_table(pa.Table.from_pylist([row], schema=SCHEMA), root / 'runs/good/wepp/output/interchange/H.pass.parquet')
    outcome.poll(job)
    result = outcome.publish(finalizer)
    assert result['succeeded'] == int(single_storm)


def test_hidden_leaf_member_policy(attempt):
    job, _, _, root = attempt
    write_outputs(root,'_logs','source')
    enrollment = outcome.enrollment_for(root,job)
    with pytest.raises(ValueError, match='Restricted'):
        outcome.output_files(root,enrollment,'_logs')


@pytest.mark.parametrize('target', ['receipt','geometry','feature'])
def test_malformed_json_shapes_fail_only_member(attempt, target):
    job, finalizer, _, root = attempt
    if target == 'receipt':
        path = root / 'runs/good/run_metadata.json'
        value = []
    else:
        path = root / 'runs/good/dem/wbt/subcatchments.WGS.geojson'
        value = [] if target == 'geometry' else {'type':'FeatureCollection','features':['invalid']}
    path.write_text(json.dumps(value))
    result = outcome.publish(finalizer)
    assert result['state'] == 'completed' and result['succeeded'] == 0


def test_cancel_before_publication_cannot_advertise_success(attempt):
    from wepppy.rq.cancel_job import _cancel_job_recursive
    job, finalizer, _, root = attempt
    _cancel_job_recursive(job, job.connection)
    result = outcome.publish(finalizer)
    assert result['state'] == 'failed' and result['reason'] == 'canceled'
    assert not (root / 'batch_results' / job.id / 'results.zip').exists()


def test_cancellation_serializes_with_publication(attempt, monkeypatch):
    import threading
    from wepppy.rq.cancel_job import _cancel_job_recursive
    job, finalizer, _, root = attempt
    started, completed = threading.Event(), threading.Event()
    def cancel():
        started.set()
        _cancel_job_recursive(Job.fetch(job.id,connection=job.connection),job.connection)
        completed.set()
    original = outcome.output_files
    threads = []
    def observe(*args, **kwargs):
        thread = threading.Thread(target=cancel)
        threads.append(thread)
        thread.start()
        assert started.wait(2)
        assert completed.wait(2)
        return original(*args, **kwargs)
    monkeypatch.setattr(outcome, 'output_files', observe)
    result = outcome.publish(finalizer)
    for thread in threads:
        thread.join(5)
    assert completed.is_set()
    assert result['results_available'] is False
    assert result['reason'] == 'canceled'
    manifest = json.loads((root / 'batch_results' / job.id / 'runs.json').read_text())
    assert all(row['status'] == 'failed' for row in manifest['runs'])
    assert len(manifest['runs']) == result['failed']
    assert not (root / 'batch_results' / job.id / 'results.zip').exists()
    assert job.get_status(refresh=True) == 'canceled'


def test_wrong_schema_ordinary_required_output_rejected(ordinary_graph):
    job, finalizer, _, _, _, root = ordinary_graph
    pq.write_table(pa.table({'unrelated':[1]}),root / 'runs/good/wepp/output/interchange/loss_pw0.out.parquet')
    outcome.poll(job)
    assert outcome.publish(finalizer)['succeeded'] == 0


@pytest.mark.parametrize('attempt', [3], indirect=True)
def test_production_finalizer_isolates_malformed_member(attempt, monkeypatch):
    job, finalizer, leaves, root = attempt
    runner = culvert_rq.CulvertsRunner(str(root), 'culvert.cfg')
    with runner.locked():
        runner._runs = {leaf.args[2]: {'wd': str(root / 'runs' / leaf.args[2])} for leaf in leaves}
    (root / 'runs/good/run_metadata.json').write_text('[]')
    (root / 'runs/bad/dem/wbt/outlet.geojson').write_text('{"features":["invalid"]}')
    monkeypatch.setattr(culvert_rq, 'get_current_job', lambda: finalizer)
    result = culvert_rq._final_culvert_batch_complete_rq('project')
    assert result['succeeded'] == 2 and result['failed'] == 2
    assert outcome.poll(job)['results_available'] is True
    assert (root / 'runs_manifest.md').is_file()
    with zipfile.ZipFile(root / 'batch_results' / job.id / 'results.zip') as archive:
        ids = {name.split('/')[1] for name in archive.namelist() if name.startswith('runs/')}
    assert ids == {'good-1', 'good-2'}


def test_cancel_http_during_publication(attempt, monkeypatch):
    from fastapi import FastAPI
    from starlette.testclient import TestClient
    from wepppy.rq import job_info, cancel_job
    from wepppy.microservices.rq_engine import job_routes
    job, finalizer, _, root = attempt
    kwargs = {'unix_socket_path': job.connection.connection_pool.connection_kwargs['path']}
    monkeypatch.setattr(job_info, 'redis_connection_kwargs', lambda *args: kwargs)
    monkeypatch.setattr(cancel_job, 'redis_connection_kwargs', lambda *args: kwargs)
    # Identity/grant fixtures isolate access policy; real route, job tree, Redis,
    # shared cancellation lease and publisher execute unchanged.
    monkeypatch.setattr(job_routes, '_authorize_cancel_request', lambda request: ({'token_class':'service'}, frozenset({'culvert:batch:submit'})))
    monkeypatch.setattr(job_routes, 'require_feature_access', lambda *args, **kwargs: None)
    app = FastAPI()
    app.include_router(job_routes.router)
    original = outcome.output_files
    def cancel_during_read(*args, **kwargs):
        with TestClient(app) as client:
            response = client.post(f'/canceljob/{job.id}')
        assert response.status_code == 200, response.text
        assert outcome.poll(Job.fetch(job.id, connection=job.connection))['reason'] == 'canceled'
        return original(*args, **kwargs)
    monkeypatch.setattr(outcome, 'output_files', cancel_during_read)
    result = outcome.publish(finalizer)
    assert result['reason'] == 'canceled' and result['results_available'] is False
    assert not (root / 'batch_results' / job.id / 'results.zip').exists()


def test_cancel_between_registration_and_enqueue_prevents_orphan(attempt, monkeypatch):
    from wepppy.rq import culvert_rq_pipeline as pipeline
    from wepppy.rq.cancel_job import _cancel_job_recursive
    job, _, _, root = attempt
    job.set_status('started')
    original = outcome.register
    def cancel_after_registration(*args, **kwargs):
        original(*args, **kwargs)
        _cancel_job_recursive(job, job.connection)
    monkeypatch.setattr(outcome, 'register', cancel_after_registration)
    queue = Queue('cancel-dispatch', connection=job.connection)
    with pytest.raises(RuntimeError, match='canceled'):
        pipeline._enqueue(queue, job, key='jobs:0,good',
                          func=culvert_rq.run_culvert_run_rq,
                          args=('culvert;;project;;good', 'project', 'good'),
                          depends_on=job.id, child_meta={'run_id':'good'})
    enrollment = outcome.enrollment_for(root, job)
    assert Job.exists(enrollment['members']['good'][0], connection=job.connection) is False
    assert queue.count == 0 and queue.deferred_job_registry.count == 0


def test_concurrent_publisher_cannot_replace_committed_manifest(attempt, monkeypatch):
    job, finalizer, _, root = attempt
    original = outcome.output_files
    inner = []
    def publish_first(*args, **kwargs):
        monkeypatch.setattr(outcome, 'output_files', original)
        inner.append(outcome.publish(finalizer))
        raise ValueError('second observer found changed output')
    monkeypatch.setattr(outcome, 'output_files', publish_first)
    result = outcome.publish(finalizer)
    assert result == inner[0]
    directory = root / 'batch_results' / job.id
    with zipfile.ZipFile(directory / 'results.zip') as archive:
        assert json.loads(archive.read('runs.json')) == json.loads((directory / 'runs.json').read_text())


def test_cancel_refreshes_children_linked_after_initial_fetch(attempt):
    import threading
    from wepppy.rq.cancel_job import _cancel_job_recursive
    job, _, _, _ = attempt
    stale = Job.fetch(job.id, connection=job.connection)
    entered, completed = threading.Event(), threading.Event()
    def cancel():
        entered.set()
        _cancel_job_recursive(stale, job.connection)
        completed.set()
    with outcome.dispatch(job):
        thread = threading.Thread(target=cancel)
        thread.start()
        assert entered.wait(2)
        child = Job.create('wepppy.rq.culvert_rq.run_culvert_run_rq',
                           args=('culvert;;project;;new', 'project', 'new'), connection=job.connection)
        child.save()
        child.set_status('queued')
        job.meta['jobs:0,new'] = child.id
        job.save_meta()
        assert not completed.wait(0.1)
    thread.join(5)
    assert completed.is_set()
    assert child.get_status(refresh=True) == 'canceled'
    job.refresh()
    assert job.meta['jobs:0,new'] == child.id
