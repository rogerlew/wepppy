# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from .locationinfo import RasterDatasetInterpolator

import os
from os.path import exists as _exists
from operator import itemgetter
from itertools import groupby
import shutil

from datetime import datetime, timedelta
from urllib.request import urlopen
import requests
from subprocess import Popen, PIPE
from collections import namedtuple
from math import radians, sin, cos, asin, sqrt

import numpy as np

from osgeo import gdal, osr

gdal.UseExceptions()

geodata_dir = '/geodata/'

RGBA = namedtuple('RGBA', list('RGBA'))
RGBA.tohex = lambda this: '#' + ''.join('{:02X}'.format(a) for a in this)


def determine_wateryear(y, j=None, mo=None):
    if j is not None:
        mo = int((datetime(int(y), 1, 1) + timedelta(int(j))).month)

    if mo > 9:
        return y + 1

    return y


def find_ranges(iterable, as_str=False):
    """Yield range of consecutive numbers."""

    def func(args):
        index, item = args
        return index - item

    ranges = []
    for key, group in groupby(enumerate(iterable), func):
        group = list(map(itemgetter(1), group))
        if len(group) > 1:
            ranges.append((group[0], group[-1]))
        else:
            ranges.append(group[0])

    if not as_str:
        return ranges

    s = []

    for arg in ranges:
        if isint(arg):
            s.append(str(arg))
        else:
            s.append('{}-{}'.format(*arg))

    return ', '.join(s)


def clamp(x: float, minimum: float, maximum: float) -> float:
    x = float(x)
    if x < minimum:
        return minimum
    elif x > maximum:
        return maximum
    return x


def clamp01(x: float) -> float:
    x = float(x)
    if x < 0.0:
        return 0.0
    elif x > 1.0:
        return 1.0
    return x


def cp_chmod(src, dst, mode):
    """
    helper function to copy a file and set chmod
    """
    shutil.copyfile(src, dst)
    os.chmod(dst, mode)


def parse_datetime(x):
    if isinstance(x, datetime):
        return x

    ymd = x.split('-')
    if len(ymd) != 3:
        ymd = x.split('/')
    if len(ymd) != 3:
        ymd = x.split('.')

    y, m, d = ymd
    y = int(y)
    m = int(m)
    d = int(d)

    return datetime(y, m, d)


def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:   # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:  # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


def isint(x):
    # noinspection PyBroadException
    try:
        return float(int(x)) == float(x)
    except Exception:
        return False


def isfloat(f):
    # noinspection PyBroadException
    try:
        float(f)
        return True
    except Exception:
        return False


def try_parse(f):
    # noinspection PyBroadException
    try:
        ff = float(f)
        # noinspection PyBroadException
        try:
            fi = int(f)
            return fi
        except Exception:
            return ff
    except Exception:
        return f


def try_parse_float(f):
    # noinspection PyBroadException
    try:
        return float(f)
    except Exception:
        return 0.0


def parse_name(colname):
    units = parse_units(colname)
    if units is None:
        return colname

    return colname.replace('({})'.format(units), '').strip()


def parse_units(colname):
    try:
        colsplit = colname.strip().split()
        if len(colsplit) < 2:
            return None

        if '(' in colsplit[-1]:
            return colsplit[-1].replace('(', '').replace(')', '')

        return None
    except IndexError:
        return None

    return None

class RowData:
    def __init__(self, row):
        self.row = row

    def __iter__(self):
        for colname in self.row:
            value = self.row[colname]
            units = parse_units(colname)
            yield value, units

wmesque_url = 'https://wepp1.nkn.uidaho.edu/webservices/wmesque/'


def wmesque_retrieve(dataset, extent, fname, cellsize):
    global wmesque_url

    assert dataset in ['ned1/2016',
                       'ssurgo/201703',
                       'nlcd/2011']

    assert isfloat(cellsize)

    assert all([isfloat(v) for v in extent])
    assert len(extent) == 4

    extent = ','.join([str(v) for v in extent])

    if fname.lower().endswith('.tif'):
        fmt = 'GTiff'

    elif fname.lower().endswith('.asc'):
        fmt = 'AAIGrid'

    elif fname.lower().endswith('.png'):
        fmt = 'PNG'

    else:
        raise ValueError('fname must end with .tif, .asc, or .png')

    url = '{wmesque_url}{dataset}/?bbox={extent}&cellsize={cellsize}&format={format}'\
          .format(wmesque_url=wmesque_url, dataset=dataset,
                  extent=extent, cellsize=cellsize, format=fmt)

    output = urlopen(url)
    with open(fname, 'wb') as fp:
        fp.write(output.read())

    return 1


def parse_datetime(s):
    return datetime.strptime(s[1:s.find(']')], '%Y-%m-%dT%H:%M:%S.%f')


wgs84_proj4 = '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'


def warp2match(src_filename, match_filename, dst_filename):
    # Source
    src = gdal.Open(src_filename, gdalconst.GA_ReadOnly)
    src_proj = src.GetProjection()
    src_geotrans = src.GetGeoTransform()

    # We want a section of source that matches this:
    match_ds = gdal.Open(match_filename, gdalconst.GA_ReadOnly)
    match_proj = match_ds.GetProjection()
    match_geotrans = match_ds.GetGeoTransform()
    wide = match_ds.RasterXSize
    high = match_ds.RasterYSize

    # Output / destination
    dst = gdal.GetDriverByName('GTiff').Create(dst_filename, wide, high, 1, gdalconst.GDT_Byte)
    dst.SetGeoTransform( match_geotrans )
    dst.SetProjection( match_proj)

    # Do the work
    gdal.ReprojectImage(src, dst, src_proj, match_proj, gdalconst.GRA_NearestNeighbour)

    del dst  # Flush


def translate_tif_to_asc(fn):
    assert fn.endswith(".tif")
    assert _exists(fn)

    fn2 = fn[:-4] + ".asc"
    cmd = ["gdal_translate", "-of", "AAIGrid", fn, fn2]
    Popen(cmd, stdout=PIPE, stderr=PIPE)

    assert _exists(fn2)

    return fn2


def read_raster(fn, dtype=np.float64):
    _fn = fn.lower()

    if _fn.endswith('.asc') or _fn.endswith('arc'):
        return read_arc(fn, dtype)
    else:
        return read_tif(fn, dtype)


def read_tif(fn, dtype=np.float64):
    """
    use gdal to read an tif file and return the data and the
    transform
    """
    assert _exists(fn), "Cannot open %s" % fn

    ds = gdal.Open(fn)
    assert ds is not None

    transform = ds.GetGeoTransform()
    data = np.array(ds.GetRasterBand(1).ReadAsArray(), dtype=dtype).T
    wkt_text = ds.GetProjection()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(wkt_text)
    proj = srs.ExportToProj4().strip()

    del ds

    data = np.array(data, dtype=dtype)

    return data, transform, proj


def read_arc(fn, dtype=np.float64):
    """
    use gdal to read an arc file and return the data and the
    transform
    """
    assert _exists(fn), "Cannot open %s" % fn

    ds = gdal.Open(fn)
    assert ds is not None

    transform = ds.GetGeoTransform()
    wkt_text = ds.GetProjection()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(wkt_text)
    proj = srs.ExportToProj4().strip()

    del ds

    with open(fn) as fp:
        data = fp.readlines()

    i = 0
    for i in range(len(data)):
        if isfloat(data[i].split()[0]):
            break

    data = [[float(v) for v in L.split()] for L in data[i:]]
    data = np.array(data, dtype=dtype).T

    return data, transform, proj


def write_arc(data, fname, ll_x, ll_y, cellsize, no_data=0):
    # template for building
    arc_template = '''\
ncols        {num_cols}
nrows        {num_rows}
xllcorner    {ll_x}
yllcorner    {ll_y}
cellsize     {cellsize}
nodata_value {no_data}
{data}'''

    _data = np.array(data)
    n, m = _data.shape

    # write junction_mask to wd as CHNJNT.ARC dataset
    data_string = [' '.join(map(str, _data[:, j].flatten())) for j in range(m)]
    data_string = [' ' + row for row in data_string]
    data_string = '\n'.join(data_string)

    with open(fname, 'w') as fp:
        fp.write(arc_template.format(num_cols=n, num_rows=m,
                                     ll_x=ll_x, ll_y=ll_y,
                                     cellsize=cellsize,
                                     no_data=no_data,
                                     data=data_string))


def identify_utm(fn):
    assert _exists(fn), "Cannot open %s" % fn

    ds = gdal.Open(fn)
    assert ds is not None

    wkt_text = ds.GetProjection()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(wkt_text)
    utm = get_utm_zone(srs)
    del ds

    return utm


def get_utm_zone(srs):
    """
    extracts the utm_zone from an osr.SpatialReference object (srs)

    returns the utm_zone as an int, returns None if utm_zone not found
    """
    if not isinstance(srs, osr.SpatialReference):
        raise TypeError('srs is not a osr.SpatialReference instance')

    if srs.IsProjected() != 1:
        return None

    projcs = srs.GetAttrValue('projcs')
    # should be something like NAD83 / UTM zone 11N...
    if '/' not in projcs:
        return None

    utm_token = projcs.split('/')[1]
    if 'UTM' not in utm_token:
        return None

    # noinspection PyBroadException
    try:
        utm_zone = int(''.join([k for k in utm_token if k in '0123456789']))
    except Exception:
        return None

    if utm_zone < 0 or utm_zone > 60:
        return None

    return utm_zone


_AVG_EARTH_RADIUS = 6371  # in km
_MILES_PER_KILOMETER = 0.621371


def haversine(point1, point2, miles=False):
    """ Calculate the great-circle distance between two points on the Earth surface.
    :input: two 2-tuples, containing the longitude and latitude of each point
    in decimal degrees.
    :output: Returns the distance between the two points.
    The default unit is kilometers. Miles can be returned
    if the ``miles`` parameter is set to True.
    """
    global _AVG_EARTH_RADIUS, _MILES_PER_KILOMETER

    # unpack latitude/longitude
    lng1, lat1 = point1
    lng2, lat2 = point2

    # convert all latitudes/longitudes from decimal degrees to radians
    lat1, lng1, lat2, lng2 = [radians(v) for v in (lat1, lng1, lat2, lng2)]

    # calculate haversine
    lat = lat2 - lat1
    lng = lng2 - lng1
    d = sin(lat * 0.5) ** 2 + \
        cos(lat1) * cos(lat2) * sin(lng * 0.5) ** 2
    h = 2 * _AVG_EARTH_RADIUS * asin(sqrt(d))
    if miles:
        return h * _MILES_PER_KILOMETER  # in miles
    else:
        return h  # in kilometers


class Extent(object):
    def __init__(self, a):
        assert len(a) == 4
        self.xmin = float(a[0])
        self.ymin = float(a[1])
        self.xmax = float(a[2])
        self.ymax = float(a[3])

        assert self.xmin < self.xmax
        assert self.ymin < self.ymax

    def intersects(self, other):
        assert isinstance(other, Extent)

        a = self
        b = other
        return (a.xmin <= b.xmax and a.xmax >= b.xmin) and \
               (a.ymin <= b.ymax and a.ymax >= b.ymin)


_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_cummdays = [31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]


def _julian_to_md(julian):
    for i, (d, cd) in enumerate(zip(_days, _cummdays)):
        if julian <= cd:
            return i+1, d - (cd - julian)


def _md_to_julian(month, day):
    return _cummdays[month-1] + day - _days[month-1]


class Julian(object):
    def __init__(self, *args, **kwargs):

        # noinspection PyUnusedLocal
        __slots__ = ["julian", "month", "day"]

        if len(kwargs) > 0:
            assert "julian" in kwargs
            julian = kwargs['julian']
            assert julian > 0
            assert julian <= 365

            assert "month" in kwargs
            assert "day" in kwargs
            month = kwargs['month']
            day = kwargs['day']

            _m, _d = _julian_to_md(julian)
            assert _m == month
            assert _d == day

            super(Julian, self).__setattr__("julian", julian)
            super(Julian, self).__setattr__("month", month)
            super(Julian, self).__setattr__("day", day)

        if len(args) == 1:
            julian = int(args[0])
            assert julian >= 0
            assert julian <= 365

            super(Julian, self).__setattr__("julian", julian)

            month, day = _julian_to_md(julian)
            super(Julian, self).__setattr__("month", month)
            super(Julian, self).__setattr__("day", day)

        elif len(args) == 2:
            month = int(args[0])
            day = int(args[1])
            assert month > 0
            assert month <= 12

            assert day > 0
            assert day <= _days[month-1]

            super(Julian, self).__setattr__("month", month)
            super(Julian, self).__setattr__("day", day)

            julian = _md_to_julian(month, day)
            super(Julian, self).__setattr__("julian", julian)

    def __str__(self):
        # noinspection PyUnresolvedReferences
        return str(self.julian)

    def __repr__(self):
        # noinspection PyUnresolvedReferences
        return 'Julian(julian=%i, month=%i, day=%i)'\
               % (self.julian, self.month, self.day)


def elevationquery(lng, lat):
    url = 'https://wepp1.nkn.uidaho.edu/webservices/elevationquery'
    r = requests.post(url, params=dict(lat=lat, lng=lng))

    if r.status_code != 200:
        raise Exception("Encountered error retrieving from elevationquery")

    # noinspection PyBroadException
    try:
        _json = r.json()
    except Exception:
        _json = None

    if _json is None:
        raise Exception("Cannot parse json from elevation response")

    return _json['Elevation']


def px2coord_factory(transform):
    return lambda x, y: (transform[0] + x * transform[1] + y * transform[2],
                         transform[3] + x * transform[4] + y * transform[5])


def c_to_f(x):
    return 9.0/5.0 * x + 32.0


def f_to_c(x):
    return (x - 32.0) * 5.0 / 9.0
