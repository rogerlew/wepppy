import os
import requests
import gzip
import io
import pandas as pd
from matplotlib import pyplot as plt

from os.path import join as _join
from os.path import exists as _exists
from subprocess import Popen, PIPE

from wepppy.all_your_base import isint, IS_WINDOWS

_thisdir = os.path.dirname(__file__)

stations_catalog = None

def read_stations_catalog():
    with open(os.path.join(_thisdir, 'ghcnd-stations.txt')) as f:
        lines = f.readlines()

    # ghcn_id      lat       lon      elev        desc                        gsn (optional)    hcn (optional)   
    # ROM00015085  47.1500   24.5000  367.0    BISTRITA  XXX                  GSN     15085

    stations = {}
    # split based on character counts
    for line in lines:
        _line = line.split()
        ghcn_id = _line[0]
        lat = float(_line[1])
        lon = float(_line[2])
        elev = float(_line[3])
        desc = ' '.join(_line[4:])
        stations[ghcn_id] = dict(ghcn_id=ghcn_id, lat=lat, lon=lon, elev=elev, desc=desc)

    return stations

def find_ghcn_id(cligen_station_meta):
    cligen_station_id = cligen_station_meta.id

    global stations_catalog

    if stations_catalog is None:
        stations_catalog = read_stations_catalog()

    upper_id = cligen_station_id.upper()

    for ghcn_id, station in stations_catalog.items():
        if ghcn_id.upper() == upper_id:
            return station
        
    # compare just number portion of the id
    number_id = ''.join([c for c in cligen_station_id if c in '0123456789'])

    matches = []
    for ghcn_id, station in stations_catalog.items():
        if number_id in ghcn_id:
            matches.append(station)

    if len(matches) == 1:
        return matches[0]
    
    elif len(matches) == 0:
        raise ValueError(f"Could not find a unique match for station id {cligen_station_id}")
    
    cligen_station_desc = cligen_station_meta.desc

    # compare description to matches and return closest match
    best_match = None
    best_score = 0
    for match in matches:
        score = 0
        for word in cligen_station_desc.split():
            if word in match['desc']:
                score += 1

        if score > best_score:
            best_score = score
            best_match = match

    if best_match is None:
        raise ValueError(f"Could not find a unique match for station id {cligen_station_id}")
    
    return best_match


def try_parse_float(x):
    try:
        return float(x)
    except ValueError:
        return None
    
def acquire_ghcn_daily_data(ghcn_id: dict):
    url = f"https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/by_station/{ghcn_id['ghcn_id']}.csv.gz"

    r = requests.get(url)
    r.raise_for_status()

    # unpack the .gz archive
    with gzip.open(io.BytesIO(r.content)) as f:
        lines = f.read().decode('utf-8').split('\n')

    d = {'TMIN':{}, 'TMAX':{}, 'PRCP':{}}

    for line in lines:
        line = line.split(',')
        try:
            element = line[2]
            date = int(line[1])
            value = try_parse_float(line[3])
        except:
            continue

        if value is None:
            continue

        if element in ['TMIN', 'TMAX', 'PRCP']:
            value /= 10.0 # convert to C, mm
            d[element][date] = value

    # find start and end date
    try:
        start_date = min(min(d['TMIN']), min(d['TMAX']), min(d['PRCP']))
    except ValueError:
        return None
        
    end_date = max(max(d['TMIN']), max(d['TMAX']), max(d['PRCP']))

    # build a dataframe
    dates = pd.date_range(start=pd.to_datetime(str(start_date), format='%Y%m%d'),
                          end=pd.to_datetime(str(end_date), format='%Y%m%d'))
    
    df = pd.DataFrame(index=dates)
    df['TMIN (C)'] = [d['TMIN'].get(int(date.strftime('%Y%m%d')), None) for date in dates]
    df['TMAX (C)'] = [d['TMAX'].get(int(date.strftime('%Y%m%d')), None) for date in dates]
    df['PRCP (mm)'] = [d['PRCP'].get(int(date.strftime('%Y%m%d')), None) for date in dates]
    df['valid'] = df['TMIN (C)'].notnull() & df['TMAX (C)'].notnull() & df['PRCP (mm)'].notnull()

    #print(df.info())

    return df


