"""Records survive failures, retries, legacy relocation and explicit recovery."""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from wepppy.nodb.mods.postfire_debris_flow import migration as m, observability as o, preflight
from wepppy.nodb.mods.postfire_debris_flow import production as p
from wepppy.nodb.mods.postfire_debris_flow.postfire_debris_flow import PostfireDebrisFlow

pytestmark = pytest.mark.unit


@pytest.fixture
def legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, 'notify', lambda wd: None)
    monkeypatch.setattr(p, 'engine_identity', lambda: deepcopy(m.TARGET_ENGINE))
    controller = PostfireDebrisFlow(str(tmp_path), 'disturbed9002_wbt.cfg')
    @contextmanager
    def admission(obj):
        obj.lock()
        try:
            yield SimpleNamespace(checkpoint=lambda: None)
        finally:
            obj.unlock()
    monkeypatch.setattr(m, '_admission', admission)  # Redis boundary only; real NoDb/filesystem.
    root = tmp_path/'postfire_debris_flow'
    attempt = root/'.staging'/('a'*32)
    attempt.mkdir(parents=True)
    external = tmp_path/'dem.tif'; external.write_bytes(b'original dem')
    source = attempt/'source.img'; source.write_bytes(b'original raster')
    normalized = attempt/'normalized.json'
    o.write_json(normalized, {'source': str(source), 'sha256': p.digest(source), 'f': .275})
    predictors = attempt/'predictors.json'
    o.write_json(predictors, {'normalized': p.digest(normalized), 'path': str(normalized), 't': .5})
    result = attempt/'results'; result.mkdir()
    for name in p.FILES[:-1]:
        (result/name).write_bytes(b'unchanged table '+name.encode())
    o.write_json(result/'manifest.json', {'predictor_sha256': p.digest(predictors), 'path': str(predictors),
                                         'probability': .6})
    hidden = attempt/'.dnbr-old'; hidden.mkdir(); (hidden/'.partial').write_bytes(b'failed bytes')
    (attempt/'invalid.json').write_bytes(b'{truncated diagnostic')
    artifacts = lambda files: {str(file.relative_to(tmp_path)): p.signature(tmp_path,file,strong=True) for file in files}
    snapshot = {'inputs': {'selections': {'engine_sha256': deepcopy(m.LEGACY_ENGINE)}}}
    with controller.locked():
        controller._state.update(active_dnbr={'id':'a'*32,'snapshot':{},'artifacts':artifacts([source,normalized,external])},
            run_attempt={'id':'a'*32,'phase':'complete','created_at':p.now(),'retryable':False,'snapshot':deepcopy(snapshot)},
            last_successful_run={'id':'a'*32,'snapshot':deepcopy(snapshot), 'artifacts':artifacts(result.iterdir()),
                                 'predictor_artifacts':artifacts([predictors, external])})
    return controller, root, attempt, external


def test_migration_preserves_payloads_and_rebases_hash_dag(legacy):
    controller, root, old, external = legacy
    prior = controller.state
    report = m.migrate_attempts(controller.wd)
    assert report['status'] == 'complete'
    controller = PostfireDebrisFlow.load_detached(controller.wd)
    new = root/'attempts'/('a'*32)
    assert not (root/'.staging').exists()
    assert not any(part.startswith('.') for file in root.rglob('*') for part in file.relative_to(root).parts)
    assert (new/'source.img').read_bytes() == b'original raster'
    assert (new/'legacy_dnbr-old'/'legacy_partial').read_bytes() == b'failed bytes'
    assert (new/'invalid.json').read_bytes() == b'{truncated diagnostic'
    normalized = json.loads((new/'normalized.json').read_text())
    predictors = json.loads((new/'predictors.json').read_text())
    manifest = json.loads((new/'results'/'manifest.json').read_text())
    assert normalized['source'] == str(new/'source.img')
    assert predictors['normalized'] == p.digest(new/'normalized.json')
    assert manifest['predictor_sha256'] == p.digest(new/'predictors.json')
    assert manifest['probability'] == .6
    assert controller.state['last_successful_run']['snapshot']['inputs']['selections']['engine_sha256'] == m.TARGET_ENGINE
    assert controller.state['active_dnbr']['artifacts']['dem.tif'] == prior['active_dnbr']['artifacts']['dem.tif']
    for key in ('active_dnbr','last_successful_run'):
        assert p.artifacts_current(controller.wd, controller.state[key])
    for name in p.FILES:
        assert (root/name).read_bytes() == (new/'results'/name).read_bytes()
    assert json.loads((new/'status.json').read_text())['attempt']['phase'] == 'complete'
    assert m.migrate_attempts(controller.wd)['status'] == 'already_visible'


@pytest.mark.parametrize('failure', ['root_rename','nested_rename','metadata','state'])
def test_interrupted_migration_can_resume(legacy, monkeypatch, failure):
    controller, root, old, _ = legacy
    with monkeypatch.context() as patch:
        if failure == 'root_rename':
            original = m.os.rename
            def stop(src,dst):
                original(src,dst)
                raise OSError('stopped root rename')
            patch.setattr(m.os,'rename',stop)
        elif failure == 'nested_rename':
            original = Path.rename
            def stop(path,dst):
                result = original(path,dst)
                raise OSError('stopped nested rename')
            patch.setattr(Path,'rename',stop)
        elif failure == 'metadata':
            original = m.os.replace
            def stop(src,dst):
                if str(src).endswith('.migration-pending'):
                    original(src,dst)
                    raise OSError('stopped metadata')
                return original(src,dst)
            patch.setattr(m.os,'replace',stop)
        else:
            patch.setattr(PostfireDebrisFlow,'dump',lambda self: (_ for _ in ()).throw(OSError('stopped state')))
        with pytest.raises(OSError, match='stopped'):
            m.migrate_attempts(controller.wd)
    audit = next((root/'migrations').iterdir())
    # Reload persisted state after an interrupted dump, as a real new process does.
    controller._state = PostfireDebrisFlow.load_detached(controller.wd).state
    assert m.migrate_attempts(controller.wd,resume=audit.name)['status'] == 'complete'


@pytest.mark.parametrize('damage', ['external','binary','plan','hash_map'])
def test_resume_rejects_changed_evidence(legacy, monkeypatch, damage):
    controller, root, old, external = legacy
    prior = controller.state
    original = m.os.rename
    def stop(src,dst):
        original(src,dst)
        raise OSError('stop')
    with monkeypatch.context() as patch:
        patch.setattr(m.os,'rename',stop)
        with pytest.raises(OSError): m.migrate_attempts(controller.wd)
    audit = next((root/'migrations').iterdir())
    if damage == 'external': external.write_bytes(b'changed dem')
    elif damage == 'binary': (root/'attempts'/('a'*32)/'source.img').write_bytes(b'changed raster')
    elif damage == 'plan': next((audit/'rebased_metadata').rglob('normalized.json')).write_text('{}')
    else:
        report = json.loads((audit/'migration.json').read_text())
        report['hashes']['arbitrary-model-value'] = 'replacement'
        o.write_json(audit/'migration.json',report)
    with pytest.raises(ValueError, match='changed'):
        m.migrate_attempts(controller.wd,resume=audit.name)
    assert controller.state == prior


def test_unknown_engine_remains_stale(legacy):
    controller, root, old, external = legacy
    with controller.locked():
        controller._state['last_successful_run']['snapshot']['inputs']['selections']['engine_sha256'] = {'unknown': 'version'}
    report = m.migrate_attempts(controller.wd)
    assert 'last_successful_run' not in report['upgraded_engine_records']
    assert PostfireDebrisFlow.load_detached(controller.wd).state['last_successful_run']['snapshot']['inputs']['selections']['engine_sha256'] == {'unknown': 'version'}


def test_mixed_tree_and_legacy_writes_rejected(legacy):
    controller, root, old, _ = legacy
    with pytest.raises(p.WorkflowError, match='migration'):
        controller.change(lambda state: state.update(frequency_source='noaa'))
    assert not (root/'attempts').exists()
    (root/'attempts').mkdir()
    with pytest.raises(ValueError, match='Both legacy'):
        m.migrate_attempts(controller.wd)


def test_receipt_and_traceback_survive_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight,'notify',lambda wd: None)
    controller = PostfireDebrisFlow(str(tmp_path),'disturbed9002_wbt.cfg')
    record = {'id':'a'*32,'phase':'failed','snapshot':{},'created_at':p.now(),'retryable':False,'job_id':'original-job','error':{'code':'invalid_raster'}}
    controller.change(lambda state: state.update(upload_attempt=record))
    try:
        raise ValueError('invalid raster example')
    except ValueError:
        o.record_error(tmp_path,record['id'])
    controller.change(lambda state: state.update(upload_attempt={'id':'b'*32,'phase':'complete','snapshot':{},'created_at':p.now(),'retryable':False}))
    root = p.directory(tmp_path,'a'*32)
    assert json.loads((root/'status.json').read_text())['attempt'] == record
    assert 'invalid raster example' in (root/'error.log').read_text()
    assert json.loads((p.directory(tmp_path,'b'*32)/'status.json').read_text())['attempt']['phase']=='complete'


def test_preparation_failure_retains_status_without_relocating(legacy,monkeypatch):
    controller, root, old, _ = legacy
    monkeypatch.setattr(m.shutil,'copyfile',lambda *args: (_ for _ in ()).throw(OSError('backup failed')))
    with pytest.raises(OSError,match='backup failed'):
        m.migrate_attempts(controller.wd)
    audit = next((root/'migrations').iterdir())
    assert json.loads((audit/'status.json').read_text())['status']=='preparing'
    assert old.exists() and not (root/'attempts').exists()


@pytest.mark.parametrize('phase', ['staged','queued','running','enqueue_unknown'])
def test_active_record_rejects_migration(phase):
    with pytest.raises(ValueError,match='active'):
        m._jobs_idle({'upload_attempt':{'phase':phase},'run_attempt':None},'run',None)


def test_resume_does_not_trust_report_planned_state(legacy,monkeypatch):
    controller, root, old, _ = legacy
    original = m.os.rename
    def stop(src,dst):
        original(src,dst)
        raise OSError('stop')
    with monkeypatch.context() as patch:
        patch.setattr(m.os,'rename',stop)
        with pytest.raises(OSError): m.migrate_attempts(controller.wd)
    audit = next((root/'migrations').iterdir())
    report = json.loads((audit/'migration.json').read_text())
    report['original_state']['frequency_source']='noaa'
    report['planned_state']=controller.state
    o.write_json(audit/'original_metadata'/'state.json',report['original_state'])
    o.write_json(audit/'migration.json',report)
    with pytest.raises(ValueError,match='NoDb backup'):
        m.migrate_attempts(controller.wd,resume=audit.name)


@pytest.mark.parametrize('tamper',['omit','forge'])
def test_accepted_inventory_is_anchored_to_original_nodb(legacy,monkeypatch,tamper):
    controller, root, old, _ = legacy
    original = m.os.rename
    def stop(src,dst):
        original(src,dst)
        raise OSError('stop')
    with monkeypatch.context() as patch:
        patch.setattr(m.os,'rename',stop)
        with pytest.raises(OSError): m.migrate_attempts(controller.wd)
    audit = next((root/'migrations').iterdir())
    report = json.loads((audit/'migration.json').read_text())
    rel = '.staging/'+('a'*32)+'/source.img'
    if tamper == 'omit':
        del report['inventory'][rel]
    else:
        source = root/'attempts'/('a'*32)/'source.img'
        source.write_bytes(b'forged payload')
        report['inventory'][rel].update(sha256=p.digest(source),size=source.stat().st_size)
    o.write_json(audit/'migration.json',report)
    with pytest.raises(ValueError,match='inventory changed'):
        m.migrate_attempts(controller.wd,resume=audit.name)


def test_registry_check_is_read_only_and_rejects_earlier_live_job(monkeypatch):
    import rq
    from rq.job import Job
    import rq.registry
    monkeypatch.setattr(rq,'Queue',lambda *a,**kw:SimpleNamespace(get_job_ids=lambda:[]))
    for name in ('StartedJobRegistry','DeferredJobRegistry','ScheduledJobRegistry'):
        monkeypatch.setattr(rq.registry,name,lambda *a,**kw:SimpleNamespace(key='registry'))
    monkeypatch.setattr(Job,'fetch',lambda *a,**kw:SimpleNamespace(
        func_name='wepppy.rq.postfire_debris_flow_rq.run_m1_rq', args=('run','a'*32),
        get_status=lambda **kw:'started'))
    connection=SimpleNamespace(zrange=lambda *args:[b'old-job'])
    with pytest.raises(ValueError,match='earlier postfire job'):
        m._jobs_idle({'upload_attempt':None,'run_attempt':None},'run',connection)


def test_legacy_migration_accepts_missing_model_without_rewriting_backup(legacy):
    controller, root, old, external = legacy
    wd = Path(controller.wd)
    with controller.locked(): controller._state.pop('model')
    original = (wd/controller.filename).read_bytes()
    report = m.migrate_attempts(wd)
    assert controller.state['model'] == 'M1'
    backups = list((root/'migrations').glob('*/original_metadata/postfire_debris_flow.nodb'))
    assert len(backups) == 1 and backups[0].read_bytes() == original
    assert not (root/'.staging').exists()


def test_future_engine_is_not_blessed_by_storage_migration(legacy, monkeypatch):
    controller, root, old, external = legacy
    monkeypatch.setattr(p, 'engine_identity', lambda: {'future': 'unapproved'})
    m.migrate_attempts(controller.wd)
    assert controller.state['last_successful_run']['snapshot']['inputs']['selections']['engine_sha256'] == m.LEGACY_ENGINE


def test_preselector_migration_resume_after_state_dump(legacy, monkeypatch):
    controller, root, old, external = legacy
    with controller.locked(): controller._state.pop('model')
    original_state_property = PostfireDebrisFlow.state
    def preselector_state(obj):
        value = original_state_property.fget(obj)
        value.pop('model', None)
        return value
    with monkeypatch.context() as patch:
        patch.setattr(PostfireDebrisFlow, 'state', property(preselector_state))
        patch.setattr(m, 'record_attempts', lambda *a: (_ for _ in ()).throw(OSError('stopped after dump')))
        with pytest.raises(OSError, match='stopped after dump'):
            m.migrate_attempts(controller.wd)
    audit = next((root/'migrations').iterdir())
    report = json.loads((audit/'migration.json').read_text())
    assert 'model' not in report['original_state']
    assert 'model' not in report['planned_state']
    controller._state = PostfireDebrisFlow.load_detached(controller.wd).state
    assert controller.state['model'] == 'M1'
    assert m.migrate_attempts(controller.wd, resume=audit.name)['status'] == 'complete'
