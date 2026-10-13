"""Inspect true hourly metadata and daily precipitation aggregation alignment."""
import json
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd

from wepppy.climates.edde.client import EddeClient,write_json

HERE=Path(__file__).resolve().parent
ROOT=Path('/home/workdir/wepppy-scratch/edde-v2-20261013')


def main():
    client=EddeClient(ROOT/'aux-cache',max_download_bytes=4_000_000_000)
    inventory=json.loads((HERE/'hourly-1995-inventory.json').read_text())
    points=[p for p in json.loads((HERE/'location-eligibility.json').read_text())
            if p['model']=='WRF-MPI' and p['eligible']]
    records=[]
    for variable in ['pr','rsds','td','wspds']:
        obj=next(o for o in inventory if o['key'].split('/')[-1].startswith(variable+'.')
                 and '.1995-01.raw.nc' in o['key'])
        path,meta=client.fetch(obj)
        with netCDF4.Dataset(path) as ds:
            v=next(v for v in ds.variables.values() if v.dimensions==('time','y','x'))
            times=pd.DatetimeIndex(netCDF4.num2date(ds['time'][:],ds['time'].units,
                                   only_use_cftime_datetimes=False))
            meta.update(variable=variable,netcdf_variable=v.name,units=v.units,
                        long_name=getattr(v,'long_name',''),cell_methods=getattr(v,'cell_methods',''),
                        first=str(times[0]),last=str(times[-1]),count=len(times))
            rows=[]
            for point in points:
                data=v[:,point['row'],point['col']]
                assert not np.ma.getmaskarray(data).any() and np.isfinite(data).all()
                rows.append(pd.DataFrame(dict(point=point['name'],date=times,value=data)))
            pd.concat(rows).to_csv(HERE/f'auxiliary-{variable}.csv',index=False)
        records.append(meta)
        print(variable,meta['units'],meta['first'],meta['last'],flush=True)
    write_json(HERE/'auxiliary-metadata.json',records)


if __name__=='__main__':main()
