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


if __name__ == '__main__':
            projects = [
                        dict(wd='gaviota',
                            extent=[-120.3141552013477, 34.43394004633613, -120.14421910815176, 34.57398210866478], 
                            map_center=[-120.22918715474974, 34.50399048806455],
                            map_zoom=13,
                            outlet=[-120.23032281909522, 34.48490768405995],
                            landuse=None,
                            cs=19, erod=0.000001, chn_chn_wepp_width=1.0,),

                        dict(wd='san_onofre',
                            extent=[-120.21858214284295, 34.46469768221383, -120.15850066090935, 34.51421866235497], 
                            map_center=[-120.18854140187615, 34.489461847890865],
                            map_zoom=14,
                            outlet=[-120.18820606852783, 34.47512017677539],
                            landuse=None,
                            cs=19, erod=0.000001, chn_chn_wepp_width=1.0,),

                        dict(wd='arroyo_hondo',
                            extent=[-120.19155843358195, 34.46206735843009, -120.10659038698398, 34.53209419430627], 
                            map_center=[-120.14907441028299, 34.49708812833236],
                            map_zoom=13.5,
                            outlet=[-120.1414948242699, 34.47684819769478],
                            landuse=None,
                            cs=19, erod=0.000001, chn_chn_wepp_width=1.0,),
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
                ron = Ron(wd, 'gaviota_2004_fire.cfg')
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
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.set_observed_pars(start_year=2004, end_year=2005)

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
