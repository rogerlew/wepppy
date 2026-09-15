"""Real owner-bound source activation, native M3, NoDb acceptance/publication."""
import json
import shutil
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import rasterio

from tests.nodb.mods.test_postfire_debris_flow_production import owner_project, prepared_inputs
from tests.nodb.mods.test_postfire_debris_flow_m3_terrain import terrain
from tests.nodb.mods.test_postfire_debris_flow_production_soils import database
from wepppy.nodb.mods.postfire_debris_flow import production as p, preflight, rainfall_io as io
from wepppy.nodb.mods.postfire_debris_flow.production_soils import activate_sources, inventory
from wepppy.nodb.mods.postfire_debris_flow.source_preparation import prepare_local_sources
from wepppy.nodb.mods.postfire_debris_flow.soil_inputs import META
from wepppy.nodb.mods.postfire_debris_flow.results import open_results
from wepppy.nodb.mods.postfire_debris_flow.staley2017 import probability

pytestmark = pytest.mark.integration


@pytest.fixture(params=[(0,7),(10000,11)],ids=['western-key7','eastern-key11'])
def project(owner_project,terrain,monkeypatch,request):
    from wepppy.nodb.core import Ron, Watershed
    from wepppy.nodb.mods.disturbed import Disturbed
    wd,_ = owner_project
    offset,key = request.param
    monkeypatch.setattr(preflight,'notify',lambda wd:None)
    ron,watershed = Ron.getInstance(str(wd)),Watershed.getInstance(str(wd))
    with ron.locked():
        ron._cellsize = 10; ron._dem_db = 'ned13/2022'
    dem,mask,pointer = Path(ron.dem_fn),Path(watershed.wbt_wd)/'bound.tif',Path(watershed.wbt_wd)/'flovec.tif'
    for source,target in zip(terrain,(dem,pointer,mask)): shutil.copyfile(source,target)
    for target in (dem,pointer,mask):
        with rasterio.open(target,'r+') as ds:
            ds.transform = rasterio.Affine.translation(offset,offset)*ds.transform
    outlet = Path(watershed.wbt_wd)/'outlet.geojson'
    outlet.write_text(json.dumps({'type':'Point','coordinates':[500045+offset,3999965+offset]}))
    sbs = Path(Disturbed.getInstance(str(wd)).sbs_4class_path)
    with rasterio.open(dem) as ds: profile = ds.profile
    values = np.zeros((7,7)); values[3,2:5] = [2,3,0]
    with rasterio.open(sbs,'w',**profile) as ds: ds.write(values,1)
    database(wd/'soils/ssurgo_tabular_cache.sqlite')
    import sqlite3
    with sqlite3.connect(wd/'soils/ssurgo_tabular_cache.sqlite') as conn:
        conn.execute('UPDATE component SET mukey=?',(str(key),))
    with rasterio.open(wd/'soils/ssurgo.tif','w',**profile) as ds: ds.write(np.full((7,7),float(key)),1)
    catalog = wd/'lineage.json'
    io.write_json(catalog,dict(schema_version=1,collection_by_mukey={str(key):'SSURGO'},source='analytical fixture',retrieved_at='2026-09-14'))
    pd.DataFrame({'prcp':[10.]*30,'year':list(range(1,31)),'month':[1]*30,'day_of_month':[1]*30,
                  'peak_intensity_15':[40.]*30,'peak_intensity_30':[20.]*30,'peak_intensity_60':[10.]*30}).to_parquet(wd/'climate/wepp_cli.parquet')
    downstream=wd/'wepp/runs';downstream.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(wd/'soils/123.sol',downstream/'p1.sol')
    (downstream/'p1.run').write_text('retained soil reference: p1.sol\n')
    return wd,dem,mask,catalog


def protected(wd):
    paths=[wd/'soils.nodb',wd/'rusle.nodb']
    for name in ('soils','rusle','wepp/runs'):
        paths.extend((wd/name).rglob('*'))
    return {str(path):io.digest(path,512*1024*1024) for path in paths if path.is_file()}


def enqueue_m3(wd):
    identity = uuid.uuid4().hex
    snapshot = dict(inputs=p.sources(wd,model='M3')[4],dnbr=None,frequency='cli')
    p.mutable(wd).change(lambda state:state.update(model='M3',frequency_source='cli',
        run_attempt=dict(id=identity,model='M3',phase='queued',created_at=p.now(),
                         retryable=False,job_id=None,snapshot=snapshot)))
    return identity


def test_fresh_basin_run_prepares_sources_and_reuses_them(project,monkeypatch):
    from wepppy.nodb.mods.postfire_debris_flow import source_acquisition
    wd,dem,mask,catalog = project
    before = protected(wd)
    calls = []
    def acquire(root,source_dem,source_mask):
        assert (root,source_dem,source_mask) == (wd,dem,mask)
        calls.append(root)
        return prepare_local_sources(root,source_dem,source_mask,collection_catalog=catalog)
    monkeypatch.setattr(source_acquisition,'acquire_sources',acquire)
    assert not (wd/META).exists()
    identity = enqueue_m3(wd)
    assert p.get_state(wd,'config',model='M3',reconcile=False)['run_ready']
    assert calls == []  # State inspection must not acquire.
    p.execute_m3(wd,identity)
    assert calls == [wd]
    assert p.state_at(wd)['last_successful_run']['coverage']['valid_cells'] == 3
    assert p.get_state(wd,'config',model='M3',reconcile=False)['freshness'] == 'current'
    assert pd.read_parquet(p.directory(wd,identity)/'results/events.parquet').probability.notna().all()
    # A new absent-pointer preparation can commit before later calculation fails.
    (wd/META).unlink()
    failed = enqueue_m3(wd)
    def fail_results(*args,**kwargs): raise OSError('injected post-promotion failure')
    with monkeypatch.context() as patch:
        patch.setattr(p,'build_results',fail_results)
        with pytest.raises(OSError,match='post-promotion'): p.execute_m3(wd,failed)
    assert (wd/META).exists()
    assert p.state_at(wd)['last_successful_run']['id'] == identity
    retried = enqueue_m3(wd)
    p.execute_m3(wd,retried)
    assert calls == [wd,wd]  # The retry reuses the promotion from the failed run.
    assert protected(wd) == before


@pytest.mark.parametrize('change',['attempt','model','frequency','sbs','wal','pointer'])
def test_first_run_rejects_changes_before_promotion(project,monkeypatch,change):
    import sqlite3
    from wepppy.nodb.mods.postfire_debris_flow import source_acquisition
    from wepppy.nodb.mods.disturbed import Disturbed
    wd,dem,mask,catalog = project
    identity = enqueue_m3(wd)
    connections = []
    def acquire(*args):
        receipt = prepare_local_sources(wd,dem,mask,collection_catalog=catalog)
        if change == 'attempt': enqueue_m3(wd)
        elif change == 'model': p.mutable(wd).change(lambda state:state.update(model='M1'))
        elif change == 'frequency': p.mutable(wd).change(lambda state:state.update(frequency_source='noaa'))
        elif change == 'pointer':
            pointer = wd/META; pointer.parent.mkdir(parents=True,exist_ok=True)
            io.write_json(pointer,{'schema_version':1})
        elif change == 'sbs':
            with rasterio.open(Disturbed.getInstance(str(wd)).sbs_4class_path,'r+') as ds:
                ds.write(np.ones(ds.shape),1)
        else:
            connection = sqlite3.connect(wd/'soils/ssurgo_tabular_cache.sqlite')
            connections.append(connection)
            connection.execute('PRAGMA journal_mode=WAL')
            connection.execute('UPDATE chorizon SET hzdepb_r=120'); connection.commit()
        return receipt
    monkeypatch.setattr(source_acquisition,'acquire_sources',acquire)
    try:
        with pytest.raises((p.WorkflowError,io.RainfallError)):
            p.execute_m3(wd,identity)
        assert p.state_at(wd)['last_successful_run'] is None
        assert (wd/META).exists() == (change == 'pointer')
    finally:
        for connection in connections: connection.close()


@pytest.mark.parametrize('change',['attempt','pointer','sbs'])
def test_first_run_rejects_changes_after_real_promotion(project,monkeypatch,change):
    from wepppy.nodb.mods.postfire_debris_flow import source_acquisition, production_soils
    from wepppy.nodb.mods.disturbed import Disturbed
    wd,dem,mask,catalog = project
    identity = enqueue_m3(wd)
    monkeypatch.setattr(source_acquisition,'acquire_sources',
                        lambda *args:prepare_local_sources(wd,dem,mask,collection_catalog=catalog))
    activate = production_soils.activate_sources
    def changed(*args,**kwargs):
        result = activate(*args,**kwargs)
        if change == 'attempt': enqueue_m3(wd)
        elif change == 'pointer': (wd/META).write_text(json.dumps({'schema_version':1}))
        else:
            with rasterio.open(Disturbed.getInstance(str(wd)).sbs_4class_path,'r+') as ds:
                ds.write(np.ones(ds.shape),1)
        return result
    monkeypatch.setattr(production_soils,'activate_sources',changed)
    with pytest.raises(p.WorkflowError): p.execute_m3(wd,identity)
    assert (wd/META).exists()  # Do not roll back a committed pointer.
    assert p.state_at(wd)['last_successful_run'] is None


def test_failed_acquisition_preserves_previous_result(project,monkeypatch):
    from wepppy.nodb.mods.postfire_debris_flow import source_acquisition
    wd,dem,mask,catalog = project
    identity = enqueue_m3(wd)
    previous = dict(id=uuid.uuid4().hex,model='M3',snapshot={},artifacts={})
    # Set a retained prior result without invoking unrelated publication machinery.
    controller = p.mutable(wd)
    with controller.locked(): controller._state['last_successful_run'] = previous
    def fail(*args):
        prepare_local_sources(wd,dem,mask)
        raise TimeoutError('bounded acquisition failure')
    monkeypatch.setattr(source_acquisition,'acquire_sources',fail)
    with pytest.raises(TimeoutError,match='bounded acquisition'): p.execute_m3(wd,identity)
    assert p.state_at(wd)['last_successful_run'] == previous
    assert list((wd/'postfire_debris_flow/source_preparation').glob('*/receipt.json'))
    assert not (wd/META).exists()


@pytest.mark.parametrize('available',[True,False])
def test_owner_bound_m3_executes_and_publishes_without_dnbr_k(project,available,monkeypatch):
    wd,dem,mask,catalog = project
    before = protected(wd)
    receipt = prepare_local_sources(wd,dem,mask,collection_catalog=catalog if available else None)
    assert activate_sources(wd,receipt,expected_sha256=io.digest(receipt))['status'] == 'committed'
    eligible,readonly,checks,paths,snapshot = p.sources(wd,model='M3')
    assert eligible and not readonly and all(v for k,v in checks.items() if k != 'noaa')
    identity = uuid.uuid4().hex
    controller = p.mutable(wd)
    controller.change(lambda state:state.update(run_attempt=dict(id=identity,model='M3',phase='queued',
        created_at=p.now(),retryable=False,job_id=None,snapshot=dict(inputs=snapshot,dnbr=None,frequency='cli'))))
    p.execute_m3(wd,identity)
    accepted = p.state_at(wd)['last_successful_run']
    assert accepted['model'] == 'M3' and accepted['coverage']['valid_cells'] == (3 if available else 0)
    output = p.directory(wd,identity)/'results'
    result = open_results(output,expected_manifest_sha256=io.digest(output/'manifest.json'))
    if available:
        for event in result.events.to_pylist():
            assert event['probability'] == probability('M3',event['duration_minutes'],T=30/np.sqrt(300),F=2/3,S=100/254,rainfall_mm=event['rainfall_mm'])
    else:
        assert all(event['probability'] is None for event in result.events.to_pylist())
    assert (wd/'postfire_debris_flow/valid_mask.tif').read_bytes() == (output/'valid_mask.tif').read_bytes()
    assert protected(wd) == before
    public = p.get_state(wd,'config',model='M3',reconcile=False)
    assert public['freshness'] == 'current'
    assert 'valid_mask.tif' in [f['name'] for f in public['results']['files']]
    assert public['results']['coverage'] == accepted['coverage']
    assert public['results']['partial_reason'] == (None if available else 'No watershed cells have all required spatial inputs.')
    # Genuine native preparation followed by a result-boundary failure and retry.
    def enqueue():
        next_id=uuid.uuid4().hex
        controller.change(lambda state:state.update(run_attempt=dict(id=next_id,model='M3',phase='queued',
            created_at=p.now(),retryable=False,job_id=None,snapshot=dict(inputs=p.sources(wd,model='M3')[4],dnbr=None,frequency='cli'))))
        return next_id
    failed=enqueue()
    def fail_results(*args,**kwargs):raise OSError('injected result writer failure')
    with monkeypatch.context() as patch:
        patch.setattr(p,'build_results',fail_results)
        with pytest.raises(OSError,match='injected result writer failure'):p.execute_m3(wd,failed)
    assert p.state_at(wd)['last_successful_run']['id']==identity
    assert protected(wd)==before
    retried=enqueue();p.execute_m3(wd,retried)
    assert p.state_at(wd)['last_successful_run']['id']==retried
    assert protected(wd)==before


def test_authoritative_activation_rejects_other_mask_and_external_receipt(project):
    wd,dem,mask,catalog = project
    other = wd/'other_mask.tif'; shutil.copyfile(mask,other)
    receipt = prepare_local_sources(wd,dem,other,collection_catalog=catalog)
    with pytest.raises(io.RainfallError,match='authoritative basin inputs'):
        activate_sources(wd,receipt,expected_sha256=io.digest(receipt))
    assert not (wd/META).exists()
    with pytest.raises(io.RainfallError,match='remain in this project'):
        activate_sources(wd,wd.parent/'external.json',expected_sha256='a'*64)


def test_optional_source_appearance_and_wal_change_affect_inventory(project):
    import sqlite3
    wd,_,_,_ = project
    initial = inventory(wd)
    path = wd/META; path.parent.mkdir(parents=True,exist_ok=True)
    io.write_json(path,{'schema_version':1})
    assert inventory(wd) != initial
    connection = sqlite3.connect(wd/'soils/ssurgo_tabular_cache.sqlite')
    try:
        connection.execute('PRAGMA journal_mode=WAL'); connection.commit()
        before = inventory(wd)
        connection.execute('UPDATE chorizon SET hzdepb_r=120'); connection.commit()
        assert inventory(wd) != before
    finally:
        connection.close()


def test_authority_change_before_locked_promotion_preserves_absence(project,monkeypatch):
    from wepppy.nodb.core import Ron
    from wepppy.nodb.mods.postfire_debris_flow import source_preparation as preparation
    wd,dem,mask,catalog = project
    receipt = prepare_local_sources(wd,dem,mask,collection_catalog=catalog)
    copy = preparation._copy
    def changed(source,target,*args,**kwargs):
        copy(source,target,*args,**kwargs)
        if target.name.startswith('promotion-'):
            ron = Ron.getInstance(str(wd))
            with ron.locked(): ron._cellsize = 30
    monkeypatch.setattr(preparation,'_copy',changed)
    with pytest.raises(p.WorkflowError,match='eligible 10 m basin'):
        activate_sources(wd,receipt,expected_sha256=io.digest(receipt))
    assert not (wd/META).exists()


@pytest.mark.parametrize('change',['wal','eligibility'])
def test_source_or_authority_change_after_results_refuses_acceptance(project,monkeypatch,change):
    import sqlite3
    wd,dem,mask,catalog = project
    receipt = prepare_local_sources(wd,dem,mask,collection_catalog=catalog)
    activate_sources(wd,receipt,expected_sha256=io.digest(receipt))
    connection = sqlite3.connect(wd/'soils/ssurgo_tabular_cache.sqlite')
    connection.execute('PRAGMA journal_mode=WAL'); connection.commit()
    snapshot = p.sources(wd,model='M3')[4]
    identity = uuid.uuid4().hex
    p.mutable(wd).change(lambda state:state.update(run_attempt=dict(id=identity,model='M3',phase='queued',
        created_at=p.now(),retryable=False,job_id=None,snapshot=dict(inputs=snapshot,dnbr=None,frequency='cli'))))
    build = p.build_results
    def changed(*args,**kwargs):
        result = build(*args,**kwargs)
        if change == 'wal':
            connection.execute('UPDATE chorizon SET hzdepb_r=120'); connection.commit()
        else:
            from wepppy.nodb.core import Ron
            ron = Ron.getInstance(str(wd))
            with ron.locked(): ron._mods.remove('postfire_debris_flow')
        return result
    monkeypatch.setattr(p,'build_results',changed)
    try:
        with pytest.raises(ValueError,match='Soil source changed|Inputs changed'):
            p.execute_m3(wd,identity)
        assert p.state_at(wd)['last_successful_run'] is None
        assert not (wd/'postfire_debris_flow/manifest.json').exists()
        assert (p.directory(wd,identity)/'results/manifest.json').is_file()
    finally:
        connection.close()
