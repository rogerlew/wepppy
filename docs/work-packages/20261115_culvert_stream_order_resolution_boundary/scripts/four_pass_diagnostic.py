from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from whitebox_tools import WhiteboxTools
root=Path('/wc1/culverts/402e8594-d597-4c25-a724-008bb72a83e7')
run=root/'runs/1040/dem/wbt'
out=Path('/wc1/culvert-resolution-replay/four-pass'); out.mkdir(exist_ok=True)
w=WhiteboxTools(verbose=False,raise_on_error=True); w.set_working_dir(str(out))
w.prune_strahler_stream_order(str(root/'topo/netful.strahler_pruned_2.tif'),str(out/'order3.tif'),binary_output=False)
w.prune_strahler_stream_order(str(out/'order3.tif'),str(out/'netful4.tif'),binary_output=True)
with rasterio.open(run/'bound.tif') as bound, rasterio.open(out/'netful4.tif') as src:
 a=src.read(1,window=from_bounds(*bound.bounds,src.transform).round_offsets().round_lengths()); b=bound.read(1); mask=(b>0)&(b!=bound.nodata); a[~mask]=0
 profile=bound.profile.copy(); profile.update(dtype='float32',nodata=0)
 with rasterio.open(out/'netw0.tif','w',**profile) as dst: dst.write(a.astype('float32'),1)
 coords=json.loads((root/'runs/1040/watershed.nodb').read_text())['py/state']['_outlet']['pixel_coords']['py/tuple']; x,y=coords
 print(json.dumps({'outlet_pixel':coords,'outlet_stream_value':float(a[y,x]),'cropped_stream_pixels':int(np.sum(a>0))}),flush=True)
w.stream_junction_identifier(str(run/'flovec.vrt'),str(out/'netw0.tif'),str(out/'chnjnt.tif'))
w.strahler_stream_order(str(run/'flovec.vrt'),str(out/'netw0.tif'),str(out/'strahler.tif'))
w.hillslopes_topaz(dem=str(run/'relief.vrt'),d8_pntr=str(run/'flovec.vrt'),streams=str(out/'netw0.tif'),pour_pts=str(run/'outlet.geojson'),watershed=str(run/'bound.tif'),chnjnt=str(out/'chnjnt.tif'),subwta=str(out/'subwta.tif'),order=str(out/'strahler.tif'),netw=str(out/'netw.tsv'))
with rasterio.open(out/'subwta.tif') as d:
 v=np.unique(d.read(1)); v=v[(v>0)&(v!=d.nodata)]; channels=v[v%10==4]; hills=v[v%10!=4]
 print(json.dumps({'channels':len(channels),'hillslopes':len(hills),'output':str(out)}),flush=True)
