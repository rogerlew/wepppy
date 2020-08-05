import shutil
import sys
import os
from os.path import join as _join
from os.path import exists as _exists

from glob import glob

from wepppy.all_your_base import ogrmerge

os.chdir('/geodata/weppcloud_runs/')

if __name__ == "__main__":
    import sys

    outdir = '/home/roger/lt2020_7'

    if _exists(outdir):
        res = input('Outdir exixsts, Delete outdir?')
        if not res.lower().startswith('y'):
            sys.exit()

        shutil.rmtree(outdir)

    os.mkdir(outdir)

    scenarios = [
                 'SimFire.202007.kikrcs.chn_cs*_fccsFuels_obs_cli',
                 'SimFire.202007.kikrcs.chn_cs*_landisFuels_obs_cli',
                 'SimFire.202007.kikrcs.chn_cs*_landisFuels_fut_cli_A2',
                 'CurCond.202007.cl532.ki5krcs.chn_cs**',
                 'PrescFireS.202007.kikrcs.chn_cs*',
                 'LowSevS.202007.kikrcs.chn_cs*',
                 'ModSevS.202007.kikrcs.chn_cs*',
                 'HighSevS.202007.kikrcs.chn_cs*',
                 'Thinn96.202007.kikrcs.chn_cs*',
                 'Thinn93.202007.kikrcs.chn_cs*',
                 'Thinn85.202007.kikrcs.chn_cs*'
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

        argv = ['-o', '%s/%s_channels.shp' % (outdir, prefix.replace('*','')), '-single'] + channels
        print(argv)
        ogrmerge.process(argv)

        argv = ['-o', '%s/%s_subcatchments.shp' % (outdir, prefix.replace('*','')), '-single'] + subcatchments
        print(argv)
        ogrmerge.process(argv)


        print('merged shps are in', outdir)
