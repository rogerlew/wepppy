from os.path import join as _join
from os.path import exists as _exists
from glob import glob
from datetime import datetime
import os
from wepppy.nodb import Ron

dirs = glob('/geodata/weppcloud_runs/*')

print(dirs)

fp = open('access.csv', 'w')

for wd in dirs:
    nodb = _join(wd, 'ron.nodb')

    if _exists(nodb):
        ron = Ron.getInstance(wd)

        cfg = ron._config
        hill_cnt = len(glob(_join(ron.output_dir, '*.pass.dat')))
        ts = os.path.getmtime(nodb)
        date = datetime.utcfromtimestamp(ts).strftime('%m/%d/%Y')
        print(wd, cfg, hill_cnt, date)

        fp.write('{},{},{},{}\n'.format(wd, cfg, hill_cnt, date))

fp.close()
