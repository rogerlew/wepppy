# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import math
import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from uuid import uuid4
from glob import glob
from subprocess import Popen, PIPE

from calendar import isleap

import traceback

import netCDF4

from osgeo import osr

from multiprocessing import Pool

from subprocess import Popen, PIPE
from flask import Flask, jsonify, request, make_response, send_file, after_this_request

from wepppy.climates.daymet import daymet_proj4
from wepppy.all_your_base import SCRATCH
from wepppy.all_your_base.geo import wgs84_proj4

import numpy as np
import xarray as xr

from wepppy.all_your_base.geo.locationinfo import  RasterDatasetInterpolator
from wepppy.all_your_base.geo.geo_transformer import GeoTransformer

from glob import glob

from osgeo import ogr, osr, gdal
gdal.UseExceptions()

def isint(x):
    # noinspection PyBroadException
    try:
        return float(int(x)) == float(x)
    except Exception:
        return False


# example GDAL error handler function
def gdal_error_handler(err_class, err_num, err_msg):
    errtype = {
            gdal.CE_None:'None',
            gdal.CE_Debug:'Debug',
            gdal.CE_Warning:'Warning',
            gdal.CE_Failure:'Failure',
            gdal.CE_Fatal:'Fatal'
    }
    err_msg = err_msg.replace('\n',' ')
    err_class = errtype.get(err_class, 'None')
    print('Error Number: %s' % (err_num))
    print('Error Type: %s' % (err_class))
    print('Error Message: %s' % (err_msg))


# install error handler
gdal.PushErrorHandler(gdal_error_handler)

geodata_dir = '/geodata/'
static_dir = None

monthly_catalog = {
    'daymet/prcp/mean' : {'Description': 'Precipitation averages calculated from daily Daymet (1980-2016)', 'Units': 'mm' },
    'daymet/prcp/std'  : {'Description': 'Precipitation standard deviations calculated from daily Daymet (1980-2016)', 'Units': 'mm' },
    'daymet/prcp/skew' : {'Description': 'Precipitation skewness calculated from daily Daymet (1980-2016)', 'Units': 'mm' },
    'daymet/prcp/pww'  : {'Description': 'Precipitation P(W/W) calculated from daily Daymet (1980-2016)', 'Units': 'P [0-])' },
    'daymet/prcp/pwd'  : {'Description': 'Precipitation P(W/D) calculated from daily Daymet (1980-2016)', 'Units': 'P [0-1]' },
    #'daymet/srad/mean' : {'Description': 'Incident shortwave radiation averages calculated from daily Daymet (1980-2016)', 'Units': 'W/m^2' },
    #'daymet/srad/std'  : {'Description': 'Incident shortwave radiation standard deviations calculated from daily Daymet (1980-2016)', 'Units': 'mm' },
    'daymet/srld/mean' : {'Description': 'Daily total radiation averages calculated from daily Daymet (1980-2016)', 'Units': 'Langleys/day' },
    #'daymet/srld/std'  : {'Description': 'Daily total radiation standard deviations calculated from daily Daymet (1980-2016)', 'Units': 'Langleys/day' },
    #'daymet/dayl/mean' : {'Description': 'Duration of the daylight period averages', 'Units': 's' },
    #'daymet/dayl/std'  : {'Description': 'duration of the daylight period standard deviations', 'Units': 's' },
    'prism/tmin'       : {'Description': 'Minimum air temperature', 'Units': 'C' },
    'prism/tmax'       : {'Description': 'Maximum air temperature', 'Units': 'C' },
    'prism/ppt'        : {'Description': 'Total precipitation in millimeters per month', 'Units': 'mm/month' },
    'prism/tmean'      : {'Description': 'Mean temperature', 'Units': 'C' },
    'prism/tdmean'     : {'Description': 'Dewpoint temperature', 'Units': 'C' },
    'eu/e-obs/tn/mean' : {'Description': 'Minimum air temperature', 'Units': 'C' },
    'eu/e-obs/tx/mean' : {'Description': 'Maximum air temperature', 'Units': 'C' },
    'eu/e-obs/rr/mean' : {'Description': 'Average daily precipitation', 'Units': 'mm' },
    'au/agdc/monthlies/tmin' : {'Description': 'Minimum air temperature', 'Units': 'C' },
    'au/agdc/monthlies/tmax' : {'Description': 'Maximum air temperature', 'Units': 'C' },
    'au/agdc/monthlies/rain' : {'Description': 'Average daily precipitation', 'Units': 'mm' }
}

daily_catalog = {
    'daymet/prcp': {'Description': 'Precipitation daily values from Daymet', 'Units': 'mm'},
    'daymet/tmin': {'Description': 'Temperature Minimum daily values from Daymet', 'Units': 'C'},
    'daymet/tmax': {'Description': 'Temperature Maximum daily values from Daymet', 'Units': 'C'},
    'daymet/v4/prcp': {'Description': 'Precipitation daily values from Daymet', 'Units': 'mm'},
    'daymet/v4/tmin': {'Description': 'Temperature Minimum daily values from Daymet', 'Units': 'C'},
    'daymet/v4/tmax': {'Description': 'Temperature Maximum daily values from Daymet', 'Units': 'C'},
    'lt/daymet/prcp': {'Description': 'Precipitation daily values from Daymet', 'Units': 'mm'},
    'lt/daymet/tmin': {'Description': 'Temperature Minimum daily values from Daymet', 'Units': 'C'},
    'lt/daymet/tmax': {'Description': 'Temperature Maximum daily values from Daymet', 'Units': 'C'}
}


def crop_nc(nc, bbox, dst):

    _wgs_2_lcc = GeoTransformer(src_proj4=wgs84_proj4,
                                dst_proj4='+proj=lcc +lat_1=25 +lat_2=60 +lat_0=42.5 +lon_0=-100 '
                                          '+x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs')

    yr_parse = lambda fn: _split(fn)[-1].split('_')[3]

    ds = netCDF4.Dataset(nc)

    # determine transform
    x = [ds.variables['x'][0],
         ds.variables['x'][1],
         ds.variables['x'][-1]]
    y = [ds.variables['y'][0],
         ds.variables['y'][1],
         ds.variables['y'][-1]]
    res = x[1] - x[0]
    transform = [x[0], res, 0.0, y[0], 0.0, -res]
    ncols = len(ds.variables['x'])
    nrows = len(ds.variables['y'])

    ll_x, ll_y, ur_x, ur_y = bbox

    assert ur_x > ll_x
    assert ur_y > ll_y

    ll_px, ll_py = _wgs_2_lcc.transform(ll_x, ll_y)
    ur_px, ur_py = _wgs_2_lcc.transform(ur_x, ur_y)

    cmd = ['ncks',
           '-d', 'x,{},{}'.format(*sorted([ll_px, ur_px])),
           '-d', 'y,{},{}'.format(*sorted([ll_py, ur_py])),
           nc, dst]

    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p.wait()

    assert _exists(dst), ' '.join(cmd)


def merge_nc(fn_list, dst):

    cmd = ['ncecat'] + fn_list + ['-O', dst]

    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p.wait()

    # Copy global attributes (including projection) from first file to merged file
    cmd2 = ['ncks', '-A', '-G', '.', fn_list[0], dst]
    p = Popen(cmd2, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p.wait()

    assert _exists(dst), ' '.join(cmd) + ' '.join(cmd2)


def exception_factory(msg='Error Handling Request',
                      stacktrace=None):
    if stacktrace is None:
        stacktrace = traceback.format_exc()

    return jsonify({'Success': False,
                    'Error': msg,
                    'StackTrace': stacktrace})


def safe_float_parse(x):
    """
    Tries to parse {x} as a float. Returns None if it fails.
    """
    try:
        return float(x)
    except:
        return None


def parse_bbox(bbox):
    """
    Tries to parse the bbox argument supplied by the request
    in a fault tolerate manner
    """
    try:
        coords = bbox.split(',')
    except:
        return (None, None, None, None)

    n = len(coords)
    if n < 4:
        coords.extend([None for i in range(4-n)])
    if n > 4:
        coords = coords[:4]

    return tuple(map(safe_float_parse, coords))


app = Flask(__name__)


@app.route('/health')
def health():
    return jsonify("OK")


@app.route('/daily/catalog')
@app.route('/daily/catalog/')
def query_daily_catalog():
    """
    https://wepp.cloud/webservices/metquery/daily/catalog/
    """
    return jsonify(daily_catalog)




@app.route('/daily_singlepoint', methods=['GET', 'POST'])
@app.route('/daily_singlepoint/', methods=['GET', 'POST'])
def query_daily_singlepoint():
    """
    https://wepp.cloud/webservices/metquery/daily_singlepoint/?dataset=daymet/prcp&lon=-116&lat=47
    """
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if request.method == 'GET':
        d = request.args
    else:  # POST
        d = request.get_json(force=True)

    lon = float(d.get('lon', None))
    lat = float(d.get('lat', None))
    dataset = d.get('dataset', None)
    start_year = int(d.get('start_year', None))
    end_year = int(d.get('end_year', None))
    _wgs_2_lcc = GeoTransformer(wgs84_proj4, daymet_proj4)

    x, y = _wgs_2_lcc.transform(lon, lat)

    if dataset is None:
        return jsonify({'Error': 'dataset not supplied'})

    if dataset not in daily_catalog.keys():
        return jsonify({'Error': 'unknown dataset "{}"'.format(dataset)})

    variable = _split(dataset)[-1]

    all_ts = []
    for yr in range(start_year, end_year + 1):
        fname = glob(_join(geodata_dir, dataset, '*{}*.nc'.format(yr)))
        fname.extend(glob(_join(geodata_dir, dataset, '*{}*.nc4'.format(yr))))

        if len(fname) == 0:
            return 'Error', 'Cannot find dataset'
        if len(fname) > 1:
            return 'Error', 'Cannot determine dataset'

        fname = fname[0]

        ds = xr.open_dataset(fname)
        data = ds.sel(x=x, y=y, method='nearest')

        ts = data[variable].values
        if isleap(yr):
            ts = np.append(ts, ts[-1])

        all_ts.append(ts)

    return np.concatenate(all_ts)


def daily_worker(args):
    yr, dataset, bbox = args

    fname = glob(_join(geodata_dir, dataset, '*{}*.nc'.format(yr)))
    fname.extend(glob(_join(geodata_dir, dataset, '*{}*.nc4'.format(yr))))

    if len(fname) == 0:
        return 'Error', 'Cannot find dataset'
    if len(fname) > 1:
        return 'Error', 'Cannot determine dataset'

    fname = fname[0]

    fn_uuid = str(uuid4().hex) + '.nc4'
    dst = os.path.join(SCRATCH, fn_uuid)

    # noinspection PyBroadException
    try:
        crop_nc(fname, bbox, dst)
    except Exception as e:
        return 'Exception', str(e)

    return 'Success', dst


@app.route('/daily', methods=['GET', 'POST'])
@app.route('/daily/', methods=['GET', 'POST'])
def query_daily():
    """
    https://wepp.cloud/webservices/metquery/daily/?dataset=daymet/prcp&bbox=-116,47,-115.98,47.02&year=2004
    https://wepp.cloud/webservices/metquery/daily/?dataset=daymet/prcp&bbox=-116,47,-115.98,47.02&year=2019
    """
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if request.method == 'GET':
        d = request.args
    else:  # POST
        d = request.get_json(force=True)

    bbox = d.get('bbox', None)
    dataset = d.get('dataset', None)
    year = d.get('year', None)
    start_year = d.get('start_year', None)
    end_year = d.get('end_year', None)

    if start_year is None and end_year is None:
        start_year = int(year)
        end_year = int(year)
    else:
        start_year = int(start_year)
        end_year = int(end_year)

    bbox = parse_bbox(bbox)

#    return jsonify(dict(bbox=bbox, start_year=start_year, end_year=end_year, dataset=dataset, daily_catalog=daily_catalog))

    if any([x is None for x in bbox]):
        return jsonify({'Error': 'bbox contains non float values'})

    if bbox[1] > bbox[3] or bbox[0] > bbox[2]:
        return jsonify({'Error': 'Expecting bbox defined as: left, bottom, right, top' + str(bbox)})

    if dataset is None:
        return jsonify({'Error': 'dataset not supplied'})

    if dataset not in daily_catalog.keys():
        return jsonify({'Error': 'unknown dataset "{}"'.format(dataset)})

    if not (isint(start_year) and isint(end_year)):
        return jsonify({'Error': 'start_year and end_year must be integers'})

    fn_list = []
    with Pool() as p:
        results = p.map(daily_worker, [(yr, dataset, bbox) for yr in range(start_year, end_year + 1)])

    for result in results:
        status, msg = result
        if status == 'Error':
            return jsonify({'Error': msg})
        elif status == 'Exception':
            return exception_factory('Error cropping dataset.'), 418
        else:
            fn_list.append(msg)

    if len(fn_list) == 1:
        dst = fn_list[0]
    else:
        fn_uuid = str(uuid4().hex) + '.nc4'
        dst = os.path.join(SCRATCH, fn_uuid)
        # noinspection PyBroadException
        try:
            merge_nc(fn_list, dst)
        except Exception:
            return exception_factory('Error cropping dataset.'), 418

    # Define a function to delete the files
    def delete_files(response):
        for file in fn_list:
            try:
                os.remove(file)
            except OSError:
                pass
        return response

    # Register the delete_files function to be executed after the request is completed
    after_this_request(delete_files)

    response = make_response(send_file(dst))
    response.headers['Content-Type'] = 'application/octet-stream'

    response.headers['Content-Disposition'] = 'attachment; filename=' + _split(dst)[1]

    response.headers['Meta'] = {'bbox': bbox,
                                'cache': dst,
                                'dataset': dataset,
                                'year': year,
                                'start_year': start_year,
                                'end_year': end_year,
                                'url': request.url
                                }

    return response


@app.route('/monthly/catalog')
@app.route('/monthly/catalog/')
def query_monthly_catalog():
    """
    https://wepp.cloud/webservices/metquery/monthly/catalog/
    """
    return jsonify(monthly_catalog)


@app.route('/monthly', methods=['GET', 'POST'])
@app.route('/monthly/', methods=['GET', 'POST'])
def query_monthly():
    """
    https://wepp.cloud/webservices/metquery/monthly/?dataset=prism/ppt&lng=-116&lat=45
    https://wepp.cloud/webservices/metquery/monthly/?dataset=daymet/prcp/mean&lng=-116&lat=45
    https://wepp.cloud/webservices/metquery/monthly/?dataset=au/agdc/monthlies/rain&lng=146.80738449096683&lat=-37.69733638487025
    """
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if request.method == 'GET':
        lat = request.args.get('lat', None)
        lng = request.args.get('lng', None)
        dataset = request.args.get('dataset', None)
        method = request.args.get('method', None)
    else:  # POST
        d = request.get_json(force=True)
        lat = d.get('lat', None)
        lng = d.get('lng', None)
        dataset = d.get('dataset', None)
        method = d.get('method', None)

    if lat is None:
        return jsonify({'Error': 'lat not supplied'})

    if lng is None:
        return jsonify({'Error': 'lng not supplied'})

    if dataset is None:
        return jsonify({'Error': 'dataset not supplied'})

    if method is None:
        method = 'cubic'
        
    lat = safe_float_parse(lat)
    lng = safe_float_parse(lng)

    if lat is None:
        return jsonify({'Error': 'could not parse lat'})

    if lng is None:
        return jsonify({'Error': 'could not parse lng'})

    if dataset not in monthly_catalog.keys():
        return jsonify({'Error': 'unknown dataset'})
        
    if method not in ['bilinear', 'cubic', 'nearest']:
        return jsonify({'Error': 'unknown method "%s".'
                        'expecting bilnear, cubic or nearest ' % method})
    
    fname = _join(geodata_dir, dataset, '.vrt')
    if not _exists(fname):
        return jsonify({'Error': 'could not find dataset "%s"' % fname})
        
    print('metquery::query_monthly fname', fname)
    print('metquery::query_monthly lat', lat)
    print('metquery::query_monthly lng', lng)
    print('metquery::query_monthly method', method)
    print('metquery::query_monthly dataset', dataset)
    rds = RasterDatasetInterpolator(fname)
    data = rds.get_location_info(lng, lat, method)
    
    assert len(data) == 12
    
    return jsonify({'Latitude': lat,
                    'Longitude': lng,
                    'Dataset': dataset,
                    'Description': monthly_catalog[dataset]['Description'],
                    'Units': monthly_catalog[dataset]['Units'],
                    'Method': method,
                    'MonthlyValues': data})


if __name__ == '__main__':
    app.run()

""" 
curl -sS 'https://wepp.cloud/webservices/metquery/daily/?dataset=daymet/prcp&bbox=-116,47,-115.98,47.02&year=2004'
"""
