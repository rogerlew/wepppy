"""Real native M3 composition with independently calculated common support."""
import json
import numpy as np
import sqlite3
import pytest
import rasterio

from tests.nodb.mods.test_postfire_debris_flow_m3_terrain import BINARY, terrain
from tests.nodb.mods.test_postfire_debris_flow_production_soils import database
from wepppy.nodb.mods.postfire_debris_flow import rainfall_io as io
from wepppy.nodb.mods.postfire_debris_flow.m3_integration import M3Inputs, build_m3_predictors
from wepppy.nodb.mods.postfire_debris_flow.source_preparation import prepare_local_sources
from wepppy.nodb.mods.postfire_debris_flow.soil_inputs import META, SOURCE_ID

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('missing', ['none', 'one', 'all'])
@pytest.mark.parametrize('depth', [100,300])
@pytest.mark.parametrize('terrain_valid', [True,False])
def test_common_support_does_not_shrink_full_basin_terrain(terrain, tmp_path, missing, depth, terrain_valid):
    dem,pointer,mask = terrain
    if not terrain_valid:
        with rasterio.open(mask,'r+') as ds:
            values = ds.read(1); values[3,2] = 0; ds.write(values,1)
    soils = tmp_path/'soils'; soils.mkdir()
    database(soils/'ssurgo_tabular_cache.sqlite')
    with sqlite3.connect(soils/'ssurgo_tabular_cache.sqlite') as connection:
        connection.execute('UPDATE chorizon SET hzdepb_r=?',(depth,))
    with rasterio.open(dem) as ds:
        profile = ds.profile.copy()
    with rasterio.open(soils/'ssurgo.tif','w',**profile) as ds:
        ds.write(np.full((7,7),7,dtype='float64'),1)
    catalog = tmp_path/'catalog.json'
    io.write_json(catalog, dict(schema_version=1, collection_by_mukey={'7':'SSURGO'},
                               source='analytical fixture',retrieved_at='2026-09-14'))
    receipt = prepare_local_sources(tmp_path,dem,mask,collection_catalog=catalog)
    target = tmp_path/META; target.parent.mkdir()
    target.write_bytes((receipt.parent/'soil_sources.json').read_bytes())
    sbs = tmp_path/'sbs.tif'
    values = np.zeros((7,7),dtype='float64'); values[3,2:5] = [2,3,0]
    if missing == 'one':
        values[3,2] = -9999
    elif missing == 'all':
        values[3,2:5] = -9999
    with rasterio.open(sbs,'w',**profile) as ds:
        ds.write(values,1)
    outlet = tmp_path/'outlet.geojson'
    io.write_json(outlet, {'type':'Feature','properties':{},
        'geometry':{'type':'Point','coordinates':[500045,3999965]}})
    expected = {str(p):io.digest(p) for p in (*terrain,sbs,outlet)}
    inputs = M3Inputs(tmp_path,dem,pointer,mask,outlet,sbs,expected,io.digest(BINARY),'synthetic')
    output = tmp_path/'predictors'
    result = build_m3_predictors(inputs,output,wbt_executable=BINARY)
    if terrain_valid:
        assert result['predictors']['T']['value'] == pytest.approx(30/np.sqrt(300))
    else:
        assert result['predictors']['T']['value'] is None
        assert result['predictors']['T']['reason'] == 'watershed_area_mismatch'
    if missing == 'all':
        assert result['predictors']['F']['value'] is None
        assert result['predictors']['S']['value'] is None
        assert result['availability'] == ('partial' if terrain_valid else 'unavailable')
    else:
        assert result['predictors']['F']['value'] == pytest.approx(.5 if missing == 'one' or not terrain_valid else 2/3)
        assert result['predictors']['S']['value'] == pytest.approx(depth/254)
    assert result['coverage']['valid_cells'] == {'none':3 if terrain_valid else 2,'one':2,'all':0}[missing]
    manifest = output/'manifest.json'
    io.load_predictors(manifest, {str(manifest):io.digest(manifest)}, {})
    if depth == 100 and missing == 'one' and terrain_valid:
        import pandas as pd
        import shutil
        from wepppy.nodb.mods.postfire_debris_flow.results import RainfallInputs, build_results, open_results
        from wepppy.nodb.mods.postfire_debris_flow.staley2017 import probability
        climate = tmp_path/'climate.parquet'
        pd.DataFrame({'prcp':[10.], 'year':[1], 'month':[1], 'day_of_month':[1],
                      'peak_intensity_15':[40.], 'peak_intensity_30':[20.], 'peak_intensity_60':[10.]}).to_parquet(climate,index=False)
        rainfall = RainfallInputs(manifest,climate,{str(manifest):io.digest(manifest),str(climate):io.digest(climate)},
                                  'fixture','cligen','simulation_labels','fixture')
        results = tmp_path/'results'
        built = build_results(rainfall,results,frequency_source='cli',return_intervals=[1,2,5,10],
                              durations=[15,30,60],target_probabilities=[.5],expected_model='M3')
        assert built['model'] == 'M3' and built['coverage'] == result['coverage']
        assert (results/'valid_mask.tif').read_bytes() == (output/'valid_mask.tif').read_bytes()
        archive = tmp_path/'archive'; shutil.copytree(results,archive)
        catalog = open_results(archive,expected_manifest_sha256=io.digest(archive/'manifest.json'))
        for event in catalog.events.to_pylist():
            assert event['probability'] == probability('M3',event['duration_minutes'],T=30/np.sqrt(300),F=.5,S=100/254,
                                                        rainfall_mm=event['rainfall_mm'])
        for inverse in pd.read_parquet(archive/'inverse.parquet').to_dict('records'):
            if inverse['status'] == 'available':
                assert probability('M3',inverse['duration_minutes'],T=30/np.sqrt(300),F=.5,S=100/254,
                                   rainfall_mm=inverse['rainfall_mm']) == pytest.approx(.5)
        built['model'] = 'M1'
        (archive/'manifest.json').write_text(json.dumps(built))
        with pytest.raises(io.RainfallError,match='model identities'):
            open_results(archive,expected_manifest_sha256=io.digest(archive/'manifest.json'))
    if missing == 'none' and depth == 100:
        result['predictors']['F']['value'] = .1
        manifest.write_text(json.dumps(result))
        with pytest.raises(io.RainfallError,match='F differs'):
            io.load_predictors(manifest,{str(manifest):io.digest(manifest)}, {})
        result['predictors']['F']['value'] = 2/3 if terrain_valid else .5
        # Preserve counts and hashes while replacing one domain cell. Reader
        # must bind membership, not merely accept internally consistent totals.
        with rasterio.open(output/'valid_mask.tif','r+') as ds:
            values = ds.read(1); values[3,3] = 255; values[2,4] = 1; ds.write(values,1)
        result['artifacts_sha256']['valid_mask.tif'] = io.digest(output/'valid_mask.tif')
        manifest.write_text(json.dumps(result))
        with pytest.raises(io.RainfallError,match='authoritative watershed'):
            io.load_predictors(manifest,{str(manifest):io.digest(manifest)}, {})


def test_mixed_nonuniform_soil_and_disjoint_missing_cells(terrain,tmp_path):
    dem,pointer,mask = terrain
    with rasterio.open(dem) as ds:
        profile = ds.profile.copy()
        grid = {'shape':list(ds.shape),'crs':str(ds.crs),'transform':list(ds.transform)[:6]}
        bounds = list(ds.bounds)
    def write(path,values):
        with rasterio.open(path,'w',**profile) as ds:
            ds.write(np.asarray(values,dtype='float64'),1)
    routing = np.zeros((7,7)); routing[3,:4] = 2; write(pointer,routing)
    domain = np.zeros((7,7)); domain[3,:5] = 1; write(mask,domain)
    soils = tmp_path/'soils'; soils.mkdir()
    database(soils/'ssurgo_tabular_cache.sqlite')
    keys = np.full((7,7),8); keys[3,0] = 7; write(soils/'ssurgo.tif',keys)
    catalog = tmp_path/'catalog.json'
    io.write_json(catalog,dict(schema_version=1,collection_by_mukey={'7':'SSURGO','8':'STATSGO'},
                              source='mixed fixture',retrieved_at='2026-09-14'))
    native = tmp_path/'thick.tif'
    inches = np.ones((7,7)); inches[3,:5] = [10,20,-9999,40,50]; write(native,inches)
    evidence = tmp_path/'thick_evidence.json'
    io.write_json(evidence,dict(schema_version=1,source_id=SOURCE_ID,source='native fixture',
                               sha256=io.digest(native),grid=grid,bounds=bounds))
    receipt = prepare_local_sources(tmp_path,dem,mask,collection_catalog=catalog,thick=native,thick_evidence=evidence)
    target = tmp_path/META; target.parent.mkdir(); target.write_bytes((receipt.parent/'soil_sources.json').read_bytes())
    sbs = tmp_path/'sbs.tif'
    severity = np.zeros((7,7)); severity[3,:5] = [2,0,3,-9999,3]; write(sbs,severity)
    outlet = tmp_path/'outlet.geojson'
    io.write_json(outlet,{'type':'Feature','properties':{},'geometry':{'type':'Point','coordinates':[500045,3999965]}})
    expected = {str(p):io.digest(p) for p in (*terrain,sbs,outlet)}
    inputs = M3Inputs(tmp_path,dem,pointer,mask,outlet,sbs,expected,io.digest(BINARY),'synthetic')
    output = tmp_path/'predictors'
    result = build_m3_predictors(inputs,output,wbt_executable=BINARY)
    assert result['predictors']['T']['reason'] == 'terrain_potentially_truncated'
    assert result['predictors']['F']['value'] == pytest.approx(2/3)
    assert result['predictors']['S']['value'] == pytest.approx((100+20*2.54+50*2.54)/3/254)
    assert result['coverage']['valid_cells'] == 3
    assert result['coverage']['primary_valid_cells'] == 1
    assert result['coverage']['fallback_valid_cells'] == 2
    manifest = output/'manifest.json'
    io.load_predictors(manifest,{str(manifest):io.digest(manifest)}, {})
