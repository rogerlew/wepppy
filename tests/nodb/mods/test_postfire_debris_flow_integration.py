"""Actual file/binary checks for the trusted local M1 composition boundary."""
from dataclasses import replace
import json
import os
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from wepppy.nodb.mods.postfire_debris_flow import integration as m1
from wepppy.nodb.mods.postfire_debris_flow.dnbr import normalize_dnbr
from wepppy.nodb.mods.postfire_debris_flow.m1_inputs import digest

pytestmark = pytest.mark.integration
BINARY = Path(os.environ.get('STALEY_WBT_EXECUTABLE', '/workdir/weppcloud-wbt/target/release/whitebox_tools'))


def raster(path, a, *, nodata=-9999, transform=None, palette=False, mask=None):
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(path, 'w', driver='GTiff', height=a.shape[0], width=a.shape[1], count=1,
                           dtype=a.dtype, crs='EPSG:32611', transform=transform or from_origin(500000, 4000000, 30, 30),
                           nodata=nodata, compress='deflate') as dst:
            dst.write(a, 1)
            if palette:
                dst.write_colormap(1, {0: (0, 0, 0, 255), 1: (255, 0, 0, 255), 2: (0, 255, 0, 255), 3: (0, 0, 255, 255)})
            if mask is not None:
                dst.write_mask(mask.astype('uint8')*255)


def refresh(inputs):
    paths = [inputs.dem, inputs.mask, inputs.sbs, inputs.outlet, inputs.k, inputs.k_manifest,
             inputs.dnbr, inputs.dnbr_manifest, *inputs.lineage_sources]
    hashes = {str(Path(p).absolute()): digest(p) for p in paths if p is not None}
    for p in list(hashes):
        sidecar = Path(p + '.msk')
        if sidecar.exists():
            hashes[str(sidecar)] = digest(sidecar)
    return replace(inputs, expected_sha256=hashes)


@pytest.fixture
def inputs(tmp_path):
    if not BINARY.is_file():
        pytest.skip('Actual StaleySlopeSbs executable unavailable; set STALEY_WBT_EXECUTABLE')
    source = tmp_path / 'sources'
    source.mkdir()
    dem = np.tile(np.arange(7, dtype='float64')*30, (7, 1))
    mask = np.zeros((7, 7), dtype='int16'); mask[1:-1, 1:-1] = 1
    raster(source/'dem.tif', dem)
    raster(source/'mask.tif', mask)
    raster(source/'sbs.tif', np.full((7, 7), 3, dtype='uint8'), nodata=255, palette=True)
    raster(source/'k_polaris_nomograph.tif', np.full((7, 7), .3))
    raster(source/'raw-dnbr.tif', np.full((7, 7), 400, dtype='int16'))
    (source/'outlet.geojson').write_text(json.dumps({'type':'Point','coordinates':[500045,3999955]}))
    k = {'selected_modes':['polaris_nomograph'], 'artifacts':{'nomograph':'rusle/k_polaris_nomograph.tif'},
         'statistic':'mean','near_surface_depths':['0_5','5_15'],'near_surface_weights_cm':{'0_5':5.,'5_15':10.},
         'gap_fill_policy':{'enabled':True}, 'gap_fill_summary':{'synthetic':True},
         'mode_contract':{'polaris_nomograph':{'vfs_source':'rusle2_estimated_from_sand',
             'structure_class_mapping':'modeled_texture_proxy_v1','permeability_class_mapping':'modeled_ksat_proxy_v1',
             'cfvo_profile_fragment_adjustment':{'status':'unavailable'}}}}
    (source/'manifest.json').write_text(json.dumps({'k':k}))
    normalize_dnbr(source/'raw-dnbr.tif', source/'dem.tif', source/'mask.tif', source/'normalized', scale_factor=.001)
    return refresh(m1.M1Inputs(dem=source/'dem.tif', mask=source/'mask.tif', outlet=source/'outlet.geojson',
                   sbs=source/'sbs.tif', k=source/'k_polaris_nomograph.tif', k_manifest=source/'manifest.json',
                   dnbr=source/'normalized/dnbr.tif', dnbr_manifest=source/'normalized/manifest.json',
                   lineage_sources=(source/'raw-dnbr.tif',), expected_sha256={},
                   wbt_sha256=digest(BINARY), source_kind='synthetic'))


def build(inputs, tmp_path):
    return m1.build_m1_predictors(inputs, tmp_path/'result', wbt_executable=BINARY)


def test_complete_actual_binary_and_scenarios(inputs, tmp_path):
    bundle = build(inputs, tmp_path)
    assert bundle['availability'] == 'complete'
    assert [bundle['predictors'][k]['value'] for k in ('T','F','S')] == pytest.approx([1,.4,.3])
    assert all(p['support']['total_cells'] == 25 for p in bundle['predictors'].values())
    assert bundle['warnings'] == ['area_outside_study_range']
    assert not (tmp_path/'result/incomplete.json').exists()
    assert json.loads((tmp_path/'result/manifest.json').read_text()) == bundle
    assert all(digest(p) == h for p,h in inputs.expected_sha256.items())
    with rasterio.open(tmp_path/'result/prepared/sbs.tif') as ds:
        assert ds.dtypes == ('int16',)
        assert np.all(ds.read(1) == 3)  # palette indices, not RGB
    rows = m1.evaluate_m1_scenarios(bundle, [(15,10),(30,20),(60,30)])
    assert all(0 < r['probability'] < 1 for r in rows)


@pytest.mark.parametrize('value', [0., -.4])
def test_zero_and_negative_dnbr(inputs, tmp_path, value):
    raster(inputs.dnbr, np.full((7,7), value))
    m = json.loads(inputs.dnbr_manifest.read_text());m['dnbr_sha256']=digest(inputs.dnbr)
    inputs.dnbr_manifest.write_text(json.dumps(m))
    b = build(refresh(inputs), tmp_path)
    assert b['predictors']['F']['value'] == pytest.approx(value)


@pytest.mark.parametrize('missing', ['k','dnbr','k_manifest','dnbr_manifest'])
def test_missing_independent_inputs(inputs, tmp_path, missing):
    b = build(refresh(replace(inputs, **{missing:None})), tmp_path)
    key = 'S' if missing.startswith('k') else 'F'
    assert b['predictors'][key]['value'] is None
    assert b['predictors']['T']['value'] == 1
    assert m1.evaluate_m1_scenarios(b, [(15,10)])[0]['probability'] is None


@pytest.mark.parametrize('bad', [-9999., -1., 1.1, float('nan')])
def test_incomplete_k_keeps_diagnostics(inputs, tmp_path, bad):
    a = np.full((7,7), .3);a[2,2] = bad;raster(inputs.k, a)
    b = build(refresh(inputs), tmp_path)
    s = b['predictors']['S']
    assert s['value'] is None and s['support']['valid_cells'] == 24
    assert s['observed_mean'] == pytest.approx(.3)
    assert b['predictors']['F']['value'] == pytest.approx(.4)


def test_valid_zero_k_and_t(inputs, tmp_path):
    raster(inputs.k, np.zeros((7,7)))
    raster(inputs.sbs, np.zeros((7,7), dtype='int16'), nodata=255)
    b = build(refresh(inputs), tmp_path)
    assert b['predictors']['S']['value'] == b['predictors']['T']['value'] == 0


@pytest.mark.parametrize('empty', [False, True])
def test_partial_empty_dnbr(inputs, tmp_path, empty):
    a = np.full((7,7), -9999. if empty else .4);a[2,2] = -9999.
    raster(inputs.dnbr, a)
    m = json.loads(inputs.dnbr_manifest.read_text());m['dnbr_sha256'] = digest(inputs.dnbr)
    inputs.dnbr_manifest.write_text(json.dumps(m))
    f = build(refresh(inputs), tmp_path)['predictors']['F']
    assert f['value'] is None if empty else f['value'] == pytest.approx(.4)
    assert f['support']['valid_cells'] == (0 if empty else 24)


def test_unknown_t_does_not_erase_f_s(inputs, tmp_path):
    a = np.full((7,7), 3, dtype='int16');a[2,2] = 255;raster(inputs.sbs, a, nodata=255)
    b = build(refresh(inputs), tmp_path)
    assert b['predictors']['T']['value'] is None
    assert b['predictors']['T']['lower'] == 24/25
    assert b['predictors']['T']['upper'] == 1
    assert b['predictors']['S']['value'] == pytest.approx(.3)


@pytest.mark.parametrize('case', ['legacy','epic','malformed','stale'])
def test_k_provenance(inputs, tmp_path, case):
    m = json.loads(inputs.k_manifest.read_text())
    if case == 'legacy': del m['k']['gap_fill_summary']
    if case == 'epic': m['k']['selected_modes']=['polaris_epic']
    if case == 'malformed': m['k']['mode_contract']=[]
    if case == 'stale': m['k']['statistic']='median'
    inputs.k_manifest.write_text(json.dumps(m));inputs=refresh(inputs)
    if case == 'legacy':
        assert build(inputs,tmp_path)['predictors']['S']['reason'] == 'missing_provenance'
    else:
        with pytest.raises(m1.M1Error, match='K'):
            build(inputs,tmp_path)
        assert (tmp_path/'result/incomplete.json').exists()
        assert not (tmp_path/'result/manifest.json').exists()


@pytest.mark.parametrize('field', ['dem','mask','sbs','k','dnbr'])
def test_source_digest_mismatch(inputs, tmp_path, field):
    with Path(getattr(inputs,field)).open('ab') as f:f.write(b'changed')
    with pytest.raises(m1.M1Error) as e: build(inputs,tmp_path)
    assert e.value.code == 'provenance_mismatch'


def test_grid_mismatch_and_nearest_opt_in(inputs, tmp_path):
    raster(inputs.sbs, np.full((7,7),3,dtype='int16'), nodata=255,
           transform=from_origin(500000,4000000,60,60))
    inputs=refresh(inputs)
    with pytest.raises(m1.M1Error) as e:build(inputs,tmp_path)
    assert e.value.code == 'invalid_grid'
    b=build(replace(inputs,sbs_alignment='nearest'),tmp_path)
    assert b['predictors']['T']['value'] == 1


def test_internal_mask_preserved(inputs, tmp_path):
    with rasterio.open(inputs.dem) as ds:a=ds.read(1)
    mask=np.ones((7,7),dtype=bool);mask[3,3]=False
    raster(inputs.dem,a,mask=mask)
    b=build(refresh(replace(inputs,dnbr_manifest=None)),tmp_path)
    assert b['predictors']['T']['value'] is None
    with rasterio.open(tmp_path/'result/prepared/dem.tif') as ds:
        assert ds.read_masks(1)[3,3] == 0


def test_existing_output_protected(inputs,tmp_path):
    out=tmp_path/'result';out.mkdir();(out/'keep').write_text('keep')
    with pytest.raises(m1.M1Error) as e:build(inputs,tmp_path)
    assert e.value.code == 'output_exists'
    assert (out/'keep').read_text() == 'keep'


def test_midbuild_mutation(inputs,tmp_path,monkeypatch):
    original=m1._invoke
    def mutate(*args):
        result=original(*args)
        with inputs.sbs.open('ab') as f:f.write(b'changed')
        return result
    monkeypatch.setattr(m1,'_invoke',mutate)
    with pytest.raises(m1.M1Error) as e:build(inputs,tmp_path)
    assert e.value.code == 'source_changed'
    assert not (tmp_path/'result/manifest.json').exists()


def test_truncated_tool_output(inputs,tmp_path,monkeypatch):
    original=m1._invoke
    def truncate(binary,output,prepared):
        result=original(binary,output,prepared)
        (output/'wbt/support.tif').write_bytes(b'truncated')
        return result
    monkeypatch.setattr(m1,'_invoke',truncate)
    with pytest.raises(m1.M1Error) as e:build(inputs,tmp_path)
    assert e.value.code == 'invalid_tool_output'


def test_absent_tool(inputs,tmp_path):
    with pytest.raises(m1.M1Error) as e:
        m1.build_m1_predictors(inputs,tmp_path/'result',wbt_executable=tmp_path/'absent')
    assert e.value.code == 'tool_unavailable'


@pytest.mark.parametrize('field', ['selected_modes','fragment'])
def test_null_k_provenance_rejected(inputs,tmp_path,field):
    m=json.loads(inputs.k_manifest.read_text())
    if field == 'fragment':m['k']['mode_contract']['polaris_nomograph']['cfvo_profile_fragment_adjustment']=None
    else:m['k'][field]=None
    inputs.k_manifest.write_text(json.dumps(m))
    with pytest.raises(m1.M1Error) as e:build(refresh(inputs),tmp_path)
    assert e.value.code == 'provenance_mismatch'


@pytest.mark.parametrize('case', ['summary','support','version','parameters'])
def test_inconsistent_wbt_products(inputs,tmp_path,monkeypatch,case):
    original=m1._invoke
    def corrupt(binary,output,prepared):
        result=original(binary,output,prepared)
        p=output/'wbt/summary.json';m=json.loads(p.read_text())
        if case == 'summary':m['counts']['slope_valid']=0
        elif case == 'version':del m['tool_version']
        elif case == 'parameters':m['parameters']['threshold_degrees']=22
        else:
            with rasterio.open(output/'wbt/support.tif','r+') as ds:
                a=ds.read(1);a[a!=255]=0;ds.write(a,1)
        p.write_text(json.dumps(m))
        return result
    monkeypatch.setattr(m1,'_invoke',corrupt)
    with pytest.raises(m1.M1Error) as e:build(inputs,tmp_path)
    assert e.value.code == 'invalid_tool_output'


def external_mask(path):
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(path,'r+') as ds:
            a=np.full(ds.shape,255,dtype='uint8');a[2,2]=0;ds.write_mask(a)


def test_external_mask_dnbr(inputs,tmp_path):
    external_mask(inputs.dnbr)
    m=json.loads(inputs.dnbr_manifest.read_text());m['dnbr_sha256']=digest(inputs.dnbr)
    inputs.dnbr_manifest.write_text(json.dumps(m))
    f=build(refresh(inputs),tmp_path)['predictors']['F']
    assert f['support']['valid_cells'] == 24
    assert f['value'] == pytest.approx(.4)


def test_added_external_mask_detected(inputs,tmp_path,monkeypatch):
    original=m1._invoke
    def mutate(*args):
        result=original(*args);external_mask(inputs.sbs);return result
    monkeypatch.setattr(m1,'_invoke',mutate)
    with pytest.raises(m1.M1Error) as e:build(inputs,tmp_path)
    assert e.value.code == 'source_changed'


def test_collision_free_dem_sentinel(inputs,tmp_path):
    from wepppy.nodb.mods.postfire_debris_flow.m1_inputs import prepare, read_raster
    values, valid, grid=read_raster(inputs.dem)
    values[0,0]=-np.finfo(np.float64).max
    out=tmp_path/'sentinel.tif';prepare(out,values,valid,grid)
    copied,support,_=read_raster(out)
    assert support[0,0] and copied[0,0] == values[0,0]
    with rasterio.open(out) as ds:assert ds.nodata != values[0,0]


@pytest.mark.parametrize('field', ['k','dnbr'])
def test_continuous_grid_mismatch(inputs,tmp_path,field):
    p=getattr(inputs,field)
    raster(p,np.ones((7,7)),transform=from_origin(500030,4000000,30,30))
    with pytest.raises(m1.M1Error) as e:build(refresh(inputs),tmp_path)
    assert e.value.code == 'invalid_grid'


def test_missing_dnbr_lineage(inputs,tmp_path):
    b=build(refresh(replace(inputs,lineage_sources=())),tmp_path)
    assert b['predictors']['F']['reason'] == 'missing_provenance'


def test_direct_executable_failure(inputs,tmp_path):
    binary=tmp_path/'failing-tool'
    binary.write_text('#!/bin/sh\nexit 7\n');binary.chmod(0o700)
    with pytest.raises(m1.M1Error) as e:
        m1.build_m1_predictors(replace(inputs,wbt_sha256=digest(binary)),tmp_path/'result',wbt_executable=binary)
    assert e.value.code == 'tool_failed'
    assert (tmp_path/'result/capability.stderr.log').exists()


def test_resource_limit_before_decode(inputs,tmp_path,monkeypatch):
    from wepppy.nodb.mods.postfire_debris_flow import m1_inputs
    monkeypatch.setattr(m1_inputs,'MAX_CELLS',40)
    with pytest.raises(m1.M1Error) as e:build(inputs,tmp_path)
    assert e.value.code == 'resource_limit'


def test_malformed_normalization_manifest(inputs,tmp_path):
    inputs.dnbr_manifest.write_text('{')
    with pytest.raises(m1.M1Error) as e:build(refresh(inputs),tmp_path)
    assert e.value.code == 'invalid_input'


def test_disguised_vrt_external_mask_rejected(inputs,tmp_path):
    sidecar=Path(str(inputs.sbs)+'.msk')
    sidecar.write_text('<VRTDataset rasterXSize="7" rasterYSize="7"><Metadata><MDI key="INTERNAL_MASK_FLAGS_1">2</MDI></Metadata><VRTRasterBand dataType="Byte" band="1"><SimpleSource><SourceFilename relativeToVRT="1">sbs.tif</SourceFilename><SourceBand>1</SourceBand></SimpleSource></VRTRasterBand></VRTDataset>')
    with pytest.raises(m1.M1Error) as e:build(refresh(inputs),tmp_path)
    assert e.value.code == 'invalid_input'
    assert 'never VRT' in str(e.value)


def test_unrecorded_worldfile_rejected(inputs,tmp_path):
    Path(str(inputs.dem)+'w').write_text('30\n0\n0\n-30\n500015\n3999985\n')
    with pytest.raises(m1.M1Error) as e:build(inputs,tmp_path)
    assert e.value.code == 'invalid_input'


@pytest.mark.parametrize('field',['gap_fill_policy','gap_fill_summary'])
def test_empty_k_provenance_unavailable(inputs,tmp_path,field):
    m=json.loads(inputs.k_manifest.read_text());m['k'][field]={}
    inputs.k_manifest.write_text(json.dumps(m))
    assert build(refresh(inputs),tmp_path)['predictors']['S']['reason'] == 'missing_provenance'


def test_external_mask_without_gdal_flag_rejected(inputs,tmp_path):
    path=Path(str(inputs.sbs)+'.msk')
    # A TIFF with the right extension/shape is not necessarily a GDAL mask.
    with rasterio.open(path,'w',driver='GTiff',height=7,width=7,count=1,dtype='uint8') as ds:
        ds.write(np.zeros((7,7),dtype='uint8'),1)
    with pytest.raises(m1.M1Error) as e:build(refresh(inputs),tmp_path)
    assert e.value.code == 'invalid_input'
    assert 'supported GDAL mask flag' in str(e.value)
