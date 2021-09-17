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

    outdir = '/home/mariana/lt2021_1'

    if _exists(outdir):
        res = input('Outdir exixsts, Delete outdir?')
        if not res.lower().startswith('y'):
            sys.exit()

        shutil.rmtree(outdir)

    os.mkdir(outdir)

    scenarios = [
                 'lt_202012*SimFire.fccsFuels_obs_cli',
                 'lt_202012*SimFire.landisFuels_obs_cli',
                 'lt_202012*SimFire.landisFuels_fut_cli_A2',
                 'lt_202012*CurCond',
                 'lt_202012*PrescFire',
                 'lt_202012*LowSev',
                 'lt_202012*ModSev',
                 'lt_202012*HighSev',
                 'lt_202012*Thinn96',
                 'lt_202012*Thinn93',
                 'lt_202012*Thinn85'
                ]

    for prefix in scenarios:
        wds = glob(_join('/geodata/weppcloud_runs', '*{}*'.format(prefix)))
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
