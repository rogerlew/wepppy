"""Attempt-owned, bounded acquisition of published NRCS-derived fine-earth Kf."""
from datetime import datetime, timezone
import math
import hashlib
from pathlib import Path
import shutil

import numpy as np
import rasterio
from rasterio.io import FilePath, MemoryFile
from rasterio.enums import ColorInterp, Resampling
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import Window, from_bounds

from . import rainfall_io as io
from .m1_inputs import read_raster, prepare, digest, companions
from .source_transport import KF_URL, Transport, RangeFile, deadline

__all__ = ['POLICY', 'acquire_kf', 'validate_manifest', 'read_prepared']
POLICY = 'statsgo_kffact_1995_cog2025_v1'
SOURCE_ID = '6750c172d34ed8d3858534d8'
AGGREGATION = 'all_recorded_layers_thickness_then_component_percentage_missing_excluded'
METADATA = Path(__file__).parent/'data/kffact_metadata.xml'


def _native_window(grid, output):
    requests = output/'requests'; requests.mkdir()
    transport = Transport(requests)
    with deadline(120):
        source = RangeFile(transport, url=KF_URL)
        with FilePath(source) as bridge, bridge.open(driver='GTiff') as ds:
            if (ds.count != 1 or ds.crs != rasterio.crs.CRS.from_epsg(5069)
                    or ds.dtypes != ('float32',) or ds.scales != (1.,) or ds.offsets != (0.,)
                    or ds.transform.a != 30 or ds.transform.e != -30 or ds.transform.b or ds.transform.d
                    or ds.tags().get('AREA_OR_POINT','Area') != 'Area'
                    or ds.colorinterp[0] not in (ColorInterp.gray,ColorInterp.undefined)
                    or any(r*c > 10_000_000 for r,c in ds.block_shapes)):
                io.fail('invalid_input', 'Unexpected published KFFACT grid or encoding')
            rows,cols = grid['shape']; affine = rasterio.Affine(*grid['transform'])
            left,top = affine*(0,0); right,bottom = affine*(cols,rows)
            bounds = transform_bounds(grid['crs'],ds.crs,left,bottom,right,top)
            f = from_bounds(*bounds,transform=ds.transform)
            col,row = math.floor(f.col_off),math.floor(f.row_off)
            width,height = math.ceil(f.col_off+f.width)-col, math.ceil(f.row_off+f.height)-row
            if (col < 0 or row < 0 or col+width > ds.width or row+height > ds.height
                    or not 0 < width*height <= 10_000_000):
                io.fail('resource_limit','Kf window is outside source coverage or exceeds the cell limit')
            window = Window(col,row,width,height)
            values = ds.read(1,window=window,masked=True)
            if source.failure is not None:
                raise source.failure
            transform = ds.window_transform(window)
            profile = dict(driver='GTiff',height=height,width=width,count=1,dtype='float32',
                           crs=ds.crs,transform=transform,nodata=np.nan,compress='deflate')
            # Preserve the original values, including the publisher's -0.1 sentinel.
            with rasterio.open(output/'native_kf.tif','w',**profile) as target:
                target.write(values.filled(np.nan),1)
            native_grid = dict(shape=[height,width],crs=str(ds.crs),transform=list(transform)[:6])
        source.verify()
    io.write_json(output/'native_evidence.json',dict(object_identity=list(source.identity),
        source_url=KF_URL,native_grid=native_grid,transferred_bytes=transport.received,
        native_sha256=io.digest(output/'native_kf.tif',io.MAX_PREDICTOR_BYTES),
        requests=transport.requests,retrieved_at=datetime.now(timezone.utc).isoformat()))


def _usable(values, valid):
    sentinel = float(np.float32(-.1))
    missing = np.isnan(values) | (values == sentinel)
    if np.any(valid & ~missing & (~np.isfinite(values) | (values < 0) | (values > 1))):
        io.fail('invalid_input','Invalid published KFFACT value; no substitution is permitted')
    return valid & ~missing


def acquire_kf(dem, mask, output_dir):
    """Reserve a new attempt directory, prepare Kf, and retain every failed stage."""
    from .source_acquisition import _supervise
    dem, mask = io.regular(dem,io.MAX_PREDICTOR_BYTES), io.regular(mask,io.MAX_PREDICTOR_BYTES)
    original = {path:digest(path) for path in (dem,mask,*companions(dem),*companions(mask))}
    _,_,grid = read_raster(dem,target_grid=True)
    domain, domain_valid, mask_grid = read_raster(mask,target_grid=True)
    if mask_grid != grid or not np.any(domain_valid & (domain > 0)):
        io.fail('invalid_grid','Kf requires the existing nonempty project watershed grid')
    output = Path(output_dir).absolute()
    if '..' in output.parts or any(p.is_symlink() for p in (output,*output.parents)):
        io.fail('invalid_input','Kf output must be a regular project directory')
    output.mkdir(exist_ok=False)
    io.write_json(output/'incomplete.json',dict(status='incomplete',policy=POLICY))
    shutil.copyfile(io.regular(METADATA,io.MAX_TEXT),output/'publisher_metadata.xml')
    _supervise('kf',_native_window,(grid,),output,120)
    evidence = io.read_json(output/'native_evidence.json')
    native = io.regular(output/'native_kf.tif',io.MAX_PREDICTOR_BYTES)
    if companions(native):
        io.fail('invalid_input','Native Kf must be self-contained')
    with io.open_local(native,io.MAX_PREDICTOR_BYTES) as stream:
        raw=stream.read(io.MAX_PREDICTOR_BYTES+1)
        if len(raw)>io.MAX_PREDICTOR_BYTES:
            io.fail('resource_limit','Native Kf grew beyond byte limit')
        native_hash = hashlib.sha256(raw).hexdigest()
        if native_hash != evidence.get('native_sha256'):
            io.fail('source_changed','Native Kf artifact changed during preparation')
        with rasterio.Env(GDAL_PAM_ENABLED='NO',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'), MemoryFile(raw) as bridge, bridge.open(driver='GTiff') as ds:
            recorded=evidence['native_grid']
            actual=dict(shape=list(ds.shape),crs=str(ds.crs),transform=list(ds.transform)[:6])
            if (actual!=recorded or ds.count!=1 or ds.dtypes!=('float32',)
                    or ds.crs!=rasterio.crs.CRS.from_epsg(5069) or ds.transform.a!=30
                    or ds.transform.e!=-30 or ds.transform.b or ds.transform.d
                    or ds.scales!=(1.,) or ds.offsets!=(0.,)
                    or ds.height*ds.width>10_000_000
                    or any(r*c>10_000_000 for r,c in ds.block_shapes)):
                io.fail('invalid_input','Native Kf differs from its source grid')
            source = ds.read(1,masked=True)
            source_valid = _usable(source.data,~np.ma.getmaskarray(source))
            values = np.where(source_valid,source.data,np.nan).astype('float32')
            target = np.full(grid['shape'],np.nan,dtype='float32')
            reproject(values,target,src_transform=ds.transform,src_crs=ds.crs,src_nodata=np.nan,
                      dst_transform=rasterio.Affine(*grid['transform']),dst_crs=grid['crs'],
                      dst_nodata=np.nan,resampling=Resampling.nearest)

    valid = np.isfinite(target)
    prepare(output/'kf.tif',target,valid,grid)
    domain = domain_valid & (domain > 0)
    manifest = dict(schema_version=1,status='complete',policy=POLICY,source_id=SOURCE_ID,
        source_url=KF_URL,release_date='2025-02-11',field='KFFACT',units='USLE_customary',
        units_interpretation='original_kffact_field_verified',aggregation=AGGREGATION,
        resampling='nearest',retrieved_at=evidence['retrieved_at'],object_identity=evidence['object_identity'],
        native_grid=evidence['native_grid'],target_grid=grid,source_metadata_sha256=io.digest(output/'publisher_metadata.xml',io.MAX_TEXT),
        artifacts_sha256={name:io.digest(output/name,io.MAX_PREDICTOR_BYTES) for name in ('native_kf.tif','kf.tif')},
        requests_sha256={p.name:io.digest(p,io.MAX_PREDICTOR_BYTES) for p in sorted((output/'requests').iterdir())},
        valid_cells=int(np.count_nonzero(domain & valid)),missing_cells=int(np.count_nonzero(domain & ~valid)))
    validate_manifest(manifest)
    if manifest['artifacts_sha256']['native_kf.tif']!=native_hash:
        io.fail('source_changed','Retained native Kf changed during alignment')
    if any(digest(path)!=value for path,value in original.items()):
        io.fail('source_changed','Project grid inputs changed during Kf preparation')
    io.write_json(output/'manifest.json',manifest)
    (output/'incomplete.json').unlink()
    return manifest


def validate_manifest(m):
    """Validate inert provenance; never follow manifest paths or fetch sources."""
    fixed = dict(schema_version=1,status='complete',policy=POLICY,source_id=SOURCE_ID,
        source_url=KF_URL,release_date='2025-02-11',field='KFFACT',units='USLE_customary',
        units_interpretation='original_kffact_field_verified',aggregation=AGGREGATION,resampling='nearest')
    if not isinstance(m,dict) or any(m.get(k)!=v for k,v in fixed.items()) or type(m.get('schema_version')) is not int:
        io.fail('invalid_input','Unsupported Kf source provenance')
    for name in ('native_grid','target_grid'):
        grid=m.get(name)
        if (not isinstance(grid,dict) or not isinstance(grid.get('crs'),str)
                or not isinstance(grid.get('shape'),list) or len(grid['shape'])!=2
                or any(type(v) is not int or v<=0 for v in grid['shape'])
                or math.prod(grid['shape'])>10_000_000 or not isinstance(grid.get('transform'),list)
                or len(grid['transform'])!=6 or not all(io.number(v) for v in grid['transform'])):
            io.fail('invalid_grid','Malformed Kf provenance grid')
    identity=m.get('object_identity')
    if (not isinstance(identity,list) or len(identity)!=3 or not isinstance(identity[0],str)
            or not identity[0].startswith('"') or not identity[0].endswith('"')
            or type(identity[1]) is not int or identity[1]<=0
            or identity[2] is not None and not isinstance(identity[2],str)
            or not isinstance(m.get('retrieved_at'),str) or not m['retrieved_at']
            or not io.hash_value(m.get('source_metadata_sha256'))):
        io.fail('invalid_input','Missing Kf source identity')
    hashes=m.get('artifacts_sha256')
    if not isinstance(hashes,dict) or set(hashes)!= {'native_kf.tif','kf.tif'} or not all(io.hash_value(v) for v in hashes.values()):
        io.fail('invalid_input','Invalid Kf artifact inventory')
    requests=m.get('requests_sha256')
    if (not isinstance(requests,dict) or not requests or len(requests)>5000
            or any(not isinstance(k,str) or '/' in k or '\\' in k or not k.startswith('request-')
                   or not io.hash_value(v) for k,v in requests.items())):
        io.fail('invalid_input','Invalid Kf request inventory')
    if any(type(m.get(k)) is not int or m[k]<0 for k in ('valid_cells','missing_cells')):
        io.fail('invalid_input','Invalid Kf coverage counts')


def read_prepared(raster, manifest, grid):
    m=io.read_json(manifest); validate_manifest(m)
    if (Path(raster).name!='kf.tif' or m['target_grid']!=grid
            or digest(raster)!=m['artifacts_sha256']['kf.tif']):
        io.fail('provenance_mismatch','Prepared Kf differs from its recorded identity')
    values,valid,actual=read_raster(raster,continuous_missing=True)
    if actual!=grid or np.any(valid & ((values<0)|(values>1))):
        io.fail('invalid_input','Invalid prepared Kf grid or values')
    return values,valid,m
