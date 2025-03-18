import rasterio
import pyproj
from pyproj import Proj
import numpy as np
import pandas as pd

import os
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

import pandas as pd
import shutil

from wepppy.climates.daymet import retrieve_historical_timeseries as daymet_retrieve_historical_timeseries
from wepppy.climates.gridmet import retrieve_historical_timeseries as gridmet_retrieve_historical_timeseries
from wepppy.climates.prism.daily_client import retrieve_historical_timeseries as prism_retrieve_historical_timeseries


def mask_outliers(df, column):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

def mask_prn_file(fn1, fn2, fn3):
    """
    Merges weather data from two files, replacing specified mask values in the second file with data from the first.

    Parameters:
    - fn1 (str): Path to the first input file with original weather data.
    - fn2 (str): Path to the second input file where '9999' mask values are present.
    - fn3 (str): Path to the output file where the merged data will be written.

    Each line in the output file is formatted as follows:
    month day year prcp tmax tmin, ensuring data alignment through left-justification of each field within a 5-character width.

    Note:
    - It's assumed that '9999' is used exclusively as a placeholder for missing data in prcp, tmin, and tmax fields.
    - The function does not return any value.
    """

    data_fn1 = {}
    with open(fn1, 'r') as f1:
        for line in f1:
            parts = line.split()
            if len(parts) == 6:  # Ensure the line has the correct number of elements
                month, day, year, prcp, tmin, tmax = parts
                # Use a tuple of (month, day, year) as the dictionary key
                data_fn1[(month, day, year)] = (prcp, tmin, tmax)

    years = set()
    # Open fn3 for writing
    with open(fn3, 'w') as fp:
        # Loop over fn2 to check and replace data
        with open(fn2, 'r') as f2:
            for line in f2:
                parts = line.split()
                if len(parts) == 6:
                    month, day, year, prcp, tmin, tmax = parts
                    years.add(year)
                    # Check if the current date from fn2 exists in the data from fn1
                    if (month, day, year) in data_fn1:
                        # Get the corresponding data from fn1
                        prcp_fn1, tmin_fn1, tmax_fn1 = data_fn1[(month, day, year)]
                        # Replace '9999' (mask) fields with values from fn1
                        prcp = prcp if prcp != '9999' else prcp_fn1
                        tmin = tmin if tmin != '9999' else tmin_fn1
                        tmax = tmax if tmax != '9999' else tmax_fn1

                    # Write the processed data to fn3
                    fp.write("{0:<5}{1:<5}{2:<5}{3:<5}{4:<5}{5:<5}\r\n"
                             .format(month, day, year, prcp, tmax, tmin))

    return min(years), max(years)

def lng_lat_to_pixel_center(lng, lat, proj4, transform, width, height):
    # Create a projection object for the raster
    raster_proj = Proj(proj4)

    # Create a projection object for WGS84 (lat/long)
    wgs84_proj = Proj(proj='latlong', datum='WGS84')

    # Convert the input lng/lat to the raster's projection
    x, y = pyproj.transform(wgs84_proj, raster_proj, lng, lat)

    # Apply the affine transformation to get pixel coordinates
    # Note: Affine transform is in the form of (a, b, c, d, e, f)
    # where x' = a * x + b * y + c and y' = d * x + e * y + f
    a, b, c, d, e, f = transform
    col = (x - a) / b
    row = (y - d) / f

    # Get nearest pixel center
    col, row = round(col), round(row)

    # Check if the pixel is within the bounds of the raster
    if 0 <= col < width and 0 <= row < height:
        # Convert the pixel position back to geographic coordinates
        lng, lat = pyproj.transform(raster_proj, wgs84_proj, col * b + a, row * f + d)
        return lng, lat
    else:
        return None, None


def daymet_pixel_center(lng, lat):
    width, height = (7814, 8075)
    proj4 = '+proj=lcc +lat_1=25 +lat_2=60 +lat_0=42.5 +lon_0=-100 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs'
    transform = (-4560750.0, 1000.0, 0.0, 4984500.0, 0.0, -1000.0)

    return lng_lat_to_pixel_center(lng, lat, proj4, transform, width, height)


def gridmet_pixel_center(lng, lat):
    width, height = (1386, 585)
    proj4 = '+proj=longlat +datum=WGS84 +no_defs'
    transform = (-124.79299639760372, 0.04166601298087771, 0.0, 49.41685580390774, 0.0, -0.041666014553749395)

    return lng_lat_to_pixel_center(lng, lat, proj4, transform, width, height)


def prism4k_pixel_center(lng, lat):
    width, height = (1405, 621)
    proj4 = '+proj=longlat +datum=NAD83 +no_defs'
    transform = (-125.02083333333336, 0.0416666666667, 0.0, 49.93749999999975, 0.0, -0.0416666666667)

    return lng_lat_to_pixel_center(lng, lat, proj4, transform, width, height)


def nexrad_pixel_center(lng, lat):
    return round(lng * 4.0) / 4.0, round(lat * 4.0) / 4.0


def _test_pixel_centers():
    lng, lat = -97.0, 38.0  # Example longitude and latitude

    nearest_pixel_lng, nearest_pixel_lat = daymet_pixel_center(lng, lat)
    print(f"Nearest pixel center: Longitude = {nearest_pixel_lng}, Latitude = {nearest_pixel_lat}")

    nearest_pixel_lng, nearest_pixel_lat = gridmet_pixel_center(lng, lat)
    print(f"Nearest pixel center: Longitude = {nearest_pixel_lng}, Latitude = {nearest_pixel_lat}")

    nearest_pixel_lng, nearest_pixel_lat = prism4k_pixel_center(lng, lat)
    print(f"Nearest pixel center: Longitude = {nearest_pixel_lng}, Latitude = {nearest_pixel_lat}")


def mm_to_in(x):
    return np.array(x) / 25.4

def c_to_f(x):
    return np.array(x) * 9.0/5.0 +32.0


if __name__ == "__main__":
    import pandas as pd

    from wepppy.climates.cligen import (
        CligenStationsManager,
        ClimateFile,
        Cligen,
        df_to_prn
    )
    from wepppy.nodb.climate import (
        download_file,
        build_observed_daymet,
        build_observed_gridmet,
        build_observed_prism,
        build_observed_snotel
    )

    from wepppy.all_your_base.geo import RasterDatasetInterpolator

    from wepppyo3.climate import cli_revision as pyo3_cli_revision

    ppt_rdi = RasterDatasetInterpolator('/geodata/prism30yrmonthly/ppt/.vrt')
    tmin_rdi = RasterDatasetInterpolator('/geodata/prism30yrmonthly/tmin/.vrt')
    tmax_rdi = RasterDatasetInterpolator('/geodata/prism30yrmonthly/tmax/.vrt')

    prism_startyear = 1981
    prism_endyear = 2022

    daymet_startyear = 1980
    daymet_endyear = 2022

    gridmet_startyear = 1980
    gridmet_endyear = 2022

    station_mgr = CligenStationsManager()

    stations = pd.read_csv('24_us_stations.csv')
#   stations = pd.read_csv('willowfire_rainguage_locations.csv')

    for key, row in stations.iterrows():

        snotel_lat = row.lat
        snotel_lng = row.long

        snotel_id = f"{row.id}_{row.statename.replace(' ', '')}"


        print(snotel_id, snotel_lat, snotel_lng)


        if _exists(snotel_id):
            shutil.rmtree(snotel_id)
            os.makedirs(snotel_id)

        station_meta = station_mgr.get_closest_station((snotel_lng, snotel_lat))
        cligen = Cligen(station_meta, wd=snotel_id)

        print(f'station_meta: {station_meta}')

        print('  building nexrad')
        nexrad_lng, nexrad_lat = nexrad_pixel_center(snotel_lng, snotel_lat)
        print(nexrad_lng, nexrad_lat)
        nexrad_cli_fn = f'{snotel_id}_nexrad_v3.cli'

        url = f'https://mesonet-dep.agron.iastate.edu/dl/climatefile.py?lon={nexrad_lng}&lat={nexrad_lat}'
        if not _exists(_join(snotel_id, nexrad_cli_fn)):
            download_file(url, _join(snotel_id, nexrad_cli_fn))

        nexrad_ppt = mm_to_in(ppt_rdi.get_location_info(nexrad_lng, nexrad_lat))
        nexrad_tmin = c_to_f(tmin_rdi.get_location_info(nexrad_lng, nexrad_lat))
        nexrad_tmax = c_to_f(tmax_rdi.get_location_info(nexrad_lng, nexrad_lat))


        snotel_ppt = mm_to_in(ppt_rdi.get_location_info(snotel_lng, snotel_lat))
        snotel_tmin = tmin_rdi.get_location_info(snotel_lng, snotel_lat)
        snotel_tmin = c_to_f(snotel_tmin)
        snotel_tmax = tmax_rdi.get_location_info(snotel_lng, snotel_lat)
        snotel_tmax = c_to_f(snotel_tmax)

        pyo3_cli_revision(f'{snotel_id}/{nexrad_cli_fn}', f'{snotel_id}/{snotel_id}_nexrad_prismrev.cli',
                          nexrad_ppt, nexrad_tmax, nexrad_tmin,
                          snotel_ppt, snotel_tmax, snotel_tmin)

        nexrad_mode6_prn = f'{snotel_id}/{snotel_id}_nexrad_v3_mode6.prn'
        nexrad_mode6_cli = f'{snotel_id}/{snotel_id}_nexrad_v3_mode6.cli'

        cli = ClimateFile(_join(f'{snotel_id}', nexrad_cli_fn))
        df = cli.as_dataframe()
        df['prcp (mm)'] = df['prcp']
        df.rename(columns={'mo': 'month', 'da': 'day'}, inplace=True)
        df['date'] = pd.to_datetime(df[['year', 'month', 'day']])
        df.set_index('date', inplace=True)

        df_to_prn(df, nexrad_mode6_prn, 'prcp (mm)', 'tmax', 'tmin')
        cligen.run_observed(_split(nexrad_mode6_prn)[-1], 
                            cli_fn=_split(nexrad_mode6_cli)[-1])

        nexrad_ppt = mm_to_in(ppt_rdi.get_location_info(nexrad_lng, nexrad_lat))

        print('  building nexrad modified')
        nexrad_cli_path = _join(snotel_id, nexrad_cli_fn)

        cli = ClimateFile(nexrad_cli_path)
        years = cli.years
        start_year = min(years)
        end_year = max(years)

        nexrad_prismscaled_cli_fn = nexrad_cli_fn[:-4] + '.prismscaled.cli'
        if not _exists(_join(snotel_id, nexrad_prismscaled_cli_fn)):
            prism_ppt = mm_to_in(ppt_rdi.get_location_info(snotel_lng, snotel_lat))

            nexrad_monthlies = cli.calc_monthlies()['ppts']
            prcp_scale = np.array(prism_ppt) / np.array(nexrad_monthlies)
            print(prism_ppt)
            print(nexrad_monthlies)
            print(prcp_scale)

            cli.transform_precip(0, prcp_scale)
            cli.write(_join(snotel_id, nexrad_prismscaled_cli_fn))

        nexrad_prism_cli_fn = nexrad_cli_fn[:-4] + '.prism.cli'
        if not _exists(_join(snotel_id, nexrad_prism_cli_fn)):
            cli = ClimateFile(nexrad_cli_path)
            from wepppy.climates.prism.daily_client import retrieve_historical_timeseries
            df = retrieve_historical_timeseries(lng=nexrad_lng, lat=nexrad_lat, start_year=start_year, end_year=2023)

            dates = df.index
            cli.replace_var('tmax', dates, df['tmax(degc)'])
            cli.replace_var('tmin', dates, df['tmin(degc)'])
            cli.replace_var('tdew', dates, df['tdmean(degc)'])

            cli.write(_join(snotel_id, nexrad_prism_cli_fn))


        nexrad_gridmet_cli_fn = nexrad_cli_fn[:-4] + '.gridmet.cli'
        if not _exists(_join(snotel_id, nexrad_gridmet_cli_fn)):
            cli = ClimateFile(nexrad_cli_path)
            df = gridmet_retrieve_historical_timeseries(nexrad_lng, nexrad_lat, start_year, end_year)

            dates = df.index
            cli.replace_var('tmax', dates, df['tmmx(degc)'])
            cli.replace_var('tmin', dates, df['tmmn(degc)'])
            cli.replace_var('rad', dates, df['srad(l/day)'])
            cli.replace_var('tdew', dates, df['tdew(degc)'])
            cli.replace_var('w-vl', dates, df['vs(m/s)'])
            cli.replace_var('w-dir', dates, df['th(DegreesClockwisefromnorth)'])

            cli.write(_join(snotel_id, nexrad_gridmet_cli_fn))

        nexrad_daymet_cli_fn = nexrad_cli_fn[:-4] + '.daymet.cli'
        if not _exists(_join(snotel_id, nexrad_daymet_cli_fn)):
            cli = ClimateFile(nexrad_cli_path)
            df = daymet_retrieve_historical_timeseries(nexrad_lng, nexrad_lat, start_year, 2023)

            dates = df.index
            cli.replace_var('tmax', dates, df['tmax(degc)'])
            cli.replace_var('tmin', dates, df['tmin(degc)'])
            cli.replace_var('rad', dates, df['srad(l/day)'])
            cli.replace_var('tdew', dates, df['tdew(degc)'])

            cli.write(_join(snotel_id, nexrad_daymet_cli_fn))



        print('  building prism')
        prism_lng, prism_lat = prism4k_pixel_center(snotel_lng, snotel_lat)
        print(prism_lng, prism_lat)
        prism_prn_fn = f'{snotel_id}_prism.prn'
        prism_cli_fn = f'{snotel_id}_prism.cli'
        build_observed_prism(
            cligen, prism_lng, prism_lat, prism_startyear, prism_endyear, 
            snotel_id, prism_prn_fn, prism_cli_fn, gridmet_wind=True)

        prism_ppt = mm_to_in(ppt_rdi.get_location_info(prism_lng, prism_lat))
        prism_tmin = c_to_f(tmin_rdi.get_location_info(prism_lng, prism_lat))
        prism_tmax = c_to_f(tmax_rdi.get_location_info(prism_lng, prism_lat))

        pyo3_cli_revision(f'{snotel_id}/{snotel_id}_prism.cli', f'{snotel_id}/{snotel_id}_prism_prismrev.cli',
                          prism_ppt, prism_tmax, prism_tmin,
                          snotel_ppt, snotel_tmax, snotel_tmin)


        print('  building daymet')
        daymet_lng, daymet_lat = daymet_pixel_center(snotel_lng, snotel_lat)
        print(daymet_lng, daymet_lat)
        daymet_prn_fn = f'{snotel_id}_daymet.prn'
        daymet_cli_fn = f'{snotel_id}_daymet.cli'
        build_observed_daymet(cligen, daymet_lng, daymet_lat, daymet_startyear, daymet_endyear, snotel_id, daymet_prn_fn, daymet_cli_fn, gridmet_wind=True)

        daymet_ppt = mm_to_in(ppt_rdi.get_location_info(daymet_lng, daymet_lat))
        daymet_tmin = c_to_f(tmin_rdi.get_location_info(daymet_lng, daymet_lat))
        daymet_tmax = c_to_f(tmax_rdi.get_location_info(daymet_lng, daymet_lat))

        pyo3_cli_revision(f'{snotel_id}/{snotel_id}_daymet.cli', f'{snotel_id}/{snotel_id}_daymet_prismrev.cli',
                          daymet_ppt, daymet_tmax, daymet_tmin,
                          snotel_ppt, snotel_tmax, snotel_tmin)


        print('  building gridmet')
        gridmet_lng, gridmet_lat = gridmet_pixel_center(snotel_lng, snotel_lat)
        print(gridmet_lng, gridmet_lat)
        gridmet_prn_fn = f'{snotel_id}_gridmet.prn'
        gridmet_cli_fn = f'{snotel_id}_gridmet.cli'
        build_observed_gridmet(cligen, gridmet_lng, gridmet_lat, gridmet_startyear, gridmet_endyear, snotel_id, gridmet_prn_fn, gridmet_cli_fn)

        gridmet_ppt = mm_to_in(ppt_rdi.get_location_info(gridmet_lng, gridmet_lat))
        gridmet_tmin = c_to_f(tmin_rdi.get_location_info(gridmet_lng, gridmet_lat))
        gridmet_tmax = c_to_f(tmax_rdi.get_location_info(gridmet_lng, gridmet_lat))

        pyo3_cli_revision(f'{snotel_id}/{snotel_id}_gridmet.cli', f'{snotel_id}/{snotel_id}_gridmet_prismrev.cli',
                          gridmet_ppt, gridmet_tmax, gridmet_tmin,
                          snotel_ppt, snotel_tmax, snotel_tmin)
