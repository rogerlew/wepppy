"""Real owned terrain executable, independent analytical basin expectations."""
import os
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from wepppy.nodb.mods.postfire_debris_flow.m3_terrain import build_terrain
from wepppy.nodb.mods.postfire_debris_flow import rainfall_io as io

pytestmark = pytest.mark.integration
BINARY = Path(os.environ.get('STALEY_WBT_EXECUTABLE', '/workdir/weppcloud-wbt/target/release/whitebox_tools'))


def raster(path, values, transform):
    with rasterio.open(path, 'w', driver='GTiff', count=1, dtype=values.dtype,
                       height=values.shape[0], width=values.shape[1], crs='EPSG:32611',
                       transform=transform, nodata=-9999) as ds:
        ds.write(values, 1)


@pytest.fixture
def terrain(tmp_path):
    if not BINARY.is_file():
        pytest.skip('Actual D8UpstreamRelief executable unavailable')
    source = tmp_path/'source'; source.mkdir()
    grid = from_origin(500000, 4000000, 10, 10)
    dem = np.zeros((7,7), dtype='float64'); dem[3,2:5] = [130,90,100]
    pointer = np.zeros((7,7), dtype='float64'); pointer[3,2:4] = 2
    mask = np.zeros((7,7), dtype='float64'); mask[3,2:5] = 1
    paths = [source/f'{name}.tif' for name in ('dem','pointer','mask')]
    for p, values in zip(paths, (dem,pointer,mask)):
        raster(p, values, grid)
    return paths


def build(paths, output, outlet=(3,4)):
    expected = {str(p):io.digest(p, 512*1024*1024) for p in (*paths, BINARY)}
    return build_terrain(*paths, outlet, output, binary=BINARY, expected_sha256=expected)


@pytest.mark.parametrize('middle', [90,120])
def test_actual_native_relief_uses_raw_outlet_not_basin_minimum(terrain, tmp_path, middle):
    with rasterio.open(terrain[0], 'r+') as ds:
        values = ds.read(1); values[3,3] = middle; ds.write(values,1)
    before = [p.read_bytes() for p in terrain]
    result = build(terrain, tmp_path/'result')
    assert result['summary']['terrain_valid'] is True
    assert result['summary']['relief_m'] == 30
    assert result['summary']['area_m2'] == 300
    assert result['summary']['full_upstream_cells'] == 3
    assert result['T'] == pytest.approx(30/np.sqrt(300))
    assert [p.read_bytes() for p in terrain] == before
    assert not (tmp_path/'result/incomplete.json').exists()
    for name, expected in result['artifacts_sha256'].items():
        assert io.digest(tmp_path/'result'/name) == expected


def test_authoritative_area_mismatch_is_unavailable(terrain, tmp_path):
    with rasterio.open(terrain[2], 'r+') as ds:
        values = ds.read(1); values[3,2] = 0; ds.write(values,1)
    result = build(terrain, tmp_path/'mismatch')
    assert result['T'] is None
    assert result['summary']['reason'] == 'watershed_area_mismatch'


def test_edge_truncation_is_not_proven_full_terrain(terrain, tmp_path):
    with rasterio.open(terrain[1], 'r+') as ds:
        values = ds.read(1); values[3,:4] = 2; ds.write(values,1)
    with rasterio.open(terrain[2], 'r+') as ds:
        values = ds.read(1); values[3,:5] = 1; ds.write(values,1)
    result = build(terrain, tmp_path/'truncated')
    assert result['T'] is None
    assert result['summary']['reason'] == 'terrain_potentially_truncated'


def test_equal_area_wrong_membership_is_rejected(terrain, tmp_path):
    with rasterio.open(terrain[2], 'r+') as ds:
        values = ds.read(1); values[3,2] = 0; values[2,4] = 1; ds.write(values,1)
    with pytest.raises(io.RainfallError, match='membership'):
        build(terrain, tmp_path/'wrong_membership')


def test_reject_outside_outlet_and_existing_output(terrain, tmp_path):
    with pytest.raises(io.RainfallError, match='Outlet'):
        build(terrain, tmp_path/'outside', (0,0))
    build(terrain, tmp_path/'result')
    with pytest.raises(FileExistsError):
        build(terrain, tmp_path/'result')
