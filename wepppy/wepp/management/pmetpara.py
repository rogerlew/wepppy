import csv
import os
from os.path import join as _join
from os.path import split as _split
from glob import glob

from .managements import get_plant_loop_names


def pmetpara_prep(runs_dir, kcb, rawp):
    plant_loops = get_plant_loop_names(runs_dir)

    n = len(plant_loops)

    if not isinstance(kcb, dict):
        _kcb = kcb

    if not isinstance(rawp, dict):
        _rawp = rawp

    description = '-'
    with open(_join(runs_dir, 'pmetpara.txt'), 'w') as fp:
        fp.write('{n}\n'.format(n=n))

        for i, plant in enumerate(plant_loops):
            if isinstance(kcb, dict):
                _kcb = kcb[plant]

            if isinstance(rawp, dict):
                _rawp = rawp[plant]

            fp.write(f'{plant},{kcb},{rawp},{i+1},{description}\n')

        fp.flush()                 # flush Python’s userspace buffer
        os.fsync(fp.fileno())      # fsync forces kernel page-cache to disk

if __name__ == "__main__":
    runs_dir = r'C:\Users\roger\Downloads\lt_obs_Blackwood_BC1_10336660_CurCond.2020.cl532.observed.ki5krcs.no_pmet.wepp_ui\wepp\runs'
    pmetpara_prep(runs_dir, kcb=0.95, rawp=0.8)
