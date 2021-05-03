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

    outdir = '/home/chinmay/Bremerton'

    if _exists(outdir):
        res = input('Outdir exixsts, Delete outdir?')
        if not res.lower().startswith('y'):
            sys.exit()

        shutil.rmtree(outdir)

    os.mkdir(outdir)

    scenarios = [
                 'Bremerton*Low_fire',
                 'Bremerton*low_Fire_2010_2040',
                 'Bremerton*low_Fire_2040_2070',
                 'Bremerton*low_Fire_2070_2099',
                 'Bremerton*Moderate_Fire',
                 'Bremerton*Moderate_Fire_2010_2040',
                 'Bremerton*Moderate_Fire_2040_2070',
                 'Bremerton*Moderate_Fire_2070_2099',
                 'Bremerton*Mulching',
                 'Bremerton*Mulching_2010_2040',
                 'Bremerton*Mulching_2040_2070',
                 'Bremerton*Mulching_2070_2099',
                 'Bremerton*NoFire',
                 'Bremerton*NoFire_2010_2040',
                 'Bremerton*NoFire_2040_2070',
                 'Bremerton*NoFire_2070_2099',
                 'Bremerton*Prescribed_Fire',
                 'Bremerton*Prescribed_fire_2010_2040',
                 'Bremerton*Prescribed_fire_2040_2070',
                 'Bremerton*Prescribed_Fire_2070_2099',
                 'Bremerton*Severe_fire',
                 'Bremerton*severe_Fire_2010_2040',
                 'Bremerton*Severe_fire_2040_2070',
                 'Bremerton*Severe_Fire_2070_2099',
                 'Bremerton*Thinning90',
                 'Bremerton*Thinning90_2010_2040',
                 'Bremerton*Thinning90_2040_2070',
                 'Bremerton*Thinning90_2070_2099'
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
