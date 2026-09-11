from pathlib import Path
import pytest
from wepppy.nodb.mods.postfire_debris_flow import production as p
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
    monkeypatch.setattr(p,'notify',lambda wd:None)
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
    monkeypatch.setattr(p,'notify',lambda wd:None)
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
    p.execute_upload(tmp_path,identity)
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

    # Climate-only rerun must reuse verified terrain, rather than invoking WBT.
    monkeypatch.setattr(p,'build_m1_predictors',lambda *a,**kw:pytest.fail('terrain should be reused'))
    next_id=uuid.uuid4().hex;p.directory(tmp_path,next_id).mkdir()
    controller.change(lambda state:state.update(run_attempt={'id':next_id,'job_id':None,'phase':'queued','created_at':p.now(),
        'retryable':False,'error':None,'snapshot':{'inputs':snapshot,'dnbr':identity,'frequency':'cli'}}))
    p.execute_model(tmp_path,next_id,BINARY)
    assert controller.state['last_successful_run']['id']==next_id


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
    assert eligible and checks['watershed'] and checks['soils'] and checks['climate'] and checks['k']
    prep.remove_timestamp(TaskEnum.build_climate)
    assert (wd/'climate/wepp_cli.parquet').is_file()
    assert not p.sources(wd)[2]['climate']
    prep[str(TaskEnum.build_climate)]=104
    prep[str(TaskEnum.build_subcatchments)]=200
    assert not p.sources(wd)[2]['watershed']
    prep[str(TaskEnum.abstract_watershed)]=201
    assert not p.sources(wd)[2]['climate']
    assert not p.sources(wd)[2]['soils']


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


@pytest.mark.parametrize('mutation',['source_after_auto','watershed_after_normalization'])
def test_upload_rejects_mutation_and_preserves_accepted(tmp_path,monkeypatch,prepared_inputs,mutation):
    import shutil,uuid
    monkeypatch.setattr(p,'notify',lambda wd:None)
    controller=PostfireDebrisFlow(str(tmp_path),'disturbed9002_wbt.cfg')
    monkeypatch.setattr(p,'mutable',lambda wd:controller)
    original_snapshot={'revision':1};current_snapshot=dict(original_snapshot)
    monkeypatch.setattr(p,'sources',lambda *a,**kw:(True,False,{'watershed':True},
        {'mask':prepared_inputs.mask,'dem':prepared_inputs.dem},dict(current_snapshot)))
    identity=uuid.uuid4().hex;folder=p.directory(tmp_path,identity);(folder/'source').mkdir(parents=True)
    source=folder/'source'/'dnbr.tif';shutil.copyfile(prepared_inputs.lineage_sources[0],source)
    old={'id':'f'*32,'snapshot':{},'artifacts':{}}
    controller.change(lambda state:state.update(active_dnbr=old,upload_attempt={'id':identity,'job_id':None,'phase':'queued',
        'created_at':p.now(),'retryable':False,'error':None,'snapshot':original_snapshot,'source_id':identity,
        'source_sha256':{str(source.relative_to(tmp_path)):p.digest(source)},'filename':source.name,'encoding':{'mode':'auto'}}))
    inspect=p.inspect_encoding;normalize=p.dnbr.normalize_dnbr
    def changed_auto(*args,**kwargs):
        result=inspect(*args,**kwargs)
        with source.open('ab') as stream:stream.write(b'changed bytes')
        return result
    def changed_watershed(*args,**kwargs):
        result=normalize(*args,**kwargs);current_snapshot['revision']=2;return result
    if mutation=='source_after_auto':monkeypatch.setattr(p,'inspect_encoding',changed_auto)
    else:monkeypatch.setattr(p.dnbr,'normalize_dnbr',changed_watershed)
    with pytest.raises(p.WorkflowError):p.execute_upload(tmp_path,identity)
    assert controller.state['active_dnbr']==old


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
