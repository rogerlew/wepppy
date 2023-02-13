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



filepath = 'geodata/small_basin_input_data/august_fire_perimeter_basins.csv'
config_filepath = 'august_complex.cfg'
fire_year = 2020
water_year = 2021
base_name = '/home/helen/geodata/wepppy_runs/august_complex/'
precip_threshold_exceeded = []
new_outlet_x = []
new_outlet_y = []
new_da = []
outlet_sed_yield = []
hs_sed_yield = []


df = pd.read_csv(filepath)
# df['postfire_sed_yield']  = zeros(len(df))
# df['precip_threshold_exceeded'] = zeros(len(df))
firename = 'august_complex'
output_name = 'august_complex_wepp_output.csv'

os.chdir('geodata/wepppy_runs')
os.mkdir(firename)
os.chdir(firename)

bigtic=time.perf_counter()

# for i in range(len(df)):
for i in range(len(df)):
    if __name__ == '__main__':
        projects = [
                    dict(wd='august_complex_' + str(i+1),
                        extent=[df.xmin[i], df.ymin[i], df.xmax[i], df.ymax[i]], 
                        map_center=[df.center_x[i], df.center_y[i]],
                        map_zoom=12,
                        outlet=[df.outlet_x[i], df.outlet_y[i]],
                        landuse=None,
                        cs=19, erod=0.000001, chn_chn_wepp_width=1.0),
                    ]

        for proj in projects:
            tic=time.perf_counter()

            wd = proj['wd']
            extent = proj['extent']
            map_center = proj['map_center']
            map_zoom = proj['map_zoom']
            outlet = proj['outlet']
            default_landuse = proj['landuse']


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
            print('basin_id=', df.basin_id[i])
            print('drainage area =', df.DA_km2[i])

            # cwd = os.getcwd()
            # print("Current working directory: {0}".format(cwd))

            
                
            print('making directory')
            os.mkdir(wd)

            

            print('initializing project')
            

            print('config filepath = ', config_filepath)
            ron = Ron(wd, config_filepath)
            ron.name = wd
            ron.set_map(extent, map_center, zoom=map_zoom)
            
            print('fetching dem')
            ron.fetch_dem()

            print('building channels')
            wat = Watershed.getInstance(wd)
            wat.build_channels()
            
            print('setting outlet')
            wat.set_outlet(*outlet)
            # print(type(wat))
            # print(dir(wat))
            # print(dir(wat.outlet))
            # print(wat.outlet.actual_loc[1])
            no = utm.from_latlon(wat.outlet.actual_loc[1], wat.outlet.actual_loc[0])
            # print(df.outlet_x[i], df.outlet_y[i])
            # print(no)
            new_outlet_x.append(no[0])
            new_outlet_y.append(no[1])
            
            print('building subcatchments')
            wat.build_subcatchments()

            print('abstracting watershed')
            wat.abstract_watershed()
            translator = wat.translator_factory()
            topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]
            print('watershed area=', wat.wsarea/1e6)
            new_da.append(wat.wsarea/1e6)

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
            climate.set_observed_pars(start_year=fire_year, end_year=water_year)

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

            # print(loss_report.out_tbl)


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
            outlet_sed_yield.append(annual_sed_data.iloc[1])

            folder_name = base_name + wd + '/export'
            os.chdir(folder_name)
            hillslopes_output = pd.read_csv('totalwatsed.csv', names=['sed_kg','wy'], skiprows=1, usecols=[13,37])
            hs_annual_sed_data = hillslopes_output.groupby(["wy"])["sed_kg"].sum()
            hs_sed_yield.append(hs_annual_sed_data.iloc[1])

            folder_name = base_name + wd + '/climate'
            os.chdir(folder_name)
            climate_data = pd.read_csv('wepp.cli',delim_whitespace=True, names=['day','month','year','prcp','dur','tp','ip'], skiprows=15, usecols=[0,1,2,3,4,5,6])
            climate_data['avg_intensity'] = climate_data['prcp'].divide(climate_data['dur'])
            climate_data['peak_intensity'] = climate_data['ip'].multiply(climate_data['avg_intensity'])
            # climate_data['wy'] = wepp_output['wy']
            climate_data.loc[(climate_data['peak_intensity'] > 24) & (wepp_output['wy'] == water_year),'thresh_intensity'] = 1
            precip_threshold_exceeded.append(climate_data['thresh_intensity'].sum())
            climate_data.to_csv('climate_data.csv')  

            os.chdir('..')
            os.chdir('..')
            # cwd = os.getcwd()
            # print("Current working directory: {0}".format(cwd))

            toc=time.perf_counter()
            print('minutes elapsed for wepppy basin calcs = ', (toc-tic)/60)
            print('----------------------------------------------------------------')
newdf = pd.DataFrame()
newdf['basinid'] = df.basin_id
newdf['outlet_sed_yield'] = outlet_sed_yield
newdf['hillslope_sed_yield'] = hs_sed_yield
newdf['precip_threshold_exceeded'] = precip_threshold_exceeded
newdf['new_outlet_x'] = new_outlet_x
newdf['new_outlet_y'] = new_outlet_y
newdf['new_da'] = new_da


print(newdf)
newdf.to_csv(output_name)

bigtoc=time.perf_counter()
print('minutes elapsed for entire basin, one year = ', (bigtoc-bigtic)/60)
print('----------------------------------------------------------------')
print('----------------------------------------------------------------')