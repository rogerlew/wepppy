"""High-throughput Daymet extraction for a single lat/lon coordinate."""

from __future__ import annotations

from glob import glob
from os.path import join as _join
from os.path import split as _split

from wepppy.all_your_base.geo import GeoTransformer, wgs84_proj4

import xarray as xr
import numpy as np
import pandas as pd

from calendar import isleap

from multiprocessing import Pool


# access over nas is slower than retrieving using daymet api

daymet_proj4 = '+proj=lcc +lat_1=25 +lat_2=60 +lat_0=42.5 +lon_0=-100 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs'


def single_point_extraction(
    lon: float,
    lat: float,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """Retrieve precipitation and temperature series for a single point.

    Args:
        lon: Longitude in decimal degrees.
        lat: Latitude in decimal degrees.
        start_year: First year to extract from the Daymet archive.
        end_year: Final year to extract.

    Returns:
        DataFrame combining precipitation, max temp, and min temp columns.
    """
    _wgs_2_lcc = GeoTransformer(src_proj4=wgs84_proj4, dst_proj4=daymet_proj4)

    x, y = _wgs_2_lcc.transform(lon, lat)

    df = pd.DataFrame()
    for dataset, units in (('prcp', 'mm/day'), ('tmax', 'degc'), ('tmin', 'degc')):
        df[f'{dataset}({units})'] = extract_variable(x, y, dataset, start_year, end_year)

    df['dates'] = pd.date_range(start=f'{start_year}-01-01', end=f'{end_year}-12-31')

    return df

def extract_variable(x: float, y: float, dataset: str, start_year: int, end_year: int) -> np.ndarray:
    """Extract one Daymet variable at the provided projected coordinate.

    Returns:
        Stitched array covering every requested year (366 entries for leaps).
    """

    all_ts = []
    for yr in range(start_year, end_year + 1):
        fname = f'/geodata/daymet/v4/{dataset}/daymet_v4_daily_na_{dataset}_{yr}.nc'

        ds = xr.open_dataset(fname)
        data = ds.sel(x=x, y=y, method='nearest')

        ts = data[dataset].values
        if isleap(yr):
            ts = np.append(ts, ts[-1])

        all_ts.append(ts)

    return np.concatenate(all_ts)
