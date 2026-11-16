"""Measure raw observations and retained WEPP outlets separately from payload snaps."""
import json
from pathlib import Path
import numpy as np
import rasterio
from pyproj import Transformer
from scipy.spatial import cKDTree
ROOT=Path('/wc1/culvert-resolution-replay/calibration')

def main():
    points=json.loads((ROOT/'source/culvert_points.geojson').read_text())['features']
    outlets=json.loads((ROOT/'source/resolved-outlets.json').read_text())
    transform=Transformer.from_crs('EPSG:4326','EPSG:32617',always_xy=True)
    refs=[]
    for f in points:
        p=f['properties']
        if p.get('Orig_Lon') is not None and p.get('Orig_Lat') is not None:
            refs.append((str(p['Point_ID']),'raw_observation',transform.transform(p['Orig_Lon'],p['Orig_Lat'])))
    for o in outlets:
        if o['outlet'] is not None:
            refs.append((str(o['point_id']),'retained_wepp_outlet',transform.transform(*o['outlet']['actual_loc']['py/tuple'])))
    xy=np.array([r[2] for r in refs])
    for path in sorted(ROOT.glob('*m/*-order.tif')):
        mode=path.name.removesuffix('-order.tif')
        with rasterio.open(path) as d:
            values=d.read(1); valid=d.read_masks(1)>0
            rows,cols=rasterio.transform.rowcol(d.transform,xy[:,0],xy[:,1])
            for passes in range(6):
                mask=valid&(values>passes)&(values>0); rr,cc=np.nonzero(mask)
                centers=np.column_stack((d.transform.c+(cc+0.5)*d.transform.a,
                                         d.transform.f+(rr+0.5)*d.transform.e))
                dist=cKDTree(centers).query(xy)[0] if len(rr) else [None]*len(refs)
                results=[]
                for ref,row,col,distance in zip(refs,rows,cols,dist):
                    inside=0<=row<d.height and 0<=col<d.width
                    results.append({'point_id':ref[0],'reference':ref[1],
                       'on_stream_cell':bool(mask[row,col]) if inside else False,
                       'nearest_stream_center_m':float(distance) if distance is not None else None})
                (path.parent/f'{mode}-pass{passes}-references.json').write_text(json.dumps(results,indent=2)+'\n')
        print(str(path),flush=True)

if __name__=='__main__': main()
