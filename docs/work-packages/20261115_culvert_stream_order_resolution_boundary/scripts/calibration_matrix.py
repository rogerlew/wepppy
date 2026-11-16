"""Isolated first-stage resolution/threshold/pruning and point-intersection study."""
import json
import math
import time
from pathlib import Path

import numpy as np
import rasterio
from osgeo import gdal
from scipy.spatial import cKDTree
from whitebox_tools import WhiteboxTools

ROOT = Path('/wc1/culvert-resolution-replay/calibration')
SOURCE = Path('/wc1/culverts/402e8594-d597-4c25-a724-008bb72a83e7/topo/breached_filled_DEM_UTM.tif')


def grid_cells(span, size):
    """Avoid an extra edge cell caused solely by source metadata rounding."""
    cells = span / size
    nearest = round(cells)
    return nearest if abs(cells - nearest) < 1e-6 else math.ceil(cells)


def main(sizes=(1, 2, 4, 8, 10)):
    gdal.UseExceptions()
    points = json.loads((ROOT / 'source/culvert_points.geojson').read_text())['features']
    xy = np.array([f['geometry']['coordinates'][:2] for f in points])
    ids = [f['properties']['Point_ID'] for f in points]
    with rasterio.open(SOURCE) as src:
        left, bottom, right, top = src.bounds
        crs = src.crs
    w = WhiteboxTools(verbose=False, raise_on_error=True)
    for size in sizes:
        directory = ROOT / f'{size}m'
        directory.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        w.set_working_dir(str(directory))
        dem = SOURCE
        if size != 1:
            averaged = directory / 'averaged.tif'
            dem = directory / 'conditioned.tif'
            bounds = [left, top - grid_cells(top-bottom, size)*size,
                      left + grid_cells(right-left, size)*size, top]
            gdal.Warp(str(averaged), str(SOURCE), format='GTiff',
                      outputBounds=bounds, xRes=size, yRes=size,
                      resampleAlg='average', dstNodata=-9999,
                      creationOptions=['COMPRESS=LZW']).FlushCache()
            w.fill_depressions(str(averaged), str(dem), fix_flats=True)
            with rasterio.open(averaged) as a, rasterio.open(dem) as b:
                original = a.read(1); filled = b.read(1)
                valid = a.read_masks(1) > 0
                delta = filled[valid] - original[valid]
                (directory/'conditioning.json').write_text(json.dumps({
                    'changed_cells': int(np.count_nonzero(delta)),
                    'maximum_raise_m': float(delta.max()),
                    'mean_raise_m': float(delta.mean())}, indent=2))
        pointer = directory / 'pointer.tif'
        accumulation = directory / 'accumulation.tif'
        w.d8_pointer(str(dem), str(pointer))
        w.d8_flow_accumulation(str(pointer), str(accumulation), out_type='cells', pntr=True)
        with rasterio.open(dem) as d:
            assert d.crs == crs
            resolution = abs(d.transform.a)
        for mode, threshold in [('cells100', 100), ('area8697', 8697/resolution**2)]:
            streams = directory / f'{mode}-streams.tif'
            short = directory / f'{mode}-short.tif'
            order = directory / f'{mode}-order.tif'
            w.extract_streams(str(accumulation), str(streams), threshold=threshold)
            w.remove_short_streams(str(pointer), str(streams), str(short), min_length=2*resolution)
            w.strahler_stream_order(str(pointer), str(short), str(order))
            with rasterio.open(order) as d:
                values = d.read(1)
                valid = d.read_masks(1) > 0
                rows, cols = rasterio.transform.rowcol(d.transform, xy[:,0], xy[:,1])
                for passes in range(6):
                    mask = valid & (values > passes) & (values > 0)
                    rr, cc = np.nonzero(mask)
                    centers = np.column_stack((d.transform.c+(cc+0.5)*resolution,
                                               d.transform.f-(rr+0.5)*resolution))
                    distances = cKDTree(centers).query(xy)[0] if len(rr) else [None]*len(ids)
                    intersections = []
                    for point_id, row, col, distance in zip(ids, rows, cols, distances):
                        inside = 0 <= row < d.height and 0 <= col < d.width
                        intersections.append({'point_id': point_id, 'inside_grid': inside,
                            'on_stream_cell': bool(mask[row,col]) if inside else False,
                            'nearest_stream_center_m': float(distance) if distance is not None else None})
                    record = {'cellsize_m': resolution, 'mode': mode,
                              'threshold_cells': threshold, 'passes': passes,
                              'stream_pixels': len(rr), 'points': intersections,
                              'elapsed_seconds': time.monotonic()-started,
                              'note': 'Original culvert points; nearest distance is not same-path distance. No hillslope count inferred.'}
                    target = directory / f'{mode}-pass{passes}.json'
                    target.write_text(json.dumps(record, indent=2)+'\n')
                    print(json.dumps({k:v for k,v in record.items() if k not in ['points','note']}), flush=True)
                    del centers
        print(f'Completed {size}m', flush=True)


if __name__ == '__main__':
    main()
