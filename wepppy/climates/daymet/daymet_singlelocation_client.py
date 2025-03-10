# Copyright (c) 2016-2023, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import time
import io
from os.path import join as _join
from concurrent.futures import ProcessPoolExecutor, as_completed

import datetime
import numpy as np
import pandas as pd
import requests

from calendar import isleap

from wepppy.all_your_base import isint

from scipy.interpolate import RegularGridInterpolator

import pyproj
from pyproj import Proj

from metpy.calc import dewpoint
from metpy.units import units

from wepppyo3.climate import interpolate_geospatial

from wepppy.climates.cligen import df_to_prn

from wepppy.nodb.status_messenger import StatusMessenger


def retrieve_historical_timeseries(lon, lat, start_year, end_year, fill_leap_years=True, gridmet_wind=False):
    assert isint(start_year)
    assert isint(end_year)

    start_year = int(start_year)
    end_year = int(end_year)

    years = ','.join(str(v) for v in range(start_year, end_year+1))

    assert start_year <= end_year
    assert 1980 <= start_year <= int(time.strftime("%Y"))-1, start_year
    assert 1980 <= end_year <= int(time.strftime("%Y"))-1, end_year

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

        skip = 0
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

        new_rows = []
        for yr in leap_years:
            condition = (df['year'] == yr) & (df['yday'] == 365)
            if condition.any():
                index = df.loc[condition].index[0]
                new_row = df.loc[index].copy()
                new_row['yday'] = 366
                new_rows.append(new_row)

        if new_rows:
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

        df = df.sort_values(by=['year', 'yday'], ascending=True).reset_index(drop=True)

    try:
        df.index = pd.to_datetime(df.year.astype(int).astype(str) + '-' +
                                  df.yday.astype(int).astype(str), format="%Y-%j")
    except ValueError:
        print(txt)
        raise

    if gridmet_wind:
        from wepppy.climates.gridmet import retrieve_historical_wind as gridmet_retrieve_historical_wind
        wind_df = gridmet_retrieve_historical_wind(lon, lat, start_year, end_year)

        df['vs(m/s)'] = wind_df['vs(m/s)']
        df['th(DegreesClockwisefromnorth)'] = wind_df['th(DegreesClockwisefromnorth)']

    df.columns = [c.replace(' ', '') for c in df.columns]

    # swat uses W/m^2
    # daymet uses J/m^2
    # wepp uses langley/day
    df['srad(J/m^2)'] = df['srad(W/m^2)'] * df['dayl(s)']
    df['srad(l/day)'] = df['srad(J/m^2)']/(3600*24) # langley is Wh/m^2

    vp = df['vp(Pa)'].values
    df['tdew(degc)'] = dewpoint(vp * units.Pa).magnitude
    df['tdew(degc)'] = np.clip(df['tdew(degc)'], df['tmin(degc)'], None)

    # return dataframe
    return df



def _retrieve_historical_timeseries_wrapper(lon, lat, start_year, end_year, fill_leap_years=True, gridmet_wind=False, attrs=None):
    df = retrieve_historical_timeseries(lon, lat, start_year, end_year, fill_leap_years=fill_leap_years, gridmet_wind=gridmet_wind)
    return attrs, df



def interpolate_daily_timeseries(
    hillslope_locations,
    start_year=2018,
    end_year=2020,
    output_dir='test',
    output_type='prn parquet',
    status_channel=None):

    debug = 1
    gridmet_wind = False


    interpolation_spec = {
        'prcp(mm/day)': {
            'method': 'cubic',
            'a_min': 0.0, # clip to 0.0
        },
        'tmax(degc)':{
            'method': 'cubic',
        },
        'tmin(degc)':{
            'method': 'cubic',
        },
        'tdew(degc)':{
            'method': 'cubic',
        },
        'srad(l/day)':{
            'method': 'linear',
            'a_min': 0.0, # clip to 0.0
        }
    }

    if gridmet_wind:
        interpolation_spec.update({
            'vs(m/s)':{
                'method': 'linear',
                'a_min': 0.0, # clip to 0.0
            },
            'th(DegreesClockwisefromnorth)':{
                'method': 'nearest'
            }
        })

    # Convert all hillslope locations to easting and northing
    proj4 = '+proj=lcc +lat_1=25 +lat_2=60 +lat_0=42.5 +lon_0=-100 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs'
    raster_proj = Proj(proj4)
    wgs84_proj = Proj(proj='latlong', datum='WGS84')

    for topaz_id, loc in hillslope_locations.items():
        hill_easting, hill_northing = pyproj.transform(wgs84_proj, raster_proj, loc['longitude'], loc['latitude'])
        hillslope_locations[topaz_id]['easting'] = hill_easting
        hillslope_locations[topaz_id]['northing'] = hill_northing

    # Calculate projected extent from easting and northing
    eastings_hills = [loc['easting'] for loc in hillslope_locations.values()]
    northings_hills = [loc['northing'] for loc in hillslope_locations.values()]
    min_easting = np.min(eastings_hills)
    max_easting = np.max(eastings_hills)
    min_northing = np.min(northings_hills)
    max_northing = np.max(northings_hills)

    if status_channel is not None:
        StatusMessenger.publish(status_channel, f'  identified extent in lcc [{min_easting}, {min_northing}, {max_easting}, {max_northing}]\n')

    ur_e = max_easting
    ur_n = max_northing
    ll_e = min_easting
    ll_n = min_northing

    # Define projection parameters
    a, b, d, f = -4560750.0, 1000.0, 4984500.0, -1000.0

    # Calculate pixel indices for the projected extent
    ur_px = round((ur_e - a) / b)
    ur_py = round((ur_n - d) / f)
    ll_px = round((ll_e - a) / b)
    ll_py = round((ll_n - d) / f)

    # Apply padding
    pad = 3
    cols = range(ll_px - pad, ur_px + pad + 1)
    rows = range(ur_py - pad, ll_py + pad + 1)

    # Generate grid eastings and northings
    eastings = np.array([a + col * b for col in cols])
    northings = np.array([d + row * f for row in rows][::-1])

    if debug:
        # Validate all hillslope locations are within the grid
        for topaz_id, loc in hillslope_locations.items():
            assert (loc['easting'] >= eastings[0] and loc['easting'] <= eastings[-1]), \
                f"Easting {loc['easting']} out of grid range [{eastings[0]}, {eastings[-1]}]"
            assert (loc['northing'] <= northings[-1] and loc['northing'] >= northings[0]), \
                f"Northing {loc['northing']} out of grid range [{northings[-1]}, {northings[0]}]"

    pixel_locations = {}
    for i, col in enumerate(cols):
        for j, row in enumerate(rows):
            lng, lat = pyproj.transform(raster_proj, wgs84_proj, eastings[i], northings[j])
            pixel_locations[col, row] = lng, lat

    px0 = ll_px - 2
    py0 = ur_py - 2
    nrows = len(northings)
    ncols = len(eastings)
    ndays = (datetime.date(end_year, 12, 31) - datetime.date(start_year, 1, 1)).days + 1

    if status_channel is not None:
        StatusMessenger.publish(status_channel, f'  acquiring daymet for grid with shape ({ncols}, {nrows}, {ndays}) and pixel origin ({px0}, {py0})\n')

    # think this should be a dictionary of np.array with shape, ncols, nrows, ndates
    # need to determine dates using start_year and end_year parameter
    raw_data = {measure: np.zeros((ncols, nrows, ndays))
                for measure in interpolation_spec.keys()}
    
    with ProcessPoolExecutor(max_workers=12) as executor:
        futures = []

        for (col, row), (lng, lat) in pixel_locations.items():
            if status_channel is not None:
                StatusMessenger.publish(status_channel, f'  fetching daymet timeseries for pixel coordinate ({col}, {row})...\n')
            futures.append(
                executor.submit(
                    _retrieve_historical_timeseries_wrapper, 
                    lng, lat, start_year, end_year, gridmet_wind=gridmet_wind, attrs=(col, row)))
            
        for future in as_completed(futures):
            (col, row), df = future.result(timeout=3600)

            if debug:
                df.to_parquet(_join(output_dir, f'daymet_observed_{col},{row}_{start_year}-{end_year}.parquet'))

            for measure in raw_data.keys():
                raw_data[measure][col - px0, row - py0, :] = df[measure].values

            if status_channel is not None:
                StatusMessenger.publish(status_channel, f'  obtained data for pixel coordinate ({col}, {row}).\n')


    dates = pd.date_range(start=f'{start_year}-01-01', end=f'{end_year}-12-31')


    with ProcessPoolExecutor(max_workers=28) as executor:
        futures = []

        for topaz_id, loc in hillslope_locations.items():
            if status_channel is not None:
                StatusMessenger.publish(status_channel, f'  interpolating topaz_id {topaz_id}...\n')
                
            # this interpolates the 3d grid using rust pyo3 and builds prn to be used by cligen
            futures.append(
                executor.submit(interpolate_daily_timeseries_for_location, 
                                topaz_id, loc, dates, 
                                eastings, northings, raw_data, interpolation_spec, 
                                output_dir, start_year, end_year))

        for future in as_completed(futures):
            topaz_id = future.result(timeout=3600)

            if status_channel is not None:
                StatusMessenger.publish(status_channel, f'  interpolating topaz_id {topaz_id}... done.\n')


def interpolate_daily_timeseries_for_location(topaz_id, loc, dates, 
                                              eastings, northings, raw_data, interpolation_spec, output_dir, 
                                              start_year, end_year, output_type='prn parquet'):

    df = pd.DataFrame(index=dates)
    hillslope_easting = loc['easting']
    hillslope_northing = loc['northing']
    npts = len(dates)

    for measure, spec in interpolation_spec.items():
        
        a_min = spec.get('a_min', None)

        values = interpolate_geospatial(
            hillslope_easting, hillslope_northing, eastings, northings, raw_data[measure], spec['method'], a_min=a_min)

        df[measure] = values

    if 'parquet' in output_type:
        df.to_parquet(_join(output_dir, f'daymet_observed_{topaz_id}_{start_year}-{end_year}.parquet'))

    if 'prn' in output_type:
        df_to_prn(df, _join(output_dir, f'daymet_observed_{topaz_id}_{start_year}-{end_year}.prn'), 
                    'prcp(mm/day)', 'tmax(degc)', 'tmin(degc)')
    
    return topaz_id


if __name__ == "__main__":

    hillslope_locations = {
        "22": {"longitude": -116.323476283, "latitude": 46.534344},
        "23":  {"longitude": -116.623476283, "latitude": 46.634344},
    }

    interpolate_daily_timeseries(hillslope_locations)

    import sys
    sys.exit()

    from wepppy.climates.cligen import df_to_prn
    
    df = retrieve_historical_timeseries(-121.829585, 36.272184, 2022, 2023)
    print(len(df.index))
    print(df.keys())
