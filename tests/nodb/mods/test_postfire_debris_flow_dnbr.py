"""Real raster boundary tests for the dNBR backend contract."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject, calculate_default_transform

from wepppy.nodb.mods.postfire_debris_flow.dnbr import DnbrError, normalize_dnbr, summarize_dnbr

pytestmark = pytest.mark.unit
FIXTURES = Path(__file__).parent / "fixtures/postfire_debris_flow_dnbr"
GRID = from_origin(500000, 4000000, 10, 10)


def write(path, values, *, transform=GRID, crs="EPSG:32612", nodata=None, driver="GTiff", scale=None):
    values = np.asarray(values)
    with rasterio.open(path, "w", driver=driver, count=1, height=values.shape[0],
                       width=values.shape[1], dtype=values.dtype, transform=transform,
                       crs=crs, nodata=nodata) as dst:
        dst.write(values, 1)
        if scale is not None:
            dst.scales = [scale]
    return path


@pytest.fixture
def refs(tmp_path):
    return (write(tmp_path / "dem.tif", np.ones((4, 4), dtype="float32")),
            write(tmp_path / "mask.tif", np.ones((4, 4), dtype="uint8")))


def run(tmp_path, refs, values, **kwargs):
    source = write(tmp_path / "input.tif", np.asarray(values, dtype="float32"))
    return normalize_dnbr(source, *refs, tmp_path / "result", scale_factor=0.001, **kwargs)


def test_equivalent_encodings_and_no_double_scale(tmp_path, refs):
    raw = np.array([[-100, 0, 500, 1000]] * 4, dtype="int16")
    integer = write(tmp_path / "scaled.tif", raw)
    floating = write(tmp_path / "float.tif", raw.astype("float32") / 1000)
    a = normalize_dnbr(integer, *refs, tmp_path / "a", scale_factor=.001)
    b = normalize_dnbr(floating, *refs, tmp_path / "b", scale_factor=1)
    assert a['watershed']['m1_f'] == pytest.approx(.35)
    assert a['watershed'] == b['watershed']
    with rasterio.open(tmp_path / "a/dnbr.tif") as ds:
        assert ds.transform == GRID and ds.shape == (4, 4)
        assert ds.dtypes == ('float32',) and np.isnan(ds.nodata)
    assert summarize_dnbr(tmp_path / "a/dnbr.tif", refs[1]) == a['watershed']


def test_partial_mean_and_no_data_catchment(tmp_path, refs):
    values = np.full((4, 4), np.nan, dtype="float32")
    values[0, :2] = [-100, 0]
    result = run(tmp_path, refs, values)
    assert result['watershed']['coverage_fraction'] == 2 / 16
    assert result['watershed']['m1_f'] == pytest.approx(-.05)
    mask = write(tmp_path / 'other.tif', np.array([[0]*4, [1]*4, [0]*4, [0]*4], dtype='uint8'))
    assert summarize_dnbr(tmp_path / 'result/dnbr.tif', mask)['status'] == 'unavailable'


@pytest.mark.parametrize('value', [np.nan, np.inf, -np.inf])
def test_nonfinite_is_invalid_support(tmp_path, refs, value):
    with pytest.raises(DnbrError, match='No valid') as e:
        run(tmp_path, refs, np.full((4, 4), value))
    assert e.value.code == 'no_valid_target_overlap'
    assert not (tmp_path / 'result').exists()


@pytest.mark.parametrize('shift', [40, 50, 5000])
def test_touch_or_disjoint_is_not_overlap(tmp_path, refs, shift):
    p = write(tmp_path / 'source.tif', np.ones((4, 4), dtype='int16'),
              transform=from_origin(500000+shift, 4000000, 10, 10))
    with pytest.raises(DnbrError) as e:
        normalize_dnbr(p, *refs, tmp_path / 'out', scale_factor=.001)
    assert e.value.code == 'no_valid_target_overlap'


@pytest.mark.parametrize('resolution,shape', [(5, (8, 8)), (20, (2, 2)), (10, (4, 4))])
def test_resolutions_and_shifted_origin(tmp_path, refs, resolution, shape):
    p = write(tmp_path / 'source.tif', np.full(shape, 600, dtype='int16'),
              transform=from_origin(500002, 4000002, resolution, resolution))
    result = normalize_dnbr(p, *refs, tmp_path / 'out', scale_factor=.001)
    assert result['watershed']['m1_f'] == pytest.approx(.6)
    with rasterio.open(tmp_path / 'out/dnbr.tif') as ds:
        assert ds.transform == GRID


def test_reproject_geographic_source(tmp_path, refs):
    with rasterio.open(refs[0]) as d:
        a, width, height = calculate_default_transform(d.crs, 'EPSG:4326', d.width, d.height, *d.bounds)
    p = write(tmp_path / 'source.tif', np.full((height,width), 400, dtype='int16'), transform=a, crs='EPSG:4326')
    result = normalize_dnbr(p, *refs, tmp_path / 'out', scale_factor=.001)
    assert result['watershed']['m1_f'] == pytest.approx(.4)


def test_no_bbox_only_overlap(tmp_path, refs):
    values = np.full((4,4), -9999, dtype='int16'); values[0,0] = 400
    p = write(tmp_path / 'source.tif', values, nodata=-9999)
    mask = write(tmp_path / 'mask2.tif', np.array([[0]*4,[1]*4,[1]*4,[1]*4], dtype='uint8'))
    with pytest.raises(DnbrError) as e:
        normalize_dnbr(p, refs[0], mask, tmp_path / 'out', scale_factor=.001)
    assert e.value.code == 'no_valid_target_overlap'


def test_small_overlap_disappearing_at_target(tmp_path, refs):
    p = write(tmp_path/'tiny.tif', np.array([[100]], dtype='int16'),
              transform=from_origin(500000,4000000,1,1))
    with pytest.raises(DnbrError) as e:
        normalize_dnbr(p,*refs,tmp_path/'out',scale_factor=.001)
    assert e.value.code == 'no_valid_target_overlap'


@pytest.mark.parametrize('scale,offset', [(0,0),(-1,0),(np.nan,0),(1,np.inf),(True,0),('bad',0)])
def test_invalid_encoding(tmp_path, refs, scale, offset):
    with pytest.raises(DnbrError) as e:
        normalize_dnbr(refs[0],*refs,tmp_path/'out',scale_factor=scale,add_offset=offset)
    assert e.value.code == 'invalid_encoding'


def test_metadata_conflict_and_apply_once(tmp_path, refs):
    p=write(tmp_path/'source.tif',np.full((4,4),500,dtype='int16'),scale=.001)
    with pytest.raises(DnbrError) as e:
        normalize_dnbr(p,*refs,tmp_path/'out',scale_factor=1)
    assert e.value.code == 'encoding_conflict'
    result=normalize_dnbr(p,*refs,tmp_path/'out',scale_factor=.001)
    assert result['watershed']['m1_f'] == .5


def test_existing_empty_and_populated_outputs_preserved(tmp_path, refs):
    out=tmp_path/'out';out.mkdir()
    for populated in (False,True):
        if populated: (out/'marker').write_text('keep')
        with pytest.raises(DnbrError) as e:
            normalize_dnbr(refs[0],*refs,out,scale_factor=1)
        assert e.value.code == 'output_exists'
        if populated: assert (out/'marker').read_text() == 'keep'


@pytest.mark.parametrize('kwargs', [dict(prefire_date='bad'),dict(prefire_date='2020-01-02',postfire_date='2020-01-01'),dict(assessment_type='bogus')])
def test_dates(tmp_path,refs,kwargs):
    with pytest.raises(DnbrError) as e: run(tmp_path,refs,np.ones((4,4)),**kwargs)
    assert e.value.code == 'invalid_dates'


def vrt(path, leaf, *, extra='', source_name=None):
    name=source_name or leaf.name
    path.write_text(f'''<VRTDataset rasterXSize="4" rasterYSize="4"><SRS>EPSG:32612</SRS>
<GeoTransform>500000,10,0,4000000,0,-10</GeoTransform>
<VRTRasterBand dataType="Float32" band="1"><SimpleSource>
<SourceFilename relativeToVRT="1">{name}</SourceFilename><SourceBand>1</SourceBand>
</SimpleSource>{extra}</VRTRasterBand></VRTDataset>''')
    return path


def test_identity_vrt(tmp_path,refs):
    p=vrt(tmp_path/'source.vrt',refs[0])
    result=normalize_dnbr(p,*refs,tmp_path/'out',scale_factor=1,source_refs=[refs[0]])
    assert result['watershed']['m1_f'] == 1


@pytest.mark.parametrize('name', ['../secret.tif','https://example.org/x.tif','/etc/passwd','/vsicurl/x'])
def test_unsafe_vrt_references(tmp_path,refs,name):
    p=vrt(tmp_path/'source.vrt',refs[0],source_name=name)
    with pytest.raises(DnbrError) as e:
        normalize_dnbr(p,*refs,tmp_path/'out',scale_factor=1,source_refs=[refs[0]])
    assert e.value.code == 'unsafe_reference'


def test_vrt_not_allowlisted_and_pixel_function(tmp_path,refs):
    p=vrt(tmp_path/'source.vrt',refs[0])
    with pytest.raises(DnbrError) as e: normalize_dnbr(p,*refs,tmp_path/'out',scale_factor=1)
    assert e.value.code == 'unsafe_reference'
    vrt(p,refs[0],extra='<PixelFunctionType>anything</PixelFunctionType>')
    with pytest.raises(DnbrError) as e: normalize_dnbr(p,*refs,tmp_path/'out',scale_factor=1,source_refs=[refs[0]])
    assert e.value.code == 'unsupported_vrt'


def test_selfcontained_img(tmp_path,refs):
    p=write(tmp_path/'source.img',np.full((4,4),200,dtype='int16'),driver='HFA')
    result=normalize_dnbr(p,*refs,tmp_path/'out',scale_factor=.001)
    assert result['watershed']['m1_f'] == pytest.approx(.2)


def test_symlink_rejected(tmp_path,refs):
    p=tmp_path/'source.tif';p.symlink_to(refs[0])
    with pytest.raises(DnbrError) as e:normalize_dnbr(p,*refs,tmp_path/'out',scale_factor=1)
    assert e.value.code == 'invalid_input'


def test_bilinear_changes_values_nearest_keeps_hole():
    source=np.array([[0,100,200],[0,np.nan,200],[0,100,200]],dtype='float64')
    results=[]
    for method in (Resampling.nearest,Resampling.bilinear):
        target=np.full((3,3),np.nan)
        reproject(source,target,src_transform=GRID,src_crs='EPSG:32612',src_nodata=np.nan,
                  dst_transform=from_origin(500002,4000002,10,10),dst_crs='EPSG:32612',dst_nodata=np.nan,resampling=method)
        results.append(target)
    assert np.isnan(results[0][1,1])
    assert set(results[0][np.isfinite(results[0])]) <= {0,100,200}
    assert not np.allclose(results[0],results[1],equal_nan=True)


@pytest.mark.parametrize('name', ['AZ3133311041620120508.tif','AZ3134011074320110214.tif'])
@pytest.mark.parametrize('upsample', [1, 3])
def test_real_arizona_fixture(tmp_path,name,upsample):
    p=FIXTURES/name
    manifest=json.loads((FIXTURES/'manifest.json').read_text())
    info=next(x for x in manifest['files'] if x['path']==name)
    assert hashlib.sha256(p.read_bytes()).hexdigest()==info['sha256']
    with rasterio.open(p) as src:
        a=src.read(1,masked=True); valid=~np.ma.getmaskarray(a) & np.isfinite(a.data)
        transform=src.transform * rasterio.Affine.scale(1/upsample); crs=src.crs
        shape=(a.shape[0]*upsample,a.shape[1]*upsample)
        dem=write(tmp_path/'dem.tif',np.ones(shape,dtype='float32'),transform=transform,crs=crs)
        mask=write(tmp_path/'mask.tif',np.ones(shape,dtype='uint8'),transform=transform,crs=crs)
    r=normalize_dnbr(p,dem,mask,tmp_path/'out',scale_factor=.001)
    assert r['watershed']['valid_cells']==int(valid.sum())*upsample**2
    expected=(a.data[valid].astype('float64')*.001).astype('float32').mean(dtype='float64')
    assert r['watershed']['m1_f']==pytest.approx(expected,abs=1e-9)
    assert r['watershed']['status']=='partial'
    assert r['prefire_date'] is None and r['postfire_date'] is None


def test_external_mask_rejected_instead_of_silently_discarded(tmp_path,refs):
    source=write(tmp_path/'source.tif',np.full((4,4),200,dtype='int16'))
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(source,'r+') as ds:
            ds.write_mask(np.array([[255,0,255,0]]*4,dtype='uint8'))
    assert Path(str(source)+'.msk').exists()
    with pytest.raises(DnbrError) as e:normalize_dnbr(source,*refs,tmp_path/'out',scale_factor=.001)
    assert e.value.code=='invalid_raster'


def test_xml_and_decoded_block_resource_limits(tmp_path,refs):
    path=tmp_path/'large.vrt';path.write_text('<VRTDataset>'+ '<SRS/>'*12000 +'</VRTDataset>')
    with pytest.raises(DnbrError) as e:normalize_dnbr(path,*refs,tmp_path/'out',scale_factor=1)
    assert e.value.code=='resource_limit'
    path=tmp_path/'padded.tif'
    with rasterio.open(path,'w',driver='GTiff',height=4,width=4,count=1,dtype='uint8',
                       transform=GRID,crs='EPSG:32612',tiled=True,blockxsize=8192,blockysize=8192,compress='deflate') as ds:
        ds.write(np.ones((4,4),dtype='uint8'),1)
    with pytest.raises(DnbrError) as e:normalize_dnbr(path,*refs,tmp_path/'out',scale_factor=1)
    assert e.value.code=='resource_limit'


def test_bad_reference_masks(tmp_path,refs):
    for name,values in [('empty',np.zeros((4,4))),('categorical',np.full((4,4),2))]:
        p=write(tmp_path/f'{name}.tif',values.astype('uint8'))
        with pytest.raises(DnbrError) as e:normalize_dnbr(refs[0],refs[0],p,tmp_path/'out',scale_factor=1)
        assert e.value.code=='invalid_mask'
    p=write(tmp_path/'missingdem.tif',np.full((4,4),np.nan,dtype='float32'),nodata=np.nan)
    with pytest.raises(DnbrError) as e:normalize_dnbr(refs[0],p,refs[1],tmp_path/'out',scale_factor=1)
    assert e.value.code=='invalid_mask'


def test_nonfinite_normalization_and_diagnostic_range(tmp_path,refs):
    with pytest.raises(DnbrError) as e:
        normalize_dnbr(refs[0],*refs,tmp_path/'out',scale_factor=1e308,add_offset=1e308)
    assert e.value.code=='invalid_encoding'
    r=normalize_dnbr(refs[0],*refs,tmp_path/'out',scale_factor=3)
    assert r['watershed']['m1_f']==3 and r['outside_ideal_range_cells']==16


def test_actual_writer_failure_preserves_sources_and_visible_incomplete_output(tmp_path,refs,monkeypatch):
    # Inject an operational write failure at the real filesystem boundary.
    import wepppy.nodb.mods.postfire_debris_flow.dnbr as module
    original=module.rasterio.open
    def fail_output(path,*args,**kwargs):
        if args and args[0]=='w':raise OSError('simulated storage failure')
        return original(path,*args,**kwargs)
    before=[hashlib.sha256(p.read_bytes()).hexdigest() for p in refs]
    monkeypatch.setattr(module.rasterio,'open',fail_output)
    with pytest.raises(OSError,match='storage failure'):
        normalize_dnbr(refs[0],*refs,tmp_path/'out',scale_factor=1)
    assert (tmp_path/'out'/'incomplete.json').is_file()
    assert not (tmp_path/'out'/'manifest.json').exists()
    assert not list(tmp_path.glob('.dnbr-*'))
    assert before==[hashlib.sha256(p.read_bytes()).hexdigest() for p in refs]


def test_source_change_aborts_publication(tmp_path,refs,monkeypatch):
    import wepppy.nodb.mods.postfire_debris_flow.dnbr as module
    original=module.reproject
    def change_after_warp(*args,**kwargs):
        result=original(*args,**kwargs)
        with rasterio.open(refs[0],'r+') as ds:
            ds.write(np.full((4,4),2,dtype='float32'),1)
        return result
    monkeypatch.setattr(module,'reproject',change_after_warp)
    with pytest.raises(DnbrError) as e:normalize_dnbr(refs[0],*refs,tmp_path/'out',scale_factor=1)
    assert e.value.code=='source_changed'
    assert (tmp_path/'out'/'incomplete.json').is_file()
    assert not (tmp_path/'out'/'manifest.json').exists()
    assert not list(tmp_path.glob('.dnbr-*'))


def test_internal_mask_is_retained(tmp_path,refs):
    p=write(tmp_path/'internal.tif',np.array([[100,1000,100,1000]]*4,dtype='int16'))
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(p,'r+') as ds:ds.write_mask(np.array([[255,0,255,0]]*4,dtype='uint8'))
    result=normalize_dnbr(p,*refs,tmp_path/'out',scale_factor=.001)
    assert result['watershed']['coverage_fraction']==.5
    assert result['watershed']['m1_f']==pytest.approx(.1)
