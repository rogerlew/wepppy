import os
import shutil
from os.path import exists as _exists
from pprint import pprint
from time import time
from time import sleep

import wepppy
from wepppy.nodb import *

if __name__ == '__main__':

    projects = [dict(wd='blackwood_lt.cfg_Obs.MultDaymet',
                     landuse=None)
                ]

    for proj in projects:
        wd = proj['wd']

        ron = Ron.getInstance(wd)
        topaz = Topaz.getInstance(wd)
        wat = Watershed.getInstance(wd)
        translator = wat.translator_factory()
        landuse = Landuse.getInstance(wd)
        soils = Soils.getInstance(wd)
        climate = Climate.getInstance(wd)

        for (topaz_id, ss) in wat._subs_summary.items():
            lng, lat = ss.centroid.lnglat
            print(topaz_id, lng, lat)

"""
        wepp = Wepp.getInstance(wd)
        wepp.prep_hillslopes()
        wepp.run_hillslopes()

        wepp = Wepp.getInstance(wd)
        wepp.prep_watershed()
        wepp.run_watershed()

        loss_report = wepp.report_loss()
        print(loss_report.out_tbl)
"""