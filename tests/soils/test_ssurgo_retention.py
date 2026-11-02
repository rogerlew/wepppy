from copy import deepcopy
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path

import pytest
from wepppy.soils.ssurgo import ssurgo as ss
from wepppy.soils.ssurgo import retention as r
from wepppy.wepp.soils.utils import WeppSoilUtil

pytestmark = pytest.mark.integration
RECEIPT = 'a'*64


def layer(**updates):
    result = dict(cokey=10, chkey=100, hzname='A', hzdepb_r=35., hzdept_r=0.,
        hzthk_r=35., dbthirdbar_r=1.2, ksat_r=12., sandtotal_r=55., claytotal_r=20.,
        om_r=2., cec7_r=10., fraggt10_r=0., frag3to10_r=0., desgnmaster='A',
        sieveno10_r=70., wthirdbar_r=20., wfifteenbar_r=8., sandvf_r=5., ll_r=None)
    result.update(updates)
    return result


def view(layers=None):
    rows = layers if layers is not None else [layer()]
    return ss._SurgoCollectionWorkerView({1}, 'Surgo',
        {1: [dict(cokey=10, muname='Example', compname='Example', comppct_r=100., albedodry_r=.16)]},
        {10: deepcopy(rows)}, {}, {h['chkey']: 'loam' for h in rows}, {10: None})


def build(layers=None, candidate=True):
    return ss.WeppSoil(view(layers), 1, retention_policy=r.POLICY if candidate else None,
                      retention_source_receipt=RECEIPT if candidate else None)


def test_post_selection_and_serialized_lineage(tmp_path):
    soil = build()
    expected_share = (1-.3)/1.2 / ((1-.3)/1.2 + .3/2.65)
    assert soil.horizons[0].field_cap == pytest.approx(.2/expected_share)
    soil.write(str(tmp_path))
    receipt = json.loads((tmp_path/'1.sol.retention.json').read_text())
    assert receipt['soil_sha256'] == hashlib.sha256((tmp_path/'1.sol').read_bytes()).hexdigest()
    assert receipt['source_receipt_sha256'] == RECEIPT
    assert receipt['cokey'] == '10'
    assert [row['values']['solthk'] for row in receipt['emitted_rows']] == [200,400]
    assert {row['chkey'] for row in receipt['emitted_rows']} == {'100'}
    assert receipt['decisions'][0]['source']['wthirdbar_r'] == 20
    assert receipt['decisions'][0]['branches'] == dict(fc='source-capped-mass',wp='source-capped-mass')
    with pytest.raises(FileExistsError):
        soil.write(str(tmp_path), overwrite=True)


@pytest.mark.parametrize('change,reason', [
    ({'sieveno10_r':100.},'eligible'),
    ({'wfifteenbar_r':None},'fallback-unchanged'),
    ({'wthirdbar_r':-9.9},'fallback-unchanged'),
    ({'wthirdbar_r':0.,'wfifteenbar_r':0.},'zero-or-unordered-source'),
    ({'sieveno10_r':10.},'native-cap-conflict'),
    ({'dbthirdbar_r':None},'missing-original-input'),
    ({'dbthirdbar_r':2.7},'density-assumption-conflict'),
    ({'wthirdbar_r':50.,'wfifteenbar_r':20.},'porosity-assumption-conflict'),
])
def test_excluded_or_zero_identity(change,reason):
    a,b = build([layer(**change)],False),build([layer(**change)])
    a.description=b.description='# fixed test description'
    assert b.retention_decisions[0]['reason'] == reason
    candidate_text = b.build_file_contents().replace('# WEPPPY_RETENTION_POLICY='+r.POLICY+'\n','')
    assert a.build_file_contents() == candidate_text


def test_restricted_source_not_transformed():
    rows=[layer(hzdepb_r=18.), layer(chkey=101,hzdept_r=18.,hzdepb_r=40.,ksat_r=.5)]
    baseline,candidate=build(rows,False),build(rows)
    assert baseline.res_lyr_i == candidate.res_lyr_i == 1
    assert candidate.retention_decisions[1]['reason']=='prior-exclusion'
    assert candidate.horizons[1].field_cap == baseline.horizons[1].field_cap


def test_real_worker_process_propagates_policy():
    # Actual process boundary; no database/network/model and no fake executor.
    with ProcessPoolExecutor(max_workers=1) as pool:
        key,soil,valid,logs=pool.submit(ss._build_soil_for_process,1,view(),.75,{},True,False,None,r.POLICY,RECEIPT).result()
    assert valid and key==1 and soil.retention_policy==r.POLICY
    assert soil.retention_decisions[0]['reason']=='eligible'
    assert soil.horizons[0].field_cap != build(candidate=False).horizons[0].field_cap


def test_make_collection_passes_policy_to_real_pool(monkeypatch):
    collection = ss.SurgoSoilCollection([])
    collection.mukeys={1}
    monkeypatch.setattr(ss.SurgoCollectionWorkerViewFactory,'build',lambda self,*args:view())
    try:
        collection.makeWeppSoils(max_workers=1,retention_policy=r.POLICY,retention_source_receipt=RECEIPT)
        assert collection.weppSoils[1].retention_decisions[0]['reason']=='eligible'
    finally:
        collection._disconnect()


def test_legacy_object_without_optional_attributes_preserves_default_text():
    soil=build(candidate=False)
    before=soil.build_file_contents()
    del soil.retention_policy
    assert soil.build_file_contents()==before
    assert r.POLICY not in before
    assert soil.horizons[0].field_cap==pytest.approx(.2/.7)
    assert soil.horizons[0].wilt_pt==pytest.approx(.08/.7)



@pytest.mark.parametrize('source,policy,receipt', [('StatsGo',r.POLICY,RECEIPT),('Surgo','bad',RECEIPT),('Surgo',r.POLICY,None)])
def test_policy_rejection(source,policy,receipt):
    v=view();v.source_data=source
    with pytest.raises(ValueError):
        ss.WeppSoil(v,1,retention_policy=policy,retention_source_receipt=receipt)


def test_legacy_writer_rejected_without_output(tmp_path):
    with pytest.raises(ValueError):
        build().write(str(tmp_path),version='2006.2')
    assert not list(tmp_path.iterdir())


def test_companion_rejects_corrupted_serialized_capacity(tmp_path):
    soil=build();path=tmp_path/'manual.sol'
    path.write_text(soil.build_file_contents())
    data=WeppSoilUtil(str(path))
    text=path.read_text(); expected=f'{soil.horizons[0].field_cap:.4f}'
    assert expected in text
    path.write_text(text.replace(expected,'0.9999'))
    with pytest.raises(ValueError,match='Serialized retention'):
        r.write_companion(soil,path)
    assert not Path(str(path)+'.retention.json').exists()



def actual_disturbed_worker():
    from wepppy.nodb.mods.disturbed.disturbed import _build_disturbed_mofe_soil
    return _build_disturbed_mofe_soil



def task(tmp_path):
    source_dir=tmp_path/'source';source_dir.mkdir();build().write(str(source_dir))
    dest=tmp_path/'treatment.sol'
    return dict(source_soil_path=str(source_dir/'1.sol'),output_path=str(dest),
        disturbed_mukey='example',replacements={'luse':'forest','stext':'loam'},
        sol_ver=9002.,h0_max_om=None,recompute_wp_fc_using_rosetta_on_bd_override=False)


def test_actual_disturbed_consumer_and_reuse_rejection(tmp_path):
    t=task(tmp_path);worker=actual_disturbed_worker();worker(t)
    target=Path(t['output_path']);receipt=json.loads(Path(str(target)+'.retention.json').read_text())
    assert receipt['soil_sha256']==hashlib.sha256(target.read_bytes()).hexdigest()
    assert [h['values']['fc'] for h in receipt['source_rows']]==[h['fc'] for h in receipt['serialized_rows']]
    with pytest.raises(FileExistsError):
        r.reject_stale_treatment(t['source_soil_path'],t['output_path'])
    with pytest.raises(FileExistsError):
        worker(t)


@pytest.mark.parametrize('mutation', ['density','recompute','tamper','repair','missing-marker'])
def test_actual_consumer_rejects_unsupported_inputs(tmp_path,mutation,monkeypatch):
    t=task(tmp_path)
    if mutation=='density': t['replacements']['bd']=1.2
    if mutation=='recompute': t['recompute_wp_fc_using_rosetta_on_bd_override']=True
    if mutation=='tamper':
        p=Path(t['source_soil_path']);p.write_bytes(p.read_bytes()+b'\n')
    if mutation=='missing-marker':
        p=Path(t['source_soil_path']);p.write_text(p.read_text().replace('# WEPPPY_RETENTION_POLICY='+r.POLICY+'\n',''))
    if mutation=='repair':
        original=WeppSoilUtil.to_over9000
        def changed(self,*args,**kwargs):
            result=original(self,*args,**kwargs)
            result.obj['ofes'][0]['horizons'][0]['fc']=.7
            return result
        monkeypatch.setattr(WeppSoilUtil,'to_over9000',changed)
    with pytest.raises(ValueError): actual_disturbed_worker()(t)
    assert not Path(t['output_path']+'.retention.json').exists()
    if mutation!='repair': assert not Path(t['output_path']).exists()


def test_missing_companion_cannot_bypass_real_consumer_or_planner(tmp_path):
    t=task(tmp_path)
    Path(t['source_soil_path']+'.retention.json').unlink()
    with pytest.raises(ValueError,match='marker'):
        actual_disturbed_worker()(t)
    with pytest.raises(ValueError,match='marker'):
        r.reject_stale_treatment(t['source_soil_path'],t['output_path'])
    assert not Path(t['output_path']).exists()


def test_ordinary_unmarked_treatment_remains_allowed(tmp_path):
    source_dir=tmp_path/'legacy';source_dir.mkdir();build(candidate=False).write(str(source_dir))
    t=dict(source_soil_path=str(source_dir/'1.sol'),output_path=str(tmp_path/'legacy-target.sol'),
        disturbed_mukey='legacy',replacements={'bd':1.3},sol_ver=9002.,
        h0_max_om=None,recompute_wp_fc_using_rosetta_on_bd_override=False)
    actual_disturbed_worker()(t)
    assert WeppSoilUtil(t['output_path']).obj['ofes'][0]['horizons'][0]['bd']==1.3
    assert not Path(t['output_path']+'.retention.json').exists()





def complete_stack(tmp_path):
    worker=actual_disturbed_worker();files=[]
    for index,fc in enumerate([20.,22.]):
        directory=tmp_path/f'source-{index}';directory.mkdir()
        candidate=build([layer(chkey=100+index,hzdepb_r=95.,wthirdbar_r=fc)])
        candidate.write(str(directory))
        output=tmp_path/f'treatment-{index}.sol'
        worker(dict(source_soil_path=str(directory/'1.sol'),output_path=str(output),
            disturbed_mukey=str(index),replacements={'luse':'forest','stext':'loam'},
            sol_ver=9002.,h0_max_om=None,recompute_wp_fc_using_rosetta_on_bd_override=False))
        files.append(str(output))
    from wepppy.wepp.soils.utils import multi_ofe as module
    target=tmp_path/'multi.sol'
    module.SoilMultipleOfeSynth(files).write(str(target))
    return target,files,module


def stage_worker():
    from wepppy.nodb.core.wepp import prep_soil
    return prep_soil


def test_actual_full_generated_artifact_chain(tmp_path):
    import shutil
    source,files,module=complete_stack(tmp_path)
    receipt=r.load_source_companion(source)
    assert [rows[0]['chkey'] for rows in receipt['lineage']]==['100','101']
    assert [[row['values']['solthk'] for row in rows] for rows in receipt['lineage']]==[[200,1000],[200,1000]]
    target=tmp_path/'p40.sol'
    stage_worker()(('182',str(source),str(target),.01,None,.75,True,700.,False,0.,False))
    staged=r.load_source_companion(target)
    assert staged['schema']=='ssurgo-retention-stage-v3'
    assert [[row['values']['solthk'] for row in rows] for rows in staged['lineage']]==[[200,700],[200,700]]
    assert [rows[0]['chkey'] for rows in staged['lineage']]==['100','101']
    for a,b in zip(receipt['lineage'],staged['lineage'],strict=True):
        assert [row['values']['fc'] for row in a]==[row['values']['fc'] for row in b]


def test_stack_requires_all_companions_and_fresh_target(tmp_path):
    source,files,module=complete_stack(tmp_path)
    with pytest.raises(FileExistsError): module.SoilMultipleOfeSynth(files).write(str(source))
    Path(files[1]+'.retention.json').unlink()
    with pytest.raises(ValueError,match='marker'): module.SoilMultipleOfeSynth(files).write(str(tmp_path/'bad.sol'))
    assert not (tmp_path/'bad.sol').exists()


def test_final_staging_missing_companion_and_unsupported_extension(tmp_path):
    source,_,_=complete_stack(tmp_path)
    target=tmp_path/'bad.sol';worker=stage_worker()
    with pytest.raises(ValueError,match='Unsupported'):
        worker(('182',str(source),str(target),.01,None,.75,True,700.,True,800.,False))
    Path(str(source)+'.retention.json').unlink()
    with pytest.raises(ValueError,match='marker'):
        worker(('182',str(source),str(target),.01,None,.75,True,700.,False,0.,False))
    assert not target.exists()


@pytest.mark.parametrize("mutation", ["order", "marker"])
def test_stage_detects_material_and_order_corruption(tmp_path,monkeypatch,mutation):
    source,_,_=complete_stack(tmp_path)
    original=WeppSoilUtil.__str__
    def reordered(self,*args,**kwargs):
        if mutation == 'order':
            self.obj['ofes'].reverse()
        result=original(self,*args,**kwargs)
        if mutation == 'marker':
            result=result.replace('# WEPPPY_RETENTION_POLICY='+r.POLICY+'\n','')
        return result
    monkeypatch.setattr(WeppSoilUtil,'__str__',reordered)
    target=tmp_path/'bad.sol'
    with pytest.raises(ValueError,match='row/order/material' if mutation=='order' else 'marker'):
        stage_worker()(('182',str(source),str(target),.01,None,.75,True,700.,False,0.,False))
    assert not Path(str(target)+'.retention.json').exists()


def test_default_stack_and_stage_keep_material_and_no_companions(tmp_path):
    source_dir=tmp_path/'default';source_dir.mkdir()
    build([layer(hzdepb_r=95.)],candidate=False).write(str(source_dir))
    source=str(source_dir/'1.sol')
    from wepppy.wepp.soils.utils import multi_ofe as module
    stack=tmp_path/'multi.sol';module.SoilMultipleOfeSynth([source,source]).write(str(stack))
    staged=tmp_path/'p40.sol'
    stage_worker()(('182',str(stack),str(staged),.01,None,.75,True,700.,False,0.,False))
    original=WeppSoilUtil(source).obj['ofes'][0]['horizons']
    actual=WeppSoilUtil(str(staged)).obj['ofes']
    assert len(actual)==2
    for ofe in actual:
        assert [h['solthk'] for h in ofe['horizons']]==[200,700]
        assert [(h['fc'],h['wp'],h['bd']) for h in ofe['horizons']]==[(h['fc'],h['wp'],h['bd']) for h in original]
    assert not Path(str(stack)+'.retention.json').exists()
    assert not Path(str(staged)+'.retention.json').exists()



@pytest.mark.parametrize('mutation', ['foreign-horizon','numeric-foreign-horizon','bad-digest','valid-foreign-digest','boolean-row','foreign-component','decision-reason'])
def test_source_lineage_mutations_rejected_without_soil_changes(tmp_path,mutation):
    t=task(tmp_path);source=Path(t['source_soil_path']);original=source.read_bytes()
    sidecar=Path(str(source)+'.retention.json');data=json.loads(sidecar.read_text());row=data['lineage'][0][0]
    if mutation=='foreign-horizon': row['chkey']='foreign-horizon'
    if mutation=='numeric-foreign-horizon': row['chkey']='999'
    if mutation=='bad-digest': row['source_receipt_sha256']='not-a-digest'
    if mutation=='valid-foreign-digest': row['source_receipt_sha256']='b'*64
    if mutation=='boolean-row': row['source_row']=False
    if mutation=='foreign-component': row['cokey']='999'
    if mutation=='decision-reason': data['decisions'][0]['reason']='fallback-unchanged'
    sidecar.write_text(json.dumps(data))
    with pytest.raises(ValueError): r.load_source_companion(source)
    assert source.read_bytes()==original


@pytest.mark.parametrize('mutation', ['foreign-id','parent-hash','swapped-parents','parent-metadata-change'])
def test_derived_identity_requires_exact_parent_chain(tmp_path,mutation):
    source,files,_=complete_stack(tmp_path);sidecar=Path(str(source)+'.retention.json')
    data=json.loads(sidecar.read_text());original=source.read_bytes()
    if mutation=='foreign-id': data['lineage'][0][0]['chkey']='999'
    if mutation=='parent-hash': data['parents'][0]['companion_sha256']='b'*64
    if mutation=='swapped-parents': data['parents'].reverse()
    if mutation=='parent-metadata-change':
        parent=Path(files[0]+'.retention.json');p=json.loads(parent.read_text());p['status']='changed';parent.write_text(json.dumps(p))
    sidecar.write_text(json.dumps(data))
    with pytest.raises(ValueError): r.load_source_companion(source)
    assert source.read_bytes()==original


def test_default_rebuild_cannot_reuse_old_optin_treatment(tmp_path):
    t=task(tmp_path);actual_disturbed_worker()(t)
    target=Path(t['output_path']);original=target.read_bytes()
    source=Path(t['source_soil_path']);Path(str(source)+'.retention.json').unlink()
    build(candidate=False).write(str(source.parent),overwrite=True)
    assert r.load_source_companion(source) is None
    with pytest.raises(ValueError,match='Default source'):
        r.reject_stale_treatment(source,target)
    with pytest.raises(ValueError,match='Default source'):
        actual_disturbed_worker()(t)
    assert target.read_bytes()==original


def test_optin_collection_requires_all_requested_successes(monkeypatch):
    collection=ss.SurgoSoilCollection([]);collection.mukeys={1,2}
    monkeypatch.setattr(ss.SurgoCollectionWorkerViewFactory,'build',lambda self,*args:view())
    try:
        with pytest.raises(ValueError,match='exact requested success set'):
            collection.makeWeppSoils(max_workers=1,retention_policy=r.POLICY,retention_source_receipt=RECEIPT)
        assert set(collection.weppSoils)=={1}
        assert set(collection.invalidSoils)=={2}
    finally:
        collection._disconnect()


def test_stage_setting_cannot_disagree_with_actual_soil(tmp_path):
    source,_,_=complete_stack(tmp_path);target=tmp_path/'p40.sol'
    stage_worker()(('182',str(source),str(target),.01,None,.75,True,700.,False,0.,False))
    sidecar=Path(str(target)+'.retention.json');data=json.loads(sidecar.read_text());data['settings']['initial_sat']=.5
    sidecar.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='settings disagree'): r.load_source_companion(target)


@pytest.mark.parametrize('mutation', ['absolute','outside','parent-symlink','sidecar-symlink','ancestor-symlink'])
def test_metadata_cannot_read_outside_caller_root(tmp_path,monkeypatch,mutation):
    project=tmp_path/'project';project.mkdir();source,files,_=complete_stack(project)
    sidecar=Path(str(source)+'.retention.json');data=json.loads(sidecar.read_text())
    outside=tmp_path/'outside.sol';outside.write_text('must never read')
    outside_sidecar=Path(str(outside)+'.retention.json');outside_sidecar.write_text('must never read')
    if mutation=='absolute': data['parents'][0]['soil_path']=str(outside)
    if mutation=='outside': data['parents'][0]['soil_path']='../outside.sol'
    if mutation=='parent-symlink':
        link=project/'alias.sol';link.symlink_to(outside);data['parents'][0]['soil_path']='alias.sol'
    if mutation=='sidecar-symlink':
        parent_sidecar=Path(files[0]+'.retention.json');parent_sidecar.unlink();parent_sidecar.symlink_to(outside_sidecar)
    if mutation=='ancestor-symlink':
        link=project/'escape';link.symlink_to(tmp_path,target_is_directory=True);data['parents'][0]['soil_path']='escape/outside.sol'
    sidecar.write_text(json.dumps(data))
    read_bytes,read_text=Path.read_bytes,Path.read_text
    def guarded_bytes(path,*args,**kwargs):
        assert path.resolve() not in (outside,outside_sidecar), 'outside metadata read'
        return read_bytes(path,*args,**kwargs)
    def guarded_text(path,*args,**kwargs):
        assert path.resolve() not in (outside,outside_sidecar), 'outside metadata read'
        return read_text(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_bytes',guarded_bytes);monkeypatch.setattr(Path,'read_text',guarded_text)
    with pytest.raises(ValueError): r.load_source_companion(source,provenance_root=project)


def test_whole_project_relocation_without_original(tmp_path):
    import shutil
    project=tmp_path/'original';project.mkdir();source,_,_=complete_stack(project)
    runs=project/'wepp'/'runs';runs.mkdir(parents=True);target=runs/'p40.sol'
    stage_worker()(('182',str(source),str(target),.01,None,.75,True,700.,False,0.,False))
    with pytest.raises(ValueError,match='root'): r.load_source_companion(target)
    expected=r.load_source_companion(target,provenance_root=project)
    moved=tmp_path/'relocated';shutil.move(str(project),str(moved))
    assert not project.exists()
    actual=r.load_source_companion(moved/'wepp/runs/p40.sol',provenance_root=moved)
    assert actual==expected
    assert actual['parents'][0]['soil_path']=='../../multi.sol'


def output_operation(kind,tmp_path):
    if kind=='source':
        soil=build();target=tmp_path/'new.sol'
        return target,lambda:soil.write(str(tmp_path),fname=target.name)
    if kind=='treatment':
        t=task(tmp_path);return Path(t['output_path']),lambda:actual_disturbed_worker()(t)
    source,files,module=complete_stack(tmp_path)
    if kind=='stack':
        target=tmp_path/'new-stack.sol'
        return target,lambda:module.SoilMultipleOfeSynth(files).write(str(target))
    target=tmp_path/'p40.sol'
    return target,lambda:stage_worker()(('182',str(source),str(target),.01,None,.75,True,700.,False,0.,False))


@pytest.mark.parametrize('kind',['source','treatment','stack','stage'])
@pytest.mark.parametrize('location',['soil','companion'])
def test_all_optin_writers_reject_dangling_output_links(tmp_path,kind,location):
    target,operation=output_operation(kind,tmp_path)
    outside=tmp_path.parent/(tmp_path.name+'-outside')
    link=target if location=='soil' else Path(str(target)+'.retention.json')
    link.symlink_to(outside)
    with pytest.raises(FileExistsError): operation()
    assert link.is_symlink() and not outside.exists()
    if location=='companion': assert not target.exists()


@pytest.mark.parametrize('kind',['source','treatment','stack','stage'])
def test_all_optin_writers_exclusive_after_preflight_race(tmp_path,monkeypatch,kind):
    import builtins
    target,operation=output_operation(kind,tmp_path);original=builtins.open;triggered=[]
    def race(path,mode='r',*args,**kwargs):
        if Path(path)==target and mode=='x' and not triggered:
            triggered.append(True)
            with original(path,'x') as stream:stream.write('concurrent-owner')
        return original(path,mode,*args,**kwargs)
    monkeypatch.setattr(builtins,'open',race)
    with pytest.raises(FileExistsError): operation()
    assert triggered and target.read_text()=='concurrent-owner'
    assert not Path(str(target)+'.retention.json').exists()


@pytest.mark.parametrize('kind',['source','treatment','stack','stage'])
def test_all_companions_exclusive_after_preflight_race(tmp_path,monkeypatch,kind):
    target,operation=output_operation(kind,tmp_path);sidecar=Path(str(target)+'.retention.json')
    original=Path.open;triggered=[]
    def race(path,mode='r',*args,**kwargs):
        if path==sidecar and mode=='x' and not triggered:
            triggered.append(True)
            with original(path,'x') as stream:stream.write('concurrent-owner')
        return original(path,mode,*args,**kwargs)
    monkeypatch.setattr(Path,'open',race)
    with pytest.raises(FileExistsError):operation()
    assert triggered and sidecar.read_text()=='concurrent-owner'


@pytest.mark.parametrize('kind',['source','treatment','stack','stage'])
def test_optin_existing_destination_symlink_rejected_before_read(tmp_path,monkeypatch,kind):
    target,operation=output_operation(kind,tmp_path)
    outside=tmp_path.parent/(tmp_path.name+'-outside');outside.write_text('outside-owner')
    target.symlink_to(outside)
    read_text,read_bytes=Path.read_text,Path.read_bytes
    def guarded_text(path,*args,**kwargs):
        assert path.resolve()!=outside,'outside destination read'
        return read_text(path,*args,**kwargs)
    def guarded_bytes(path,*args,**kwargs):
        assert path.resolve()!=outside,'outside destination read'
        return read_bytes(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',guarded_text);monkeypatch.setattr(Path,'read_bytes',guarded_bytes)
    with pytest.raises(FileExistsError):operation()
    assert read_text(outside)=='outside-owner'
    assert target.is_symlink()


@pytest.mark.parametrize('density', ['', '  ', None])
def test_actual_forest_lookup_blank_density_is_not_an_override(tmp_path,density):
    from wepppy.nodb.mods.disturbed.disturbed import read_disturbed_land_soil_lookup
    from wepppy.nodb.mods.disturbed import disturbed
    row=read_disturbed_land_soil_lookup(str(Path(disturbed.__file__).parent/'data/disturbed_land_soil_lookup.csv'))[('loam','forest')]
    assert row['bd']==''
    t=task(tmp_path);t['replacements']=dict(row,bd=density)
    actual_disturbed_worker()(t)
    proof=r.load_source_companion(t['output_path'])
    assert proof is not None
    assert [row['values']['fc'] for row in proof['source_rows']]==[row['fc'] for row in proof['serialized_rows']]


@pytest.mark.parametrize('density',[1.2,'1.2',float('nan'),float('inf'),-1,0,True,'bad'])
def test_actual_treatment_rejects_density_changes_or_invalid_values(tmp_path,density):
    t=task(tmp_path);t['replacements']['bd']=density
    with pytest.raises(ValueError):actual_disturbed_worker()(t)
    assert not Path(t['output_path']).exists()


def _installed_spawn_stage(args):
    # Imported normally in the spawned interpreter: deliberately no initializer.
    from wepppy.nodb.core import wepp
    result=wepp.prep_soil(args)
    return result,str(Path(wepp.__file__).resolve()),hashlib.sha256(Path(wepp.__file__).read_bytes()).hexdigest()


@pytest.mark.slow
def test_real_spawn_loads_installed_staging_writer_and_emits_companion(tmp_path):
    import multiprocessing
    from wepppy.nodb.core import wepp
    source,_,_=complete_stack(tmp_path)
    target=tmp_path/'spawned.sol'
    args=('182',str(source),str(target),.01,None,.75,True,700.,False,0.,False)
    with ProcessPoolExecutor(max_workers=1,mp_context=multiprocessing.get_context('spawn')) as pool:
        result,origin,digest=pool.submit(_installed_spawn_stage,args).result(timeout=90)
    assert origin==str(Path(wepp.__file__).resolve())
    assert digest==hashlib.sha256(Path(wepp.__file__).read_bytes()).hexdigest()
    proof=r.load_source_companion(target)
    assert proof['schema']=='ssurgo-retention-stage-v3'
    assert [[row['values']['solthk'] for row in rows] for rows in proof['lineage']]==[[200,700],[200,700]]
