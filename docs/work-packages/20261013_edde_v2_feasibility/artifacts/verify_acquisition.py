"""Independent direct-NetCDF parity, native-edge checks, and warm-cache benchmark."""
import json
from pathlib import Path
import resource
import time

import netCDF4
import numpy as np
import pandas as pd
from pyproj import Transformer

from wepppy.climates.edde.client import EddeClient,EligibilityError,Point,locate,sha256,write_json

HERE=Path(__file__).resolve().parent
ROOT=Path('/home/workdir/wepppy-scratch/edde-v2-20261013')


def main():
    root=HERE/'queries/WRF-MPI/Historical'
    manifest=json.loads((root/'1995.json').read_text())
    points=[Point(p['name'],p['longitude'],p['latitude']) for p in manifest['points']]
    client=EddeClient(ROOT/'cache/WRF-MPI/Historical')
    started=time.monotonic()
    table,warm=client.query(points,'WRF-MPI','Historical','1995-01-01','1995-12-31',['prday','tsmax','tsmin'])
    source=pd.read_csv(root/'1995.csv',parse_dates=['date'])
    pd.testing.assert_frame_equal(table,source,check_dtype=False,check_names=False)
    record=dict(cold_seconds=manifest['wall_seconds'],warm_seconds=time.monotonic()-started,
                cold_transferred_bytes=manifest['transferred_bytes'],warm_transferred_bytes=warm['transferred_bytes'],
                source_bytes=manifest['source_bytes'],point_days=len(table),
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,direct_parity=[])
    for obj in manifest['objects'][:3]:
        path,meta=client.fetch(obj['source'])
        with netCDF4.Dataset(path) as ds:
            variable=ds[obj['netcdf_variable']]
            for point in manifest['points']:
                expected=variable[:,point['row'],point['col']]
                actual=source[(source.point==point['name'])&(source.date.dt.month==1)][obj['variable']]
                error=float(np.max(abs(expected-actual.to_numpy())))
                if not np.array_equal(expected,actual.to_numpy(dtype=expected.dtype)):
                    raise ValueError('Native float32 round-trip parity failed')
                record['direct_parity'].append(dict(point=point['name'],variable=obj['variable'],max_decimal_readback_error=error,native_float32_equal=True))
    write_json(HERE/'warm-cache-and-direct-parity.json',record)
    edges=[]
    for model in ['WRF-MPI','WRF-Nor']:
        grid,meta=client.grid(model)
        with netCDF4.Dataset(grid) as ds:
            x,y=ds['x'][:],ds['y'][:];mask=ds['LANDMASK'][:]
            edge=np.argwhere((mask==1)&(np.indices(mask.shape)[0]==len(y)-1))[0]
            row,col=map(int,edge)
            transform=Transformer.from_crs(ds.CRS,4326,always_xy=True)
            for name,px,py in [('north-edge',x[col],y[row]),('outside-north',x[col],y[-1]+12000)]:
                lon,lat=transform.transform(px,py)
                point=Point(name,lon,lat)
                try:result=dict(eligible=True,**locate(grid,[point])[0])
                except EligibilityError as error:result=dict(eligible=False,name=name,reason=str(error))
                edges.append(dict(model=model,**result))
    write_json(HERE/'native-edge-probes.json',edges)
    print(record['cold_seconds'],record['warm_seconds'],record['warm_transferred_bytes'])


if __name__=='__main__':main()
