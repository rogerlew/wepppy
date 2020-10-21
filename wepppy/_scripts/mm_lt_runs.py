
import os
import shutil
#print("import tiffle")
#import tifffile
#import imageio

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

if __name__ == '__main__':
    projects = [

        dict(wd='mm_Watershed_2',
             extent=[-120.25497436523439, 39.072244930479926, -120.0146484375, 39.25857565711887],
             map_center=[-120.1348114013672, 39.165471994238374],
             map_zoom=12,
             outlet=[-120.11460381632118, 39.18896973503106],
             landuse=None,
             cs=12, erod=0.000001),
                ]

    failed = open('failed', 'w')
    for proj in projects:
        try:
            wd = proj['wd']
            extent = proj['extent']
            map_center = proj['map_center']
            map_zoom = proj['map_zoom']
            outlet = proj['outlet']
            default_landuse = proj['landuse']

            print('cleaning dir')
            if _exists(wd):
                print()
                shutil.rmtree(wd)
            os.mkdir(wd)

            print('initializing project')
            #ron = Ron(wd, "lt-fire.cfg")
            ron = Ron(wd, "lt.cfg")
            #ron = Ron(wd, "0.cfg")
            ron.name = wd
            ron.set_map(extent, map_center, zoom=map_zoom)

            print('fetching dem')
            ron.fetch_dem()

            print('building channels')
            topaz = Topaz.getInstance(wd)
            topaz.build_channels(csa=5, mcl=100)
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
            landuse.mode = LanduseMode.Gridded
            landuse.build()
            landuse = Landuse.getInstance(wd)

            # 105 - Tahoe High severity fire
            # topaz_ids is a list of string ids e.g. ['22', '23']
            if default_landuse is not None:
                print('setting default landuse')
                landuse.modify(topaz_ids, default_landuse)

            print('building soils')
            soils = Soils.getInstance(wd)
            print('I got an instance of soils')
            soils.mode = SoilsMode.Gridded
            print('I did a dot mode')
            soils.build()
            print('I built a soil')

            print('building climate')
            climate = Climate.getInstance(wd)
            print('climate instance')
            stations = climate.find_closest_stations()
            print('nearest station')
            climate.input_years = 27
            climate.climatestation = stations[0]['id']
            print('nearest station id')
            climate.climate_mode = ClimateMode.Observed
            climate.climate_spatialmode = ClimateSpatialMode.Multiple
            climate.set_observed_pars(start_year=1990, end_year=2016)
            print('build climate')
            climate.build(verbose=1)

            print('prepping wepp')
            wepp = Wepp.getInstance(wd)
            wepp.prep_hillslopes()

            print('running hillslopes')
            wepp.run_hillslopes()

            print('prepping watershed')
            wepp = Wepp.getInstance(wd)
            wepp.prep_watershed(erodibility=proj['erod'], critical_shear=proj['cs'])

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
        except:
            failed.write('%s\n' % wd)

