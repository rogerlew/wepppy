import csv
import os
from os.path import join as _join
from os.path import split as _split
from glob import glob

from .managements import get_plant_loop_names


def pmetpara_prep(runs_dir, mid_season_crop_coeff, p_coeff):
    plant_loops = get_plant_loop_names(runs_dir)

    n = len(plant_loops)

    if not isinstance(mid_season_crop_coeff, dict):
        _mid_season_crop_coeff = mid_season_crop_coeff

    if not isinstance(p_coeff, dict):
        _p_coeff = p_coeff

    with open(_join(runs_dir, 'pmetpara.txt'), 'w') as fp:
        fp.write('{n}\n'.format(n=n))

        for i, plant in enumerate(plant_loops):
            if isinstance(mid_season_crop_coeff, dict):
                _mid_season_crop_coeff = mid_season_crop_coeff[plant]

            if isinstance(p_coeff, dict):
                _p_coeff = p_coeff[plant]

            fp.write('{plant},{mid_season_crop_coeff},{p_coeff},{i},{description}\n'.
                     format(plant=plant,
                            mid_season_crop_coeff=mid_season_crop_coeff,
                            p_coeff=p_coeff,
                            i=i,
                            description='-'))


if __name__ == "__main__":
    runs_dir = r'C:\Users\roger\Downloads\lt_obs_Blackwood_BC1_10336660_CurCond.2020.cl532.observed.ki5krcs.no_pmet.wepp_ui\wepp\runs'
    pmetpara_prep(runs_dir, mid_season_crop_coeff=0.7, p_coeff=0.95)
