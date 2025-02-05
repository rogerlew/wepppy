import requests
import numpy as np
import pandas as pd
import json

from pprint import pprint


def retrieve_historical_timeseries(lng=-116.5, lat=46.5, start_year=2022, end_year=2022, gridmet_wind=False):
    
    start_date = f'{start_year}0101'
    end_date = f'{end_year}1231'

    headers = {
        'Connection': 'keep-alive',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://urldefense.com/v3/__http://www.prism.oregonstate.edu__;!!JYXjzlvb!3ZDOIAhm7pFSzmiM7_EJD34CLw1Yk7mdvmYxOSBXgjka-wrUX2U91YedF_X8WpPLKg$ ',
        'Referer': 'https://urldefense.com/v3/__http://www.prism.oregonstate.edu/explorer/__;!!JYXjzlvb!3ZDOIAhm7pFSzmiM7_EJD34CLw1Yk7mdvmYxOSBXgjka-wrUX2U91YedF_VPuIUC5w$ ',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    data = {
        'spares': '4km',
        'interp': 'idw',
        'stats': 'ppt tmin tmean tmax tdmean vpdmin vpdmax',
        'units': 'si',
        'range': 'daily',
        'start': start_date,
        'end': end_date,
        'stability': 'stable',
        'lon': str(lng),
        'lat': str(lat),
        'elev': '143',
        'call': 'pp/daily_timeseries',
        'proc': 'gridserv'
    }

    response = requests.post(
        'https://www.prism.oregonstate.edu/explorer/dataexplorer/rpc.php',
        headers=headers, data=data)

    result = json.loads(response.text)
    if 'result' not in result:
        print(response.text)
        return None

    data = result['result']['data']
    df = pd.DataFrame(data)

    df['tdmean'] = np.clip(df['tdmean'], df['tmin'], None)

    df.rename(columns={'ppt': 'ppt(mm)',
                       'tmax': 'tmax(degc)',
                       'tmin': 'tmin(degc)',
                       'tdmean': 'tdmean(degc)',
                       'tmean': 'tmean(degc)',
                       'vpdmin': 'vpdmin(hPa)',
                       'vpdmax': 'vpdmax(hPa)'}, inplace=True)

    _start_date = pd.to_datetime(start_date, format='%Y%m%d')
    _end_date = pd.to_datetime(end_date, format='%Y%m%d')
    df['date'] = pd.date_range(start=_start_date, end=_end_date)
    df.set_index('date', inplace=True)

    if gridmet_wind:
        from wepppy.climates.gridmet import retrieve_historical_wind as gridmet_retrieve_historical_wind
        wind_df = gridmet_retrieve_historical_wind(lon, lat, start_year, end_year)

        df['vs(m/s)'] = wind_df['vs(m/s)']
        df['th(DegreesClockwisefromnorth)'] = wind_df['th(DegreesClockwisefromnorth)']

    return df

if __name__ == "__main__":
    d = retrieve_historical_timeseries(lng=-122.0, lat=44.5)
    print(d)
