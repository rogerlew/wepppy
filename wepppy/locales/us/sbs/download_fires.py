import requests
import os
import json
import wget
from os.path import split as _split
from os.path import exists as _exists
from os.path import join as _join


fp = open('/geodata/revegetation/sbs_download_log.csv', 'w')

for yr in range(2022, 2023):
    print(yr)
    url1 = f'https://burnseverity.cr.usgs.gov/baer/api/form/baer-downloads?year={yr}'
    _json = requests.get(url1).text
    data = json.loads(_json)

    for item in data['data']['items']:
        for item2 in item['items']:
            fire_name, fire_id = item2.get('fire_name'), item2.get('fire_id')
            if fire_id is None:
                print('Error', item2)
                continue
            fire_id = fire_id.lower()
            print(fire_name, fire_id)

            if not _exists(fire_id):
                os.makedirs(fire_id)

            with open(_join(fire_id, 'meta.json'), 'w') as fp2:
                json.dump(item2, fp2)

            has_sbs = False
            sbs_url = item2.get('soil_burn_file_url')
            if sbs_url.startswith('http'):
                try:
                    wget.download(sbs_url, out=fire_id)
                    has_sbs = True
                except:
                    pass


            fp.write(f'{fire_id},{fire_name},{has_sbs},{yr}\n')
fp.close()

