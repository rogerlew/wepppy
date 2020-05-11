import requests
import pandas as pd
import json


def retrieve_daily(lon=-117.45, lat=46.534, start_date='19790101', end_date='20170110'):
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
        'stats': 'ppt tmin tmax',
        'units': 'si',
        'range': 'daily',
        'start': start_date,
        'end': end_date,
        'stability': 'stable',
        'lon': str(lon),
        'lat': str(lat),
        'elev': '48',
        'call': 'pp/daily_timeseries',
        'proc': 'gridserv'
    }

    data['start'] = '19900101'
    data['end'] = '20171231'
    data['lat'] = '46.0000'
    data['lon'] = '-116.0000'

    response = requests.post(
        'http://www.prism.oregonstate.edu/explorer/dataexplorer/rpc.php',
        headers=headers, data=data, verify=False)

    my_data = json.loads(response.text)
    ppt = my_data['result']['data']['ppt']
    tmin = my_data['result']['data']['tmin']
    tmax = my_data['result']['data']['tmax']

    prism = pd.DataFrame(
        {'Prepitation (mm)': ppt,
         'Tmax (degC)': tmax,
         'Tmin (degC)': tmin,
         })
    prism['Date'] = pd.date_range(start=data['start'], end=data['end'])
    prism = prism[['Date', 'Prepitation (mm)', 'Tmax (degC)', 'Tmin (degC)']]

    # View the first ten rows
    prism.to_csv("prism.csv", index=False)


if __name__ == "__main__":
    retrieve_daily()