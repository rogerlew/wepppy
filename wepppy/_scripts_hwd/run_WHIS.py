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


base_name = '/home/helen/geodata/wepppy_runs/'


if __name__ == '__main__':
            projects = [
                        dict(wd='brandy_creek',
                            extent=[-122.72563935723157, 40.47289496432364, -122.48531342949718, 40.655465095849934], 
                            map_center=[-122.60547639336438, 40.564242278932966],
                            map_zoom=12,
                            outlet=[-122.57321813700284, 40.61518587365536],
                            landuse=None,
                            cs=19, erod=0.000001, chn_chn_wepp_width=1.0,
                            gwstorage=240, bfcoeff=0.9, dscoeff=0.00, bfthreshold=1.001),

                        dict(wd='boulder_creek',
                            extent=[-122.685330164953, 40.55728107528918, -122.51539407175706, 40.68626657133447], 
                            map_center=[-122.60036211835504, 40.621804957447615],
                            map_zoom=12,
                            outlet=[-122.59187910192986, 40.641378801781244],
                            landuse=None,
                            cs=19, erod=0.000001, chn_chn_wepp_width=1.0,
                            gwstorage=240, bfcoeff=0.9, dscoeff=0.00, bfthreshold=1.001),

                        dict(wd='whiskey_creek',
                            extent=[-122.64551656597567, 40.611731040593284, -122.47558047277975, 40.74061143626555], 
                            map_center=[-122.56054851937769, 40.67620238161505],
                            map_zoom=12,
                            outlet=[-122.5588998559944, 40.655022909367034],
                            landuse=None,
                            cs=19, erod=0.000001, chn_chn_wepp_width=1.0,
                            gwstorage=240, bfcoeff=0.9, dscoeff=0.00, bfthreshold=1.001),
                        ]

            for proj in projects:
                wd = proj['wd']
                extent = proj['extent']
                map_center = proj['map_center']
                map_zoom = proj['map_zoom']
                outlet = proj['outlet']
                default_landuse = proj['landuse']



                if _exists(wd):
                    shutil.rmtree(wd)

                os.chdir('geodata/wepppy_runs')
                    
                print('making directory')
                os.mkdir(wd)

                tic=time.perf_counter()

                print('initializing project')
                ron = Ron(wd, 'whis_carr_fire.cfg')
                ron.name = wd
                ron.set_map(extent, map_center, zoom=map_zoom)
                
                print('fetching dem')
                ron.fetch_dem()

                print('building channels')
                wat = Watershed.getInstance(wd)
                wat.build_channels(csa=10, mcl=100)
                
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
                climate.climate_spatialmode = ClimateSpatialMode.Single
                climate.set_observed_pars(start_year=2018, end_year=2019)

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

                folder_name = base_name + wd + '/wepp/output'
                os.chdir(folder_name)

                wepp_output = pd.read_csv('ebe_pw0.txt', delim_whitespace=True, names=['day','month','year','precip','runoff_vol','runoff_peak','sed_kg'], skiprows=9, usecols=[0,1,2,3,4,5,6])

                yr = fire_year
                for j in range(2):
                    wepp_output.loc[(wepp_output['month'] <10) & (wepp_output['year'] == j+1), 'wy'] = yr
                    wepp_output.loc[(wepp_output['month'] >9) & (wepp_output['year'] == j+1), 'wy'] = yr+1
                    yr = yr+1

                annual_sed_data = wepp_output.groupby(["wy"])["sed_kg"].sum()
                print('annual_sed_data.iloc[1]=',annual_sed_data.iloc[1])
                postfire_sed_yield.append(annual_sed_data.iloc[1])

                folder_name = base_name + wd + '/climate'
                os.chdir(folder_name)
                climate_data = pd.read_csv('wepp.cli',delim_whitespace=True, names=['day','month','year','prcp','dur','tp','ip'], skiprows=15, usecols=[0,1,2,3,4,5,6])
                climate_data['avg_intensity'] = climate_data['prcp'].divide(climate_data['dur'])
                climate_data['peak_intensity'] = climate_data['ip'].multiply(climate_data['avg_intensity'])
                climate_data['wy'] = wepp_output['wy']
                # climate_data['thresh_intensity'] = []
                # climate_data.loc[(climate_data['peak_intensity'] < 24),'thresh_intensity'] = 0
                climate_data.loc[(climate_data['peak_intensity'] > 24) & (climate_data['wy'] == water_year),'thresh_intensity'] = 1
                precip_threshold_exceeded.append(climate_data['thresh_intensity'].sum())
                climate_data.to_csv('climate_data.csv')  


                os.chdir('..')
                os.chdir('..')
                toc=time.perf_counter()
                print('minutes elapsed for wepppy basin calcs = ', (toc-tic)/60)
                print('----------------------------------------------------------------')
