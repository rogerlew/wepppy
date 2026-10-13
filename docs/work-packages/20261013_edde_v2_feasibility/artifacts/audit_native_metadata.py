"""Read every retained native monthly header/time axis without query abstractions."""
import hashlib
import json
from pathlib import Path
import time

import netCDF4
import numpy as np
import pandas as pd

from wepppy.climates.edde.client import write_json
from workflows import HERE,ROOT


def main():
    started=time.monotonic();records=[]
    for manifest in sorted((HERE/'queries').glob('*/*/*.json')):
        state=json.loads(manifest.read_text())
        if state['status']!='complete':continue
        cache=ROOT/'cache'/state['model']/state['scenario']
        key=state['grid']['source']['key'];grid=cache/(hashlib.sha256(key.encode()).hexdigest()+'.nc')
        with netCDF4.Dataset(grid) as ds:
            x,y=np.asarray(ds['x'][:]),np.asarray(ds['y'][:]);crs=ds.CRS
        for obj in state['objects']:
            key=obj['source']['key'];path=cache/(hashlib.sha256(key.encode()).hexdigest()+'.nc')
            with netCDF4.Dataset(path) as ds:
                if ds.CRS!=crs or not np.array_equal(x,ds['x'][:]) or not np.array_equal(y,ds['y'][:]):
                    raise ValueError(f'Native grid disagreement: {key}')
                times=pd.DatetimeIndex(np.asarray(netCDF4.num2date(ds['time'][:],ds['time'].units,only_use_cftime_datetimes=False)))
                strings=netCDF4.chartostring(ds['mtime'][:]).tolist()
                expected=[d.strftime('%Y-%m-%d-%H:%M:%S') for d in times]
                if strings!=expected:raise ValueError(f'Native dual-time disagreement: {key}')
                if obj['first']!=str(times[0]) or obj['last']!=str(times[-1]):raise ValueError('Manifest time mismatch')
                field=ds[obj['netcdf_variable']]
                if field.units!=obj['units']:raise ValueError('Manifest unit mismatch')
                records.append(dict(key=key,days=len(times),first=str(times[0]),last=str(times[-1])))
    write_json(HERE/'native-metadata-audit.json',dict(status='complete',mtime_format='YYYY-MM-DD-HH:MM:SS',objects=len(records),seconds=time.monotonic()-started,
                checks=['All source axes and CRS agree with the selected static grid',
                        'Every CF time agrees with its published mtime string',
                        'Manifest unit and first/last times agree with native fields'],
                records=records))
    print(len(records),'native monthly objects verified')


if __name__=='__main__':main()
