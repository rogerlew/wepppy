# Copyright (c) 2016-2020, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from typing import Tuple

from .locationinfo import RasterDatasetInterpolator, RDIOutOfBoundsException
from .geo_transformer import GeoTransformer
import sys
import collections
import os
from os.path import exists as _exists
from operator import itemgetter
from itertools import groupby
import shutil
import json

from datetime import datetime, timedelta, date
from urllib.request import urlopen
import requests
from subprocess import Popen, PIPE
from collections import namedtuple
import math
import utm
from uuid import uuid4
import xml.etree.ElementTree as ET

from math import radians, sin, cos, asin, sqrt

import numpy as np
import multiprocessing

try:
    import win32com.shell.shell as shell
except:
    pass

from osgeo import gdal, osr, ogr
gdal.UseExceptions()

try:
    NCPU = int(os.environ['WEPPPY_NCPU'])
except KeyError:
    NCPU = math.floor(multiprocessing.cpu_count() * 0.5)
    if NCPU < 1:
        NCPU = 1

geodata_dir = '/geodata/'

RGBA = namedtuple('RGBA', list('RGBA'))
RGBA.tohex = lambda this: '#' + ''.join('{:02X}'.format(a) for a in this)


SCRATCH = '/media/ramdisk'

if not _exists(SCRATCH):
    SCRATCH = '/Users/roger/Downloads'

if not _exists(SCRATCH):
    SCRATCH = '/workdir'

IS_WINDOWS = os.name == 'nt'


def make_symlink(src, dst):
    if IS_WINDOWS:
        if _exists(dst):
            os.remove(dst)
        params = ' '.join(['mklink', dst, src])
        shell.ShellExecuteEx(lpVerb='runas', lpFile=sys.executable, lpParameters=params)
    else:
        os.symlink(src, dst)


def cmyk_to_rgb(c, m, y, k):
    """
    """
    r = (1.0 - c) * (1.0 - k)
    g = (1.0 - m) * (1.0 - k)
    b = (1.0 - y) * (1.0 - k)
    return r, g, b


def utm_srid(zone, datum='WGS84', hemisphere='N'):
    zone = str(zone)
    if hemisphere == 'N':
        if datum == 'NAD83':
            return {
                '4': 26904,
                '5': 26905,
                '6': 26906,
                '7': 26907,
                '8': 26908,
                '9': 26909,
                '10': 26910,
                '11': 26911,
                '12': 26912,
                '13': 26913,
                '14': 26914,
                '15': 26915,
                '16': 26916,
                '17': 26917,
                '18': 26918,
                '19': 26919,
                '20': 26920,
                '21': 26921,
                '22': 26922,
                '23': 26923 }.get(str(zone), None)

        elif datum == 'WGS84' or datum is None:
            return {
                '4': 32604,
                '5': 32605,
                '6': 32606,
                '7': 32607,
                '8': 32608,
                '9': 32609,
                '10': 32610,
                '11': 32611,
                '12': 32612,
                '13': 32613,
                '14': 32614,
                '15': 32615,
                '16': 32616,
                '17': 32617,
                '18': 32618,
                '19': 32619,
                '20': 32620,
                '21': 32621,
                '22': 32622,
                '23': 32623,
                '24': 32624,
                '25': 32625,
                '26': 32626,
                '27': 32627,
                '28': 32628,
                '29': 32629,
                '30': 32630,
                '31': 32631,
                '32': 32632,
                '33': 32633,
                '34': 32634,
                '35': 32635,
                '36': 32636,
                '37': 32637,
                '38': 32638,
                '39': 32639,
                '40': 32640,
                '41': 32641,
                '42': 32642,
                '43': 32643,
                '44': 32644,
                '45': 32645,
                '46': 32646,
                '47': 32647,
                '48': 32648,
                '49': 32649,
                '50': 32650,
                '51': 32651,
                '52': 32652,
                '53': 32653,
                '54': 32654,
                '55': 32655,
                '56': 32656,
                '57': 32657,
                '58': 32658,
                '59': 32659,
                '60': 32660}.get(str(zone), None)
    else:
        if datum == 'WGS84' or datum is None:
            return {
                '4': 32704,
                '5': 32705,
                '6': 32706,
                '7': 32707,
                '8': 32708,
                '9': 32709,
                '10': 32710,
                '11': 32711,
                '12': 32712,
                '13': 32713,
                '14': 32714,
                '15': 32715,
                '16': 32716,
                '17': 32717,
                '18': 32718,
                '19': 32719,
                '20': 32720,
                '21': 32721,
                '22': 32722,
                '23': 32723,
                '24': 32724,
                '25': 32725,
                '26': 32726,
                '27': 32727,
                '28': 32728,
                '29': 32729,
                '30': 32730,
                '31': 32731,
                '32': 32732,
                '33': 32733,
                '34': 32734,
                '35': 32735,
                '36': 32736,
                '37': 32737,
                '38': 32738,
                '39': 32739,
                '40': 32740,
                '41': 32741,
                '42': 32742,
                '43': 32743,
                '44': 32744,
                '45': 32745,
                '46': 32746,
                '47': 32747,
                '48': 32748,
                '49': 32749,
                '50': 32750,
                '51': 32751,
                '52': 32752,
                '53': 32753,
                '54': 32754,
                '55': 32755,
                '56': 32756,
                '57': 32757,
                '58': 32758,
                '59': 32759,
                '60': 32760}.get(str(zone), None)
    return None


def flatten(l):
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el, (str, bytes)):
            yield from flatten(el)
        else:
            yield el


def centroid_px(indx, indy) -> Tuple[int, int]:
    """
    given a sets of x and y indices calulates a central [x,y] index
    """
    return (int(round(float(np.mean(indx)))),
            int(round(float(np.mean(indy)))))


def determine_wateryear(y, j=None, mo=None):
    if j is not None:
        mo = int((datetime(int(y), 1, 1) + timedelta(int(j))).month)

    if int(mo) > 9:
        return int(y) + 1

    return int(y)


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


def parse_date(x):
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


def isbool(x):
    # noinspection PyBroadException
    return x in (0, 1, True, False)


def isnan(f):
    if not isfloat(f):
        return False
    return math.isnan(float(f))


def isinf(f):
    if not isfloat(f):
        return False
    return math.isinf(float(f))


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


wmesque_url = 'https://wepp1.nkn.uidaho.edu/webservices/wmesque/'


def wmesque_retrieve(dataset, extent, fname, cellsize):
    global wmesque_url


    #assert dataset in ['ned1/2016',
    #                   'eu/eu-dem-v1.1',
    #                   'au/srtm-1s-dem-h',
    #                   'ssurgo/201703',
    #                   'nlcd/2011'], '"%s"' % dataset

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

    try:
        output = urlopen(url, timeout=60)
        with open(fname, 'wb') as fp:
            fp.write(output.read())
    except Exception:
        raise Exception("Error retrieving: %s" % url)

    return 1


def crop_geojson(fn, bbox):
    l, b, r, t = bbox

    assert l < r
    assert b < t
    assert _exists(fn)

    js = json.load(open(fn))

    _features = []
    for feature in js['features']:
        lng, lat = feature['geometry']['coordinates']
        if l < lng < r and b < lat < t:
            _features.append(feature)

    js['features'] = _features

    return js


def parse_datetime(s):
    return datetime.strptime(s[1:s.find(']')], '%Y-%m-%dT%H:%M:%S.%f')


wgs84_proj4 = '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'
wgs84_wkt = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]'


def warp2match(src_filename, match_filename, dst_filename):
    # Source
    src = gdal.Open(src_filename, gdal.GA_ReadOnly)
    src_proj = src.GetProjection()
    src_geotrans = src.GetGeoTransform()

    # We want a section of source that matches this:
    match_ds = gdal.Open(match_filename, gdal.GA_ReadOnly)
    match_proj = match_ds.GetProjection()
    match_geotrans = match_ds.GetGeoTransform()
    wide = match_ds.RasterXSize
    high = match_ds.RasterYSize

    # Output / destination
    dst = gdal.GetDriverByName('GTiff').Create(dst_filename, wide, high, 1, gdal.GDT_Byte)
    dst.SetGeoTransform( match_geotrans )
    dst.SetProjection( match_proj)

    # Do the work
    gdal.ReprojectImage(src, dst, src_proj, match_proj, gdal.GRA_NearestNeighbour)

    del dst  # Flush


def px_to_utm(transform, x: int, y: int):
    e = transform[0] + transform[1] * x
    n = transform[3] + transform[5] * y
    return e, n


def px_to_lnglat(transform, x: int, y: int, utm_proj, wgs_proj):
    e, n = px_to_utm(transform, x, y)

    geo_transformer = GeoTransformer(src_proj4=utm_proj, dst_proj4=wgs_proj)
    return geo_transformer.transform(e, n)


def centroid_px(indx, indy):
    """
    given a sets of x and y indices calulates a central [x,y] index
    """
    return (int(round(float(np.mean(indx)))),
            int(round(float(np.mean(indy)))))


def translate_tif_to_asc(fn, fn2=None):
    assert fn.endswith(".tif")
    assert _exists(fn)

    if fn2 is None:
        fn2 = fn[:-4] + ".asc"

    if _exists(fn2):
        os.remove(fn2)

    cmd = ["gdal_translate", "-of", "AAIGrid", fn, fn2]
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p.wait()

    assert _exists(fn2)

    return fn2


def translate_asc_to_tif(fn, fn2=None):
    assert fn.endswith(".asc")
    assert _exists(fn)

    if fn2 is None:
        fn2 = fn[:-4] + ".tif"

    if _exists(fn2):
        os.remove(fn2)

    cmd = ["gdal_translate", "-of", "GTiff", fn, fn2]
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p.wait()

    assert _exists(fn2), fn2

    return fn2


def raster_extent(fn):
    assert _exists(fn)
    data = gdal.Open(fn)
    geoTransform = data.GetGeoTransform()
    minx = geoTransform[0]
    maxy = geoTransform[3]
    maxx = minx + geoTransform[1] * data.RasterXSize
    miny = maxy + geoTransform[5] * data.RasterYSize
    data = None
    return [minx, miny, maxx, maxy]


def read_raster(fn, dtype=np.float64):
    _fn = fn.lower()

    if _fn.endswith('.asc') or _fn.endswith('arc'):
        return read_arc(fn, dtype)
    else:
        return read_tif(fn, dtype)


def wkt_2_proj4(wkt):
    srs = osr.SpatialReference()
    srs.ImportFromWkt(wkt)
    return srs.ExportToProj4().strip()


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


def build_mask(points, georef_fn):

    # This function is based loosely off of Frank's tests for
    # gdal.RasterizeLayer.
    # https://svn.osgeo.org/gdal/trunk/autotest/alg/rasterize.py

    # open the reference
    # we use this to find the size, projection,
    # spatial reference, and geotransform to
    # project the subcatchment to
    ds = gdal.Open(georef_fn)

    pszProjection = ds.GetProjectionRef()
    if pszProjection is not None:
        srs = osr.SpatialReference()
        if srs.ImportFromWkt(pszProjection) == gdal.CE_None:
            pszPrettyWkt = srs.ExportToPrettyWkt(False)


    geoTransform = ds.GetGeoTransform()

    # initialize a new raster in memory
    driver = gdal.GetDriverByName('MEM')
    target_ds = driver.Create('',
                              ds.RasterXSize,
                              ds.RasterYSize,
                              1, gdal.GDT_Byte)
    target_ds.SetGeoTransform(geoTransform)
    target_ds.SetProjection(pszProjection)

    # close the reference
    ds = None

    # Create a memory layer to rasterize from.
    rast_ogr_ds = ogr.GetDriverByName('Memory') \
        .CreateDataSource('wrk')
    rast_mem_lyr = rast_ogr_ds.CreateLayer('poly', srs=srs)

    # Add a polygon.
    coords = ','.join(['%f %f' % (lng, lat) for lng, lat in points])
    wkt_geom = 'POLYGON((%s))' % coords
    feat = ogr.Feature(rast_mem_lyr.GetLayerDefn())
    feat.SetGeometryDirectly(ogr.Geometry(wkt=wkt_geom))
    rast_mem_lyr.CreateFeature(feat)

    # Run the rasterization algorithm
    err = gdal.RasterizeLayer(target_ds, [1], rast_mem_lyr,
                              burn_values=[255])
    rast_ogr_ds = None
    rast_mem_lyr = None

    band = target_ds.GetRasterBand(1)
    data = band.ReadAsArray().T

    # find nonzero indices and return
    return -1 * (data / 255.0) + 1


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

    if '/' in projcs:
        utm_token = projcs.split('/')[1]
    else:
        utm_token = projcs
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


class YearlessDate(object):
    def __init__(self, month, day):
        month = int(month)
        day = int(day)
        assert month in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        self.month = month

        assert day > 0
        assert day <= _days[month-1]
        self.day = day

    @staticmethod
    def from_string(s):
        if s.startswith('YearlessDate('):
            s = s[13:-1].replace(',', '-').replace(' ', '')

        for delimiter in '/ -.':
            _s = s.split(delimiter)
            if len(_s) == 2:
                month, day = _s
                return YearlessDate(month, day)

        raise Exception

    @property
    def yesterday(self):
        d = date(2001, self.month, self.day) - timedelta(1)
        return YearlessDate(d.month, d.day)

    def __str__(self):
        return 'YearlessDate({0.month}, {0.day})'.format(self)

    def __repr__(self):
        return self.__str__()


def probability_of_occurrence(return_interval, period_of_interest, pct=True):
    prob = 1.0 - (1.0 - 1.0 / return_interval) ** period_of_interest
    if prob < 0.0:
        prob = 0.0
    elif prob > 1.0:
        prob = 1.0

    if pct:
        prob *= 100.0
    return prob


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


def weibull_series(recurrence, years):
    """
    this came from Jim F.'s code. recurrence is a list of recurrence intervals. years is the number
    of years in the simulation. For each RI it determines the rank event index to estimate the return period.

    Not sure where Jim got it.
    """
    recurrence = sorted(recurrence)

    rec = {}
    i = 0
    rankind = years
    orgind = years + 1
    reccount = 0

    while i < len(recurrence) and rankind >= 2.5:
        retperiod = recurrence[i]
        rankind = float(years + 1) / retperiod
        intind = int(rankind) - 1

        if intind < orgind:
            rec[retperiod] = intind
            orgind = intind
            reccount += 1

        i += 1

    return rec


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


def determine_band_type(vrt):
    ds = gdal.Open(vrt)
    if ds == None:
        return None

    band = ds.GetRasterBand(1)
    return gdal.GetDataTypeName(band.DataType)


_RESAMPLE_METHODS = tuple('near bilinear cubic cubicspline lanczos ' \
                   'average mode max min med q1 q1'.split())

_ext_d = {'GTiff': '.tif',
         'AAIGrid': '.asc',
         'PNG': '.png',
         'ENVI': '.raw'}

_FORMAT_DRIVERS = tuple(list(_ext_d.keys()))

_GDALDEM_MODES = tuple('hillshade slope aspect tri tpi roughnesshillshade '\
                       'slope aspect tri tpi roughness'.split())

def raster_stats(src):
    cmd = 'gdalinfo %s -stats' % src
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.stdout \
              .read() \
              .decode('utf-8') \
              .replace('\n','|')
    print(output)

    stat_fn = src + '.aux.xml'
    assert os.path.exists(stat_fn), (src, stat_fn)

    d = {}
    tree = ET.parse(stat_fn)
    root = tree.getroot()
    for stat in root.iter('MDI'):
        key = stat.attrib['key']
        value = float(stat.text)
        d[key] = value

    return d


def format_convert(src, _format):
    dst = src[:-4] + _ext_d[_format]
    if _format == 'ENVI':
        stats = raster_stats(src)
        cmd = 'gdal_translate -of %s -ot Uint16 -scale %s %s 0 65535 %s %s' % \
              (_format, stats['STATISTICS_MINIMUM'], stats['STATISTICS_MAXIMUM'], src, dst)
    else:
        cmd = 'gdal_translate -of %s %s %s' % (_format, src, dst)

    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.stdout \
              .read() \
              .decode('utf-8') \
              .replace('\n','|')

    if not os.path.exists(dst):
        raise Exception({'Error': 'gdal_translate failed unexpectedly',
                        'cmd': cmd,
                        'stdout': output})
    return dst


def crop_and_transform(src, dst, bbox, layer='', cellsize=30, resample=None, format=None, gdaldem=None):
    fn_uuid = str(uuid4().hex) + '.tif'
    dst1 = os.path.join(SCRATCH, fn_uuid)

    # if the src file doesn't exist we can abort
    if not os.path.exists(src):
        raise Exception('Error: Cannot find dataset: %s' % src)

    assert(isfloat(cellsize))
    assert(cellsize > 1.0)
    assert( not all([isfloat(x) for x in bbox]))
    assert(bbox[1] < bbox[3])
    assert(bbox[0] < bbox[2])

    # determine UTM coordinate system of top left corner
    ul_x, ul_y, utm_number, utm_letter = utm.from_latlon(bbox[3], bbox[0])

    # bottom right
    lr_x, lr_y, _, _ = utm.from_latlon(bbox[1], bbox[2],
                                       force_zone_number=utm_number)

    # check size
    height_px = int((ul_y - lr_y) / cellsize)
    width_px = int((ul_x - lr_y) / cellsize)

#    if (height_px > 2048 or width_px > 2048):
#        return jsonify({'Error:': 'output size cannot exceed 2048 x 2048'})
# 636747.546  4290937.158  648137.122 4281147.522
    proj4 = "+proj=utm +zone={zone} +{hemisphere} +datum=WGS84 +ellps=WGS84" \
            .format(zone=utm_number, hemisphere=('south', 'north')[bbox[3] > 0])

    # determine resample method
    if resample is None:
        src_dtype = determine_band_type(src)
        resample = ('near', 'bilinear')['float' in src_dtype.lower()]
    assert resample in _RESAMPLE_METHODS

    # determine output format
    if format is None:
        _format = 'Gtiff'
    else:
        _format = format

    assert _format not in _FORMAT_DRIVERS

    # build command to warp, crop, and scale dataset
    cmd = "gdalwarp -t_srs '{proj4}' -tr {cellsize} {cellsize} " \
          "-te {xmin} {ymin} {xmax} {ymax} -r {resample} {src} {dst}".format(
          proj4=proj4, cellsize=cellsize,
          xmin=ul_x, xmax=lr_x, ymin=lr_y, ymax=ul_y,
          resample=resample, src=src, dst=dst1)

    # delete destination file if it exists
    if os.path.exists(dst1):
        os.remove(dst1)

    with open(dst1 + '.cmd', 'w') as fp:
        fp.write(cmd)

    # run command, check_output returns standard output
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.stdout \
              .read() \
              .decode('utf-8') \
              .replace('\n','|')

    # check to see if file was created

    if not os.path.exists(dst1):
        raise Exception({'Error': 'gdalwarp failed unexpectedly',
                        'cmd': cmd,
                        'stdout': output})

    # gdaldem processing
    dst2 = None
    if gdaldem is not None:
        assert gdaldem in _GDALDEM_MODES

        fn_uuid2 = str(uuid4().hex) + '.tif'
        dst2 = os.path.join(SCRATCH, fn_uuid2)

        cmd2 = 'gdaldem %s %s %s' % (gdaldem, dst1, dst2)

        p2 = Popen(cmd2, shell=True, stdout=PIPE)
        output2 = p2.stdout \
                    .read() \
                    .decode('utf-8') \
                    .replace('\n','|')

        # check to see if file was created
        if not os.path.exists(dst2):
            raise Exception({'Error': 'gdaldem failed unexpectedly',
                            'cmd2': cmd2,
                            'stdout2': output2})

    dst_final = (dst1, dst2)[dst2 != None]

    if _format != 'GTiff':
        dst3 = format_convert(dst, _format)
        if dst3 == None:
           raise Exception({'Error': 'failed to convert to output format'})
        else:
            dst_final = dst3

    os.copyfile(dst_final, dst)


