import os
from glob import glob

from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

from wepppy.nodb import Ash

wds = glob(_join('/geodata/weppcloud_runs/au', '*'))
wds = [wd for wd in wds if os.path.isdir(wd)]


def rerun(wd):
    # delete any active locks
    locks = glob(_join(wd, '*.lock'))
    for fn in locks:
        os.remove(fn)

    ash = Ash.getInstance(wd)
    ash.run_ash(ini_white_ash_depth_mm=16.5625, ini_black_ash_depth_mm=17.166666666666668)


for wd in wds:
    print(wd)

    if not _exists(_join(wd, 'wepp/output/loss_pw0.txt')):
        continue


    head, tail = _split(wd)

    if tail.startswith('1'):
        continue

    rerun(wd)
