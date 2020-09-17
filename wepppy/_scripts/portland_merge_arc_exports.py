import shutil
import sys
import os
from os.path import join as _join
from os.path import exists as _exists

from glob import glob

import subprocess
#from wepppy.all_your_base import ogrmerge

os.chdir('/geodata/weppcloud_runs/')

if __name__ == "__main__":
    import sys

    outdir = '/workdir/wepppy/wepppy/weppcloud/static/mods/portland/results/' % prefix

    scenarios = [
                 'CurCond.202009.cl532.chn_cs',
                 'CurCond.202009.cl532_gridmet.chn_cs',
                 'CurCond.202009.cl532_future.chn_cs',
                 'SimFire_Eagle.202009.cl532.chn_cs',
                 'SimFire_Norse.202009.cl532.chn_cs',
                 'PrescFireS.202009.chn_cs',
                 'LowSevS.202009.chn_cs',
                 'ModSevS.202009.chn_cs',
                 'HighSevS.202009.chn_cs'
                ]

    for prefix in scenarios:
        wds = glob(_join('/geodata/weppcloud_runs', 'portland*{}*'.format(prefix)))
        wds = [wd for wd in wds if os.path.isdir(wd)]

        channels = []
        subcatchments = []

        for i, wd in enumerate(wds):
            if wd.endswith('.zip'):
                continue

            print(wd)

            chn = _join(wd, 'export', 'arcmap', 'channels.shp')
            assert _exists(chn), chn
            channels.append(chn)

            sub = _join(wd, 'export', 'arcmap', 'subcatchments.shp')
            assert _exists(sub), sub
            subcatchments.append(sub)

        print(channels)
        print(sub)

        argv = ['python3', 'ogrmerge.py', '-o', '%s/%s_channels.shp' % (outdir, prefix.replace('*','')), '-single'] + channels
        print(argv)
        subprocess.call(argv)
        #ogrmerge.process(argv)

        argv = ['python3', 'ogrmerge.py', '-o', '%s/%s_subcatchments.shp' % (outdir, prefix.replace('*','')), '-single'] + subcatchments
        print(argv)
        subprocess.call(argv)

        #ogrmerge.process(argv)


        print('merged shps are in', outdir)
