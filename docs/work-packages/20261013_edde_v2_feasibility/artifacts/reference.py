"""Retain public Daymet reference records without silently filling leap days."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import requests

from wepppy.climates.edde.client import sha256, write_json

HERE=Path(__file__).resolve().parent


def acquire(point):
    root=HERE/'reference'
    root.mkdir(exist_ok=True)
    path=root/f'{point["name"]}.csv'
    if path.exists(): return point['name']
    params={'lat':point['latitude'],'lon':point['longitude'],
            'year':','.join(str(y) for y in range(1995,2015))}
    with requests.Session() as session:
        session.trust_env=False
        response=session.get('https://daymet.ornl.gov/single-pixel/api/data',params=params,timeout=180,allow_redirects=False)
    if response.status_code!=200:raise ValueError(f'Daymet response status {response.status_code}')
    response.raise_for_status()
    if 'year,yday' not in response.text: raise ValueError('Unrecognized Daymet CSV header')
    path.write_text(response.text)
    write_json(path.with_suffix('.json'),dict(url=response.url,sha256=sha256(path),
               note='Daymet 365-day year convention retained; no leap-day synthesis; compare common calendar days'))
    print(point['name'],len(response.content),flush=True)
    return point['name']


if __name__=='__main__':
    points=[p for p in json.loads((HERE/'location-eligibility.json').read_text())
            if p['model']=='WRF-MPI' and p['eligible']]
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(acquire,points))
