import os
import shutil
from os.path import exists as _exists
from pprint import pprint
from time import time
from time import sleep
import time
import utm
import pandas as pd
import numpy as np

import wepppy
from wepppy.nodb import *
from os.path import join as _join
from wepppy.wepp.out import TotalWatSed

from osgeo import gdal, osr
gdal.UseExceptions()



filepath = 'geodata/small_basin_input_data/bigsur_subbasins_10m_may2_v8.csv'
df = pd.read_csv(filepath)






bigtic=time.perf_counter()

for i in range(len(df)):
    if __name__ == '__main__':
        projects = [
                    dict(wd='bigsur_subbasin' + str(i),
                        extent=[df.xmin[i], df.ymin[i], df.xmax[i], df.ymax[i]], 
                        map_center=[df.center_x[i], df.center_y[i]],
                        map_zoom=12,
                        outlet=[df.outlet_x[i], df.outlet_y[i]],
                        landuse=None,
                        cs=10, erod=0.000001, chn_chn_wepp_width=1.0),
                    ]

        for proj in projects:
            wd = proj['wd']
            extent = proj['extent']
            map_center = proj['map_center']
            map_zoom = proj['map_zoom']
            outlet = proj['outlet']
            default_landuse = proj['landuse']

            print('drainage area of current basin [km2] = ', df.DA_km2[i])
            # print('outlet = ', outlet)


            temp = utm.to_latlon(extent[0],extent[1],10,'S')
            extent[0] = temp[1]
            extent[1] = temp[0]
            temp = utm.to_latlon(extent[2],extent[3],10,'S')
            extent[2] = temp[1]
            extent[3] = temp[0]

            temp = utm.to_latlon(map_center[0],map_center[1],10,'S')
            map_center[0] = temp[1]
            map_center[1] = temp[0]

            temp = utm.to_latlon(outlet[0],outlet[1],10,'S')
            outlet[0] = temp[1]
            outlet[1] = temp[0]



            if _exists(wd):
                shutil.rmtree(wd)

            print('outlet=', outlet)

            os.chdir('geodata/wepppy_runs')
                
            print('making directory')
            os.mkdir(wd)

            tic=time.perf_counter()

            print('initializing project')
            config_filepath = 'ca_hindcast_2016.cfg'

            print('config filepath = ', config_filepath)
            ron = Ron(wd, config_filepath)
            ron.name = wd
            ron.set_map(extent, map_center, zoom=map_zoom)
            
            print('fetching dem')
            ron.fetch_dem()

            print('building channels')
            wat = Watershed.getInstance(wd)
            wat.build_channels(csa=5, mcl=15)
            
            print('setting outlet')
            wat.set_outlet(*outlet)
            
            print('building subcatchments')
            wat.build_subcatchments()

            print('abstracting watershed')
            wat.abstract_watershed()
            translator = wat.translator_factory()
            topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]

            print('building landuse')
            landuse = Landuse.getInstance(wd)
            landuse.mode = LanduseMode.Gridded
            landuse.build()
            landuse = Landuse.getInstance(wd)

            print('building soils')
            soils = Soils.getInstance(wd)
            soils.mode = SoilsMode.Gridded
            soils.build()

            print('building climate')
            climate = Climate.getInstance(wd)
            stations = climate.find_closest_stations()
            climate.input_years = 2
            climate.climatestation = stations[0]['id']

            climate.climate_mode = ClimateMode.GridMetPRISM
            climate.climate_spatialmode = ClimateSpatialMode.Multiple
            climate.set_observed_pars(start_year=2016, end_year=2017)

            climate.build(verbose=1)

            print('running wepp')
            wepp = Wepp.getInstance(wd)
            wepp.prep_hillslopes()
            wepp.run_hillslopes()

            wepp = Wepp.getInstance(wd)
            wepp.prep_watershed(erodibility=proj['erod'], critical_shear=proj['cs'])
            wepp.run_watershed()
        
            print('running post wepp processing')
            loss_report = wepp.report_loss()

            fn = _join(ron.export_dir, 'totalwatsed.csv')

            totwatsed = TotalWatSed(_join(ron.output_dir, 'totalwatsed.txt'),
                                    wepp.baseflow_opts, wepp.phosphorus_opts)
            totwatsed.export(fn)
            assert _exists(fn)

            print(loss_report.out_tbl)
            os.chdir('..')
            os.chdir('..')
            toc=time.perf_counter()
            print('minutes elapsed for wepppy basin calcs = ', (toc-tic)/60)
            print('----------------------------------------------------------------')

    bigtoc=time.perf_counter()
    print('minutes elapsed for entire basin, one year = ', (bigtoc-bigtic)/60)
    print('----------------------------------------------------------------')
    print('----------------------------------------------------------------')