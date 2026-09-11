from pathlib import Path
import pytest
from wepppy.nodb.mods.postfire_debris_flow import production as p, preflight
from wepppy.nodb.mods.postfire_debris_flow.postfire_debris_flow import PostfireDebrisFlow

pytestmark = pytest.mark.unit


def test_path_parent_escape_and_symlink(tmp_path):
    root=tmp_path/'project';root.mkdir()
    outside=tmp_path/'outside';outside.write_text('secret')
    with pytest.raises(p.WorkflowError):p.safe(root,root/'..'/'outside')
    (root/'alias').symlink_to(outside)
    with pytest.raises(p.WorkflowError):p.safe(root,root/'alias')
    good=root/'good';good.write_text('safe')
    assert p.safe(root,good)==good


def test_artifact_signature_changes_and_removal(tmp_path):
    source=tmp_path/'source';source.write_text('old')
    record={'artifacts':{'source':p.signature(tmp_path,source,strong=True)}}
    assert p.artifacts_current(tmp_path,record)
    source.write_text('new')
    assert not p.artifacts_current(tmp_path,record)
    source.unlink()
    assert not p.artifacts_current(tmp_path,record)


def test_absent_read_does_not_create_nodb(tmp_path):
    assert p.state_at(tmp_path)['active_dnbr'] is None
    assert not (tmp_path/PostfireDebrisFlow.filename).exists()


def test_real_nodb_roundtrip(tmp_path,monkeypatch):
    monkeypatch.setattr(preflight,'notify',lambda wd:None)
    obj=PostfireDebrisFlow(str(tmp_path),'disturbed9002_wbt.cfg')
    obj.change(lambda state:state.update(frequency_source='noaa'))
    loaded=PostfireDebrisFlow.load_detached(str(tmp_path))
    assert loaded.state['frequency_source']=='noaa'
    assert (tmp_path/PostfireDebrisFlow.filename).is_file()

@pytest.fixture
def prepared_inputs(tmp_path):
    from tests.nodb.mods.test_postfire_debris_flow_integration import inputs
    return inputs.__wrapped__(tmp_path)


def test_upload_and_model_real_artifacts(tmp_path,monkeypatch,prepared_inputs):
    import json, uuid
    import pandas as pd
    from types import SimpleNamespace
    from tests.nodb.mods.test_postfire_debris_flow_integration import BINARY
    i=prepared_inputs
    from wepppy.nodb.core import Ron
    Ron(str(tmp_path),'disturbed9002_wbt.cfg')
    monkeypatch.setattr(preflight,'notify',lambda wd:None)
    controller=PostfireDebrisFlow(str(tmp_path),'disturbed9002_wbt.cfg')
    monkeypatch.setattr(p,'mutable',lambda wd:controller)
    parquet=tmp_path/'climate.parquet'
    pd.DataFrame({'prcp':[20.]*30,'year':list(range(1,31)), 'month':[7.]*30,'day_of_month':[1.]*30,
                  'peak_intensity_15':[30.]*30,'peak_intensity_30':[20.]*30,'peak_intensity_60':[10.]*30}).to_parquet(parquet)
    paths={'dem':i.dem,'mask':i.mask,'outlet':i.outlet,'sbs':i.sbs,'k':i.k,'k_manifest':i.k_manifest,'cli':parquet}
    snapshot={'selections':{'climate_mode':'Vanilla','engine_sha256':p.engine_identity()},'files':{}}
    def sources(wd,**kwargs):
        return True,False,{'watershed':True,'soils':True,'sbs':True,'k':True,'climate':True,'noaa':False},dict(paths),snapshot
    monkeypatch.setattr(p,'sources',sources)
    identity=uuid.uuid4().hex;folder=p.directory(tmp_path,identity);(folder/'source').mkdir(parents=True)
    import shutil
    shutil.copyfile(i.lineage_sources[0],folder/'source'/'dnbr.tif')
    controller.change(lambda state:state.update(upload_attempt={'id':identity,'job_id':None,'phase':'queued','created_at':p.now(),
        'retryable':False,'error':None,'snapshot':snapshot,'source_id':identity,'source_sha256':{str((folder/'source'/'dnbr.tif').relative_to(tmp_path)):p.digest(folder/'source'/'dnbr.tif')},'filename':'dnbr.tif','encoding':{'mode':'auto'}}))
    statistics = Path(str(i.dem) + '.aux.xml')
    statistics.write_text('<PAMDataset><PAMRasterBand band="1"><Metadata><MDI key="STATISTICS_MINIMUM">0</MDI></Metadata></PAMRasterBand></PAMDataset>')
    p.execute_upload(tmp_path,identity)
    import numpy as np
    before, before_valid, before_grid = p.read_raster(i.dem)
    after, after_valid, after_grid = p.read_raster(folder/'dem.tif')
    assert before_grid == after_grid
    np.testing.assert_array_equal(before_valid, after_valid)
    np.testing.assert_array_equal(before[before_valid], after[after_valid])
    manifest = json.loads((folder/'normalized'/'manifest.json').read_text())
    assert str(folder/'dem.tif') in manifest['input_sha256']
    assert str((folder/'dem.tif').relative_to(tmp_path)) in PostfireDebrisFlow.load_detached(str(tmp_path)).state['active_dnbr']['artifacts']
    loaded=PostfireDebrisFlow.load_detached(str(tmp_path))
    assert loaded.state['active_dnbr']['scale_factor']==.001
    runid=uuid.uuid4().hex;p.directory(tmp_path,runid).mkdir()
    controller.change(lambda state:state.update(run_attempt={'id':runid,'job_id':None,'phase':'queued','created_at':p.now(),
        'retryable':False,'error':None,'snapshot':{'inputs':snapshot,'dnbr':identity,'frequency':'cli'}}))
    p.execute_model(tmp_path,runid,BINARY)
    accepted=PostfireDebrisFlow.load_detached(str(tmp_path)).state['last_successful_run']
    assert accepted['id']==runid
    assert accepted['area_warning'] is True
    result=json.loads((p.directory(tmp_path,runid)/'results'/'manifest.json').read_text())
    assert result['status']=='complete'
    assert not (tmp_path/'postfire_debris_flow'/'runs').exists()
    assert len(pd.read_parquet(p.directory(tmp_path,runid)/'results'/'events.parquet'))==90

    statistics.write_text(statistics.read_text().replace('>0<', '>1<'))
    assert p.artifacts_current(tmp_path, PostfireDebrisFlow.load_detached(str(tmp_path)).state['active_dnbr'])
    # Climate-only rerun must reuse verified terrain, rather than invoking WBT.
    monkeypatch.setattr(p,'build_m1_predictors',lambda *a,**kw:pytest.fail('terrain should be reused'))
    next_id=uuid.uuid4().hex;p.directory(tmp_path,next_id).mkdir()
    controller.change(lambda state:state.update(run_attempt={'id':next_id,'job_id':None,'phase':'queued','created_at':p.now(),
        'retryable':False,'error':None,'snapshot':{'inputs':snapshot,'dnbr':identity,'frequency':'cli'}}))
    p.execute_model(tmp_path,next_id,BINARY)
    assert PostfireDebrisFlow.load_detached(str(tmp_path)).state['last_successful_run']['id']==next_id
    statistics.unlink()
    assert p.artifacts_current(tmp_path, PostfireDebrisFlow.load_detached(str(tmp_path)).state['active_dnbr'])
    with (folder/'dem.tif').open('ab') as stream:
        stream.write(b'tampered')
    assert not p.artifacts_current(tmp_path, PostfireDebrisFlow.load_detached(str(tmp_path)).state['active_dnbr'])


@pytest.fixture
def owner_project(tmp_path,prepared_inputs):
    """Real NoDb owners and owner RedisPrep state; no readiness mocking."""
    import json, shutil, time
    from wepppy.nodb.core import Ron, Watershed, Soils, Climate
    from wepppy.nodb.core.soils import SoilsMode
    from wepppy.nodb.mods.disturbed import Disturbed
    from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
    from wepppy.soils.ssurgo import SoilSummary
    ron=Ron(str(tmp_path),'disturbed9002_wbt.cfg')
    with ron.locked():ron._mods += ['postfire_debris_flow','rusle','polaris']
    watershed=Watershed.getInstance(str(tmp_path));disturbed=Disturbed.getInstance(str(tmp_path))
    paths={prepared_inputs.dem:Path(ron.dem_fn),prepared_inputs.mask:Path(watershed.wbt_wd)/'bound.tif',
           prepared_inputs.outlet:Path(watershed.wbt_wd)/'outlet.geojson',prepared_inputs.sbs:Path(disturbed.sbs_4class_path)}
    for source,dest in paths.items():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
    for prop in ('sand','silt','clay','om','ksat'):
        for depth in ('0_5','5_15'):
            dest=tmp_path/'polaris'/f'{prop}_mean_{depth}.tif';dest.parent.mkdir(exist_ok=True);shutil.copyfile(prepared_inputs.k,dest)
    soils=Soils.getInstance(str(tmp_path));Path(soils.soils_dir).mkdir(exist_ok=True)
    shutil.copyfile(next((Path(__file__).resolve().parents[2]/'omni'/'fixtures').rglob('p118.sol')), Path(soils.soils_dir)/'123.sol')
    with soils.locked():
        soils._mode=SoilsMode.Gridded;soils.domsoil_d={'1':'123'}
        soils.soils={'123':SoilSummary(mukey='123',fname='123.sol',soils_dir=soils.soils_dir,build_date='2026-09-10',desc='fixture')}
    climate=Climate.getInstance(str(tmp_path))
    with climate.locked():climate.cli_fn='owner.cli'
    Path(climate.cli_dir).mkdir(exist_ok=True)
    (Path(climate.cli_dir)/climate.cli_fn).write_text('owner CLI')
    (tmp_path/'climate').mkdir(exist_ok=True);(tmp_path/'climate'/'wepp_cli.parquet').write_bytes(b'owner climate artifact')
    dest=tmp_path/'rusle';dest.mkdir(exist_ok=True);shutil.copyfile(prepared_inputs.k,dest/'k_polaris_nomograph.tif')
    manifest=json.loads(prepared_inputs.k_manifest.read_text());manifest['k'].update(generated_utc=p.now(),statistic='mean',selected_modes=['polaris_nomograph'],artifacts={'nomograph':'rusle/k_polaris_nomograph.tif'})
    (dest/'manifest.json').write_text(json.dumps(manifest))
    prep=RedisPrep.getInstance(str(tmp_path))
    for i,task in enumerate((TaskEnum.build_subcatchments,TaskEnum.abstract_watershed,TaskEnum.build_landuse,TaskEnum.build_soils,TaskEnum.build_climate,TaskEnum.init_sbs_map,TaskEnum.fetch_polaris)):
        prep[str(task)]=100+i
    return tmp_path,prep


def test_owner_climate_invalidation_and_watershed_rebuild(owner_project):
    from wepppy.nodb.redis_prep import TaskEnum
    wd,prep=owner_project
    eligible,_,checks,_,_=p.sources(wd)
    assert eligible and checks['watershed'] and 'soils' not in checks and checks['climate'] and checks['k']
    prep.remove_timestamp(TaskEnum.build_climate)
    assert (wd/'climate/wepp_cli.parquet').is_file()
    assert not p.sources(wd)[2]['climate']
    prep[str(TaskEnum.build_climate)]=104
    prep[str(TaskEnum.build_subcatchments)]=200
    assert not p.sources(wd)[2]['watershed']
    prep[str(TaskEnum.abstract_watershed)]=201
    assert not p.sources(wd)[2]['climate']
    assert not p.sources(wd, model='M3')[2]['soils']


def test_k_source_rewrite_and_used_cfvo_removal(owner_project):
    import json,os
    wd,prep=owner_project
    assert p.sources(wd)[2]['k']
    path=wd/'polaris'/'sand_mean_0_5.tif';st=path.stat();k_st=(wd/'rusle/k_polaris_nomograph.tif').stat()
    os.utime(path,ns=(st.st_atime_ns,k_st.st_mtime_ns+1))
    assert not p.sources(wd)[2]['k']
    os.utime(path,ns=(st.st_atime_ns,st.st_mtime_ns))
    manifest=wd/'rusle/manifest.json';m=json.loads(manifest.read_text())
    m['k']['cfvo_summary']={'status':'available','source':{'top_path':str(wd/'polaris/missing-cfvo.tif')}}
    manifest.write_text(json.dumps(m))
    assert not p.sources(wd)[2]['k']


def test_completed_climate_with_failed_parquet_export_is_not_ready(owner_project):
    import os
    from wepppy.nodb.core import Climate
    wd,prep=owner_project
    assert p.sources(wd)[2]['climate']
    climate=Climate.getInstance(str(wd));cli=Path(climate.cli_dir)/climate.cli_fn
    exported=(wd/'climate/wepp_cli.parquet').stat().st_mtime_ns
    os.utime(cli,ns=(exported+1,exported+1))
    assert not p.sources(wd)[2]['climate']


@pytest.mark.parametrize('mutation',['source_after_auto','watershed_after_normalization','dem_after_auto','dem_mask_after_auto'])
def test_upload_rejects_mutation_and_preserves_accepted(tmp_path,monkeypatch,prepared_inputs,mutation):
    import shutil,uuid
    monkeypatch.setattr(preflight,'notify',lambda wd:None)
    controller=PostfireDebrisFlow(str(tmp_path),'disturbed9002_wbt.cfg')
    monkeypatch.setattr(p,'mutable',lambda wd:controller)
    original_snapshot={'revision':1};current_snapshot=dict(original_snapshot)
    paths={'mask':prepared_inputs.mask,'dem':prepared_inputs.dem}
    if mutation == 'dem_mask_after_auto':
        import rasterio, numpy as np
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
            with rasterio.open(prepared_inputs.dem, 'r+') as ds:
                ds.write_mask(np.full(ds.shape, 255, dtype='uint8'))
        paths['dem_mask']=Path(str(prepared_inputs.dem)+'.msk')
    monkeypatch.setattr(p,'sources',lambda *a,**kw:(True,False,{'watershed':True},
        dict(paths),dict(current_snapshot)))
    identity=uuid.uuid4().hex;folder=p.directory(tmp_path,identity);(folder/'source').mkdir(parents=True)
    source=folder/'source'/'dnbr.tif';shutil.copyfile(prepared_inputs.lineage_sources[0],source)
    old={'id':'f'*32,'snapshot':{},'artifacts':{}}
    controller.change(lambda state:state.update(active_dnbr=old,upload_attempt={'id':identity,'job_id':None,'phase':'queued',
        'created_at':p.now(),'retryable':False,'error':None,'snapshot':original_snapshot,'source_id':identity,
        'source_sha256':{str(source.relative_to(tmp_path)):p.digest(source)},'filename':source.name,'encoding':{'mode':'auto'}}))
    inspect=p.inspect_encoding;normalize=p.dnbr.normalize_dnbr
    def changed_auto(*args,**kwargs):
        result=inspect(*args,**kwargs)
        changed = paths['dem_mask'] if mutation == 'dem_mask_after_auto' else prepared_inputs.dem if mutation == 'dem_after_auto' else source
        with changed.open('ab') as stream:stream.write(b'changed bytes')
        return result
    def changed_watershed(*args,**kwargs):
        result=normalize(*args,**kwargs);current_snapshot['revision']=2;return result
    if mutation in ('source_after_auto','dem_after_auto','dem_mask_after_auto'):monkeypatch.setattr(p,'inspect_encoding',changed_auto)
    else:monkeypatch.setattr(p.dnbr,'normalize_dnbr',changed_watershed)
    with pytest.raises(p.WorkflowError):p.execute_upload(tmp_path,identity)
    assert PostfireDebrisFlow.load_detached(str(tmp_path)).state['active_dnbr']==old


def test_reuse_ignores_unrecorded_external_symlink(tmp_path,monkeypatch):
    import json
    identity='a'*32;previous=p.directory(tmp_path,identity)/'predictors';previous.mkdir(parents=True)
    manifest={'tool':{'sha256':'tool'},'sources_sha256':{}}
    (previous/'manifest.json').write_text(json.dumps(manifest));(previous/'good').write_text('verified')
    records={str(path.relative_to(tmp_path)):p.signature(tmp_path,path,strong=True) for path in previous.iterdir()}
    outside=tmp_path/'outside';outside.mkdir();(outside/'private').write_text('must not copy')
    (previous/'unrecorded').write_text('not inventoried');(previous/'alias').symlink_to(outside,target_is_directory=True)
    accepted={'id':identity,'predictor_artifacts':records,'snapshot':{'inputs':{'selections':{'engine_sha256':p.engine_identity()}}}}
    # Schema validation is separate; exercise actual inventory-safe copying.
    from wepppy.nodb.mods.postfire_debris_flow import rainfall_io
    monkeypatch.setattr(rainfall_io,'validate_predictors',lambda m:None)
    output=tmp_path/'copied'
    assert p.reuse_predictors(tmp_path,accepted,{},'tool',output)
    assert sorted(path.name for path in output.iterdir())==['good','manifest.json']


@pytest.mark.parametrize('kind,accepted_key,function', [
    ('upload_attempt', 'active_dnbr', 'upload_dnbr_rq'),
    ('run_attempt', 'last_successful_run', 'run_m1_rq'),
])
def test_reconciliation_keeps_worker_publication_revision_together(tmp_path, monkeypatch, kind, accepted_key, function):
    from copy import deepcopy
    from types import SimpleNamespace
    from rq.job import Job
    from wepppy.nodb.core import Ron
    monkeypatch.setattr(Ron, 'getInstance', lambda wd: SimpleNamespace(runid='run'))
    before = p.empty_state()
    before[kind] = {'id': 'a'*32, 'job_id': 'job', 'phase': 'running'}
    before[accepted_key] = {'id': 'b'*32}
    published = deepcopy(before)
    published[kind]['phase'] = 'complete'
    published[accepted_key] = {'id': 'a'*32}
    monkeypatch.setattr(p, 'state_at', lambda wd: deepcopy(published))
    monkeypatch.setattr(Job, 'fetch', lambda *a, **kw: SimpleNamespace(
        args=('run', 'a'*32), origin='default',
        func_name='wepppy.rq.postfire_debris_flow_rq.'+function,
        get_status=lambda **kw: 'finished'))
    assert p.reconcile_attempts(tmp_path, before, None) == published


def test_enable_materializes_both_soil_dependencies(tmp_path):
    from wepppy.nodb.core import Ron
    from wepppy.weppcloud.routes.nodb_api.project_bp import _enable_mod_for_run
    ron = Ron(str(tmp_path), 'disturbed9002_wbt.cfg')
    assert _enable_mod_for_run(ron, str(tmp_path), ron.config_stem, 'postfire_debris_flow')
    assert {'postfire_debris_flow', 'rusle', 'polaris'}.issubset(ron.mods)
    for filename in ('postfire_debris_flow.nodb', 'rusle.nodb', 'polaris.nodb'):
        assert (tmp_path/filename).is_file()


@pytest.mark.parametrize('payload', [
    b'', b'<PAMDataset/>', b'<PAMDataset>',
    b'<!DOCTYPE PAMDataset [<!ENTITY x SYSTEM "file:///etc/passwd">]><PAMDataset/>',
    '<PAMDataset/>'.encode('utf-16'),
    b'<PAMDataset><SRS>EPSG:4326</SRS></PAMDataset>',
    b'<PAMDataset><PAMRasterBand band="1"><NoDataValue>0</NoDataValue></PAMRasterBand></PAMDataset>',
    b'<PAMDataset><PAMRasterBand band="1"><Metadata/></PAMRasterBand></PAMDataset>',
    *[('<PAMDataset><PAMRasterBand band="1"><Metadata>'+entry+'</Metadata></PAMRasterBand></PAMDataset>').encode() for entry in [
        '<MDI key="STATISTICS_MINIMUM">nan</MDI>',
        '<MDI key="STATISTICS_MINIMUM">inf</MDI>',
        '<MDI key="STATISTICS_MINIMUM"></MDI>',
        '<MDI key="STATISTICS_MINIMUM">1</MDI><MDI key="STATISTICS_MINIMUM">2</MDI>',
        '<MDI key="SCALE">0.001</MDI>',
        '<MDI key="STATISTICS_APPROXIMATE">MAYBE</MDI>',
        '<MDI key="STATISTICS_MINIMUM" source="external">1</MDI>',
        '<MDI key="STATISTICS_MINIMUM"><SourceFilename>other</SourceFilename></MDI>',
    ]],
    b' ' * (64*1024+1),
])
def test_reject_unsafe_or_meaningful_statistics_cache(tmp_path, payload):
    from wepppy.nodb.mods.postfire_debris_flow.m1_inputs import validate_statistics_cache, M1Error
    cache=tmp_path/'dem.tif.aux.xml';cache.write_bytes(payload)
    with pytest.raises(M1Error): validate_statistics_cache(cache)


def test_statistics_cache_preserves_raster_and_strict_upload_boundary(tmp_path):
    import numpy as np
    from tests.nodb.mods.test_postfire_debris_flow_integration import raster
    from wepppy.nodb.mods.postfire_debris_flow.m1_inputs import companions, read_raster, validate_statistics_cache, M1Error
    from wepppy.nodb.mods.postfire_debris_flow.dnbr import _raster, DnbrError
    source=tmp_path/'dem.tif'; raster(source,np.array([[5.,6.],[7.,-9999.]]))
    expected, valid, grid=read_raster(source)
    original_hash=p.digest(source)
    cache=Path(str(source)+'.aux.xml')
    for value in ('1', '200'):
        cache.write_text('<PAMDataset><PAMRasterBand band="1"><Metadata><MDI key="STATISTICS_MINIMUM">'+value+'</MDI><MDI key="STATISTICS_APPROXIMATE">YES</MDI></Metadata></PAMRasterBand></PAMDataset>')
        actual, support, actual_grid=read_raster(source)
        np.testing.assert_array_equal(actual,expected)
        np.testing.assert_array_equal(support,valid)
        assert actual_grid==grid and p.digest(source)==original_hash
        assert companions(source)==[]
        with pytest.raises(DnbrError):
            with _raster(source): pytest.fail('uploaded sidecar must remain forbidden')
    cache.unlink()
    assert companions(source)==[]
    cache.symlink_to(source)
    with pytest.raises(M1Error): validate_statistics_cache(cache)
    cache.unlink();cache.mkdir()
    with pytest.raises(M1Error): validate_statistics_cache(cache)


def test_project_masks_change_dependency_snapshot_but_statistics_do_not(owner_project):
    wd, _ = owner_project
    before = p.sources(wd, rainfall=False)[4]
    dem = p.sources(wd, rainfall=False)[3]['dem']
    primary_hash = p.digest(dem)
    cache = Path(str(dem)+'.aux.xml')
    cache.write_text('<PAMDataset><PAMRasterBand band="1"><Metadata><MDI key="STATISTICS_MINIMUM">0</MDI></Metadata></PAMRasterBand></PAMDataset>')
    assert p.sources(wd, rainfall=False)[4] == before
    cache.unlink()
    assert p.sources(wd, rainfall=False)[4] == before
    mask = Path(str(dem)+'.msk')
    mask.write_bytes(b'first mask bytes')
    added = p.sources(wd, rainfall=False)[4]
    assert added != before and 'dem_mask' in added['files']
    mask.write_bytes(b'changed mask bytes')
    assert p.sources(wd, rainfall=False)[4] != added
    mask.unlink()
    assert p.sources(wd, rainfall=False)[4] == before
    assert p.digest(dem) == primary_hash


@pytest.mark.parametrize('case,expected', [
    ('absent', None), ('partial', 1789094046), ('complete', 1789094046),
    ('failed_retry', 1789094046), ('replacement', None), ('frequency', 1789094046),
])
def test_preflight_projects_durable_publication(tmp_path, monkeypatch, case, expected):
    from unittest.mock import MagicMock
    from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
    controller = PostfireDebrisFlow(str(tmp_path), 'disturbed9002_wbt.cfg')
    state = p.empty_state()
    if case != 'absent':
        state['active_dnbr'] = {'id': 'a'*32, 'snapshot': {}, 'artifacts': {}}
        state['last_successful_run'] = {
            'id': 'b'*32, 'completed_at': '2026-09-11T02:34:06+00:00',
            'snapshot': {'dnbr': 'a'*32, 'frequency': 'cli'},
            'artifacts': {}, 'partial': case == 'partial',
        }
        if case == 'replacement': state['active_dnbr']['id'] = 'c'*32
        if case == 'frequency': state['frequency_source'] = 'noaa'
        if case == 'failed_retry':
            state['run_attempt'] = {'id': 'd'*32, 'snapshot': {}, 'phase': 'failed',
                                    'created_at': p.now(), 'retryable': True}
    with controller.locked(): controller._state = state
    prep = MagicMock(run_id='test-run')
    lock = prep.redis.lock.return_value.__enter__.return_value
    lock.owned.return_value = True
    monkeypatch.setattr(RedisPrep, 'getInstance', lambda wd: prep)
    preflight.notify(tmp_path)
    pipe = prep.redis.pipeline.return_value.__enter__.return_value
    key = 'timestamps:run_postfire_debris_flow'
    if expected is None:
        pipe.hdel.assert_called_once_with('test-run', key)
    else:
        assert expected == int(p.datetime.fromisoformat(state['last_successful_run']['completed_at']).timestamp())
        assert ('test-run', key, expected) in [call.args for call in pipe.hset.call_args_list]
        pipe.hdel.assert_not_called()
    pipe.execute.assert_called_once()
    prep.dump.assert_called_once()
    assert TaskEnum.run_postfire_debris_flow.emoji() == '🌋'
    assert TaskEnum.run_postfire_debris_flow.label() == 'Run Post-fire Debris Flow'


def test_preflight_reads_after_lock_and_skips_expired_lease(tmp_path, monkeypatch, caplog):
    from unittest.mock import MagicMock
    from wepppy.nodb.redis_prep import RedisPrep
    prep = MagicMock(run_id='test-run')
    lock = prep.redis.lock.return_value.__enter__.return_value
    lock.owned.return_value = False
    monkeypatch.setattr(RedisPrep, 'getInstance', lambda wd: prep)
    def latest(wd):
        prep.redis.lock.return_value.__enter__.assert_called_once()
        return p.empty_state()
    monkeypatch.setattr(p, 'state_at', latest)
    preflight.notify(tmp_path)
    prep.redis.pipeline.assert_not_called()
    assert 'projection lease expired' in caplog.text


def test_delayed_preflight_notifier_reads_replacement_after_acquiring_lock(tmp_path, monkeypatch):
    from unittest.mock import MagicMock
    from wepppy.nodb.redis_prep import RedisPrep
    state = p.empty_state()
    state['active_dnbr'] = {'id': 'a'*32}
    state['last_successful_run'] = {
        'snapshot': {'dnbr': 'a'*32, 'frequency': 'cli'},
        'completed_at': '2026-09-11T02:34:06+00:00',
    }
    prep = MagicMock(run_id='test-run')
    lock = MagicMock()
    lock.owned.return_value = True
    def acquire_after_replacement():
        state['active_dnbr']['id'] = 'c'*32
        return lock
    prep.redis.lock.return_value.__enter__.side_effect = acquire_after_replacement
    monkeypatch.setattr(RedisPrep, 'getInstance', lambda wd: prep)
    monkeypatch.setattr(p, 'state_at', lambda wd: state)
    preflight.notify(tmp_path)
    pipe = prep.redis.pipeline.return_value.__enter__.return_value
    pipe.hdel.assert_called_once_with('test-run', 'timestamps:run_postfire_debris_flow')
    assert len(pipe.hset.call_args_list) == 2  # Model and revision notification.


def test_model_selection_legacy_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, 'notify', lambda wd: None)
    obj = PostfireDebrisFlow(str(tmp_path), 'disturbed9002_wbt.cfg')
    with obj.locked(): obj._state.pop('model')
    assert obj.state['model'] == 'M1'
    assert 'model' not in obj._state  # Read projection does not mutate legacy state.
    obj.change(lambda state: state.update(model='M3'))
    assert PostfireDebrisFlow.load_detached(str(tmp_path)).state['model'] == 'M3'


def test_model_source_dependencies_are_separate(owner_project):
    from wepppy.nodb.core import Ron
    from wepppy.nodb.redis_prep import TaskEnum
    wd, prep = owner_project
    ron = Ron.getInstance(str(wd))
    with ron.locked():
        ron._cellsize = 10
        ron._dem_db = 'ned13/2022'
    m1 = p.sources(wd)[4]
    prep[str(TaskEnum.build_soils)] = 200
    assert p.sources(wd)[4] == m1
    m3 = p.sources(wd, model='M3')
    assert m3[2]['watershed'] and m3[2]['soils']
    assert 'k' not in m3[2] and not any(k.startswith('polaris') for k in m3[3])
    prep[str(TaskEnum.fetch_polaris)] = 300
    (wd/'rusle/k_polaris_nomograph.tif').unlink()
    assert p.sources(wd, model='M3')[4] == m3[4]
    assert not p.sources(wd)[2]['k']
    with ron.locked(): ron._cellsize = 30
    assert not p.sources(wd, model='M3')[2]['watershed']
    assert p.sources(wd)[2]['watershed']


def test_m3_task_retains_failure_and_preserves_previous_result(tmp_path, monkeypatch):
    import json
    from wepppy.rq import postfire_debris_flow_rq as worker
    monkeypatch.setattr(preflight, 'notify', lambda wd: None)
    controller = PostfireDebrisFlow(str(tmp_path), 'disturbed9002_wbt.cfg')
    snapshot = {'inputs': {}, 'dnbr': None, 'frequency': 'cli'}
    attempt = {'id': 'c'*32, 'model': 'M3', 'snapshot': snapshot, 'phase': 'queued',
               'created_at': p.now(), 'retryable': False, 'job_id': 'test-job'}
    controller.change(lambda state: state.update(run_attempt=attempt, model='M1', frequency_source='noaa'))
    monkeypatch.setattr(p, 'mutable', lambda wd: controller)
    monkeypatch.setattr(p, 'sources', lambda wd, **kw: (True, False, {'watershed':True,'soils':True,'sbs':True,'climate':True,'noaa':False}, {}, {}))
    monkeypatch.setattr(worker, 'get_wd', lambda runid: str(tmp_path))
    monkeypatch.setattr(worker, 'get_current_job', lambda: None)
    with pytest.raises(RuntimeError, match='integration_pending'):
        worker.run_m3_rq('test', attempt['id'])
    state = PostfireDebrisFlow.load_detached(str(tmp_path)).state
    assert state['run_attempt']['phase'] == 'failed'
    assert state['run_attempt']['error']['code'] == 'integration_pending'
    assert state['model'] == 'M1' and state['frequency_source'] == 'noaa'
    assert state['last_successful_run'] is None
    root = p.directory(tmp_path, attempt['id'])
    assert 'integration is not implemented' in (root/'error.log').read_text()
    assert json.loads((root/'status.json').read_text())['attempt']['phase'] == 'failed'


def test_public_run_uses_immutable_legacy_or_explicit_identity():
    attempt = {'id':'a'*32, 'snapshot':{'frequency':'cli'}, 'phase':'running'}
    assert p.public_attempt(attempt, model=True)['model'] == 'M1'
    attempt.update(model='M3', frequency_source='noaa')
    public = p.public_attempt(attempt, model=True)
    assert public['model'] == 'M3' and public['frequency_source'] == 'noaa'
    assert 'snapshot' not in public


def test_m1_reuse_refuses_m3_before_reading_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(p, 'artifacts_current', lambda *a, **kw: pytest.fail('foreign model inspected'))
    assert not p.reuse_predictors(tmp_path, {'model':'M3','predictor_artifacts':{'irrelevant':[]}}, {}, 'hash', tmp_path/'out')


@pytest.mark.parametrize('model,irrelevant', [('M1','build_soils'),('M1','build_landuse'),('M3','build_polaris')])
def test_irrelevant_malformed_receipt_does_not_block_model(owner_project, model, irrelevant):
    wd, prep = owner_project
    prep.redis.hset(prep.run_id, 'timestamps:'+irrelevant, 'malformed')
    p.sources(wd, model=model)
    p.sources(wd, rainfall=False)
