from typing import Tuple
import json

import os
from os.path import exists as _exists
from os.path import split as _split
import shutil
import math
from uuid import uuid4

# noinspection PyPep8Naming
import xml.etree.ElementTree as ET

from subprocess import Popen, PIPE

import utm
import numpy as np
from osgeo import gdal, osr, ogr
import subprocess

from deprecated import deprecated

from ..all_your_base import isfloat
from .geo_transformer import GeoTransformer
from .locationinfo import RasterDatasetInterpolator

import rasterio
import rasterio.warp
from rasterio.warp import reproject, Resampling, calculate_default_transform

from wepppy import f_esri as _f_esri

gdal.UseExceptions()

SCRATCH_DIR = '/dev/shm'


wgs84_proj4 = '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'
wgs84_wkt = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],'\
            'AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'\
            'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]'


resample_methods = 'near bilinear cubic cubicspline lanczos ' \
                'average mode max min med q1 q1'.split()
resample_methods = tuple(resample_methods)


# https://github.com/rogerlew/gdal-grande

def has_f_esri():
    return _f_esri.has_f_esri()


def f_esri_gpkg_to_gdb(gpkg_fn, gdb_fn):
    """
    Runs the docker command to convert a GeoPackage to a FileGDB.
    """

    _f_esri.c2c_gpkg_to_gdb(gpkg_fn, gdb_fn)

def utm_raster_transform(wgs_extent, src_fn, dst_fn, cellsize, resample='bilinear'):
    west, south, east, north = wgs_extent

    assert src_fn is not None, 'Failed to download DEM'
    assert _exists(src_fn), 'Failed to save DEM'

    ul_x, ul_y, utm_number, utm_letter = utm.from_latlon(north, west)

    # bottom right
    lr_x, lr_y, _, _ = utm.from_latlon(south, east, 
                                       force_zone_number=utm_number)

    # check size
    height_px = int((ul_y - lr_y) / cellsize)
    width_px = int((ul_x - lr_y) / cellsize)

    proj4 = "+proj=utm +zone={zone} +{hemisphere} +datum=WGS84 +ellps=WGS84" \
            .format(zone=utm_number, hemisphere=('south', 'north')[north > 0])

    assert resample in resample_methods, 'resample method not valid'

    # build command to warp, crop, and scale dataset
    cmd = "gdalwarp -t_srs '{proj4}' -tr {cellsize} {cellsize} " \
          "-te {xmin} {ymin} {xmax} {ymax} -r {resample} {src} {dst}".format(
          proj4=proj4, cellsize=cellsize,
          xmin=ul_x, xmax=lr_x, ymin=lr_y, ymax=ul_y,
          resample=resample, src=src_fn, dst=dst_fn)

    # delete destination file if it exists
    if os.path.exists(dst_fn):
        os.remove(dst_fn)

    # run command, check_output returns standard output
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.stdout \
              .read() \
              .decode('utf-8') \
              .replace('\n','|')

    # check to see if file was created
    assert os.path.exists(dst_fn), json.dumps(dict(cmd=cmd, output=output))

def validate_srs(file_path):
    """
    Validates the SRS of a given file using gdalsrsinfo.

    Parameters:
        file_path (str): Path to the file to validate.

    Returns:
        bool: True if the SRS is valid, False otherwise.
    """
    cmd = ["gdalsrsinfo", "-v", file_path]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
                                universal_newlines=True, encoding='utf-8')

        if "Validate Succeeds" in result.stdout:
            return True
    except subprocess.CalledProcessError:
        # This block will be executed if gdalsrsinfo returns a non-zero exit status
        pass

    return False


def utm_srid(zone, northern) -> [str, None]:
    return f"326{zone:02d}" if northern else f"327{zone:02d}"


def centroid_px(indx, indy) -> Tuple[int, int]:
    """
    given a sets of x and y indices calulates a central [x,y] index
    """
    return (int(round(float(np.mean(indx)))),
            int(round(float(np.mean(indy)))))


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


def get_raster_extent(match_fn, wgs=False):
    rdi = RasterDatasetInterpolator(match_fn)
    proj4 = rdi.proj4

    if wgs:
        extent = rdi.extent
    else:
        extent = rdi.left, rdi.lower, rdi.right, rdi.upper
    return extent


def raster_stacker(src_fn, match_fn, dst_fn, resample='near'):
    """
    Warps a source raster to match the grid of another raster using rasterio.

    Args:
        src_fn (str): Path to the source raster to be warped.
        match_fn (str): Path to the raster whose grid (CRS, transform, extent)
                        will be used as the target.
        dst_fn (str): Path for the output warped raster.
        resample (str): Resampling algorithm (e.g., 'near', 'bilinear', 'cubic').
    """
    # A mapping from string names to rasterio's Resampling methods
    resampling_methods = {
        'near': Resampling.nearest,
        'bilinear': Resampling.bilinear,
        'cubic': Resampling.cubic,
        'cubic_spline': Resampling.cubic_spline,
        'lanczos': Resampling.lanczos,
        'average': Resampling.average,
        'mode': Resampling.mode
    }
    
    if resample not in resampling_methods:
        raise ValueError(f"Invalid resampling method '{resample}'. "
                         f"Choose from: {list(resampling_methods.keys())}")

    # 1. Use the "match" raster to define the output grid.
    with rasterio.open(match_fn) as match:
        # Get the metadata to use for the output file.
        # This ensures the new raster has the exact same grid as the match raster.
        out_profile = match.profile.copy()
    
    # 2. Open the source raster to get its data.
    with rasterio.open(src_fn) as src:
        # Update the output profile with source properties and compression.
        # It's important to use the source's nodata value and data type.
        out_profile.update({
            'compress': 'lzw',
            'nodata': src.nodata,
            'dtype': src.dtypes[0]
        })
        
        # 3. Create the destination file and perform the reprojection.
        with rasterio.open(dst_fn, 'w', **out_profile) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=match.transform,
                dst_crs=match.crs,
                resampling=resampling_methods[resample]
            )


@deprecated
def warp2match(src_filename, match_filename, dst_filename):
    # Source
    src = gdal.Open(src_filename, gdal.GA_ReadOnly)
    src_proj = src.GetProjection()

    nbands = src.RasterCount
    dtype = src.GetRasterBand(1).DataType

    # We want a section of source that matches this:
    match_ds = gdal.Open(match_filename, gdal.GA_ReadOnly)
    match_proj = match_ds.GetProjection()
    match_geotrans = match_ds.GetGeoTransform()
    wide = match_ds.RasterXSize
    high = match_ds.RasterYSize

    # Output / destination
    dst = gdal.GetDriverByName('GTiff').Create(dst_filename, wide, high, nbands, dtype)
    dst.SetGeoTransform(match_geotrans)
    dst.SetProjection(match_proj)

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
    transform = data.GetGeoTransform()
    minx = transform[0]
    maxy = transform[3]
    maxx = minx + transform[1] * data.RasterXSize
    miny = maxy + transform[5] * data.RasterYSize
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


def read_tif(fn, dtype=np.float64, band=1):
    """
    use gdal to read an tif file and return the data and the
    transform
    """
    assert _exists(fn), "Cannot open %s" % fn

    ds = rasterio.open(fn)
    transform = ds.transform.to_gdal()
    proj = None
    if ds.crs:
        proj = ds.crs.to_proj4()
    _data = ds.read()
    data = np.array(_data[band-1,:,:], dtype=dtype).T

    data = np.array(data, dtype=dtype)

    return data, transform, proj


def read_arc(fn, dtype=np.float64):
    """
    use gdal to read an arc file and return the data and the
    transform
    """
    assert _exists(fn), "Cannot open %s" % fn

    ds = rasterio.open(fn)
    transform = ds.transform.to_gdal()
    proj = ds.crs.to_proj4()

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

    psz_projection = ds.GetProjectionRef()
    srs = None
    if psz_projection is not None:
        srs = osr.SpatialReference()

    transform = ds.GetGeoTransform()

    # initialize a new raster in memory
    driver = gdal.GetDriverByName('MEM')
    target_ds = driver.Create('',
                              ds.RasterXSize,
                              ds.RasterYSize,
                              1, gdal.GDT_Byte)
    target_ds.SetGeoTransform(transform)
    target_ds.SetProjection(psz_projection)

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


def get_utm_zone(srs):
    """
    extracts the utm_zone from an osr.SpatialReference object (srs)

    returns the utm_zone as an int, returns None if utm_zone not found
    """
    if not isinstance(srs, osr.SpatialReference):
        if _exists(srs):
            fn = srs
            ds = gdal.Open(fn)
            assert ds is not None
            srs = osr.SpatialReference()

    if not isinstance(srs, osr.SpatialReference):
        raise TypeError('srs is not a osr.SpatialReference instance')

    if srs.IsProjected() != 1:
        return None

    projcs = srs.GetAttrValue('projcs').replace(' ', '').replace('_', '')
    assert 'UTM' in projcs

    datum = None
    if 'NAD83' in projcs:
        datum = 'NAD83'
    elif 'WGS84' in projcs:
        datum = 'WGS84'
    elif 'NAD27' in projcs:
        datum = 'NAD27'

    # should be something like NAD83 / UTM zone 11N...

    if 'UTM' not in projcs:
        return None

    utm_token = projcs.split('UTM')[1]

    # noinspection PyBroadException
    try:
        utm_zone = int(''.join([k for k in utm_token if k in '0123456789']))
    except Exception:
        return None

    if utm_zone < 0 or utm_zone > 60:
        return None

    hemisphere = projcs[-1]
    return datum, utm_zone, hemisphere


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
    lat1, lng1, lat2, lng2 = [math.radians(v) for v in (lat1, lng1, lat2, lng2)]

    # calculate haversine
    lat = lat2 - lat1
    lng = lng2 - lng1
    d = math.sin(lat * 0.5) ** 2 + \
        math.cos(lat1) * math.cos(lat2) * math.sin(lng * 0.5) ** 2
    h = 2 * _AVG_EARTH_RADIUS * math.asin(math.sqrt(d))
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


def determine_band_type(vrt):
    ds = gdal.Open(vrt)
    if ds is None:
        return None

    band = ds.GetRasterBand(1)
    return gdal.GetDataTypeName(band.DataType)


_RESAMPLE_METHODS = tuple('near bilinear cubic cubicspline lanczos '
                          'average mode max min med q1 q1'.split())

_ext_d = {'GTiff': '.tif',
          'AAIGrid': '.asc',
          'PNG': '.png',
          'ENVI': '.raw'}

_FORMAT_DRIVERS = tuple(list(_ext_d.keys()))

_GDALDEM_MODES = tuple('hillshade slope aspect tri tpi roughnesshillshade '
                       'slope aspect tri tpi roughness'.split())


def raster_stats(src):
    cmd = 'gdalinfo %s -stats' % src
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.stdout \
              .read() \
              .decode('utf-8') \
              .replace('\n', '|')

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
              .replace('\n', '|')

    if not os.path.exists(dst):
        raise Exception({'Error': 'gdal_translate failed unexpectedly',
                         'cmd': cmd,
                         'stdout': output})
    return dst


def crop_and_transform(src, dst, bbox, layer='', cellsize=30, resample=None, fmt=None, gdaldem=None):
    fn_uuid = str(uuid4().hex) + '.tif'
    dst1 = os.path.join(SCRATCH_DIR, fn_uuid)

    # if the src file doesn't exist we can abort
    if not os.path.exists(src):
        raise Exception('Error: Cannot find dataset: %s' % src)

    assert(isfloat(cellsize))
    assert(cellsize > 1.0)
    assert(not all([isfloat(x) for x in bbox]))
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
    if fmt is None:
        _format = 'Gtiff'
    else:
        _format = fmt

    assert _format not in _FORMAT_DRIVERS

    # build command to warp, crop, and scale dataset
    cmd = "gdalwarp -t_srs '{proj4}' -tr {cellsize} {cellsize} " \
          "-te {xmin} {ymin} {xmax} {ymax} -r {resample} {src} {dst}" \
          .format(proj4=proj4, cellsize=cellsize,
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
              .replace('\n', '|')

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
        dst2 = os.path.join(SCRATCH_DIR, fn_uuid2)

        cmd2 = 'gdaldem %s %s %s' % (gdaldem, dst1, dst2)

        p2 = Popen(cmd2, shell=True, stdout=PIPE)
        output2 = p2.stdout \
                    .read() \
                    .decode('utf-8') \
                    .replace('\n', '|')

        # check to see if file was created
        if not os.path.exists(dst2):
            raise Exception({'Error': 'gdaldem failed unexpectedly',
                             'cmd2': cmd2,
                             'stdout2': output2})

    dst_final = (dst1, dst2)[dst2 is not None]

    if _format != 'GTiff':
        dst3 = format_convert(dst, _format)
        if dst3 is None:
            raise Exception({'Error': 'failed to convert to output format'})
        else:
            dst_final = dst3

    shutil.copyfile(dst_final, dst)


def rasterize_geometry_from_geojson(dem_fn, geometry, dst_fn):
    import pyproj
    from rasterio.features import rasterize
    from shapely.ops import transform as shapely_transform

    # Open the DEM GeoTIFF file
    with rasterio.open(dem_fn) as dem:
        # Get the metadata from the DEM
        transform = dem.transform
        crs = dem.crs  # This is the UTM CRS of the DEM
        width = dem.width
        height = dem.height
        dtype = rasterio.uint8  # Adjust the dtype as needed

    # Reproject the geometry from WGS84 to the UTM CRS
    project = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform
    geometry_utm = shapely_transform(project, geometry)

    # Create an empty raster with the same dimensions as the DEM
    raster_shape = (height, width)
    out_raster = np.zeros(raster_shape, dtype=dtype)

    # Convert geometry to the format required for rasterize
    shapes = [(geometry_utm, 1)]

    # Rasterize the geometry
    rasterized = rasterize(
        shapes,
        out_shape=raster_shape,
        transform=transform,
        fill=0,
        dtype=dtype,
    )

    # Save the rasterized output to the specified file
    with rasterio.open(
        dst_fn,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(rasterized, 1)
