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
filepath = 'geodata/small_basins_forecasting/santaynez_utm10half_outlets_to_polygons.csv'
areaname = 'santa_ynez_utm10basins_2020to2030_testing'
utmzn = 10
utmzs = 'S'
main_folder = '/media/helen/HelenData/wepppy_runs/SantaYnez/'
sy = 2019
ey = 2030
outlet_sed_2020 = []
outlet_sed_2021 = []
outlet_sed_2022 = []
outlet_sed_2023 = []
outlet_sed_2024 = []
outlet_sed_2025 = []
outlet_sed_2026 = []
outlet_sed_2027 = []
outlet_sed_2028 = []
outlet_sed_2029 = []
outlet_sed_2030 = []
# outlet_sed_2031 = []
# outlet_sed_2032 = []
# outlet_sed_2033 = []
# outlet_sed_2034 = []
# outlet_sed_2035 = []
# outlet_sed_2036 = []
# outlet_sed_2037 = []
# outlet_sed_2038 = []
# outlet_sed_2039 = []
# outlet_sed_2040 = []
# outlet_sed_2041 = []
# outlet_sed_2042 = []
# outlet_sed_2043 = []
# outlet_sed_2044 = []
# outlet_sed_2045 = []
# outlet_sed_2046 = []
# outlet_sed_2047 = []
# outlet_sed_2048 = []
# outlet_sed_2049 = []
# outlet_sed_2050 = []
#############


# config_filepath = firename + '.cfg'
# base_name = '/home/helen/geodata/wepppy_runs/' + firename + '/'
config_filepath = '/home/helen/wepppy/wepppy/nodb/configs/run_future.cfg'
base_name = main_folder + areaname + '/'

basin_ids_keep = []
new_outlet_x = []
new_outlet_y = []
new_da = []

# hs_sed_yield = []

# max_precip = []
# cum_precip = []
# max_avg_intensity =[]
# max_peak_intensity =[]
# precip_threshold_exceeded = []



numyears = ey-sy


df = pd.read_csv(filepath)

output_name = areaname + '_wepp_output.csv'

os.chdir(main_folder)
os.mkdir(areaname)
os.chdir(areaname)

bigtic=time.perf_counter()

for i in range(1,2):
    print(areaname)
    # try:
    if __name__ == '__main__':
            projects = [
                        dict(wd= areaname + '_' + str(df.basin_id[i]),
                            extent=[df.xmin[i], df.ymin[i], df.xmax[i], df.ymax[i]], 
                            map_center=[df.center_x[i], df.center_y[i]],
                            map_zoom=12,
                            outlet=[df.outlet_x[i], df.outlet_y[i]],
                            landuse=None,
                            cs=19, erod=0.000001, chn_chn_wepp_width=1.0,
                            da=df.DA_km2[i]),
                        ]

            for proj in projects:
                tic=time.perf_counter()


                wd = proj['wd']
                extent = proj['extent']
                map_center = proj['map_center']
                map_zoom = proj['map_zoom']
                outlet = proj['outlet']
                default_landuse = proj['landuse']
                drainage_area = proj['da']


                temp = utm.to_latlon(extent[0],extent[1],utmzn,utmzs)
                extent[0] = temp[1]
                extent[1] = temp[0]
                temp = utm.to_latlon(extent[2],extent[3],utmzn,utmzs)
                extent[2] = temp[1]
                extent[3] = temp[0]

                temp = utm.to_latlon(map_center[0],map_center[1],utmzn,utmzs)
                map_center[0] = temp[1]
                map_center[1] = temp[0]

                temp = utm.to_latlon(outlet[0],outlet[1],utmzn,utmzs)
                outlet[0] = temp[1]
                outlet[1] = temp[0]

                print('type(extent)=', type(extent))



                if _exists(wd):
                    shutil.rmtree(wd)

                print('outlet=', outlet)
                print('basin_id=', df.basin_id[i])
                print('drainage area =', drainage_area)

                    
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
                wat.set_outlet(*outlet, drainage_area)
                no = utm.from_latlon(wat.outlet.actual_loc[1], wat.outlet.actual_loc[0])
                # print('wat.outlet.actual_loc[1]=', wat.outlet.actual_loc[1])
                # print('wat.outlet.actual_loc[0]=', wat.outlet.actual_loc[0])
                # print('no[0], df.outlet_x[i]', no[0], df.outlet_x[i])
                # print('no[1], df.outlet_y[i]', no[1], df.outlet_y[i])
                distance = math.sqrt((no[0] - df.outlet_x[i])**2 + (no[1] - df.outlet_y[i])**2)
                print('distance in meters from original outlet =', distance)
                
                
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

                # from wepppy.nodb.mods.disturbed import Disturbed
                # disturbed = Disturbed.getInstance(wd)
                # print(disturbed.sbs_coverage)

                print('building climate')
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = numyears
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Future
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.set_future_pars(start_year=sy, end_year=ey)
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

                totalwatsed = TotalWatSed2(wd, wepp.baseflow_opts, wepp.phosphorus_opts)
                totalwatsed.export(fn)
                assert _exists(fn)

                # print(loss_report.out_tbl)


                folder_name = base_name + wd + '/wepp/output'
                os.chdir(folder_name)
                wepp_output = pd.read_csv('ebe_pw0.txt', delim_whitespace=True, names=['day','month','year','precip','runoff_vol','runoff_peak','sed_kg'], skiprows=9, usecols=[0,1,2,3,4,5,6])
                yr = sy
                for j in range(numyears+1):
                    wepp_output.loc[(wepp_output['month'] <10) & (wepp_output['year'] == j+1), 'wy'] = yr
                    wepp_output.loc[(wepp_output['month'] >9) & (wepp_output['year'] == j+1), 'wy'] = yr+1
                    yr = yr+1
                annual_sed_data = wepp_output.groupby(["wy"])["sed_kg"].sum()
                print(annual_sed_data)
                # print('annual_sed_data.iloc[1]=', annual_sed_data.iloc[1])
                # print('annual_sed_data.iloc[2]=', annual_sed_data.iloc[2])

                outlet_sed_2020.append(annual_sed_data.iloc[1])
                outlet_sed_2021.append(annual_sed_data.iloc[2])
                outlet_sed_2022.append(annual_sed_data.iloc[3])
                outlet_sed_2023.append(annual_sed_data.iloc[4])
                outlet_sed_2024.append(annual_sed_data.iloc[5])
                outlet_sed_2025.append(annual_sed_data.iloc[6])
                outlet_sed_2026.append(annual_sed_data.iloc[7])
                outlet_sed_2027.append(annual_sed_data.iloc[8])
                outlet_sed_2028.append(annual_sed_data.iloc[9])
                outlet_sed_2029.append(annual_sed_data.iloc[10])
                outlet_sed_2030.append(annual_sed_data.iloc[11])
                # outlet_sed_2031.append(annual_sed_data.iloc[12])
                # outlet_sed_2032.append(annual_sed_data.iloc[13])
                # outlet_sed_2033.append(annual_sed_data.iloc[14])
                # outlet_sed_2034.append(annual_sed_data.iloc[15])
                # outlet_sed_2035.append(annual_sed_data.iloc[16])
                # outlet_sed_2036.append(annual_sed_data.iloc[17])
                # outlet_sed_2037.append(annual_sed_data.iloc[18])
                # outlet_sed_2038.append(annual_sed_data.iloc[19])
                # outlet_sed_2039.append(annual_sed_data.iloc[20])
                # outlet_sed_2040.append(annual_sed_data.iloc[21])
                # outlet_sed_2041.append(annual_sed_data.iloc[22])
                # outlet_sed_2042.append(annual_sed_data.iloc[23])
                # outlet_sed_2043.append(annual_sed_data.iloc[24])
                # outlet_sed_2044.append(annual_sed_data.iloc[25])
                # outlet_sed_2045.append(annual_sed_data.iloc[26])
                # outlet_sed_2046.append(annual_sed_data.iloc[27])
                # outlet_sed_2047.append(annual_sed_data.iloc[28])
                # outlet_sed_2048.append(annual_sed_data.iloc[29])
                # outlet_sed_2049.append(annual_sed_data.iloc[30])
                # outlet_sed_2050.append(annual_sed_data.iloc[31])


                # print('outlet_sed_yield_85', outlet_sed_yield_85)
                # print('annual_sed_data.iloc[1]=',annual_sed_data.iloc[1])
                # outlet_sed_yield.append(annual_sed_data.iloc[1])

                # folder_name = base_name + wd + '/export'
                # os.chdir(folder_name)
                # hillslopes_output = pd.read_csv('totalwatsed.csv', names=['wy','sed_kg'], skiprows=5, usecols=[4,5])
                # print('hillslopes_output=', hillslopes_output)
                # hs_annual_sed_data = hillslopes_output.groupby(["wy"])["sed_kg"].sum()
                # hs_sed_yield.append(hs_annual_sed_data.iloc[1])

                # folder_name = base_name + wd + '/climate'
                # os.chdir(folder_name)
                # climate_data = pd.read_csv('wepp.cli',delim_whitespace=True, names=['day','month','year','prcp','dur','tp','ip'], skiprows=15, usecols=[0,1,2,3,4,5,6])
                # climate_data['avg_intensity'] = climate_data['prcp'].divide(climate_data['dur'])
                # climate_data['peak_intensity'] = climate_data['ip'].multiply(climate_data['avg_intensity'])
                # # climate_data['wy'] = wepp_output['wy']
                # climate_data.loc[(climate_data['peak_intensity'] > 24) & (wepp_output['wy'] == water_year),'thresh_intensity'] = 1
                # precip_threshold_exceeded.append(climate_data['thresh_intensity'].sum())
                # climate_data.to_csv('climate_data.csv')  

                basin_ids_keep.append(df.basin_id[i])
                new_outlet_x.append(no[0])
                new_outlet_y.append(no[1])
                new_da.append(wat.wsarea/1e6)

                # os.chdir('..')
                ## remove a bunch of directories that take up too much space
                # shutil.rmtree('climate')
                # shutil.rmtree('dem')
                # shutil.rmtree('disturbed')
                # shutil.rmtree('landuse')
                # shutil.rmtree('soils')
                # shutil.rmtree('watershed')
                # shutil.rmtree('observed')

                # cwd = os.getcwd()
                # dir_list = os.listdir(cwd)
                # for item in dir_list:
                #     if item.endswith('.nodb'):
                #         os.remove(os.path.join(cwd, item))
                os.chdir('..')
                os.chdir('..')
                os.chdir('..')
                cwd = os.getcwd()
                print("Current working directory: {0}".format(cwd))

                toc=time.perf_counter()
                print('minutes elapsed for wepppy basin calcs = ', (toc-tic)/60)
                print('----------------------------------------------------------------')
    # except:
    #     shutil.rmtree(wd)
    #     pass

newdf = pd.DataFrame()
newdf['basinid'] = basin_ids_keep
newdf['new_da'] = new_da
newdf['outlet_sed_2020'] = outlet_sed_2020
newdf['outlet_sed_2021'] = outlet_sed_2021
newdf['outlet_sed_2022'] = outlet_sed_2022
newdf['outlet_sed_2023'] = outlet_sed_2023
newdf['outlet_sed_2024'] = outlet_sed_2024
newdf['outlet_sed_2025'] = outlet_sed_2025
newdf['outlet_sed_2026'] = outlet_sed_2026
newdf['outlet_sed_2027'] = outlet_sed_2027
newdf['outlet_sed_2028'] = outlet_sed_2028
newdf['outlet_sed_2029'] = outlet_sed_2029
newdf['outlet_sed_2030'] = outlet_sed_2030
# newdf['outlet_sed_2031'] = outlet_sed_2031
# newdf['outlet_sed_2032'] = outlet_sed_2032
# newdf['outlet_sed_2033'] = outlet_sed_2033
# newdf['outlet_sed_2034'] = outlet_sed_2034
# newdf['outlet_sed_2035'] = outlet_sed_2035
# newdf['outlet_sed_2036'] = outlet_sed_2036
# newdf['outlet_sed_2037'] = outlet_sed_2037
# newdf['outlet_sed_2038'] = outlet_sed_2038
# newdf['outlet_sed_2039'] = outlet_sed_2039
# newdf['outlet_sed_2040'] = outlet_sed_2040
# newdf['outlet_sed_2041'] = outlet_sed_2041
# newdf['outlet_sed_2042'] = outlet_sed_2042
# newdf['outlet_sed_2043'] = outlet_sed_2043
# newdf['outlet_sed_2044'] = outlet_sed_2044
# newdf['outlet_sed_2045'] = outlet_sed_2045
# newdf['outlet_sed_2046'] = outlet_sed_2046
# newdf['outlet_sed_2047'] = outlet_sed_2047
# newdf['outlet_sed_2048'] = outlet_sed_2048
# newdf['outlet_sed_2049'] = outlet_sed_2049
# newdf['outlet_sed_2050'] = outlet_sed_2050
# newdf['hillslope_sed_yield'] = hs_sed_yield
# newdf['precip_threshold_exceeded'] = precip_threshold_exceeded
# newdf['new_outlet_x'] = new_outlet_x
# newdf['new_outlet_y'] = new_outlet_y



print(newdf)
newdf.to_csv(output_name)

bigtoc=time.perf_counter()
print('minutes elapsed for entire basin, one year = ', (bigtoc-bigtic)/60)
print('----------------------------------------------------------------')
print('----------------------------------------------------------------')