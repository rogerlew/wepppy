"""Bounded upload encoding detection; distribution-v1 is specified by ADR-0063."""
from pathlib import Path

import numpy as np
from rasterio.enums import Resampling
from rasterio.warp import reproject

from . import dnbr

__all__ = ['inspect_encoding']


def distribution(values):
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if not values.size:
        return {'count': 0, 'range': None, 'factor': None}
    q95, q99 = np.quantile(np.abs(values), [.95, .99])
    fractional = float(np.mean(np.abs(values - np.round(values)) > 1e-6))
    factor = None
    if values.size >= 32:
        if q99 <= 2 and fractional >= .05:
            factor = 1.0
        elif q95 > 2 and q99 <= 2000:
            factor = .001
    return {'count': int(values.size), 'range': [float(values.min()), float(values.max())],
            'q95_absolute': float(q95), 'q99_absolute': float(q99),
            'fraction_noninteger': fractional, 'factor': factor}


def inspect_encoding(source, dem, mask, *, mode='auto', factor=None, offset=0, refs=()):
    """Inspect only through the accepted detached decoder; never directly open VRT."""
    source, dem, mask = map(dnbr._file, (source, dem, mask))
    leaf, identity = dnbr._identity_vrt(source, refs) if source.suffix.lower() == '.vrt' else (source, None)
    with dnbr._raster(leaf) as src, dnbr._raster(Path(dem)) as reference, dnbr._raster(Path(mask)) as watershed:
        grid = dnbr._grid(reference)
        inside = dnbr._mask(watershed, grid)
        if identity:
            import rasterio
            if identity != (src.width, src.height, src.transform, src.crs, rasterio.dtypes._gdal_typename(src.dtypes[0])):
                raise dnbr.DnbrError('unsupported_vrt', 'VRT must match its uploaded raster.')
        values, valid = dnbr._read(src)
        values[~valid] = np.nan
        aligned = np.full(grid[0], np.nan, dtype=np.float64)
        reproject(values, aligned, src_transform=src.transform, src_crs=src.crs,
                  src_nodata=np.nan, dst_transform=grid[1], dst_crs=grid[2],
                  dst_nodata=np.nan, resampling=Resampling.nearest)
        whole, local = distribution(values), distribution(aligned[inside])
        if not local['count']:
            raise dnbr.DnbrError('no_valid_target_overlap', 'The dNBR map has no usable data inside this watershed.')
        metadata = (src.scales[0], src.offsets[0])
        method = 'selected'
        if mode == 'auto':
            choices = {d['factor'] for d in (whole, local) if d['factor'] is not None}
            if len(choices) > 1:
                raise dnbr.DnbrError('ambiguous_encoding', 'Could not determine the dNBR value scale. Choose the scale used by your map.')
            factor = next(iter(choices)) if choices else None
            offset, method = 0., 'distribution'
            if factor is None and metadata != (1., 0.):
                factor, offset = metadata
                method = 'metadata'
            if factor is None:
                raise dnbr.DnbrError('ambiguous_encoding', 'Could not determine the dNBR value scale. Choose the scale used by your map.')
        elif mode in ('scaled_1000', 'normalized'):
            factor, offset = (.001 if mode == 'scaled_1000' else 1.), 0.
        elif mode != 'custom':
            raise dnbr.DnbrError('invalid_encoding', 'Choose a supported dNBR value scale.')
        factor, offset = dnbr._encoding(factor, offset)
        if metadata != (1., 0.) and metadata != (factor, offset):
            raise dnbr.DnbrError('encoding_conflict', 'The selected scale conflicts with the map metadata.')
        return {'version': 'distribution-v1', 'mode': mode, 'factor': factor, 'offset': offset,
                'method': method, 'source': whole, 'watershed': local,
                'format': src.driver, 'dtype': src.dtypes[0]}
