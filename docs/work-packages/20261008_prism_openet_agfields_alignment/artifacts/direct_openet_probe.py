"""Separate scientific alignment probe; does not replace Climate Engine in production."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import requests

OUT = Path(__file__).resolve().parent
GEO = Path('/wc1/prism-downstream-alignment-20261008/sample-hillslopes.geojson')
key = (Path.home()/'openet.key').read_text().strip()
assert key
features = json.loads(GEO.read_text())['features']

def acquire(job):
    feature, model = job
    topaz = str(feature['properties']['TopazID'])
    target = OUT/f'direct-openet-{topaz}-{model}.json'
    payload = dict(date_range=['2019-01-01','2021-12-31'], interval='monthly',
                   geojson=dict(type='FeatureCollection',features=[feature]),
                   model=model, variable='ET', reference_et='gridMET', reducer='mean',
                   units='mm', file_format='JSON', version=2.1)
    if target.exists():
        prior = json.loads(target.read_text())
        assert prior['request'] == payload and prior['status'] == 200
        return
    try:
        response = requests.post('https://openet-api.org/raster/timeseries/polygon',
                                 headers={'Authorization':key}, json=payload,
                                 timeout=180, allow_redirects=False)
    except requests.RequestException as exc:
        raise RuntimeError(f'Direct OpenET transport failure: {type(exc).__name__}') from None
    target.write_text(json.dumps(dict(request=payload, status=response.status_code,
                          retrieved_utc=datetime.now(timezone.utc).isoformat(),
                          body=response.text.replace(key,'[REDACTED]')),indent=2)+'\n')
    print({'topaz_id':topaz,'model':model,'status':response.status_code},flush=True)
    assert response.status_code == 200

with ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(acquire, [(f,m) for f in features for m in ['Ensemble','eeMETRIC']]))
