import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.features import geometry_mask,bounds
from rasterio.windows import from_bounds,Window
root=Path('/wc1/culvert-resolution-replay/calibration')
features=json.loads((root/'source/watersheds.geojson').read_text())['features']
points=json.loads((root/'1m/cells100-pass4.json').read_text())['points']
lost={str(p['point_id']) for p in points if not p['on_stream_cell']}
out=[]
with rasterio.open(root/'1m/cells100-order.tif') as ds:
 for f in features:
  ident=str(f['properties']['Point_ID'])
  if ident not in lost:continue
  w=from_bounds(*bounds(f['geometry']),ds.transform).round_offsets().round_lengths().intersection(Window(0,0,ds.width,ds.height))
  a=ds.read(1,window=w);valid=ds.read_masks(1,window=w)>0
  inside=geometry_mask([f['geometry']],out_shape=a.shape,transform=ds.window_transform(w),invert=True)
  n=int(np.sum(inside&valid&(a>4)))
  out.append({'point_id':ident,'remaining_channel_pixels_inside_supplied_polygon':n,'zero_coverage_fallback_expected':n==0})
print(json.dumps(out,indent=2))
