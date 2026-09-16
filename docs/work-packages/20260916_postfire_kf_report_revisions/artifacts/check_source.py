"""Research-only source parity probe; no run writes or production integration.
Run from repository root with .venv/bin/python <this-file>.
"""
import importlib.util
import json
from pathlib import Path
import fiona
import numpy as np
import rasterio
from rasterio.io import FilePath
from rasterio.features import rasterize
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import from_bounds, Window

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('research_transport', 'wepppy/nodb/mods/postfire_debris_flow/source_transport.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
# This isolated research process reuses bounded transport without changing
# the production allowlist or any project files.
transport.THICK_URL = 'https://prod-is-usgs-sb-prod-publish.s3.amazonaws.com/6750c172d34ed8d3858534d8/statsgo-KFFACT.tif'
output = ROOT / 'source-probe'
output.mkdir(exist_ok=False)
requests = output / 'requests'
requests.mkdir()
t = transport.Transport(requests)
results = []
with transport.deadline(120):
    source = transport.RangeFile(t)
    with FilePath(source) as bridge, bridge.open(driver='GTiff') as ds:
        for name, region, bounds in [('thomas', '18', (-119.67, 34.40, -119.56, 34.50)), ('arizona', '15', (-110.90, 33.75, -110.80, 33.85))]:
            projected = transform_bounds('EPSG:4326', ds.crs, *bounds)
            f = from_bounds(*projected, transform=ds.transform)
            win = Window(np.floor(f.col_off), np.floor(f.row_off), np.ceil(f.width)+2, np.ceil(f.height)+2)
            values = ds.read(1, window=win)
            affine = ds.window_transform(win)
            with fiona.open('zip://' + str((ROOT / 'source-evidence' / f'ussoils_{region}shp.zip').resolve())) as vectors:
                features = list(vectors.filter(bbox=projected))
                shapes = [(feature['geometry'], feature['properties']['KFFACT']) for feature in features]
                reference = rasterize(shapes, out_shape=values.shape, transform=affine, fill=np.nan, dtype='float32')
            valid = np.isfinite(values) & np.isfinite(reference)
            difference = np.abs(values[valid]-reference[valid])
            profile = dict(driver='GTiff', width=values.shape[1], height=values.shape[0], count=1, dtype='float32', crs=ds.crs, transform=affine, nodata=np.nan, compress='deflate')
            with rasterio.open(output / f'{name}-native.tif', 'w', **profile) as dst:
                dst.write(values, 1)
            result = dict(name=name, valid_comparison_cells=int(valid.sum()), exact_cells=int((difference==0).sum()), max_absolute_error=float(difference.max()), source_values=np.unique(values[valid]).tolist(), map_units=[dict(f['properties']) for f in features])
            if name == 'thomas':
                saved = Path('/wc1/runs/ne/nervous-mesquite/postfire_debris_flow/attempts/a909f2c1b3c0468084d31a8cdd0e24f2/predictors/prepared')
                with rasterio.open(saved / 'common_domain.tif') as domain:
                    mask = domain.read(1)>0
                    target = np.full(domain.shape, np.nan, dtype='float32')
                    reproject(values, target, src_transform=affine, src_crs=ds.crs, src_nodata=np.nan, dst_transform=domain.transform, dst_crs=domain.crs, dst_nodata=np.nan, resampling=Resampling.nearest)
                    use = mask & np.isfinite(target) & (target>=0)
                    result['legacy_common_support_probe'] = dict(cells=int(use.sum()), mean=float(target[use].astype('float64').mean()), note='Research only; legacy support includes POLARIS validity. Not the new Kf production common mask.')
            results.append(result)
    source.verify()
    (output / 'results.json').write_text(json.dumps(dict(results=results, identity=source.identity, bytes=t.received, requests=t.requests), indent=2)+'\n')
print(json.dumps([dict((k,v) for k,v in r.items() if k!='map_units') for r in results], indent=2))
