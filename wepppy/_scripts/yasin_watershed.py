import os
import sys

from copy import deepcopy

import shutil
from os.path import exists as _exists
from pprint import pprint
from datetime import datetime
from time import time
from time import sleep

import wepppy
from wepppy.nodb import *
from wepppy.nodb.mods.locations import TurkeyMod
from os.path import join as _join
from wepppy.wepp.out import TotalWatSed
from wepppy.export import arc_export

from osgeo import gdal, osr
gdal.UseExceptions()

os.chdir('/geodata/weppcloud_runs/')


def log_print(*msg):
    now = datetime.now()
    print('[{now}] {wd}: {msg}'.format(now=now, wd=wd, msg=', '.join(str(v) for v in msg)))


if __name__ == "__main__":

    wd = 'yasin'
    outlet = (40.5935646536361, 38.7291580351105)

    log_print('Cleaning wd')
    if _exists(wd):
        shutil.rmtree(wd)
    os.mkdir(wd)

    log_print('Initializing Project')
    ron = Ron(wd, 'yasin.cfg')

    assert _exists(wd)

    assert _exists(ron.dem_fn)

    log_print('building channels')
    topaz = Topaz.getInstance(wd)
    topaz.build_channels()

    """
    log_print('setting outlet')
    topaz.set_outlet(*outlet)

    log_print('building subcatchments')
    topaz.build_subcatchments()

    log_print('abstracting watershed')
    watershed = Watershed.getInstance(wd)
    watershed.abstract_watershed()
    translator = watershed.translator_factory()
    topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]
    
    log_print('building landuse')
    turkey = TurkeyMod.getInstance(wd)
    turkey.build_landuse()

    log_print('building soils')
    turkey = TurkeyMod.getInstance(wd)
    turkey.build_soils()
    
    log_print('building climate')
    climate = Climate.getInstance(wd)
    climate.climatestation_mode = ClimateStationMode.EUHeuristic
    climate.climate_spatialmode = ClimateSpatialMode.Single
    stations = climate.find_eu_heuristic_stations()
    climate.climatestation = stations[1]['id']

    climate.climate_mode = ClimateMode.Vanilla
    climate.input_years = 100
    climate.build()

    log_print('running wepp')
    wepp = Wepp.getInstance(wd)
    wepp.prep_hillslopes()
    log_print('running hillslopes')
    wepp.run_hillslopes()

    wepp = Wepp.getInstance(wd)
    wepp.prep_watershed()
    wepp.run_watershed()
    loss_report = wepp.report_loss()

    log_print('running wepppost')
    fn = _join(ron.export_dir, 'totalwatsed.csv')

    totwatsed = TotalWatSed(_join(ron.output_dir, 'totalwatsed.txt'),
                            wepp.baseflow_opts, wepp.phosphorus_opts)
    totwatsed.export(fn)
    assert _exists(fn)

    arc_export(wd)
    """