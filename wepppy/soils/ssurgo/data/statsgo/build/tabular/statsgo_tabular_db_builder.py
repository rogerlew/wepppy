import os
import sys
from time import time
import shutil
from os.path import join as _join
from os.path import exists as _exists

from wepppy.ssurgo import (
    StatsgoSpatial,
    SurgoSoilCollection,
)

if __name__ == '__main__':

    _thisdir = os.path.dirname(__file__)
    _statsgo_data_dir = '../../'
    _db = '../../statsgo_tabular.db'

    _soils_dir = _join(_statsgo_data_dir, 'soils')
    _valid_dir = _join(_soils_dir, 'valid')
    _invalid_dir = _join(_soils_dir, 'invalid')
    if _exists(_soils_dir):
        shutil.rmtree(_soils_dir)

    os.mkdir(_soils_dir)
    os.mkdir(_valid_dir)
    os.mkdir(_invalid_dir)

    if _exists(_db):
        os.remove(_db)

    mukeys = StatsgoSpatial().mukeys
    m = len(mukeys)
    n = 334
    for i in range(int(m/n)+1):
        t0 = time()

        i0 = i * n
        iend = i * n + n
        if iend > m:
            iend = m

        sys.stdout.write('mukeys[{}:{}]... '.format(i0, iend))

        _mukeys = mukeys[i0:iend]
        surgo_c = SurgoSoilCollection(_mukeys, use_statsgo=True)
        surgo_c.makeWeppSoils()
        surgo_c.writeWeppSoils(wd=_valid_dir, write_logs=True, db_build=True)
        surgo_c.logInvalidSoils(wd=_invalid_dir, db_build=True)
        valid = surgo_c.getValidWeppSoils()

        # noinspection PyProtectedMember
        sys.stdout.write('done, time: {}, sync_n: {}, invalid: {}\n'
                         .format(time() - t0, surgo_c._sync_n,
                                 set(_mukeys).difference(valid)))
