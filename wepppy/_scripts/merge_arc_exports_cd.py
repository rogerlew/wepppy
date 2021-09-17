import shutil
import sys
import os
from os.path import join as _join
from os.path import exists as _exists

from glob import glob

import subprocess

from wepppy.export import arc_export

#from wepppy.all_your_base import ogrmerge

os.chdir('/geodata/weppcloud_runs/')

if __name__ == "__main__":
    import sys

    outdir = '/home/chinmay/Palouse202103'

    if _exists(outdir):
        res = input('Outdir exixsts, Delete outdir?')
        if not res.lower().startswith('y'):
            sys.exit()

        shutil.rmtree(outdir)

    os.mkdir(outdir)

    scenarios = [
                 'Palouse202103*Mulch_Till',
                 'Palouse202103*No_Till',
                 'Palouse202103*Conventional_Till'
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
            
            arc_export(wd)

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
