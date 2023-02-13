import os
import shutil
from os.path import exists as _exists
from pprint import pprint
from time import time
import utm
import pandas as pd
import numpy as np

import wepppy
from wepppy.nodb import *
from os.path import join as _join
from wepppy.wepp.out import TotalWatSed

from osgeo import gdal, osr
gdal.UseExceptions()

filepath = 'geodata/small_basin_input_data/centralcoast_subbasins.csv'
df = pd.read_csv(filepath)


years = (2015, 2016, 2017, 2018, 2019, 2020)

for year in years:

    for i in range(len(df)):

        if __name__ == '__main__':
            projects = [
                        dict(wd='central_coast_subbasin' + str(i) + '_year' + str(year),
                            extent=[df.xmin[i], df.ymin[i], df.xmax[i], df.ymax[i]], 
                            map_center=[df.center_x[i], df.center_y[i]],
                            map_zoom=12.5,
                            outlet=[df.x_outlet[i], df.y_outlet[i]],
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

                

                temp = utm.to_latlon(extent[0]-20000,extent[1]-20000,10,'S')
                extent[0] = temp[1]
                extent[1] = temp[0]
                temp = utm.to_latlon(extent[2]+20000,extent[3]+20000,10,'S')
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


                os.chdir('geodata/wepppy_runs')
                    
                print('making directory')
                os.mkdir(wd)

                print('initializing project')
                config_filepath = 'ca_hindcast_' + str(year) + '.cfg'
                print('config filepath = ', config_filepath)
                ron = Ron(wd, config_filepath)
                ron.name = wd
                ron.set_map(extent, map_center, zoom=map_zoom)
                
                print('fetching dem')
                ron.fetch_dem()

                print('building channels')
                wat = Watershed.getInstance(wd)
                wat.build_channels(csa=5, mcl=60)
                
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

                climate.climate_mode = ClimateMode.Observed
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.set_observed_pars(start_year=year, end_year=year+1)

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
