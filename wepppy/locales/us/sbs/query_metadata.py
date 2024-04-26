import requests
import os
import json
import wget
from os.path import split as _split
from os.path import exists as _exists
from os.path import join as _join

for yr in range(2012, 2023):
    print(yr)
    url1 = f'https://burnseverity.cr.usgs.gov/baer/api/form/baer-downloads?year={yr}'
    _json = requests.get(url1).text
    data = json.loads(_json)

    for item in data['data']['items']:
        for item2 in item['items']:
            fire_name, fire_id = item2.get('fire_name'), item2.get('fire_id')
            fire_id = fire_id.lower()
            print(fire_name, fire_id)

            if not _exists(fire_id):
                os.makedirs(fire_id)

            with open(_join(fire_id, 'meta.json'), 'w') as fp:
                json.dump(item2, fp)
