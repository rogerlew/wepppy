"""Additive exact-support result artifact, independent of original run paths."""
import numpy as np
import rasterio

from . import rainfall_io as io
from .m1_inputs import read_raster
from .soil_inputs import _copy

__all__ = ['copy_support', 'read_support']


def copy_support(source, output, predictors):
    expected = predictors['artifacts_sha256']['valid_mask.tif']
    _copy(source/'valid_mask.tif',output/'valid_mask.tif',expected,io.MAX_PREDICTOR_BYTES)
    return {'coverage':dict(predictors['coverage']),'artifacts_sha256':{'valid_mask.tif':expected}}


def read_support(directory,manifest,consumed):
    predictors = manifest['predictor_snapshot']
    if predictors['schema_version'] == 1:
        if 'coverage' in manifest or 'artifacts_sha256' in manifest:
            io.fail('invalid_input','Legacy result cannot assert unrecorded support')
        return {}
    expected = predictors['artifacts_sha256']['valid_mask.tif']
    if (manifest.get('coverage') != predictors['coverage']
            or manifest.get('artifacts_sha256') != {'valid_mask.tif':expected}):
        io.fail('invalid_input','Result support differs from predictor snapshot')
    path = directory/'valid_mask.tif'
    io.pinned(path,{str(path):expected},consumed,io.MAX_PREDICTOR_BYTES)
    values,valid,grid = read_raster(path,categorical=True)
    with rasterio.open(path) as ds:
        if ds.dtypes != ('uint8',) or ds.nodata != 255:
            io.fail('invalid_input','Invalid result support mask encoding')
    coverage = manifest['coverage']
    if (grid != predictors['grid'] or not np.isin(values[valid],[0,1]).all()
            or np.any(values[~valid] != 255) or int(valid.sum()) != coverage['total_cells']
            or int(np.count_nonzero(valid & (values == 1))) != coverage['valid_cells']):
        io.fail('invalid_input','Result mask differs from coverage')
    return {str(path):io.MAX_PREDICTOR_BYTES}
