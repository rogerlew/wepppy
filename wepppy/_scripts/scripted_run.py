import os
import shutil
from os.path import exists as _exists
from pprint import pprint
from time import time
from time import sleep

import wepppy
from wepppy.nodb import *

if __name__ == '__main__':

    projects = [dict(wd='blackwood_lt.cfg_Obs.MultPRISM',
                     extent=[-120.339849,39.011816,-120.065191,39.171695],
                     map_center=[-120.2042, 39.0909],
                     map_zoom=12,
                     outlet=[-120.1686, 39.1092],
                     landuse=None)
                ]

    for proj in projects:
        wd = proj['wd']
        extent = proj['extent']
        map_center = proj['map_center']
        map_zoom = proj['map_zoom']
        outlet = proj['outlet']
        default_landuse = proj['landuse']

        if _exists(wd):
            print()
            shutil.rmtree(wd)
        os.mkdir(wd)

        ron = Ron(wd, "lt.cfg")
#        ron = Ron(wd, "0.cfg")
        ron.name = wd
        ron.set_map(extent, map_center, zoom=map_zoom)
        ron.fetch_dem()

        topaz = Topaz.getInstance(wd)
        topaz.build_channels(csa=5, mcl=75)
        topaz.set_outlet(*outlet)
        sleep(0.5)
        topaz.build_subcatchments()

        wat = Watershed.getInstance(wd)
        wat.abstract_watershed()
        translator = wat.translator_factory()
        topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]
        print('topaz_ids:', topaz_ids)

        landuse = Landuse.getInstance(wd)
        landuse.mode = LanduseMode.Gridded
        landuse.build()
        landuse = Landuse.getInstance(wd)

        # 105 - Tahoe High severity fire
        # topaz_ids is a list of string ids e.g. ['22', '23']
        if default_landuse is not None:
            landuse.modify(topaz_ids, default_landuse)

        soils = Soils.getInstance(wd)
        soils.mode = SoilsMode.Gridded
        soils.build()

        climate = Climate.getInstance(wd)
        stations = climate.find_closest_stations()
        climate.input_years = 18
        climate.climatestation = stations[0]['id'] #45854
#        climate.climate_mode = ClimateMode.Single
#        climate.climate_mode = ClimateMode.SinglePRISM
#        climate.climate_mode = ClimateMode.Observed.SinglePRISM


        climate.climate_mode = ClimateMode.ObservedPRISM
        climate.set_original_climate_fn(climate_fn='/home/weppdev/PycharmProjects/wepppy/wepppy/nodb/mods/lt/data/tahoe/observed/Daily/WardCreek_daily.cli')

        climate.build(verbose=1)
        

        wepp = Wepp.getInstance(wd)
        wepp.prep_hillslopes()
        wepp.run_hillslopes()

        wepp = Wepp.getInstance(wd)
        wepp.prep_watershed()
        wepp.run_watershed()

        loss_report = wepp.report_loss()
        print(loss_report.out_tbl)
