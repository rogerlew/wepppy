# Copyright (c) 2016-2023, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from datetime import datetime, timedelta
import time
import io
import pandas as pd
import requests

from metpy.calc import dewpoint_from_relative_humidity
from metpy.units import units

from calendar import isleap

from wepppy.all_your_base import isint

def retrieve_historical_timeseries(lon, lat, start_year, end_year):
    yesterday = datetime.now() - timedelta(2)
    if end_year == yesterday.year:
        end_date = datetime.strftime(yesterday, '%Y-%m-%d')
    else:
        end_date = f'{end_year}-12-31'

    url = f"https://climate-dev.nkn.uidaho.edu/Services/get-netcdf-data/?decimal-precision=8&request-JSON=True&"\
          f"lat={lat}&lon={lon}&positive-east-longitude=False&"\
          f"data-path=http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_pr_1979_CurrentYear_CONUS.nc&variable=precipitation_amount&variable-name=pr&start-date={start_year}-01-01&end-date={end_date}&"\
          f"data-path=http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_srad_1979_CurrentYear_CONUS.nc&variable=daily_mean_shortwave_radiation_at_surface&variable-name=srad&start-date={end_date}-01-01&end-date={end_date}&"\
          f"data-path=http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_tmmx_1979_CurrentYear_CONUS.nc&variable=daily_maximum_temperature&variable-name=tmmx&start-date={start_year}-01-01&end-date={end_date}&"\
          f"data-path=http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_tmmn_1979_CurrentYear_CONUS.nc&variable=daily_minimum_temperature&variable-name=tmmn&start-date={start_year}-01-01&end-date={end_date}&"\
          f"data-path=http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_vs_1979_CurrentYear_CONUS.nc&variable=daily_mean_wind_speed&variable-name=vs&start-date={start_year}-01-01&end-date={end_date}&"\
          f"data-path=http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_th_1979_CurrentYear_CONUS.nc&variable=daily_mean_wind_direction&variable-name=th&start-date={start_year}-01-01&end-date={end_date}&"\
          f"data-path=http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_rmin_1979_CurrentYear_CONUS.nc&variable=daily_minimum_relative_humidity&variable-name=rmin&start-date={start_year}-01-01&end-date={end_date}&"\
          f"data-path=http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_rmax_1979_CurrentYear_CONUS.nc&variable=daily_maximum_relative_humidity&variable-name=rmax&start-date={start_year}-01-01&end-date={end_date}&"\
          f"filename=gridmet_ts.shaw"

#          f"data-path=http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_sph_1979_CurrentYear_CONUS.nc&variable=daily_mean_specific_humidity&variable-name=sph&start-date={start_year}-01-01&end-date={end_date}&"\
#          f"data-path=http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_vpd_1979_CurrentYear_CONUS.nc&variable=daily_mean_vapor_pressure_deficit&variable-name=vpd&start-date={start_year}-01-01&end-date={end_date}&"\

    headers = {'Accept': 'application/json', 'referer': 'https://wepp.cloud'}
    response = requests.get(url, headers=headers)

    response_data = response.json()

    data = response_data['data'][0]

    #print(data.keys())
    #dict_keys(['metadata', 'lat_lon', 'yyyy-mm-dd', 'pr(mm)', 'srad(Wm-2)', 'tmmx(K)', 'tmmn(K)', 'vs(m/s)', 'th(DegreesClockwisefromnorth)', 'rmin(%)', 'rmax(%)'])

    df = pd.DataFrame()
    df['pr(mm/day)'] = pd.Series(data['pr(mm)']).astype(float)
    df['srad(Wm-2)'] = pd.Series(data['srad(Wm-2)']).astype(float)
    df['srad(l/day)'] = df['srad(Wm-2)'] * 2.06362996638
    df['tmmx(degc)'] = pd.Series(data['tmmx(K)']).astype(float) - 273.15
    df['tmmn(degc)'] = pd.Series(data['tmmn(K)']).astype(float) - 273.15
    df['tavg(degc)'] = (df['tmmx(degc)'] + df['tmmn(degc)']) / 2
    df['vs(m/s)'] = pd.Series(data['vs(m/s)']).astype(float)
    df['th(DegreesClockwisefromnorth)'] = pd.Series(data['th(DegreesClockwisefromnorth)']).astype(float)
    df['rmax(%)'] = pd.Series(data['rmax(%)']).astype(float)
    df['rmin(%)'] = pd.Series(data['rmin(%)']).astype(float)
    df['ravg(%)'] = (df['rmax(%)'] + df['rmin(%)']) / 2
    df['tdew(degc)'] = dewpoint_from_relative_humidity(df['tavg(degc)'].values * units.degC,
                                                    df['ravg(%)'].values * units.percent).magnitude

    df.index = pd.to_datetime(data['yyyy-mm-dd'], format='%Y-%m-%d')

    return df


if __name__ == '__main__':
    from pprint import pprint
    lon = -116.2
    lat = 43.7
    start_year = 2023
    end_year = 2023

    df = retrieve_historical_timeseries(lon, lat, start_year, end_year)
    print(df.info())

