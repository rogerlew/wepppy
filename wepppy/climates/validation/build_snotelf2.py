import rasterio
import pyproj
from pyproj import Proj
import numpy as np
import pandas as pd

import os
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

from wepppy.climates.cligen import Prn
from wepppy.climates.daymet import retrieve_historical_timeseries as daymet_retrieve_historical_timeseries
from wepppy.climates.gridmet import retrieve_historical_timeseries as gridmet_retrieve_historical_timeseries
from wepppy.climates.prism.daily_client import retrieve_historical_timeseries as prism_retrieve_historical_timeseries


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

    stations = pd.read_csv('snotel_locations.csv')

    for key, row in stations.iterrows():

        snotel_lat = row.lat
        snotel_lng = row.long
        snotel_id = row.SNTL_stations

        print(snotel_id)

        os.makedirs(snotel_id, exist_ok=True)

        snotel_prn_fn = f'{snotel_id}/{snotel_id}_snotel.prn'
        snotel_cli_fn = f'{snotel_id}/{snotel_id}_snotel.cli'

        snotel_ppt = mm_to_in(ppt_rdi.get_location_info(snotel_lng, snotel_lat))
        snotel_tmin = c_to_f(tmin_rdi.get_location_info(snotel_lng, snotel_lat))
        snotel_tmax = c_to_f(tmax_rdi.get_location_info(snotel_lng, snotel_lat))

        station_meta = station_mgr.get_closest_station((snotel_lng, snotel_lat))
        cligen = Cligen(station_meta, wd=snotel_id)

        print(f'station_meta: {station_meta}')

        if not _exists(snotel_cli_fn):
            print('  building snotel')
            build_observed_snotel(
                cligen, snotel_lng, snotel_lat, snotel_id,
                daymet_startyear, daymet_endyear, snotel_id, snotel_prn_fn, snotel_cli_fn)


        gridmet_prn_fn = f'{snotel_id}/{snotel_id}_gridmet.prn'
        gridmet_cli_fn = f'{snotel_id}/{snotel_id}_gridmet.cli'

        if not _exists(gridmet_cli_fn):
            print('  building gridmet')
            gridmet_lng, gridmet_lat = gridmet_pixel_center(snotel_lng, snotel_lat)
            print(gridmet_lng, gridmet_lat)
            build_observed_gridmet(cligen, gridmet_lng, gridmet_lat, gridmet_startyear, gridmet_endyear, snotel_id, gridmet_prn_fn, gridmet_cli_fn)

        gridmet_prismrev_cli_fn = f'{snotel_id}/{snotel_id}_gridmet_prismrev.cli'
        if not _exists(gridmet_prismrev_cli_fn):
            gridmet_ppt = mm_to_in(ppt_rdi.get_location_info(gridmet_lng, gridmet_lat))
            gridmet_tmin = c_to_f(tmin_rdi.get_location_info(gridmet_lng, gridmet_lat))
            gridmet_tmax = c_to_f(tmax_rdi.get_location_info(gridmet_lng, gridmet_lat))

            pyo3_cli_revision(gridmet_cli_fn, gridmet_prismrev_cli_fn,
                              gridmet_ppt, gridmet_tmax, gridmet_tmin,
                              snotel_ppt, snotel_tmax, snotel_tmin)

        snotel_prn = Prn(snotel_prn_fn)
        gridmet_prn = Prn(gridmet_prn_fn)


        snotelf2_prn = f'{snotel_id}_snotelf2.prn'
        snotelf2_cli = f'{snotel_id}_snotelf2.cli'
        snotel_prn.replace_outliers(gridmet_prn)
        snotel_prn.write(_join(snotel_id, snotelf2_prn))
        cligen.run_observed(snotelf2_prn, snotelf2_cli)


