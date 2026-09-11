from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from wepppy.nodb.mods.postfire_debris_flow.encoding import distribution, inspect_encoding
from wepppy.nodb.mods.postfire_debris_flow.dnbr import DnbrError

pytestmark = pytest.mark.unit

@pytest.mark.parametrize('values,factor', [
    (np.linspace(-500, 900, 100), .001),
    (np.linspace(-.5, .9, 100), 1.),
    (np.zeros(100), None), (np.tile([-1, 0, 1], 100), None),
    (np.arange(20), None), (np.linspace(3000, 9000, 100), None),
    (np.r_[np.linspace(-.5, .9, 9999), 999999], 1.),
])
def test_distribution(values, factor):
    assert distribution(values)['factor'] == factor


def write(path, a, *, shift=0, scale=1):
    with rasterio.open(path, 'w', driver='GTiff', width=10, height=10,
                       count=1, dtype='float32', crs='EPSG:32611',
                       transform=from_origin(500000+shift, 4000000, 10, 10), nodata=-9999) as dst:
        dst.write(np.asarray(a, dtype='float32').reshape(10, 10), 1)
        dst.scales = [scale]


def test_real_decoder_mask_overlap_and_conflict(tmp_path):
    dem, mask, source = (tmp_path / name for name in ('dem.tif','mask.tif','source.tif'))
    write(dem, np.ones(100)*100); write(mask, np.ones(100))
    values = np.linspace(-500, 900, 100); values[0] = -9999
    write(source, values)
    result = inspect_encoding(source, dem, mask)
    assert result['factor'] == .001
    assert result['source']['count'] == 99
    write(source, values, scale=.01)
    with pytest.raises(DnbrError, match='conflicts'):
        inspect_encoding(source, dem, mask)
    write(source, values, shift=100000)
    with pytest.raises(DnbrError, match='no usable data'):
        inspect_encoding(source, dem, mask)


def test_unsafe_vrt_never_decoded(tmp_path):
    source=tmp_path/'source.vrt'
    source.write_text('<VRTDataset><VRTRasterBand subClass="VRTDerivedRasterBand"><PixelFunctionType>evil</PixelFunctionType></VRTRasterBand></VRTDataset>')
    with pytest.raises(DnbrError):
        inspect_encoding(source, tmp_path/'dem.tif', tmp_path/'mask.tif')
