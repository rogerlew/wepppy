# Copyright (c) 2016-2023, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import time
import io
import pandas as pd
import requests

from calendar import isleap

from wepppy.all_your_base import isint


from metpy.calc import dewpoint
from metpy.units import units

def retrieve_historical_timeseries(lon, lat, start_year, end_year, fill_leap_years=True):
    assert isint(start_year)
    assert isint(end_year)
    
    start_year = int(start_year)
    end_year = int(end_year)
    
    years = ','.join(str(v) for v in range(start_year, end_year+1))
    
    assert start_year <= end_year
    assert 1980 <= start_year <= int(time.strftime("%Y"))-1
    assert 1980 <= end_year <= int(time.strftime("%Y"))-1
    
    # request data
    url = 'https://daymet.ornl.gov/single-pixel/api/data'\
          '?lat={lat}&lon={lon}'\
          '&year={years}'\
          .format(lat=lat, lon=lon, years=years)

    attempts = 0
    txt = None
    while txt is None and attempts < 10:
        r = requests.get(url)

        if r.status_code != 200:
            attempts += 1
            continue

        lines = r.text.split('\n')

        if len(lines) < (start_year - end_year) * 365:
            attempts += 1
            continue

        skip = -1
        for L in lines:
            if L.lower().startswith('year'):
                break

            skip += 1

        attempts += 1

        txt = r.text.replace('YEAR,', 'year,')\
                    .replace('DAY,', 'yday,')

    if txt is None:
        raise Exception('Error retrieving from daymet:\n' + r.text)

    # create a virtual file to create pandas dataframe
    fp = io.StringIO()
    fp.write(txt)
    fp.seek(0)

    # create dataframe
    df = pd.read_csv(fp, header=skip)

    if fill_leap_years:
        years = sorted(list(set(df.year)))
        leap_years = [yr for yr in years if isleap(yr)]

        if len(leap_years) > 0:
            for yr in leap_years:
                index = df[(df['year'] == yr) & (df['yday'] == 365)].index[0]
                new_row = df.loc[index].copy()
                new_row.yday = 366
                df.append(new_row)

            # Sort the DataFrame by multiple columns
            df = df.sort_values(by=['year', 'yday'], ascending=True).reset_index(drop=True)

    try:
        df.index = pd.to_datetime(df.year.astype(int).astype(str) + '-' +
                                  df.yday.astype(int).astype(str), format="%Y-%j")
    except ValueError:
        print(txt)
        raise

    df.columns = [c.replace(' ', '') for c in df.columns]

    df['srad(l/day)'] = df['srad(W/m^2)'] * 2.06362996638

    vp = df['vp(Pa)'].values
    df['tdew(degc)'] = dewpoint(vp * units.Pa).magnitude

    # return dataframe
    return df


if __name__ == "__main__":
    from wepppy.climates.cligen import df_to_prn
    
    df = retrieve_historical_timeseries(-121.829585, 36.272184, 1980, 2021)
    print(len(df.index))
    print(df.keys())
    df_to_prn(df, '/home/roger/input.prn', 'prcp(mm/day)', 'tmax(degc)', 'tmin(degc)', julian_key='yday')

