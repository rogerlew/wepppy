#!/usr/bin/env python3
"""Reproduce the unauthenticated PRISM normals acquisition; retain raw evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import zipfile

import pandas as pd
import rasterio
import requests
from pyproj import Transformer

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/workdir/wepppy-scratch/prism-stochastic-dewpoint-20261008')
RPC = 'https://prism.oregonstate.edu/explorer/dataexplorer/rpc.php'


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    request = json.loads((HERE / 'normals-request.json').read_text())
    if not (HERE / 'normals.csv').exists():
        response = requests.post(RPC, data=request['params'], timeout=60)
        response.raise_for_status()
        save('normals-submit.json', response.json())
        result = response.json()
        ticket = result.get('gricket')
        for attempt in range(120):
            if result.get('errors'):
                raise ValueError(result['errors'])
            if 'result' in result:
                break
            assert ticket and 'delay' in result
            time.sleep(5)
            response = requests.post(RPC, data=dict(call='pp/checkup', proc='gridserv', gricket=ticket), timeout=60)
            response.raise_for_status()
            result = response.json()
            save(f'normals-poll-{attempt}.json', result)
        else:
            raise TimeoutError(ticket)
        url = 'https://prism.oregonstate.edu/explorer/tmp/' + result['result']['csv']
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        (HERE / 'normals.csv').write_bytes(response.content)
        save('normals-download.json', dict(url=url, headers=dict(response.headers)))
    data = pd.read_csv(HERE / 'normals.csv', skiprows=10)
    assert 'Monthly 1991-2020 Normals' in (HERE / 'normals.csv').read_text()
    assert len(data) == 117 and len(set(data.Name)) == 9
    archive = ROOT / 'prism-normal-ppt-01.zip'
    if not archive.exists():
        response = requests.get('https://services.nacse.org/prism/data/get/normals/us/800m/ppt/01', timeout=90)
        response.raise_for_status()
        ROOT.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(response.content)
    grid_record = json.loads((HERE / 'normal-grid-validation.json').read_text())
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == grid_record['sha256']
    sites = json.loads((HERE.parents[1] / '20261008_dewpoint_openet/artifacts/manifest.json').read_text())['sites']
    # WGS84 to NAD83: record the installed PROJ operation and calculated coordinates.
    transformer = Transformer.from_crs(4326, 4269, always_xy=True)
    records = []
    with zipfile.ZipFile(archive) as z:
        filename = next(n for n in z.namelist() if n.endswith('.tif'))
        for name in z.namelist():
            if name.endswith(('.info.txt', '.xml', '.prj')) and not name.endswith('.aux.xml'):
                (HERE / name).write_bytes(z.read(name))
    with rasterio.open(f'/vsizip/{archive}/{filename}') as ds:
        for site, point in zip(sites, request['locations']):
            assert site['site'] == point['site']
            x, y = transformer.transform(site['lon'], site['lat'])
            row, col = ds.index(x,y)
            assert (row,col) == (point['row'],point['col'])
            center = ds.xy(row,col)
            assert abs(center[0] - point['lon']) < 1e-6 and abs(center[1]-point['lat']) < 1e-6
            raster_value = float(next(ds.sample([center]))[0])
            bulk = data[(data.Name == site['site']) & (data.Date == 'January')].iloc[0]
            assert abs(raster_value - bulk['ppt (mm)']) <= .0051
            assert abs(bulk.Longitude-point['lon']) < .000051 and abs(bulk.Latitude-point['lat']) < .000051
            records.append(dict(site=site['site'],row=row,col=col,center=list(center),transformed_site=[x,y],january_raster_p_mm=raster_value,january_bulk_p_mm=bulk['ppt (mm)'],grid_elevation_m=int(bulk['Elevation (m)']),hill_elevation_m=site['elevation_m']))
    save('normal-validation.json', dict(verified_utc=datetime.now(timezone.utc).isoformat(),period='1991-2020',resolution='800m',sampling='nearest native cell; no interpolation or nearest-valid substitution',projection_operation=transformer.get_last_used_operation().description, projection_accuracy_m=transformer.get_last_used_operation().accuracy,grid_sha256=grid_record['sha256'],csv_sha256=hashlib.sha256((HERE/'normals.csv').read_bytes()).hexdigest(),sites=records,limitation='Single-month ppt grid parity verifies geometry and point extraction; not all-variable grid parity or immutable bulk revision identity.'))
    print('All nine nearest cells and January grid samples verified.')


if __name__ == '__main__':
    main()
