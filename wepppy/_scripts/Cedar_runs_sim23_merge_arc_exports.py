import shutil
import sys
import os
from os.path import join as _join
from os.path import exists as _exists

from glob import glob

import subprocess

from wepppy.export import arc_export

# from wepppy.all_your_base import ogrmerge
from wepppy.weppcloud.combined_watershed_viewer_generator import combined_watershed_viewer_generator

from Cedar_runs_sim23 import projects, scenarios

os.chdir('/geodata/weppcloud_runs/')

if __name__ == "__main__":
    prefix = 's1'

    outdir = '/home/roger/%s_arcs' % prefix

    if _exists(outdir):
        res = input('Outdir exists, Delete outdir?')
        if not res.lower().startswith('y'):
            sys.exit()

        shutil.rmtree(outdir)

    os.mkdir(outdir)

    # find unique conditions of scenario
    conditions = set()

    for proj in projects:
        if proj['scenario'] != prefix:
            continue

        conditions.add(proj['condition'])


    for condition in conditions:
        print(prefix, condition)
        channels = []
        subcatchments = []
        wds = []

        for proj in projects:
            if proj['scenario'] != prefix:
                continue

            if proj['condition'] != condition:
                continue

            wds.append(proj['wd'])

            wd = _join('/geodata/weppcloud_runs', proj['wd'])

            chn = _join(wd, 'export', 'arcmap', 'channels.shp')
            assert _exists(chn), chn
            channels.append(chn)

            sub = _join(wd, 'export', 'arcmap', 'subcatchments.shp')
            assert _exists(sub), sub
            subcatchments.append(sub)

        print(wds)
        #url = combined_watershed_viewer_generator(wds, f'{prefix} {condition}')
        #print(url)
        #continue

        argv = ['python3', 'ogrmerge.py', '-o', f'{outdir}/{prefix}_{condition}_channels.shp',
                '-single'] + channels
        print(argv)
        subprocess.call(argv)
        # ogrmerge.process(argv)

        argv = ['python3', 'ogrmerge.py', '-o', f'{outdir}/{prefix}_{condition}_subcatchments.shp',
                '-single'] + subcatchments
        print(argv)
        subprocess.call(argv)

        # ogrmerge.process(argv)

        print('merged shps are in', outdir)
