import os
from os.path import join as _join
from os.path import exists as _exists

from wepppy.nodb.core import Watershed
from wepppy.wepp.out import TotalWatSed2

def totalwatsed_partitioned_dss_export(wd):
    watershed = Watershed.getInstance(wd)
    translator = watershed.translator_factory()
    dss_file = _join(wd, 'wepp', 'output', 'totwatsed2.dss')

    if _exists(dss_file):
        os.remove(dss_file)

    for chn_id in translator.iter_chn_ids():
        totwatsed = TotalWatSed2(wd, chn_id=chn_id)
        totwatsed.to_dss(dss_file)



if __name__ == '__main__':
    wd = '/geodata/weppcloud_runs/srivas42-macroeconomic-javelin/'
    totalwatsed_partitioned_dss_export(wd)

