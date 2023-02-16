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
import math

import wepppy
from wepppy.nodb import *
from os.path import join as _join
from wepppy.wepp.out import TotalWatSed2

from osgeo import gdal, osr
gdal.UseExceptions()

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


############# THESE ARE THE ONLY INPUTS TO CHANGE
filepath = 'geodata/small_basin_input_data/august_complex_basins_from_fire_perimeter_0p1_to_45km2_extent500m.csv'
firename = 'august_complex'
fire_year = 2020
water_year = 2021
#############


# config_filepath = firename + '.cfg'
base_name = '/home/helen/geodata/wepppy_runs/' + firename + '/'
# base_name = '/media/helen/HelenData/wepppy_runs/' + firename + '/'
precip_threshold_exceeded = []
new_outlet_x = []
new_outlet_y = []
new_da = []
outlet_sed_yield = []
hs_sed_yield = []
basin_ids_keep = []


df = pd.read_csv(filepath)
# df['postfire_sed_yield']  = zeros(len(df))
# df['precip_threshold_exceeded'] = zeros(len(df))

output_name = firename + '_wepp_output.csv'

os.chdir('geodata/wepppy_runs')
# os.chdir('/media/helen/HelenData/wepppy_runs')
os.chdir(firename)


for i in range(len(df)):
    try:
        wd = firename + '_' + str(df.basin_id[i])
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
        hillslopes_output = pd.read_csv('totalwatsed.csv', names=['wy','sed_kg'], skiprows=5, usecols=[4,5])
        print('hillslopes_output=', hillslopes_output)
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

        basin_ids_keep.append(df.basin_id[i])
        # new_outlet_x.append(no[0])
        # new_outlet_y.append(no[1])
        # new_da.append(wat.wsarea/1e6)

        os.chdir('..')
        os.chdir('..')
                # cwd = os.getcwd()
                # print("Current working directory: {0}".format(cwd))


    except:
        pass

newdf = pd.DataFrame()
newdf['basinid'] = basin_ids_keep
newdf['outlet_sed_yield'] = outlet_sed_yield
newdf['hillslope_sed_yield'] = hs_sed_yield
newdf['precip_threshold_exceeded'] = precip_threshold_exceeded
# newdf['new_outlet_x'] = new_outlet_x
# newdf['new_outlet_y'] = new_outlet_y
# newdf['new_da'] = new_da


print(newdf)
newdf.to_csv(output_name)

# bigtoc=time.perf_counter()
# print('minutes elapsed for entire basin, one year = ', (bigtoc-bigtic)/60)
print('----------------------------------------------------------------')
print('----------------------------------------------------------------')