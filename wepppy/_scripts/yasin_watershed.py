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
from wepppy.climates.cligen import StationMeta, Cligen

from osgeo import gdal, osr
gdal.UseExceptions()

# change the working directory to where the run will be stored
os.chdir('/geodata/weppcloud_runs/')


def log_print(*msg):
    now = datetime.now()
    print('[{now}] {wd}: {msg}'.format(now=now, wd=wd, msg=', '.join(str(v) for v in msg)))


if __name__ == "__main__":

    wd = 'yasin'
    outlet = (40.5866759978392, 38.7510854093549)

    log_print('Cleaning wd')
    if _exists(wd):
        shutil.rmtree(wd)
    os.mkdir(wd)

    log_print('Initializing Project')

    # When the project is initialized the dem specified in the config is copied to the yasin/dem
    # the landuse specified in the config is copied to yasin/landuse
    # and the soil map in the config is copied to yasin/soils
    ron = Ron(wd, 'yasin.cfg')  # this file is in wepppy/nodb/configs/

    # Setting these map parameters isn't strictly necessary for running WEPP but is needed for viewing the project on
    # the web interface
    ron.set_map(extent=(40.51792144775391, 38.65897345576361, 40.75824737548829, 38.84639268206848),
                center=(40.6381, 38.7527), zoom=12)

    # double check that the dem was copied
    assert _exists(ron.dem_fn)  # the locations of these resources are specified as properties in the nodb base class

    log_print('building channels')
    # TOPAZ is a fortran program compiled for linux. The Topaz NoDb instance runs the fortran program to build the maps
    # and other outputs in the dem/topaz directory. NETFUL.ARC is the channel map. The subcatchments are in the
    # SUBWTA.ARC map
    topaz = Topaz.getInstance(wd)
    topaz.build_channels(csa=10, mcl=100)

    log_print('setting outlet')
    topaz.set_outlet(*outlet)  # sets the outlet specified on line 35 (lng, lat)

    log_print('building subcatchments')
    topaz.build_subcatchments()

    log_print('abstracting watershed')
    # The watershed abstraction takes the rasters produced by TOPAZ and generates representative hillslopes (a
    # rectangular slope with a width and length) by walking down the flowpaths in each subcatchment.
    # The topaz_ids are produced by TOPAZ and are numbered such that the channels always end in 4 and the hillslopes
    # end in 1, 2, 3. WEPP uses its own numbering scheme
    watershed = Watershed.getInstance(wd)
    watershed.abstract_watershed()
    translator = watershed.translator_factory()
    topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]
    
    log_print('building landuse')
    turkey = TurkeyMod.getInstance(wd)
    # the landuses are mapped according the the wepppy/wepp/data/turkey_map.json
    turkey.build_landuse()

    log_print('building soils')
    turkey = TurkeyMod.getInstance(wd)
    # the soils are mapped according the _soils_map defined on line 47 of wepppy/nodb/mods/locations/turkey.nodb
    turkey.build_soils()
    
    log_print('building climate')
    turkey.build_climate(user_par='bingol2020.par', years=100)

    log_print('running wepp')
    wepp = Wepp.getInstance(wd)

    log_print('prepping hillslooes')
    # this copies the slope, managements, soils, and climates to the yasin/wepp/runs/ folder and build the .run files
    wepp.prep_hillslopes()

    log_print('running hillslopes')
    # this runs the hillslopes in parallel
    wepp.run_hillslopes()

    log_print('prepping watershed')
    # this generates the pw0.* input files for running wepp
    wepp.prep_watershed()

    log_print('running watershed')
    wepp.run_watershed()
    loss_report = wepp.report_loss()

    log_print('running wepppost')
    fn = _join(ron.export_dir, 'totalwatsed.csv')

    totwatsed = TotalWatSed(_join(ron.output_dir, 'totalwatsed.txt'),
                            wepp.baseflow_opts, wepp.phosphorus_opts)

    # this generates the totalwatsed.csv
    totwatsed.export(fn)
    assert _exists(fn)

    arc_export(wd)