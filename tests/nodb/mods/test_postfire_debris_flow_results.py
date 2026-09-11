"""Controlled persisted-bundle composition and bounded query regressions."""
from dataclasses import replace
import json
import math
from pathlib import Path

import pandas as pd
import pytest

from wepppy.nodb.mods.postfire_debris_flow import results as r
from wepppy.nodb.mods.postfire_debris_flow import rainfall_io as io
from wepppy.nodb.mods.postfire_debris_flow.staley2017 import probability

pytestmark = pytest.mark.unit


@pytest.fixture
def inputs(tmp_path):
    # Controlled pinned artifact bytes exercise loading, not raster/scientific acceptance.
    b=tmp_path/'predictors';(b/'wbt').mkdir(parents=True)
    summary={'T':.2,'T_lower':.2,'T_upper':.2,'status':'complete','schema_version':1,
             'tool':'StaleySlopeSbs','grid':{'rows':10,'columns':10,'epsg':32612,'resolution_m':30,'west':0,'north':300},
             'parameters':{'algorithm':'Horn 3x3','dem_source':'raw','edges':'nine-valid-cells',
                           'threshold_degrees':23,'elevation_units':'m','sbs_classes':[0,1,2,3]},'counts':{'basin':10,'intersection_true':2,'intersection_false':8,'intersection_unknown':0}}
    (b/'wbt/summary.json').write_text(json.dumps(summary))
    for name in ('slope','intersection','support'):(b/f'wbt/{name}.tif').write_bytes(b'controlled boundary bytes')
    preds={k:{'value':v,'status':'available','reason':None,'units':u,
              'support':{'total_cells':10,'valid_cells':10,'coverage_fraction':1.}}
           for k,v,u in [('T',.2,'fraction'),('F',.4,'normalized_dNBR'),('S',.3,'USLE_customary')]}
    preds['F'].update(observed_mean=.4)
    preds['S'].update(multiplier=1.,observed_mean=.3)
    preds['T'].update(lower=.2,upper=.2,wbt_summary=summary)
    m={'schema_version':1,'status':'complete','availability':'complete','source_kind':'synthetic',
       'area_km2':.009,'warnings':['area_outside_study_range'],'predictors':preds,'readiness':{},
       'grid':{'shape':[10,10],'crs':'EPSG:32612','transform':[30,0,0,0,-30,300]},
       'outlet':{'type':'Point','coordinates':[30,30]},'tool':{'sha256':'a'*64},
       'sources_sha256':{'never/reopen/me':'b'*64},'prepared_sha256':{'unopened':'c'*64},
       'k_provenance':{'selected_modes':['polaris_nomograph'],'artifacts':{'nomograph':'rusle/k_polaris_nomograph.tif'},
           'statistic':'mean','near_surface_depths':['0_5','5_15'],'near_surface_weights_cm':{'0_5':5.,'5_15':10.},
           'gap_fill_policy':{'controlled':True},'gap_fill_summary':{'controlled':True},
           'mode_contract':{'polaris_nomograph':{'vfs_source':'rusle2_estimated_from_sand',
               'structure_class_mapping':'modeled_texture_proxy_v1','permeability_class_mapping':'modeled_ksat_proxy_v1',
               'cfvo_profile_fragment_adjustment':{'status':'controlled'}}}},'artifacts_sha256':{k:io.digest(b/k) for k in io.ARTIFACTS}}
    manifest=b/'manifest.json';manifest.write_text(json.dumps(m))
    p=tmp_path/'climate.parquet'
    pd.DataFrame({'prcp':[1.,1.,1.],'year':[1,1,1],'month':[1,1,1],'day_of_month':[1,1,2],
                  'peak_intensity_15':[40.,40.,0.],'peak_intensity_30':[20.,30.,40.],
                  'peak_intensity_60':[10.,20.,30.]}).to_parquet(p,index=False)
    return r.RainfallInputs(manifest,p,{str(manifest):io.digest(manifest),str(p):io.digest(p)},
                           'controlled','cligen','simulation_labels','controlled')


def build(inputs,path,**kw):
    return r.build_m1_results(inputs,path,frequency_source='noaa',return_intervals=[1,2,5,10],
                             durations=[15,30,60],target_probabilities=[.5,.75],**kw)


def catalog(path):return r.open_results(path,expected_manifest_sha256=io.digest(path/'manifest.json'))


def test_output_query_parity_and_repeat(inputs,tmp_path):
    path=tmp_path/'result';m=build(inputs,path);c=catalog(path)
    page=r.list_events(c,duration_minutes=15,sort='probability',descending=True,limit=1)
    assert page['total']==3 and page['rows'][0]['row_ordinal']==0
    second=r.list_events(c,duration_minutes=15,sort='probability',descending=True,limit=1,offset=1)
    assert second['rows'][0]['row_ordinal']==1
    details=r.get_event(c,page['rows'][0]['event_id'])['rows']
    assert len(details)==3
    for row in details:
        assert row['rainfall_mm']==10
        assert row['probability']==probability('M1',row['duration_minutes'],T=.2,F=.4,S=.3,rainfall_mm=10.)
    inverse=pd.read_parquet(path/'inverse.parquet')
    for row in inverse.itertuples():
        assert probability('M1',row.duration_minutes,T=.2,F=.4,S=.3,rainfall_mm=row.rainfall_mm)==pytest.approx(row.target_probability)
    assert set(pd.read_parquet(path/'design.parquet').reason)=={'missing_noaa'}
    other=tmp_path/'other';other_m=build(inputs,other)
    assert m==other_m
    with pytest.raises(io.RainfallError) as e:build(inputs,path)
    assert e.value.code=='output_exists'
    with pytest.raises(KeyError):r.get_event(c,'0'*64+':1')


def mutate(inputs,fn):
    m=json.loads(inputs.predictor_manifest.read_text());fn(m)
    inputs.predictor_manifest.write_text(json.dumps(m))
    return replace(inputs,expected_sha256={**inputs.expected_sha256,str(inputs.predictor_manifest):io.digest(inputs.predictor_manifest)})


def test_missing_predictors_keep_rainfall(inputs,tmp_path):
    def missing(m):
        m['predictors']['S'].update(value=None,status='unavailable',reason='missing_input')
        m['availability']='partial'
    inputs=mutate(inputs,missing)
    build(inputs,tmp_path/'partial');c=catalog(tmp_path/'partial')
    rows=r.list_events(c,duration_minutes=15)['rows']
    assert rows[0]['rainfall_mm']==10 and rows[0]['probability'] is None
    assert rows[0]['reason']=='missing_predictors'
    assert not r.list_events(c,duration_minutes=15,min_probability=0)['rows']


@pytest.mark.parametrize('change', [lambda m:m.update(status='incomplete'),
    lambda m:m.update(availability='partial'),lambda m:m['predictors']['S'].update(value=float('inf')),
    lambda m:m['predictors']['T']['support'].update(coverage_fraction=.5),
    lambda m:m['artifacts_sha256'].update({'../../escape':'a'*64})])
def test_malformed_predictor(inputs,tmp_path,change):
    inputs=mutate(inputs,change)
    with pytest.raises(io.RainfallError):build(inputs,tmp_path/'bad')


@pytest.mark.parametrize('kw', [{'limit':1001},{'limit':True},{'offset':-1},{'sort':'SELECT *'},
                               {'min_probability':float('nan')},{'year':'1'},{'descending':1}])
def test_query_limits(inputs,tmp_path,kw):
    build(inputs,tmp_path/'result')
    with pytest.raises(io.RainfallError):r.list_events(catalog(tmp_path/'result'),duration_minutes=15,**kw)


def test_incomplete_changed_and_tampered_tables(inputs,tmp_path,monkeypatch):
    path=tmp_path/'result'
    def changed(consumed, *, limits=None):
        inputs.cli_parquet.write_bytes(b'changed')
        io.recheck(consumed, limits=limits)
    monkeypatch.setattr(r,'recheck',changed)
    with pytest.raises(io.RainfallError) as e:build(inputs,path)
    assert e.value.code=='source_changed'
    assert (path/'incomplete.json').is_file() and not (path/'manifest.json').exists()
    with pytest.raises(io.RainfallError) as e:catalog_without_hash(path)
    assert e.value.code=='incomplete_output'


def catalog_without_hash(path):return r.open_results(path,expected_manifest_sha256='0'*64)


def test_output_tamper(inputs,tmp_path):
    path=tmp_path/'result';build(inputs,path)
    (path/'events.parquet').write_bytes(b'changed')
    with pytest.raises(io.RainfallError) as e:catalog(path)
    assert e.value.code=='provenance_mismatch'


@pytest.mark.parametrize('mutation', [
    lambda rows:rows[0].update(probability=.99),
    lambda rows:rows[0].update(month=13.,date_status='simulation_labels'),
    lambda rows:rows.__setitem__(1,dict(rows[0])),
    lambda rows:rows[0].update(status='unavailable',reason='missing_duration'),
])
def test_pinned_but_semantically_invalid_output(inputs,tmp_path,mutation):
    import pyarrow as pa
    import pyarrow.parquet as pq
    path=tmp_path/'result';build(inputs,path)
    p=path/'events.parquet';rows=pq.read_table(p).to_pylist();mutation(rows)
    pq.write_table(pa.Table.from_pylist(rows,schema=r.SCHEMAS['events']),p)
    m=json.loads((path/'manifest.json').read_text());m['tables']['events']['sha256']=io.digest(p)
    (path/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(io.RainfallError):catalog(path)


def test_partial_f_and_nonunique_inverse(inputs,tmp_path):
    def partial(m):
        m['predictors']['F']['support'].update(valid_cells=5,coverage_fraction=.5)
    inputs=mutate(inputs,partial)
    build(inputs,tmp_path/'partial-f')
    assert r.list_events(catalog(tmp_path/'partial-f'),duration_minutes=15)['rows'][0]['probability'] is not None
    # Controlled constant response at 15 min: T=S=0, F=0. Rebuild pinned summary.
    def constant(m):
        for key in ('T','F','S'):m['predictors'][key]['value']=0.
        m['predictors']['S']['observed_mean']=0.
        m['predictors']['F']['observed_mean']=0.
        t=m['predictors']['T'];t.update(lower=0.,upper=0.)
        summary=t['wbt_summary'];summary.update(T=0.,T_lower=0.,T_upper=0.)
        summary['counts'].update(intersection_true=0,intersection_false=10)
        p=inputs.predictor_manifest.parent/'wbt/summary.json';p.write_text(json.dumps(summary))
        m['artifacts_sha256']['wbt/summary.json']=io.digest(p)
    inputs=mutate(inputs,constant)
    baseline=probability('M1',15,T=0.,F=0.,S=0.,rainfall_mm=0.)
    path=tmp_path/'constant'
    r.build_m1_results(inputs,path,frequency_source='noaa',return_intervals=[1],durations=[15],target_probabilities=[baseline,.5])
    inverse=pd.read_parquet(path/'inverse.parquet')
    assert list(inverse.status)==['nonunique','unavailable']
    catalog(path)


@pytest.mark.parametrize('change', [
    lambda m:m.update(k_provenance=None),
    lambda m:m['predictors']['S'].update(multiplier=100.),
    lambda m:m['predictors']['F'].update(observed_mean=.5),
    lambda m:m['grid'].update(crs='EPSG:4326'),
    lambda m:m['predictors']['T']['wbt_summary']['parameters'].update(threshold_degrees=24),
    lambda m:m['predictors']['T']['wbt_summary']['counts'].update(intersection_true=3),
    lambda m:m['predictors']['T'].pop('wbt_summary'),
])
def test_predictor_semantic_checks(inputs,tmp_path,change):
    inputs=mutate(inputs,change)
    with pytest.raises(io.RainfallError) as e:build(inputs,tmp_path/'invalid')
    assert e.value.code=='invalid_input'


def test_empty_bundle_and_unavailable_null_sort(inputs,tmp_path):
    p=inputs.cli_parquet
    pd.DataFrame({'prcp':pd.Series([],dtype=float),'year':pd.Series([],dtype=float)}).to_parquet(p,index=False)
    inputs=replace(inputs,expected_sha256={**inputs.expected_sha256,str(p):io.digest(p)})
    path=tmp_path/'empty';build(inputs,path)
    assert r.list_events(catalog(path),duration_minutes=15)['rows']==[]
    df=pd.DataFrame({'prcp':[1.,1.,1.],'year':[1,1,1],'peak_intensity_15':[float('nan'),40.,40.]})
    df.to_parquet(p,index=False)
    inputs=replace(inputs,expected_sha256={**inputs.expected_sha256,str(p):io.digest(p)})
    path=tmp_path/'nulls';build(inputs,path)
    for descending in (True,False):
        rows=r.list_events(catalog(path),duration_minutes=15,sort='probability',descending=descending)['rows']
        assert [row['row_ordinal'] for row in rows]==[1,2,0]


@pytest.mark.parametrize('field,value,message', [
    ('units',{'rainfall_mm':'inches'},'Invalid result units'),
    ('identity',{},'Invalid result identity'),
])
def test_rehashed_manifest_semantics(inputs,tmp_path,field,value,message):
    path=tmp_path/'result';build(inputs,path)
    m=json.loads((path/'manifest.json').read_text());m[field]=value
    (path/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(io.RainfallError,match=message) as e:catalog(path)
    assert e.value.code=='invalid_input'


@pytest.mark.parametrize('table_name,change,message', [
    ('design','remove','Missing result combinations'),
    ('inverse','remove','Missing result combinations'),
    ('inverse','value','Inverse result disagrees'),
])
def test_rehashed_design_inverse_semantics(inputs,tmp_path,table_name,change,message):
    import pyarrow as pa
    import pyarrow.parquet as pq
    path=tmp_path/'result';build(inputs,path)
    p=path/f'{table_name}.parquet';rows=pq.read_table(p).to_pylist()
    if change=='remove':rows.pop()
    else:
        rows[0]['rainfall_mm']*=2
        rows[0]['intensity_mm_per_hour']*=2
    pq.write_table(pa.Table.from_pylist(rows,schema=r.SCHEMAS[table_name]),p)
    m=json.loads((path/'manifest.json').read_text())
    m['tables'][table_name]={'rows':len(rows),'sha256':io.digest(p)}
    (path/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(io.RainfallError,match=message) as e:catalog(path)
    assert e.value.code=='invalid_input'


def test_sparse_cli_publishes_and_reopens_all_result_families(inputs,tmp_path):
    p=inputs.cli_parquet
    pd.DataFrame({'prcp':[1.]*10,'year':list(range(1,11)),
                  'peak_intensity_15':[40.]+[0.]*9,'peak_intensity_30':[40.]*10,
                  'peak_intensity_60':[0.]*10}).to_parquet(p,index=False)
    inputs=replace(inputs,expected_sha256={**inputs.expected_sha256,str(p):io.digest(p)})
    output=tmp_path/'sparse'
    m=r.build_m1_results(inputs,output,frequency_source='cli',return_intervals=[1,2,5,10],
                         durations=[15,30,60],target_probabilities=[.5,.75])
    c=catalog(output)
    assert r.list_events(c,duration_minutes=15)['total']==10
    assert m['tables']['design']['rows']==12 and m['tables']['inverse']['rows']==6
    design=pd.read_parquet(output/'design.parquet')
    unsupported=design[(design.duration_minutes==15)&(design.return_interval_years<10)]
    assert set(unsupported.reason)=={'insufficient_positive_samples'}
    assert unsupported[['rainfall_mm','intensity_mm_per_hour','probability']].isna().all().all()
    assert list(unsupported.rank_index)==[9,4,1]
    assert set(unsupported.positive_samples)=={1}
    assert set(design[design.duration_minutes==30].status)=={'available'}
    assert set(design[design.duration_minutes==60].reason)=={'no_positive_samples'}
    assert design[(design.duration_minutes==15)&(design.return_interval_years==10)].iloc[0].rainfall_mm==10.


@pytest.mark.parametrize('missing_predictor', [False,True])
def test_reopen_rejects_clamped_rainfall_at_unsupported_rank(inputs,tmp_path,missing_predictor):
    import pyarrow as pa
    import pyarrow.parquet as pq
    if missing_predictor:
        def missing(m):
            m['predictors']['S'].update(value=None,status='unavailable',reason='missing_input')
            m['availability']='partial'
        inputs=mutate(inputs,missing)
    output=tmp_path/'supported'
    r.build_m1_results(inputs,output,frequency_source='cli',return_intervals=[1],
                       durations=[15],target_probabilities=[.5])
    p=output/'design.parquet';rows=pq.read_table(p).to_pylist()
    assert rows[0]['rainfall_mm'] is not None
    rows[0]['rank_index']=rows[0]['positive_samples']
    pq.write_table(pa.Table.from_pylist(rows,schema=r.SCHEMAS['design']),p)
    m=json.loads((output/'manifest.json').read_text());m['tables']['design']['sha256']=io.digest(p)
    (output/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(io.RainfallError,match='requires a supported positive rank') as e:catalog(output)
    assert e.value.code=='invalid_input'


def test_large_predictor_publishes_and_rechecks_without_widening_rainfall(inputs, tmp_path):
    slope = inputs.predictor_manifest.parent / 'wbt/slope.tif'
    # Sparse controlled bytes test hashing/admission, not TIFF decoding.
    with slope.open('wb') as stream:
        stream.truncate(96 * 1024 * 1024)
    manifest = json.loads(inputs.predictor_manifest.read_text())
    manifest['artifacts_sha256']['wbt/slope.tif'] = io.digest(slope, io.MAX_PREDICTOR_BYTES)
    inputs.predictor_manifest.write_text(json.dumps(manifest))
    inputs = replace(inputs, expected_sha256={**inputs.expected_sha256,
        str(inputs.predictor_manifest): io.digest(inputs.predictor_manifest)})
    with pytest.raises(io.RainfallError, match='byte limit'):
        io.digest(slope)  # Default rainfall admission is still 64 MiB.
    result = build(inputs, tmp_path/'large-results')
    assert result['status'] == 'complete'
    assert (tmp_path/'large-results/manifest.json').is_file()
    consumed, limits = {}, {}
    io.load_predictors(inputs.predictor_manifest, inputs.expected_sha256, consumed, artifact_limits=limits)
    io.recheck(consumed, limits=limits)
    with slope.open('r+b') as stream:
        stream.write(b'changed')
    with pytest.raises(io.RainfallError, match='Source changed'):
        io.recheck(consumed, limits=limits)
    with pytest.raises(io.RainfallError, match='digest mismatch'):
        io.load_predictors(inputs.predictor_manifest, inputs.expected_sha256, {})


@pytest.mark.parametrize('name,size', [
    ('slope.tif', 96*1024*1024+1),
    ('summary.json', 1024*1024+1),
])
def test_predictor_artifact_caps_before_hashing(inputs, name, size):
    artifact = inputs.predictor_manifest.parent/'wbt'/name
    with artifact.open('wb') as stream:
        stream.truncate(size)
    with pytest.raises(io.RainfallError, match='byte limit'):
        io.load_predictors(inputs.predictor_manifest, inputs.expected_sha256, {})
