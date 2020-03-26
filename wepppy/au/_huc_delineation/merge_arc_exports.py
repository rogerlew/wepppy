import shutil
import sys
import os
from os.path import join as _join
from os.path import exists as _exists

from glob import glob

from ogrmerge import process

if __name__ == "__main__":

    prefix = 'au_2020_gwc2'
    outdir = '/geodata/au/%s_shps' % prefix

    if _exists(outdir):
        res = input('Outdir exists, Delete outdir?')
        if not res.lower().startswith('y'):
            sys.exit()

        shutil.rmtree(outdir)

    os.mkdir(outdir)

    wds = glob(_join('/geodata/weppcloud_runs/au', '*'))
    wds = [wd for wd in wds if os.path.isdir(wd)]

    _wds = []
    for i, wd in enumerate(wds):
        if not os.path.isdir(wd):
            continue


        if not _exists(_join(wd, 'wepp/output/loss_pw0.txt')):
            continue

        from wepppy.export import archive_project, arc_export

        try:
        #   arc_export(wd)
           _wds.append(wd)
           print(wd)
        except:
            pass


    channels = []
    subcatchments = []

    for i, wd in enumerate(_wds):
        if wd.endswith('.zip'):
            continue

        print(wd)

        chn = _join(wd, 'export', 'arcmap', 'channels.shp')
        assert _exists(chn), chn
        channels.append(chn)

        sub = _join(wd, 'export', 'arcmap', 'subcatchments.shp')
        assert _exists(sub), sub
        subcatchments.append(sub)

    # print(channels)
    # print(subcatchments)

    argv = ['-o', '%s/%s_channels.shp' % (outdir, prefix), '-single'] + channels
    print(argv)
    process(argv)

    argv = ['-o', '%s/%s_subcatchments.shp' % (outdir, prefix), '-single'] + subcatchments
    print(argv)
    process(argv)

    print('merged shps are in', outdir)
