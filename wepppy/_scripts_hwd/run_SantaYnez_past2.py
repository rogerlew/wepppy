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
filepath = 'geodata/small_basins_forecasting/santaynez_utm11half_outlets_to_polygons_zb1_d150.csv'
areaname = 'santa_ynez_utm11basins_1980to2000'
utmzn = 11
utmzs = 'S'
main_folder = '/media/helen/HelenData/wepppy_runs/SantaYnez/'
sy = 1979
ey = 2000
outlet_sed_80 = []
outlet_sed_81 = []
outlet_sed_82 = []
outlet_sed_83 = []
outlet_sed_84 = []
outlet_sed_85 = []
outlet_sed_86 = []
outlet_sed_87 = []
outlet_sed_88 = []
outlet_sed_89 = []
outlet_sed_90 = []
outlet_sed_91 = []
outlet_sed_92 = []
outlet_sed_93 = []
outlet_sed_94 = []
outlet_sed_95 = []
outlet_sed_96 = []
outlet_sed_97 = []
outlet_sed_98 = []
outlet_sed_99 = []
outlet_sed_00 = []
#############


# config_filepath = firename + '.cfg'
# base_name = '/home/helen/geodata/wepppy_runs/' + firename + '/'
config_filepath = '/home/helen/wepppy/wepppy/nodb/configs/run_santa_ynez_past.cfg'
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

for i in range(len(df)):
    print(areaname)
    try:
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
                soils.build_statsgo()

                from wepppy.nodb.mods.disturbed import Disturbed
                disturbed = Disturbed.getInstance(wd)
                # print(disturbed.sbs_coverage)

                print('building climate')
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = numyears
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.GridMetPRISM
                climate.climate_spatialmode = ClimateSpatialMode.Single
                climate.set_observed_pars(start_year=sy, end_year=ey)

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


                outlet_sed_80.append(annual_sed_data.iloc[1])
                outlet_sed_81.append(annual_sed_data.iloc[2])
                outlet_sed_82.append(annual_sed_data.iloc[3])
                outlet_sed_83.append(annual_sed_data.iloc[4])
                outlet_sed_84.append(annual_sed_data.iloc[5])
                outlet_sed_85.append(annual_sed_data.iloc[6])
                outlet_sed_86.append(annual_sed_data.iloc[7])
                outlet_sed_87.append(annual_sed_data.iloc[8])
                outlet_sed_88.append(annual_sed_data.iloc[9])
                outlet_sed_89.append(annual_sed_data.iloc[10])
                outlet_sed_90.append(annual_sed_data.iloc[11])
                outlet_sed_91.append(annual_sed_data.iloc[12])
                outlet_sed_92.append(annual_sed_data.iloc[13])
                outlet_sed_93.append(annual_sed_data.iloc[14])
                outlet_sed_94.append(annual_sed_data.iloc[15])
                outlet_sed_95.append(annual_sed_data.iloc[16])
                outlet_sed_96.append(annual_sed_data.iloc[17])
                outlet_sed_97.append(annual_sed_data.iloc[18])
                outlet_sed_98.append(annual_sed_data.iloc[19])
                outlet_sed_99.append(annual_sed_data.iloc[20])
                outlet_sed_00.append(annual_sed_data.iloc[21])


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
    except:
        shutil.rmtree(wd)
        pass

newdf = pd.DataFrame()
newdf['basinid'] = basin_ids_keep
newdf['new_da'] = new_da
newdf['outlet_sed_80'] = outlet_sed_80
newdf['outlet_sed_81'] = outlet_sed_81
newdf['outlet_sed_82'] = outlet_sed_82
newdf['outlet_sed_83'] = outlet_sed_83
newdf['outlet_sed_84'] = outlet_sed_84
newdf['outlet_sed_85'] = outlet_sed_85
newdf['outlet_sed_86'] = outlet_sed_86
newdf['outlet_sed_87'] = outlet_sed_87
newdf['outlet_sed_88'] = outlet_sed_88
newdf['outlet_sed_89'] = outlet_sed_89
newdf['outlet_sed_90'] = outlet_sed_90
newdf['outlet_sed_91'] = outlet_sed_91
newdf['outlet_sed_92'] = outlet_sed_92
newdf['outlet_sed_93'] = outlet_sed_93
newdf['outlet_sed_94'] = outlet_sed_94
newdf['outlet_sed_95'] = outlet_sed_95
newdf['outlet_sed_96'] = outlet_sed_96
newdf['outlet_sed_97'] = outlet_sed_97
newdf['outlet_sed_98'] = outlet_sed_98
newdf['outlet_sed_99'] = outlet_sed_99
newdf['outlet_sed_00'] = outlet_sed_00




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