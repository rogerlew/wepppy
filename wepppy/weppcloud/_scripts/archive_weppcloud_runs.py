from glob import glob
import os
from datetime import datetime, timedelta
from os.path import join as _join
from os.path import split as _split
from os.path import exists
import shutil
import subprocess

from wepppy.nodb import Ron

import requests

def archive_run(runid, archive_dir, wd):
    print('Archiving', runid)
    
    # Get the first two characters for the subdirectory (handle short runids)
    prefix = runid[:2] if len(runid) >= 2 else runid.ljust(2, '_')
    
    # Create the subdirectory path (e.g., archive_dir/th)
    subdir = os.path.join(archive_dir, prefix)
    os.makedirs(subdir, exist_ok=True)  # Create if it doesn’t exist
    
    # Full path for the .tar.gz file (e.g., archive_dir/th/thunderHub.tar.gz)
    arc_fn = os.path.join(subdir, runid + '.tar.gz')

    if os.path.exists(arc_fn):
        os.remove(arc_fn)

    # Use tar -czf directly
#    subprocess.run(['tar', '-czf', arc_fn, '-C', wd, '.'], check=True)
    subprocess.run(f'tar -cf - -C "{wd}" . | pigz -p 8 > "{arc_fn}"', shell=True, check=True)

    if os.path.exists(arc_fn):
        print('Archived', runid, 'to', arc_fn)
        # Remove the original directory

        try:
            shutil.rmtree(wd)
        except PermissionError:
            print('PermissionError: Failed to remove', wd)

    else:
        print('Failed to archive', runid)
    


def has_owners(runid):
    url = 'https://wepp.cloud/weppcloud/runs/{runid}/cfg/hasowners/'.format(runid=runid)
    r = requests.post(url)
    w1 = r.text.startswith('true')

    url = 'https://dev.wepp.cloud/weppcloud/runs/{runid}/cfg/hasowners/'.format(runid=runid)
    r = requests.post(url)
    w2 = r.text.startswith('true')

    return w1 or w2 


fns = glob(r'/geodata/weppcloud_runs/*')

archive_dir = '/geodata/archive'

for fn in fns:
    if not os.path.exists(fn):
        continue

    if not os.path.isdir(fn):
        continue

    if '__pycache__' in fn:
        continue

    if 'mdobre' in fn:
        continue

    if 'srivas' in fn:
        continue 

    if 'lt' in fn:
        continue

    if 'BullRun' in fn:
        continue

    if 'NorthFork' in fn:
        continue

    if 'LittleSandy' in fn:
        continue

    if 'FirCreek' in fn:
        continue

    if 'CedarCreek' in fn:
        continue

    if 'BRnearMultnoma' in fn:
       continue

    if 'BlazedAlder' in fn:
       continue

    if 'CedarRiver' in fn:
       continue

    if 'Tolt_NorthFork' in fn:
       continue

    if 'Taylor_Creek' in fn:
       continue

    if 'seattle' in fn:
       continue

    if 'portland' in fn:
       continue

    if '202012' in fn:
       continue

    if '202010' in fn:
       continue

    if '202009' in fn:
       continue

    if 'mdobre' in fn:
       continue

    if exists(_join(fn, 'READONLY')):
        continue

    if exists(_join(fn, 'PERPETUAL')):
        continue

    if exists(_join(fn, 'rhem')):
        continue

    ts =  os.stat(fn).st_mtime
    dt = datetime.now() - datetime.utcfromtimestamp(ts)
    if dt < timedelta(days=180):
        continue

    if not os.path.isdir(fn):
        continue

    runid = _split(fn)[-1]
    wd = fn

    _hasowners = has_owners(runid)
    if _hasowners:
        continue

    if not os.path.exists(fn):
        continue

    archive_run(runid, archive_dir, wd)