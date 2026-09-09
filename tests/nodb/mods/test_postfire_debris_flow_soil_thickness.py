"""Offline thickness contracts and actual source-to-artifact propagation."""
import csv
import hashlib
from pathlib import Path
import sqlite3

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from wepppy.nodb.mods.postfire_debris_flow.soil_thickness import (
    derive_component, derive_mapunits, read_cache, build_artifacts,
)

pytestmark = pytest.mark.unit
FIXTURES = Path(__file__).parent / "fixtures/postfire_debris_flow_soils"


def horizon(key, top, bottom, master="A", name=None):
    return dict(cokey="1", chkey=str(key), hzdept_r=top, hzdepb_r=bottom,
                hzthk_r=None, desgnmaster=master, hzname=name or master)


def test_contiguous_and_alternative_diagnostics():
    rows = [horizon(1, 0, 10), horizon(2, 10, 30)]
    result = derive_component(rows + [rows[0]])
    assert result["thickness_cm"] == 30
    assert result["interval_sum_cm"] == result["interval_union_cm"] == 30
    assert result["horizon_count"] == 2
    duplicate_range = derive_component(rows + [horizon(3, 0, 10)])
    assert duplicate_range["thickness_cm"] is None
    assert duplicate_range["interval_sum_cm"] == 40
    assert duplicate_range["interval_union_cm"] == 30
    assert "overlap" in duplicate_range["reason_codes"]


@pytest.mark.parametrize("rows,reason", [
    ([], "missing_horizons"),
    ([horizon(1, 1, 10)], "nonzero_start"),
    ([horizon(1, 0, 10), horizon(2, 20, 30)], "gap"),
    ([horizon(1, 0, 20), horizon(2, 10, 30)], "overlap"),
    ([horizon(1, 0, 10), horizon(1, 0, 20)], "duplicate_id_conflict"),
    ([horizon(1, -1, 10)], "invalid_depth"),
    ([horizon(1, 10, 0)], "invalid_depth"),
    ([horizon(1, 0, float('nan'))], "invalid_depth"),
    ([horizon(1, None, 10)], "invalid_depth"),
    ([horizon(1, 0, 0)], "invalid_depth"),
    ([horizon(1, 0, 10, 'C', 'Cr')], "ambiguous_material"),
    ([horizon(1, 0, 10, 'H')], "ambiguous_material"),
    ([dict(horizon(1, 0, 10), hzthk_r=20)], "thickness_conflict"),
])
def test_rejected_intervals(rows, reason):
    result = derive_component(rows)
    assert result["thickness_cm"] is None
    assert reason in result["reason_codes"]


def test_bedrock_and_weathered_sensitivity():
    rows = [horizon(1, 0, 30), horizon(2, 30, 100, 'R')]
    assert derive_component(rows)["thickness_cm"] == 30
    assert derive_component(rows, policy='all_layers')["thickness_cm"] == 100
    assert derive_component([horizon(1, 0, 20, 'R')])["status"] == "nonsoil"
    assert derive_component([horizon(1, 0, 20, 'C', 'Cr')], policy='all_layers')["thickness_cm"] == 20
    assert derive_component([horizon(1, 0, 20, 'R'), horizon(2, 20, 30)])["thickness_cm"] is None


def records():
    components = [dict(mukey='7', cokey='1', comppct_r=60, compname='a'),
                  dict(mukey='7', cokey='2', comppct_r=40, compname='b')]
    horizons = [horizon(1, 0, 30), dict(horizon(2, 0, 100), cokey='2')]
    return components, horizons


def test_weights_partial_substitution_and_units():
    c, h = records()
    _, rows = derive_mapunits(c, h)
    assert rows[0]['mean_cm'] == 58
    assert rows[0]['valid_fraction'] == 1
    _, partial = derive_mapunits(c, h[:1])
    assert partial[0]['mean_cm'] == 30
    assert partial[0]['valid_fraction'] == .6
    assert partial[0]['omitted_percentage'] == 40
    assert derive_mapunits(c, h, substituted_mukeys=['7'])[1][0]['mean_cm'] is None
    assert 100/254 == pytest.approx(39.3700787/100, abs=1e-9)


@pytest.mark.parametrize('weight', [None, -1, 101, float('inf')])
def test_invalid_component_weight(weight):
    c,h = records(); c[0]['comppct_r'] = weight
    assert derive_mapunits(c,h)[1][0]['mean_cm'] is None


def test_overfull_and_missing_weights():
    c,h=records();c[0]['comppct_r']=70
    assert 'overfull_percentage' in derive_mapunits(c,h)[1][0]['reason_codes']
    with pytest.raises(ValueError, match='Duplicate'):
        derive_mapunits(c+c,h)
    with pytest.raises(ValueError, match='Orphan'):
        derive_mapunits(c[:1],h)


def database(path, components, horizons):
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE component (mukey TEXT,cokey TEXT,compname TEXT,comppct_r REAL)')
        db.execute('CREATE TABLE chorizon (cokey TEXT,chkey TEXT,hzname TEXT,hzdept_r REAL,hzdepb_r REAL,hzthk_r REAL,desgnmaster TEXT)')
        for table, rows in [('component',components),('chorizon',horizons)]:
            cols=[r[1] for r in db.execute(f'PRAGMA table_info({table})')]
            db.executemany(f"INSERT INTO {table} VALUES ({','.join('?' for _ in cols)})",
                           [[None if r.get(col) == "" else r.get(col) for col in cols] for r in rows])
    return path


def write_raster(path, values, nodata=0):
    values=np.asarray(values,dtype='int32')
    with rasterio.open(path,'w',driver='GTiff',height=values.shape[0],width=values.shape[1],
                       count=1,dtype='int32',crs='EPSG:32611',transform=from_origin(500000,5000000,10,10),nodata=nodata) as ds:
        ds.write(values,1)
    return path


def test_readonly_boundaries(tmp_path):
    absent=tmp_path/'absent.sqlite'
    with pytest.raises(FileNotFoundError): read_cache(absent)
    assert not absent.exists()
    bad=tmp_path/'bad.sqlite';bad.write_text('not SQLite')
    with pytest.raises(sqlite3.DatabaseError):read_cache(bad)
    empty=tmp_path/'empty.sqlite'
    with sqlite3.connect(empty):pass
    with pytest.raises(ValueError,match='schema'):read_cache(empty)
    blank=database(tmp_path/'blank.sqlite',[],[])
    with pytest.raises(ValueError,match='Empty'):read_cache(blank)
    c,h=records();p=database(tmp_path/'cache ?#.sqlite',c,h)
    before=p.read_bytes(); assert len(read_cache(p)[0])==2;assert p.read_bytes()==before


def test_generated_pipeline_full_partial_unknown_water(tmp_path):
    c,h=records()
    db=database(tmp_path/'source.sqlite',c,h)
    keys=write_raster(tmp_path/'keys.tif',[[7,7],[99,0]])
    mask=write_raster(tmp_path/'mask.tif',[[1,1],[1,1]])
    before=hashlib.sha256(db.read_bytes()).hexdigest()
    rows=build_artifacts(db,keys,{'a':mask},tmp_path/'out',source_id='test')
    r=rows[0]
    assert r['valid_fraction']==.5
    assert r['known_mean_cm']==58
    assert r['known_S']==58/254
    assert r['full_S'] is None
    assert 'unknown_mukey' in r['reason_codes'] and 'outside_survey' in r['reason_codes']
    assert r['source_sha256']==before==hashlib.sha256(db.read_bytes()).hexdigest()
    with rasterio.open(tmp_path/'out/thickness_cm.tif') as ds:
        a=ds.read(1);assert a[0,0]==58;assert np.isnan(a[1,1])
    full=write_raster(tmp_path/'full.tif',[[1,1],[0,0]])
    assert build_artifacts(db,keys,{'a':full},tmp_path/'fullout',source_id='test')[0]['full_S']==58/254
    with pytest.raises(FileExistsError):build_artifacts(db,keys,{'a':mask},tmp_path/'out',source_id='test')


def test_real_public_subset(tmp_path):
    c=list(csv.DictReader((FIXTURES/'topanga_component.csv').open()))
    h=list(csv.DictReader((FIXTURES/'topanga_chorizon.csv').open()))
    db=database(tmp_path/'public.sqlite',c,h)
    cr,mu=derive_mapunits(*read_cache(db),policy='all_layers')
    assert len(cr)==64 and len(mu)==13
    assert any(r['thickness_cm'] is not None for r in cr)
    assert any('missing_horizons' in r['reason_codes'] for r in cr)
    assert sum(r['status'] == 'valid' for r in cr) == 31


@pytest.mark.parametrize('field,value', [('mukey','0'),('mukey','abc'),('cokey',None),('cokey','-1')])
def test_malformed_source_keys(field,value):
    c,h=records();c[0][field]=value
    with pytest.raises(ValueError,match='positive integer'):derive_mapunits(c,h)


@pytest.mark.parametrize('master',['L','V'])
def test_undeclared_materials(master):
    assert derive_component([horizon(1,0,30,master)])['thickness_cm'] is None


def study_module():
    import importlib.util
    path=Path(__file__).resolve().parents[3]/'docs/work-packages/20260908_staley_m3_soils/artifacts/run_study.py'
    spec=importlib.util.spec_from_file_location('soil_study_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_diagnostic_m3_propagation_and_inverse():
    study=study_module()
    row=dict(site='test',outlet='test',policy='strict_soil',support_mode='common_support',
             outside_area_range=False,ssurgo_mean_cm=100.,statsgo_mean_cm=58.)
    scenarios=study.scenarios(row,.3)
    assert len(scenarios)==21
    for r in scenarios:
        assert r['ssurgo_S']==100/254
        if r['scenario'].startswith('inverse_'):
            duration,b,ct,cf,cs=next(c for c in study.COEFFICIENTS if c[0]==r['duration_min'])
            d=ct*.3+cf*.5+cs*100/254
            assert study.probability(b+r['ssurgo_threshold_mm']*d)==pytest.approx(r['reference_probability'],abs=1e-12)
            assert r['delta_threshold_mm']<0
            assert r['delta_threshold_pct']==pytest.approx(100*r['delta_threshold_mm']/r['reference_threshold_mm'])
        else:
            assert r['delta_probability_pp']>0
            assert r['delta_probability_pp']==pytest.approx(100*(r['ssurgo_probability']-r['reference_probability']))
    assert study.probability(1000)==1
    assert study.probability(-1000)==0
    with pytest.raises(ValueError,match='denominator'):study.scenarios(row,-100)
    assert study.scenarios(dict(row,ssurgo_mean_cm=None),.3)==[]


def test_disguised_vrt_rejected_before_output(tmp_path):
    c,h=records();db=database(tmp_path/'source.sqlite',c,h)
    mask=write_raster(tmp_path/'mask.tif',[[1]])
    disguised=tmp_path/'disguised.tif'
    disguised.write_text('<VRTDataset rasterXSize="1" rasterYSize="1"><VRTRasterBand dataType="Int32" band="1"><SimpleSource><SourceFilename>/not-a-study-source.tif</SourceFilename><SourceBand>1</SourceBand></SimpleSource></VRTRasterBand></VRTDataset>')
    with pytest.raises(rasterio.errors.RasterioIOError):
        build_artifacts(db,disguised,{'a':mask},tmp_path/'out',source_id='test')
    assert not (tmp_path/'out').exists()
    keys=write_raster(tmp_path/'keys.tif',[[7]])
    with pytest.raises(rasterio.errors.RasterioIOError):
        build_artifacts(db,keys,{'a':disguised},tmp_path/'out2',source_id='test')
    assert not (tmp_path/'out2').exists()


def test_reference_sentinel_support(tmp_path):
    study=study_module()
    profile=dict(driver='GTiff',height=2,width=2,count=1,dtype='float32',crs='EPSG:32611',
                 transform=from_origin(500000,5000000,10,10),nodata=float('nan'))
    with rasterio.open(tmp_path/'site_statsgo_native.tif','w',**profile) as ds:
        ds.write(np.array([[10.,-.1],[float('nan'),0.]],dtype='float32'),1)
    values,support=study.statsgo(tmp_path,'site',profile,(2,2))
    assert values[0,0]==pytest.approx(25.4,abs=1e-4)
    assert np.isnan(values[0,1]) and np.isnan(values[1,0])
    assert values[1,1]==0
    np.testing.assert_array_equal(support,[[1,0],[0,1]])


def test_partial_component_fraction_reaches_catchment(tmp_path):
    c,h=records();db=database(tmp_path/'source.sqlite',c,h[:1])
    keys=write_raster(tmp_path/'keys.tif',[[7,7]])
    mask=write_raster(tmp_path/'mask.tif',[[1,1]])
    row=build_artifacts(db,keys,{'a':mask},tmp_path/'out',source_id='test')[0]
    assert row['valid_fraction']==.6
    assert row['known_mean_cm']==30
    assert row['full_S'] is None
    with rasterio.open(tmp_path/'out/valid_fraction.tif') as ds:
        np.testing.assert_allclose(ds.read(1),.6,atol=1e-7)


def test_nonfinite_arithmetic_and_raster_representation(tmp_path):
    c,h=records();c=c[:1];c[0]['comppct_r']=100;h=h[:1];h[0]['hzdepb_r']=1e308
    with pytest.raises(ValueError,match='Nonfinite'):derive_mapunits(c,h)
    h[0]['hzdepb_r']=1e40
    db=database(tmp_path/'large.sqlite',c,h)
    keys=write_raster(tmp_path/'keys.tif',[[7]])
    mask=write_raster(tmp_path/'mask.tif',[[1]])
    with pytest.raises(ValueError,match='Float32'):
        build_artifacts(db,keys,{'a':mask},tmp_path/'out',source_id='test')
    assert not (tmp_path/'out').exists()
