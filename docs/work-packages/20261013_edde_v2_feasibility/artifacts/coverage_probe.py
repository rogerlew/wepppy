"""Check PRISM coverage independently of EDDE eligibility using a retained native grid."""
import json
from pathlib import Path
import zipfile

import rasterio
from pyproj import Transformer

from wepppy.climates.edde.client import sha256,write_json

HERE=Path(__file__).resolve().parent
GRID=Path('/home/workdir/wepppy-scratch/prism-stochastic-dewpoint-20261008/prism-normal-ppt-01.zip')


def main():
    expected=json.loads((HERE.parents[1]/'20261008_prism_stochastic_dewpoint/artifacts/normal-grid-validation.json').read_text())['sha256']
    if sha256(GRID)!=expected:raise ValueError('PRISM grid differs from retained acquisition')
    with zipfile.ZipFile(GRID) as archive:name=next(n for n in archive.namelist() if n.endswith('.tif'))
    records=[]
    with rasterio.open(f'/vsizip/{GRID}/{name}') as ds:
        transform=Transformer.from_crs(4326,ds.crs,always_xy=True)
        points=json.loads((HERE/'location-eligibility.json').read_text())
        for point in [p for p in points if p['model']=='WRF-MPI']:
            x,y=transform.transform(point['longitude'],point['latitude'])
            value=next(ds.sample([(x,y)],masked=True))[0];row,col=ds.index(x,y)
            valid=0<=row<ds.height and 0<=col<ds.width and not bool(getattr(value,'mask',False))
            records.append(dict(point=point['name'],january_ppt_valid=valid,value_mm=float(value) if valid else None))
    write_json(HERE/'prism-coverage-probe.json',dict(source_sha256=expected,source_path=str(GRID),records=records,
               limitation='One-month precipitation grid is an exclusion probe; a pass does not establish all-variable/year-round PRISM eligibility'))


if __name__=='__main__':main()
