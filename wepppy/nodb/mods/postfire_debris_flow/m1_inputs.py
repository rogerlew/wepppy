"""Trusted local M1 raster boundary; see docs/m1_predictors.md."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import ColorInterp, Resampling
from rasterio.warp import reproject

__all__ = ["M1Error"]
MAX_CELLS = 10_000_000
MAX_BYTES = 512 * 1024 * 1024


class M1Error(ValueError):
    """Expected local boundary failure with stable code."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def fail(code, message):
    raise M1Error(code, message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def regular(path, limit=MAX_BYTES):
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        fail('invalid_input', f'Expected regular nonsymlink file: {p}')
    if p.stat().st_size > limit:
        fail('resource_limit', f'File exceeds byte limit: {p}')
    return p.absolute()


def read_json(path):
    p = regular(path, 1024 * 1024)
    try:
        result = json.loads(p.read_text(), parse_constant=lambda s: fail('invalid_input', f'Nonfinite JSON: {s}'))
    except (ValueError, UnicodeError) as exc:
        raise M1Error('invalid_input', f'Invalid JSON: {p}') from exc
    if not isinstance(result, dict):
        fail('invalid_input', f'Expected JSON object: {p}')
    return result


def write_json(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def companions(path):
    """Admit only explicit external masks, never silently discard metadata."""
    path = Path(path)
    forbidden = {path.name.lower() + ext for ext in ('.aux.xml', '.ovr', 'w')}
    forbidden.update(path.stem.lower() + ext for ext in ('.aux', '.aux.xml', '.tfw', '.wld', '.rrd'))
    masks = []
    for child in path.parent.iterdir():
        if child.name.lower() in forbidden:
            fail('invalid_input', f'Unsupported raster companion: {child}')
        if child.name.lower() == path.name.lower() + '.msk':
            if child.name != path.name + '.msk':
                fail('invalid_input', 'External mask must use canonical .msk suffix')
            masks.append(regular(child))
    return masks


def grid_of(ds):
    return {'shape': list(ds.shape), 'crs': str(ds.crs), 'transform': list(ds.transform)[:6]}


def validate_grid(grid):
    a = rasterio.Affine(*grid['transform'])
    crs = rasterio.crs.CRS.from_user_input(grid['crs'])
    epsg = crs.to_epsg()
    if (epsg is None or not (32601 <= epsg <= 32660 or 32701 <= epsg <= 32760)
            or not all(math.isfinite(v) for v in a[:6]) or a.b != 0 or a.d != 0
            or a.a <= 0 or a.e != -a.a):
        fail('invalid_grid', 'Expected square north-up WGS84 UTM meter grid')


def read_raster(path, *, categorical=False, continuous_missing=False, target_grid=False):
    path = regular(path)
    masks = companions(path)
    mask_shapes = []
    for mask in masks:
        if companions(mask):
            fail('invalid_input', 'Nested external masks are unsupported')
        with mask.open('rb') as stream:
            if stream.read(4) not in (b'II*\x00', b'MM\x00*', b'II+\x00', b'MM\x00+'):
                fail('invalid_input', 'External masks must be self-contained GeoTIFF, never VRT')
        try:
            with rasterio.Env(GDAL_PAM_ENABLED='NO', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
                with rasterio.open(mask, driver='GTiff') as ds:
                    if ds.driver != 'GTiff' or ds.count != 1 or ds.dtypes != ('uint8',):
                        fail('invalid_input', 'External mask must contain one Byte band')
                    if ds.tags().get('INTERNAL_MASK_FLAGS_1') not in ('0', '2'):
                        fail('invalid_input', 'External mask must declare a supported GDAL mask flag')
                    if ds.width * ds.height > MAX_CELLS or any(r*c > MAX_CELLS for r,c in ds.block_shapes):
                        fail('resource_limit', 'External mask exceeds cell limit')
                    mask_shapes.append(ds.shape)
        except rasterio.errors.RasterioError as exc:
            raise M1Error('invalid_input', 'Cannot decode self-contained external mask') from exc
    if path.suffix.lower() not in ('.tif', '.tiff'):
        fail('invalid_input', 'Only local GeoTIFF is supported')
    try:
        with rasterio.Env(GDAL_PAM_ENABLED='NO', GDAL_VRT_ENABLE_PYTHON='NO'):
            with rasterio.open(path, driver='GTiff', GEOREF_SOURCES='INTERNAL') as ds:
                if any(shape != ds.shape for shape in mask_shapes):
                    fail('invalid_input', 'External mask dimensions differ from source')
                if ds.driver != 'GTiff' or ds.count != 1 or np.dtype(ds.dtypes[0]).kind not in 'iuf':
                    fail('invalid_input', 'Expected one scalar GeoTIFF band')
                if ds.width * ds.height > MAX_CELLS or any(r*c > MAX_CELLS for r, c in ds.block_shapes):
                    fail('resource_limit', 'Raster exceeds 10 million cells')
                if np.dtype(ds.dtypes[0]).itemsize > 8 or ds.dtypes[0] in ('int64', 'uint64'):
                    fail('invalid_input', '64-bit integer samples cannot be losslessly represented')
                if ds.scales != (1.0,) or ds.offsets != (0.0,):
                    fail('invalid_encoding', 'Raster must have identity sample encoding')
                if ds.tags().get('AREA_OR_POINT', 'Area') != 'Area':
                    fail('invalid_grid', 'Pixel-area raster required')
                if ds.units[0] not in (None, '', 'm', 'metre', 'meter') and not categorical:
                    fail('invalid_encoding', 'Contradictory raster unit declaration')
                allowed = {ColorInterp.gray, ColorInterp.undefined}
                if categorical:
                    allowed.add(ColorInterp.palette)
                if ds.colorinterp[0] not in allowed:
                    fail('invalid_input', 'Unsupported raster color interpretation')
                if ds.crs is None:
                    fail('invalid_grid', 'Raster requires CRS')
                grid = grid_of(ds)
                a = ds.transform
                if not all(math.isfinite(v) for v in a[:6]) or a.determinant == 0:
                    fail('invalid_grid', 'Invalid affine grid')
                if target_grid:
                    validate_grid(grid)
                values = ds.read(1, masked=True).astype(np.float64)
                valid = ~np.ma.getmaskarray(values)
                if not continuous_missing and np.any(valid & ~np.isfinite(values.data)):
                    fail('invalid_input', 'Unmasked nonfinite samples are unsupported')
                valid &= np.isfinite(values.data)
                return values.data, valid, grid
    except rasterio.errors.RasterioError as exc:
        raise M1Error('invalid_input', f'Cannot decode GeoTIFF: {path}') from exc


def prepare(path, values, valid, grid, *, sbs=False):
    dtype = 'int16' if sbs else 'float64'
    nodata = 255 if sbs else -np.finfo(np.float64).max
    if not sbs:
        # GDAL mask comparisons can treat adjacent floats as equal to NoData.
        # Use widely separated candidates, then verify the decoded support below.
        candidates = [-np.finfo(np.float64).max, np.finfo(np.float64).max]
        candidates.extend(-32768. * (i + 1) for i in range(30))
        for nodata in candidates:
            with np.errstate(over='ignore', invalid='ignore'):
                collision = np.any(np.isclose(values[valid], nodata, rtol=1e-12, atol=0))
            if not collision:
                break
        else:
            fail('preparation_failed', 'No collision-free sentinel among bounded candidates')
    if np.any(values[valid] == nodata):
        fail('preparation_failed', 'NoData collides with valid samples')
    data = np.where(valid, values, nodata).astype(dtype)
    with rasterio.open(path, 'w', driver='GTiff', height=grid['shape'][0], width=grid['shape'][1],
                       count=1, dtype=dtype, nodata=nodata, crs=grid['crs'],
                       transform=rasterio.Affine(*grid['transform']), tiled=False,
                       compress='none', BIGTIFF='NO') as dst:
        dst.write(data, 1)
    copied, support, copied_grid = read_raster(path, categorical=sbs, target_grid=True)
    if copied_grid != grid or not np.array_equal(valid, support) or not np.array_equal(values[valid], copied[valid]):
        fail('preparation_failed', 'Prepared samples, support or grid changed')


def align_sbs(values, valid, source_grid, target_grid):
    target = np.full(target_grid['shape'], 255., dtype=np.float64)
    reproject(np.where(valid, values, 255.), target,
              src_transform=rasterio.Affine(*source_grid['transform']), src_crs=source_grid['crs'],
              dst_transform=rasterio.Affine(*target_grid['transform']), dst_crs=target_grid['crs'],
              src_nodata=255., dst_nodata=255., resampling=Resampling.nearest)
    return target, target != 255.
