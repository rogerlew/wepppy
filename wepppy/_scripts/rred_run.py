import os
import sys

from copy import deepcopy

import shutil
from os.path import exists as _exists
from pprint import pprint
from time import time
from time import sleep

import wepppy
from wepppy.nodb import *
from os.path import join as _join
from wepppy.wepp.out import TotalWatSed
from wepppy.export import arc_export

from osgeo import gdal, osr
gdal.UseExceptions()
import sys


def run_rred_project(proj):
    wd = proj['wd']
    outlet = proj['outlet']
    soils_mode = proj['soils_mode']
    landuse_mode = proj['landuse_mode']

    print('cleaning dir')
    if _exists(wd):
        shutil.rmtree(wd)
    os.mkdir(wd)

    print('initializing project')
    ron = Ron(wd, "rred.cfg")
    ron.name = wd

    rred = Rred.getInstance(wd)
    rred.import_project(proj['rred_key'])

    ron = Ron.getInstance(wd)
    ron.set_map(rred.wgs_extent, rred.wgs_center, 11)

    print('building channels')
    topaz = Topaz.getInstance(wd)
    topaz.build_channels(csa=5, mcl=60)
    topaz.set_outlet(*outlet)
    sleep(0.5)

    print('building subcatchments')
    topaz.build_subcatchments()

    print('abstracting watershed')
    wat = Watershed.getInstance(wd)
    wat.abstract_watershed()
    translator = wat.translator_factory()
    topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]

    print('building landuse')
    landuse = Landuse.getInstance(wd)
    landuse.mode = landuse_mode
    landuse.build()
    landuse = Landuse.getInstance(wd)

    print('building soils')
    soils = Soils.getInstance(wd)
    soils.mode = soils_mode
    soils.build()

    print('building climate')
    climate = Climate.getInstance(wd)
    stations = climate.find_closest_stations()
    climate.input_years = 27
    climate.climatestation = stations[0]['id']
    climate.climate_mode = ClimateMode.Vanilla
    climate.climate_spatialmode = ClimateSpatialMode.Single
    climate.build(verbose=1)

    print('prepping wepp')
    wepp = Wepp.getInstance(wd)
    wepp.prep_hillslopes()

    print('running hillslopes')
    wepp.run_hillslopes()

    print('prepping watershed')
    wepp = Wepp.getInstance(wd)
    wepp.prep_watershed()

    print('running watershed')
    wepp.run_watershed()

    print('generating loss report')
    loss_report = wepp.report_loss()

    print('generating totalwatsed report')
    fn = _join(ron.export_dir, 'totalwatsed.csv')

    totwatsed = TotalWatSed(_join(ron.output_dir, 'totalwatsed.txt'),
                            wepp.baseflow_opts, wepp.phosphorus_opts)
    totwatsed.export(fn)
    assert _exists(fn)

    print('exporting arcmap resources')
    arc_export(wd)


if __name__ == '__main__':
    projects = [
        dict(wd='RRED_RattleSnake_Burned',
             rred_key='daa1a462de01ca9f022694103ce30a21',
             outlet=[-116.32628459650955, 45.22590653656753],
             landuse_mode=LanduseMode.RRED_Burned,
             soils_mode=SoilsMode.RRED_Burned),
        dict(wd='RRED_RattleSnake_Unburned',
             rred_key='daa1a462de01ca9f022694103ce30a21',
             outlet=[-116.32628459650955, 45.22590653656753],
             landuse_mode=LanduseMode.RRED_Unburned,
             soils_mode=SoilsMode.RRED_Unburned)
        ]

    for proj in projects:
        run_rred_project(proj)



