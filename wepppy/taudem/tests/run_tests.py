import os
from os.path import join as _join
from os.path import exists as _exists
import shutil
from time import time
from wepppy.taudem import TauDEMTopazEmulator

if __name__ == "__main__":
    t0 = time()

    for test_dir in ['blackwood', 'logan', 'taylor_creek']:
        wd = _join(test_dir, 'test')

        if _exists(wd):
            shutil.rmtree(wd)

        os.mkdir(wd)

        dem = _join(test_dir, 'dem.tif')
        with open(_join(test_dir, 'outlet.txt')) as fp:
            lng, lat = fp.readline().split(',')

        lng = float(lng)
        lat = float(lat)

        taudem = TauDEMTopazEmulator(wd=wd, dem=dem)

        taudem.run_pitremove()
        taudem.run_d8flowdir()
        taudem.run_aread8()
        taudem.run_gridnet()
        taudem.run_src_threshold()
        taudem.run_moveoutletstostrm(long=lng, lat=lat)

        taudem.run_peukerdouglas()
        taudem.run_peukerdouglas_stream_delineation()  #threshold=10)
        taudem.run_streamnet()
        taudem.run_dinfflowdir()
        taudem.run_areadinf()
        taudem.run_dinfdistdown()

        taudem.delineate_subcatchments()
        taudem.abstract_channels()
        taudem.abstract_subcatchments()
        taudem.abstract_structure()

    print()
    print(time() - t0)

# gage_watershed for each subcatchment: 194.7 s
# using support lib 178 s ???
