# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from __future__ import print_function

from datetime import datetime
import requests
import pandas as pd

from wepppy.all_your_base import isfloat, try_parse


def parse_datetime(x):
    """
    parses x in yyyy-mm-dd, yyyy-mm-dd, yyyy/mm/dd, or yyyy mm dd
    to datetime object.
    """
    if isinstance(x, datetime):
        return x
        
    ymd = x.split('-')
    if len(ymd) != 3:
        ymd = x.split('/')
    if len(ymd) != 3:
        ymd = x.split('.')
    if len(ymd) != 3:
        ymd = x.split()
    
    y, m, d = ymd
    y = int(y)
    m = int(m)
    d = int(d)
    
    return datetime(y, m, d)

        
variables_d = {'pr': 'precipitation',
               'tasmax': 'air_temperature',
               'tasmin': 'air_temperature',
               'rsds': 'surface_downwelling_shortwave_flux_in_air',
               'uas': 'eastward_wind',
               'vas': 'northward_wind',
               'huss': 'specific_humidity'}
        
_url_template = \
    'https://climate-dev.nkn.uidaho.edu/Services/get-netcdf-data/'\
    '?decimal-precision=8'\
    '&request-JSON=True'\
    '&lat={lat}'\
    '&lon={lng}'\
    '&positive-east-longitude=True'\
    '&data-path=http://thredds.northwestknowledge.net:8080/thredds/dodsC/'\
    'agg_macav2metdata_{variable_name}_{model}_r1i1p1_{scenario}_CONUS_daily.nc'\
    '&variable={variable}'\
    '&variable-name={variable_name}'\
    '&start-date={start_date}'\
    '&end-date={end_date}'


def _retrieve(lng, lat, start_date, end_date, model, scenario, variable_name, verbose=False):
    global variables_d
        
    # validate input parameters
    assert isfloat(lng)
    assert isfloat(lat)
    
    start_date = parse_datetime(start_date)
    end_date = parse_datetime(end_date)
    
    assert model in ['GFDL-ESM2G', 'GFDL-ESM2M']
    
    assert scenario in ["rcp45_2006_2099",
                        "rcp85_2006_2099",
                        "historical_1950_2005"]
                        
    if scenario == "historical_1950_2005":
        d0 = datetime(1950, 1, 1)
        dend = datetime(2005, 12, 31)
    else:
        d0 = datetime(2006, 1, 1)
        dend = datetime(2099, 12, 31)
    
    assert start_date >= d0
    assert start_date <= dend
    
    assert end_date >= d0
    assert end_date <= dend
    
    start_date = start_date.strftime('%Y-%m-%d')
    end_date = end_date.strftime('%Y-%m-%d')
    
    assert variable_name in variables_d
    
    # build url for query
    url = _url_template.format(lat=lat, lng=lng, 
                               start_date=start_date, end_date=end_date, 
                               model=model, scenario=scenario,
                               variable=variables_d[variable_name], 
                               variable_name=variable_name)

    if verbose:
        print(url)

    # query server
    referer = 'https://wepp1.nkn.uidaho.edu'
    s = requests.Session()
    r = s.get(url,  headers={'referer': referer})
    
    if r.status_code != 200:
        raise Exception("Encountered error retrieving "
                        "from downscaledForecast server.\n%s" % url)
        
    # process returned data
    data = r.json()['data'][0]
    assert u'yyyy-mm-dd' in data

    df = pd.DataFrame()
    for k in data:
        if k in [u'lat_lon', u'metadata']:
            continue

        if k == u'yyyy-mm-dd':
            year_month_day = [row.split('-') for row in data[k]]
            df['year'] = [row[0] for row in year_month_day]
            df['month'] = [row[1] for row in year_month_day]
            df['day'] = [row[2] for row in year_month_day]
            df['date'] = data[k]

        elif variable_name in k:
            df[k] = [try_parse(v) for v in data[k]]

    df.set_index(pd.DatetimeIndex(df['date']))
    return df


def _retrieve_timeseries(lng, lat, start_date, end_date, model, scenario, verbose=False):
    result = None
    for variable_name in variables_d:
        df = _retrieve(lng, lat, start_date, end_date, 
                       model, scenario, variable_name, verbose=verbose)
        
        if result is None:
            result = df
        else:
            result = pd.merge(result, df)
    
    if u'tasmin(K)' in result:
        result[u'tasmin(degc)'] = result[u'tasmin(K)'] - 273.15
        
    if u'tasmax(K)' in result:
        result[u'tasmax(degc)'] = result[u'tasmax(K)'] - 273.15

    for key in [u'month_x', u'month_y', u'day_x', u'day_y', u'year_x', u'year_y']:
        if key in result:
            del result[key]

    return result


def retrieve_rcp85_timeseries(lng, lat, start_date, end_date, 
                              model='GFDL-ESM2G', verbose=False):
    scenario = "rcp85_2006_2099"
    return _retrieve_timeseries(lng, lat, start_date, end_date, 
                                model, scenario, verbose=verbose)


def retrieve_rcp45_timeseries(lng, lat, start_date, end_date, 
                              model='GFDL-ESM2G', verbose=False):
    scenario = "rcp45_2006_2099"
    return _retrieve_timeseries(lng, lat, start_date, end_date, 
                                model, scenario, verbose=verbose)


def retrieve_historical_timeseries(lng, lat, start_date, end_date, 
                                   model='GFDL-ESM2G', verbose=False):
    scenario = "historical_1950_2005"
    return _retrieve_timeseries(lng, lat, start_date, end_date, 
                                model, scenario, verbose=verbose)


if __name__ == "__main__":
    from time import time
    
    t0 = time()
    df2 = retrieve_rcp85_timeseries(-116, 47, datetime(2018, 1, 1), datetime(2018, 1, 31), verbose=True)
    print(df2)
    print(time() - t0)
    print(df2.keys())
    
#    t0 = time()
#    df = retrieve_historical_timeseries(-116, 47, '1954/10/1', '1954/10/31')
#    print(df)
#    print(time() - t0)
#    sys.exit()
