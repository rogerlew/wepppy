import uuid

import requests
import shutil
from enum import Enum
import os
from os.path import join as _join
from os.path import exists, dirname

import numpy as np

import netCDF4

from concurrent.futures import ProcessPoolExecutor, as_completed

import datetime
import numpy as np
import pandas as pd
import requests

from calendar import isleap

from wepppy.all_your_base import SCRATCH, isint
from wepppy.all_your_base.geo import RasterDatasetInterpolator

from scipy.interpolate import RegularGridInterpolator

import pyproj
from pyproj import Proj

from metpy.calc import  dewpoint_from_relative_humidity
from metpy.units import units

from wepppyo3.climate import interpolate_geospatial

from wepppy.climates.cligen import df_to_prn

from wepppy.nodb.status_messenger import StatusMessenger



class GridMetVariable(Enum):
    Precipitation = 1
    MinimumTemperature = 2
    MaximumTemperature = 3
    SurfaceRadiation = 4
    PalmarDroughtSeverityIndex = 5
    PotentialEvapotranspiration = 6
    BurningIndex = 7
    WindDirection = 8
    WindSpeed = 9
    MinimumRelativeHumidity = 10
    MaximumRelativeHumidity = 11

# http://www.climatologylab.org/gridmet.html
# The variable names can be obtained by downloading the dataset for a year and looking at the attributes using HDFView


interpolation_spec = {
    'pr': {
        'method': 'cubic',
        'a_min': 0.0, # clip to 0.0
    },
    'tmmn':{
        'method': 'cubic',
    },
    'tmmx(degc)':{
        'method': 'cubic',
    },
    'rmin':{
        'method': 'cubic',
    },
    'rmax':{
        'method': 'cubic',
    },
    'srad':{
        'method': 'linear',
        'a_min': 0.0, # clip to 0.0
    },
    'srad':{
        'method': 'linear',
        'a_min': 0.0, # clip to 0.0
    },
    'vs':{
        'method': 'linear',
        'a_min': 0.0, # clip to 0.0
    },
    'th':{
        'method': 'nearest'
    }
}


_var_meta = {
    GridMetVariable.Precipitation: ('pr', 'precipitation_amount'),
    GridMetVariable.MinimumTemperature: ('tmmn', 'air_temperature'),
    GridMetVariable.MaximumTemperature: ('tmmx', 'air_temperature'),
    GridMetVariable.MinimumRelativeHumidity: ('rmin', 'relative_humidity'),
    GridMetVariable.MaximumRelativeHumidity: ('rmax', 'relative_humidity'),
    GridMetVariable.SurfaceRadiation: ('srad', 'surface_downwelling_shortwave_flux_in_air'),
    GridMetVariable.PalmarDroughtSeverityIndex: ('pdsi', 'palmer_drought_severity_index'),
    GridMetVariable.PotentialEvapotranspiration: ('pet', 'potential_evapotranspiration'),
    GridMetVariable.BurningIndex: ('bi', 'burning_index_g'),
    GridMetVariable.WindDirection: ('th', 'wind_from_direction'),
    GridMetVariable.WindSpeed: ('vs', 'wind_speed'),
}


def nc_extract(fn, locations):
    rds = RasterDatasetInterpolator(fn, proj='EPSG:4326')

    d = {}
    for key in locations:
        lng, lat = locations[key]
        data = rds.get_location_info(lng, lat, 'nearest')

        d[key] = data

    return d


def retrieve_nc(gridvariable: GridMetVariable, bbox, year, met_dir=None, _id=None):
    global _var_meta

    abbrv, variable_name = _var_meta[gridvariable]

    assert len(bbox) == 4
    west, north, east, south = [float(v) for v in bbox]
    assert east > west
    assert south < north

    url = 'http://thredds.northwestknowledge.net:8080/thredds/ncss/MET/{abbrv}/{abbrv}_{year}.nc?' \
          'var={variable_name}&' \
          'north={north}&west={west}&east={east}&south={south}&' \
          'disableProjSubset=on&horizStride=1&' \
          'time_start={year}-01-01T00%3A00%3A00Z&' \
          'time_end={year}-12-31T00%3A00%3A00Z&' \
          'timeStride=1&accept=netcdf'\
          .format(abbrv=abbrv, year=year, variable_name=variable_name, north=north, west=west, east=east, south=south)

    referer = 'https://wepp.cloud'
    s = requests.Session()
    response = s.get(url, headers={'referer': referer}, stream=True)
    if _id is None:
        _id = str(uuid.uuid4())+abbrv+str(year)
    if met_dir is None:
        met_dir = SCRATCH

    with open(_join(met_dir, '%s.nc' % _id), 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response

    return _id


def read_nc_longlat(fn):
    ds = netCDF4.Dataset(fn)
    longitudes = ds.variables['lon'][:]
    latitudes = ds.variables['lat'][:]
    return longitudes, latitudes


def read_nc(fn, gridvariable):
    abbrv, variable_name = _var_meta[gridvariable]
    ds = netCDF4.Dataset(fn)
    variable = ds.variables[variable_name]
    desc = variable.description
    units = variable.units
    scale_factor = getattr(variable, 'scale_factor', 1.0)
    add_offset = getattr(variable, 'add_offset', 0.0)

    ts = variable[:]

    ts = np.array(ts, dtype=np.float64)

#    ts *= scale_factor
#    ts += add_offset
    if 'K' == units:
        ts -= 273.15
        units = 'degc'

    # ts is dates, lats, longs
    return ts, abbrv, units.replace(' ', '')


def dump(abbrv, year, key, ts, desc, units, met_dir):
    fn = _join(met_dir, key, '%s_%s.npy' % (abbrv, str(year)))
    os.makedirs(dirname(fn), exist_ok=True)

    with open(fn, 'wb') as fp:
        np.save(fp, ts)


def retrieve_timeseries(variables, locations, start_year, end_year, met_dir):
    global _var_meta

    lons = [loc[0] for loc in locations.values()]
    lats = [loc[1] for loc in locations.values()]

    ll_x, ll_y = min(lons), min(lats)
    ur_x, ur_y = max(lons), max(lats)

    if len(locations) == 1:
        ll_x -= 0.04
        ll_y -= 0.04
        ur_x += 0.04
        ur_y += 0.04

    bbox = [ll_x, ur_y, ur_x, ll_y]

    start_year = int(start_year)
    end_year = int(end_year)

    assert start_year <= end_year

    for gridvariable in variables:
        for year in range(start_year, end_year + 1):
            id = retrieve_nc(gridvariable, bbox, year)
            fn = _join(SCRATCH, '%s.nc' % id)

            try:
                _d = nc_extract(fn, locations)

                abbrv, variable_name = _var_meta[gridvariable]
                ds = netCDF4.Dataset(fn)
                variable = ds.variables[variable_name]
                desc = variable.description
                units = variable.units
                scale_factor = getattr(variable, 'scale_factor', 1.0)
                add_offset = getattr(variable, 'add_offset', 0.0)

                if _d is not None:
                    for key, ts in _d.items():
                        ts = np.array(ts, dtype=np.float64)
#                        ts *= scale_factor
#                        ts += add_offset
                        if 'K' == units:
                            ts -= 273.15
                            units = 'degc'

                        # print(desc, ts)

                        dump(abbrv, year, key, ts, desc, units, met_dir)
                        #ts = [int(x) for x in ts]
                        #d['{}-{}-{}'.format(abbrv, year, key)] = (ts, desc, units)

                os.remove(fn)
            except:
                os.remove(fn)
                raise
    #return d


def interpolate_daily_timeseries_for_location(topaz_id, loc, dates, 
                                              longitudes, latitudes, raw_data, interpolation_spec, output_dir, 
                                              start_year, end_year, output_type='prn parquet'):

    df = pd.DataFrame(index=dates)
    hillslope_lng = loc['longitude']
    hillslope_lat = loc['latitude']
    npts = len(dates)

    for measure, spec in interpolation_spec.items():
        
        a_min = spec.get('a_min', None)

        values = interpolate_geospatial(
            hillslope_lng, hillslope_lat, longitudes, latitudes, raw_data[measure], spec['method'], a_min=a_min)

        df[measure] = values

 
    df['srad(l/day)'] = df['srad(Wm-2)'] * 2.06362996638
    
    df['tavg(degc)'] = (df['tmmx(degc)'] + df['tmmn(degc)']) / 2
    df['vs(m/s)'] = pd.Series(df['vs(m/s)']).astype(float)
    df['th(DegreesClockwisefromnorth)'] = pd.Series(df['th(DegreesClockwisefromnorth)']).astype(float)
    df['rmax(%)'] = pd.Series(df['rmax(%)']).astype(float)
    df['rmin(%)'] = pd.Series(df['rmin(%)']).astype(float)
    df['ravg(%)'] = (df['rmax(%)'] + df['rmin(%)']) / 2
    df['tdew(degc)'] = dewpoint_from_relative_humidity(df['tavg(degc)'].values * units.degC,
                                                       df['ravg(%)'].values * units.percent).magnitude
    df['tdew(degc)'] = np.clip(df['tdew(degc)'], df['tmmn(degc)'], None)


    if 'parquet' in output_type:
        df.to_parquet(_join(output_dir, f'gridmet_observed_{topaz_id}_{start_year}-{end_year}.parquet'))

    if 'prn' in output_type:
        df_to_prn(df, _join(output_dir, f'gridmet_observed_{topaz_id}_{start_year}-{end_year}.prn'), 
                    'pr(mm)', 'tmmx(degc)', 'tmmn(degc)')
    
    return topaz_id



if __name__ == "__main__":
    locations = {'666': [-116.92849537373276, 46.80427719462155]}
    variables = [GridMetVariable.Precipitation, GridMetVariable.MinimumTemperature, GridMetVariable.MaximumTemperature, GridMetVariable.WindSpeed, GridMetVariable.WindDirection]
    gridmet_dir = '/home/roger/Downloads'
    year = 1981
    retrieve_timeseries(variables, locations, year, year, gridmet_dir)

    for var in ['pr', 'tmmn', 'tmmx', 'th', 'vs']:
        fn = _join(gridmet_dir, '666', '%s_%s.npy' % (var, str(year)))
        assert exists(fn)
        print(var, [float(x) for x in list(np.load(fn))])
