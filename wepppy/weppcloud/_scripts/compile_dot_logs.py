from glob import glob
import json

import os
from os.path import split as _split
from os.path import join as _join
from os.path import exists as _exists

from collections import Counter
from datetime import datetime

from wepppy.nodb import Ron

fns = glob('/geodata/weppcloud_runs/.*')
print(fns)

fp = open('/geodata/weppcloud_runs/access.csv', 'w')

fp.write('runid,config,has_sbs,hillslopes,ash_hillslopes,year,user,ip,date\n')

runs_counter = Counter()

for fn in fns:
    if fn.endswith('.swp'):
        continue

    wd = _join('/geodata/weppcloud_runs', _split(fn)[1][1:])
    if not _exists(_join(wd, 'ron.nodb')):
        print(wd)
        config = None
        has_sbs = None
    else:
        try:
            ron = Ron.getInstance(wd)
            config = ron.config_stem
            has_sbs = ron.has_sbs
        except:
            config = None
            has_sbs = None

    if _exists(_join(wd, 'wepp', 'runs')):
        slopes = len(_join(wd, 'wepp', 'runs', '*.slp'))
    else:
        slopes = 0

    if _exists(_join(wd, 'ash')):
        ash_slopes = len(_join(wd, 'ash', '*ash.csv'))
    else:
        ash_slopes = 0

    try:
        lines = open(fn).readlines()
    except:
        print(fn)
        continue

    first_access = datetime(3000, 1, 1)
    for line in lines:
        _date = line.split(',')[-1].strip()
        _date = datetime.strptime(_date, '%Y-%m-%d %H:%M:%S.%f')
        fp.write('{},"{}",{},{},{},{},{}'.format(fn[1:], config, has_sbs, slopes, ash_slopes, _date.year, line))
        if _date < first_access:
            first_access = _date

    if config is None:
        continue

    if '?' in config:
        config = config.split('?')

    if first_access > datetime(2024, 1, 1):
        if 'rhem' in config and 'eu' not in config:
            runs_counter['rhem_projects'] += 1
            runs_counter['rhem_hillruns'] += slopes
        elif 'eu' in config:
            runs_counter['eu_projects'] += 1
            runs_counter['eu_hillruns'] += slopes
            runs_counter['eu_ash_hillruns'] += ash_slopes
        elif 'au' in config:
            runs_counter['au_projects'] += 1
            runs_counter['au_hillruns'] += slopes
            runs_counter['au_ash_hillruns'] += ash_slopes
        elif 'reveg' in config:
            runs_counter['reveg_projects'] += 1
            runs_counter['reveg_hillruns'] += slopes
        else:
            runs_counter['disturbed_projects'] += 1
            runs_counter['disturbed_hillruns'] += slopes
            runs_counter['disturbed_ash_hillruns'] += ash_slopes

        runs_counter['projects'] +=1
        runs_counter['hillruns'] += slopes
        runs_counter['ash_hillruns'] += ash_slopes

fp.close()

with open('/geodata/weppcloud_runs/runs_counter.json', 'w') as fp:
    json.dump(runs_counter, fp)

os.chmod('/geodata/weppcloud_runs/runs_counter.json', 0o777)
