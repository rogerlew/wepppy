import pandas as pd
import numpy as np
from calendar import isleap
from collections import defaultdict
from concurrent.futures import wait, FIRST_COMPLETED
import os
from os.path import join as _join
from os.path import exists as _exists
import logging

from metpy.calc import dewpoint
from metpy.units import units

from osgeo import gdalconst

from osgeo import gdal, gdalconst, osr
from osgeo.gdal_array import BandRasterIONumPy
from osgeo_utils.auxiliary.array_util import ArrayLike, ArrayOrScalarLike
from osgeo_utils.auxiliary.base import is_path_like
from osgeo_utils.auxiliary.gdal_argparse import GDALArgumentParser, GDALScript
from osgeo_utils.auxiliary.numpy_util import GDALTypeCodeAndNumericTypeCodeFromDataSet
from osgeo_utils.auxiliary.osr_util import (
    OAMS_AXIS_ORDER,
    AnySRS,
    get_axis_order_from_gis_order,
    get_srs,
    get_transform,
    transform_points,
)
from osgeo_utils.auxiliary.util import (
    PathOrDS,
    get_band_nums,
    get_bands,
    get_scales_and_offsets,
    open_ds,
)

from wepppy.climates.cligen import (
    CligenStationsManager, 
    ClimateFile, 
    Cligen,
    df_to_prn
)

from wepppy.all_your_base.geo.gdallocationinfo import (
    gdallocationinfo_util, 
    LocationInfoOutput, 
    LocationInfoSRS
)

from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.nodb.base import createProcessPoolExecutor

_logger = logging.getLogger(__name__)

from pprint import pprint


def process_measure(year, measure, hillslope_locations, daymet_version='v4'):

    if daymet_version == 'v4':
        daymet_dir = '/geodata/daymet/v4'
        dataset_fn = _join(daymet_dir, measure, f'daymet_v4_daily_na_{measure}_{year}.nc')
    elif daymet_version == 'v3':
        daymet_dir = '/geodata/daymet'
        dataset_fn = _join(daymet_dir, measure, f'daymet_v3_{measure}_{year}_na.nc4')

    x = np.array([loc['pixel_q'] for loc in hillslope_locations.values()])
    y = np.array([loc['line_q'] for loc in hillslope_locations.values()])

    result = gdallocationinfo_util(
        f'NETCDF:"{dataset_fn}":{measure}', 
        x, y, 
        resample_alg=gdalconst.GRIORA_Cubic, 
        output_mode=LocationInfoOutput.Quiet,
        allow_xy_outside_extent=True, 
        ovr_idx=None, 
        axis_order=0)
    
    # handle leap years
    if isleap(year) and result.shape[0] == 365:
        result = np.vstack((result, result[-1, :]))

    dfs = {}
    for idx, topaz_id in enumerate(hillslope_locations):
        dfs[topaz_id] = dict(year=year, measure=measure, data=pd.Series(result[:, idx]))
    return dfs
    

def interpolate_daily_timeseries(
    hillslope_locations,
    start_year=2018,
    end_year=2020,
    output_dir='test',
    output_type='prn parquet',
    status_channel=None,
    max_workers=28):

    os.makedirs(output_dir, exist_ok=True)

    years = list(range(start_year, end_year + 1))

    measures = ['prcp', 'tmin', 'tmax']

    if 'parquet' in output_type:
        measures.extend(['srad', 'vp', 'dayl'])
    
    # 12 workers 91 seconds
    # 20 workers 80 seconds
    # 24 workers 77 seconds
    # 30 workers 74 seconds
    # 36 workers 79 seconds
    # 56 workers 131 seconds
    with createProcessPoolExecutor(max_workers=max_workers, logger=_logger) as executor:
        futures = []

        for measure in measures:
            for year in years:
                if status_channel is not None:
                    StatusMessenger.publish(status_channel, f'  processing {measure} for {year}...')
                futures.append(executor.submit(process_measure, year, measure, hillslope_locations))

        aggregated = defaultdict(lambda: defaultdict(dict))
        pending = set(futures)

        while pending:
            done, pending = wait(pending, timeout=60, return_when=FIRST_COMPLETED)

            if not done:
                if status_channel is not None:
                    StatusMessenger.publish(status_channel, '  waiting on Daymet measure processing...')
                _logger.warning('Daymet measure processing still running after 60 seconds; continuing to wait.')
                continue

            for future in done:
                try:
                    yearly_data = future.result()
                except Exception:
                    for remaining in pending:
                        remaining.cancel()
                    raise

                for topaz_id, d in yearly_data.items():
                    year = d['year']
                    measure = d['measure']
                    data = d['data']

                    if status_channel is not None:
                        StatusMessenger.publish(status_channel, f'  collecting {topaz_id}: {measure} for {year}...')

                    aggregated[topaz_id][measure][year] = data


    for topaz_id in hillslope_locations:

        if status_channel is not None:
            StatusMessenger.publish(status_channel, f'  compiling {topaz_id} for {start_year}-{end_year}...')
            
        df = pd.DataFrame()

        _start_date = pd.to_datetime(f'{start_year}0101', format='%Y%m%d')
        _end_date = pd.to_datetime(f'{end_year}1231', format='%Y%m%d')
        df.index = pd.date_range(start=_start_date, end=_end_date)
    
        for measure in measures:
            series = pd.concat([aggregated[topaz_id][measure][year] for year in years], ignore_index=True)
            if measure == 'prcp':
                series = series.clip(lower=0.0)
            df[measure] = pd.Series(series.values, index=df.index)
            
        df = df.rename(columns={
            "prcp": "prcp(mm/day)",
            "tmax": "tmax(degc)",
            "tmin": "tmin(degc)",
            "srad": "srad(W/m^2)",
            "dayl": "dayl(s)",
            "vp": "vp(Pa)"
        })

        if 'parquet' in output_type:
            # swat uses W/m^2
            # daymet uses J/m^2
            # wepp uses langley/day
            df['srad(J/m^2)'] = df['srad(W/m^2)'] * df['dayl(s)']
            df['srad(l/day)'] = df['srad(J/m^2)']/(3600*24) # langley is Wh/m^2

            vp = df['vp(Pa)'].values
            df['tdew(degc)'] = dewpoint(vp * units.Pa).magnitude
            df['tdew(degc)'] = np.clip(df['tdew(degc)'], df['tmin(degc)'], None)

            df.to_parquet(_join(output_dir, f'daymet_observed_{topaz_id}_{start_year}-{end_year}.parquet'))

        if 'prn' in output_type:
            df_to_prn(df, _join(output_dir, f'daymet_observed_{topaz_id}_{start_year}-{end_year}.prn'), 
                      'prcp(mm/day)', 'tmax(degc)', 'tmin(degc)')


def identify_pixel_coords(hillslope_locations, srs=4326, daymet_version='v4'):
    # copied this out of gdallocationinfo.py to avoid having to do this for every file.
    
    axis_order=0
    ovr_idx=None
    inline_xy_replacement=False

    x = np.array([d['longitude'] for d in hillslope_locations.values()])
    y = np.array([d['latitude'] for d in hillslope_locations.values()])

    if daymet_version == 'v4':
        daymet_dir = '/geodata/daymet/v4'
        filename_or_ds = _join(daymet_dir, 'prcp', 'daymet_v4_daily_na_prcp_2020.nc')
    elif daymet_version == 'v3':
        daymet_dir = '/geodata/daymet'
        filename_or_ds = _join(daymet_dir, 'prcp', 'daymet_v3_prcp_2020_na.nc4')

    ds = open_ds(filename_or_ds, open_options=None)
    filename = filename_or_ds if is_path_like(filename_or_ds) else ""
    if ds is None:
        raise Exception(f"Could not open {filename}.")
    if not isinstance(x, ArrayLike.__args__):
        x = [x]
    if not isinstance(y, ArrayLike.__args__):
        y = [y]
    if len(x) != len(y):
        raise Exception(f"len(x)={len(x)} should be the same as len(y)={len(y)}")
    point_count = len(x)

    dtype = np.float64
    if not isinstance(x, np.ndarray) or not isinstance(y, np.ndarray):
        x = np.array(x, dtype=dtype)
        y = np.array(y, dtype=dtype)
        inline_xy_replacement = True

    if srs is None:
        srs = LocationInfoSRS.PixelLine

    # Build Spatial Reference object based on coordinate system, fetched from the opened dataset
    if srs != LocationInfoSRS.PixelLine:
        if srs != LocationInfoSRS.SameAsDS_SRS:
            ds_srs = ds.GetSpatialRef()
            ct = None
            if isinstance(srs, osr.CoordinateTransformation):
                ct = srs
            else:
                if srs == LocationInfoSRS.SameAsDS_SRS_GeogCS:
                    points_srs = ds_srs.CloneGeogCS()
                else:
                    points_srs = get_srs(srs, axis_order=axis_order)
                ct = get_transform(points_srs, ds_srs)
            if ct is not None:
                if not inline_xy_replacement:
                    x = x.copy()
                    y = y.copy()
                    inline_xy_replacement = True
                transform_points(ct, x, y)
                
        # Read geotransform matrix and calculate corresponding pixel coordinates
        geotransform = ds.GetGeoTransform()
        inv_geotransform = gdal.InvGeoTransform(geotransform)
        if inv_geotransform is None:
            raise Exception("Failed InvGeoTransform()")

        # can we inline this transformation ?
        x, y = (
            inv_geotransform[0] + inv_geotransform[1] * x + inv_geotransform[2] * y
        ), (inv_geotransform[3] + inv_geotransform[4] * x + inv_geotransform[5] * y)
        inline_xy_replacement = True

    xsize, ysize = ds.RasterXSize, ds.RasterYSize
    band_nums = None
    bands = get_bands(ds, band_nums, ovr_idx=ovr_idx)
    ovr_xsize, ovr_ysize = bands[0].XSize, bands[0].YSize
    pixel_fact, line_fact = (
        (ovr_xsize / xsize, ovr_ysize / ysize) if ovr_idx else (1, 1)
    )
    bnd_count = len(bands)

    shape = (bnd_count, point_count)
    np_dtype, np_dtype = GDALTypeCodeAndNumericTypeCodeFromDataSet(ds)
    results = np.empty(shape=shape, dtype=np_dtype)

    if pixel_fact == 1:
        pixels_q = x
    else:
        pixels_q = x * pixel_fact

    if line_fact == 1:
        lines_q = y
    else:
        lines_q = y * line_fact

    for topaz_id, pixel_q, line_q in zip(hillslope_locations, pixels_q, lines_q):
        hillslope_locations[topaz_id]['pixel_q'] = pixel_q
        hillslope_locations[topaz_id]['line_q'] = line_q

    return hillslope_locations


if __name__ == "__main__":

    hillslope_locations = {
        "22": {"longitude": -116.323476283, "latitude": 46.534344},
        "23":  {"longitude": -116.623476283, "latitude": 46.634344},
        # Add other hillslopes here
    }

    hillslope_locations = identify_pixel_coords(hillslope_locations)

    print(hillslope_locations)


    """
    on wepp.cloud the netcdf/h5py/gdal libraries SNAFU

    work around is this /var/www/.bashrc
export LD_LIBRARY_PATH=/workdir/miniconda3/envs/wepppy310-env/lib:$LD_LIBRARY_PATH
export LD_PRELOAD=/workdir/miniconda3/envs/wepppy310-env/lib/libhdf5.so
source /workdir/miniconda3/etc/profile.d/conda.sh
conda activate wepppy310-env
    """
