
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

wd = 'NewlanCreek'
extent = [-110.93814239837229, 46.64418501500508, -110.69781647063795, 46.80892368391386]
map_center = [-110.81797943450513, 46.72661723764761]
map_zoom = 12
outlet = [-110.85264865346161, 46.728935920690255]
cfg = '0'

# print('cleaning dir')
# if _exists(wd):
#     print()
#     shutil.rmtree(wd)
# os.mkdir(wd)

print('initializing project')
# ron = Ron(wd, "%s.cfg" % cfg)
# ron.name = wd
# ron.set_map(extent, map_center, zoom=map_zoom)

ron = Ron.getInstance(wd)

# print('fetching dem')
# ron.fetch_dem()

print('building channels')
topaz = Topaz.getInstance(wd)
# topaz.build_channels(csa=6.5, mcl=100)
# topaz.set_outlet(*outlet)
# sleep(0.5)

# print('building subcatchments')
# topaz.build_subcatchments()

print('abstracting watershed')
wat = Watershed.getInstance(wd)
# wat.abstract_watershed()
translator = wat.translator_factory()
topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]

print('building landuse')
landuse = Landuse.getInstance(wd)
# landuse.mode = LanduseMode.Gridded
# landuse.build()
# landuse = Landuse.getInstance(wd)

print('building soils')
soils = Soils.getInstance(wd)
# soils.mode = SoilsMode.Gridded
# soils.build()

print('building climate')
climate = Climate.getInstance(wd)
stations = climate.find_heuristic_stations(10)
climate.climatestation = stations[0]['id']

climate.climate_mode = ClimateMode.PRISM
climate.climate_spatialmode = ClimateSpatialMode.Single
climate.input_years = 30
climate.build(verbose=1)

print('prepping wepp')
wepp = Wepp.getInstance(wd)
# wepp.prep_hillslopes()
#
# print('running hillslopes')
# wepp.run_hillslopes()

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