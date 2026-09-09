import json
import numpy as np
from affine import Affine
from pfdf import watershed
from pfdf.raster import Raster
for name, heights in [('descending',[130,120,100,95,90]),('internal_maximum',[110,130,100,95,90]),('pit',[130,90,100,95,90])]:
    z=np.full((5,9),-9999.,dtype=float)
    f=np.full((5,9),-9999,dtype=np.int64)
    z[2,2:7]=heights
    f[2,2:7]=1
    kw=dict(nodata=-9999,crs=32611,transform=Affine(10,0,500000,0,-10,5200000))
    dem=Raster.from_array(z,**kw); flow=Raster.from_array(f,**kw)
    print(json.dumps(dict(case=name,heights=heights,relief=watershed.relief(dem,flow).values[2,2:7].tolist(),area=watershed.accumulation(flow,times=100).values[2,2:7].tolist())),flush=True)
