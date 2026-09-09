"""Read the frozen Topanga fixture; print evidence without modifying inputs.

Run from the repository root with wctl run-python and redirect stdout to
artifacts/watershed_artifact_audit.json. This is an offline evidence script,
not a production artifact loader or a raster routing implementation.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask


ROOT = Path('/workdir/weppcloud-wbt/test_fixtures/staley_m3_resolution/topanga/10m/dem')


def main():
    paths = ['dem.tif', 'wbt/flovec.tif', 'wbt/bound.tif', 'wbt/subwta.tif',
             'wbt/outlet.geojson', 'wbt/bound.geojson', 'wbt/bound.WGS.geojson']
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
              for name in paths}
    outlet = json.loads((ROOT / 'wbt/outlet.geojson').read_text())['features'][0]
    props = outlet['properties']
    row, col = props['row'], props['column']
    with rasterio.open(ROOT / 'wbt/bound.tif') as bound:
        values = bound.read(1, masked=True)
        support = (~np.ma.getmaskarray(values)) & (values.filled(0) > 0)
        transform, crs, shape = bound.transform, bound.crs, bound.shape
        pixel_area = abs(transform.a * transform.e - transform.b * transform.d)
        polygon = json.loads((ROOT / 'wbt/bound.geojson').read_text())
        polygon_support = geometry_mask(
            [f['geometry'] for f in polygon['features']], shape, transform,
            invert=True, all_touched=False,
        )
        edges = np.zeros(shape, dtype=bool)
        edges[[0, -1], :] = True
        edges[:, [0, -1]] = True
        result = dict(
            fixture=str(ROOT), source_sha256=hashes,
            grid=dict(shape=list(shape), affine=list(transform)[:6], crs=str(crs),
                      linear_units=crs.linear_units),
            positive_mask_labels=np.unique(values.compressed()).tolist(),
            mask_cells=int(support.sum()), cell_area_m2=pixel_area,
            watershed_area_m2=float(support.sum() * pixel_area),
            mask_edge_cells=int(np.count_nonzero(support & edges)),
            outlet_row=row, outlet_column=col, outlet_in_routed_mask=bool(support[row, col]),
            outlet_xy=list(bound.xy(row, col)),
            outlet_geojson_xy=outlet['geometry']['coordinates'],
            requested_row=props['requested_row'], requested_column=props['requested_col'],
            selection_metadata_outlet_in_mask=props['outlet_in_mask'],
            selection_metadata_watershed_cell_count=props['watershed_cell_count'],
            derived_polygon_center_mask_difference_cells=int(np.count_nonzero(
                polygon_support != support)),
        )
    grids = {}
    for name in ['dem.tif', 'wbt/flovec.tif', 'wbt/subwta.tif']:
        with rasterio.open(ROOT / name) as source:
            grids[name] = source.shape == shape and source.crs == crs and source.transform == transform
            if name == 'wbt/subwta.tif':
                data = source.read(1, masked=True)
                sub_support = (~np.ma.getmaskarray(data)) & (data.filled(0) > 0)
                result['subwta_mask_difference_cells'] = int(np.count_nonzero(sub_support != support))
    result['grid_matches'] = grids
    assert all(grids.values())
    assert result['outlet_in_routed_mask']
    assert result['outlet_xy'] == result['outlet_geojson_xy']
    assert result['subwta_mask_difference_cells'] == 0
    assert hashes == {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                      for name in paths}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
