#!/usr/bin/python

# Copyright (c) 2016, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""
WMSesque is a flask web application that provides an endpoint for acquiring
tiled raster datasets. The web application reprojects (warps) the map to UTM
based on the top left corner of the bounding box {bbox} provided to the
application. It also scales the map data based on arguments supplied in the
request {cellsize}. Returns GeoTiff. Header contains information related to
the request and the map processing.

The WMSesque server assumes that the datasets have been downloaded onto the
machine running EMSeque. The datasets should be in the {geodata_dir}. Each
should have its own directory with a subdirectory for each year. Tiles or
single maps should be combined as a gdal virtual dataset (vrt). WMSesque
looks for: {geodata_dir}/{dataset}/{year}/.vrt
"""

import subprocess
import fnmatch
import os
import shlex
from uuid import uuid4

import utm
from flask import Flask, jsonify, url_for, request, make_response, send_file
from osgeo import gdal
import xml.etree.ElementTree as ET

geodata_dir = '/geodata'
resample_methods = 'near bilinear cubic cubicspline lanczos ' \
                   'average mode max min med q1 q1'.split()
resample_methods = tuple(resample_methods)

ext_d = {'GTiff': '.tif',
         'AAIGrid': '.asc',
         'PNG': '.png',
         'ENVI': '.raw'}

format_drivers = tuple(list(ext_d.keys()))

gdaldem_modes = 'hillshade slope aspect tri tpi roughnesshillshade '\
                'slope aspect tri tpi roughness'.split()
gdaldem_modes = tuple(gdaldem_modes)

_this_dir = os.path.dirname(__file__)
_catalog = os.path.join(_this_dir, 'catalog')


def raster_stats(src):
    cmd = 'gdalinfo %s -stats' % src
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
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
    dst = src[:-4] + ext_d[_format]
    if _format == 'ENVI':
        stats = raster_stats(src)
        cmd = 'gdal_translate -of %s -ot Uint16 -scale %s %s 0 65535 %s %s' % \
              (_format, stats['STATISTICS_MINIMUM'], stats['STATISTICS_MAXIMUM'], src, dst)
    else:
        cmd = 'gdal_translate -of %s %s %s' % (_format, src, dst)

    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    output = p.stdout \
              .read() \
              .decode('utf-8') \
              .replace('\n','|')

    if os.path.exists(dst):
        return dst

    return None


def determine_band_type(vrt):
    ds = gdal.Open(vrt)
    if ds == None:
        return None

    band = ds.GetRasterBand(1)
    return gdal.GetDataTypeName(band.DataType)


def build_catalog(geodata):
    """
    recursively searches for .vrt files from the
    path speicified by {geodata_dir}
    """
    fp = open(_catalog, 'w')


    dirs = [os.path.join(geodata, o) for o in os.listdir(geodata)
            if os.path.isdir(os.path.join(geodata, o))]

    dirs = [d for d in dirs if 'weppcloud_runs' not in d]

    for _dir in dirs:
        for root, dirnames, filenames in os.walk(_dir):
            print(root, dirnames)

            for filename in fnmatch.filter(filenames, '.vrt'):
                path = os.path.join(root, filename)
                fp.write(path + '\n')
    fp.close()


def find_maps(geodata):
    """
    recursively searches for .vrt files from the
    path speicified by {geodata_dir}
    """
    maps = open(_catalog).readlines()
    maps = [fn.strip() for fn in maps if fn.startswith(geodata)]

    return maps


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
        coords.extend([None for i in xrange(4-n)])
    if n > 4:
        coords = coords[:4]

    return tuple(map(safe_float_parse, coords))


app = Flask(__name__)


@app.route('/')
def api_root():
    """
    Return a list of available maps
    """
    d = []
    for map in find_maps(geodata_dir):
        path = os.path.split(map)[0].replace(geodata_dir, '')
        d.append(path)
    return jsonify(d)


@app.route('/<dataset>')
@app.route('/<dataset>/')
def api_dataset(dataset):
    """
    Return a list of available years
    """

    path = os.path.join(geodata_dir, dataset)
    if os.path.exists(path):
        return jsonify(find_maps(path))
    else:
        return 'error: cannot find dataset: %s' % dataset


@app.route('/<dataset>/<year>')
@app.route('/<dataset>/<year>/')
@app.route('/<dataset>/<year>/<layer>')
@app.route('/<dataset>/<year>/<layer>/')
@app.route('/<dataset>/<year>/<layer>/<foo>')
@app.route('/<dataset>/<year>/<layer>/<foo>/')
@app.route('/<dataset>/<year>/<layer>/<foo>/<bar>')
@app.route('/<dataset>/<year>/<layer>/<foo>/<bar>/')
def api_dataset_year(dataset, year, layer='', foo='', bar='', methods=['GET', 'POST']):
    """
    Process and serve the map
    """
    # determine src vrt and dst filename
    if layer == '':
        src = os.path.join(geodata_dir, dataset, year,'.vrt')
    else:
        if foo == '':
            src = os.path.join(geodata_dir, dataset, year, layer, '.vrt')
        else:
            if bar == '':
                src = os.path.join(geodata_dir, dataset, year, layer, foo, '.vrt')
            else:
                src = os.path.join(geodata_dir, dataset, year, layer, foo, bar, '.vrt')

    fn_uuid = str(uuid4().hex) + '.tif'
    dst = os.path.join('/var/www/WMesque/FlaskApp/static', fn_uuid)

    # if the src file doesn't exist we can abort
    if not os.path.exists(src):
        return jsonify({'Error': 'Cannot find dataset/year: %s/%s' % (dataset, year)})

    # if request is not GET we should abort
    # need to implement POST
    if request.method not in ['GET']:
        return jsonify({'Error': 'Expecting GET'})

    # if cellsize argument is not supplied assume 30m
    if 'cellsize' not in request.args:
        cellsize = 30.0 # in meters
    else:
        cellsize = safe_float_parse(request.args['cellsize'])
        if cellsize == None:
            return jsonify({'Error': 'Cellsize should be a float'})

    if cellsize < 1.0:
        return jsonify({'Error': 'Cellsize must be greater than 1'})

    # parse bbox
    if 'bbox' not in request.args:
        return jsonify({'Error': 'bbox is required (left, bottom, right, top)'})

    bbox = request.args['bbox']
    bbox = parse_bbox(bbox)

    if any([x==None for x in bbox]):
        return jsonify({'Error': 'bbox contains non float values'})

    if bbox[1] > bbox [3] or bbox[0] > bbox[2]:
        return jsonify({'Error': 'Expecting bbox defined as: left, bottom, right, top'})

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

    proj4 = "+proj=utm +zone={zone} +{hemisphere} +datum=WGS84 +ellps=WGS84" \
            .format(zone=utm_number, hemisphere=('south', 'north')[bbox[3] > 0])

    # determine resample method
    if 'resample' not in request.args:
        src_dtype = determine_band_type(src)
        resample = ('near', 'bilinear')['float' in src_dtype.lower()]
    else:
        resample = request.args['resample']
        if resample not in resample_methods:
            return jsonify({'Error': 'resample method not valid'})

    # determine output format
    if 'format' not in request.args:
        _format = 'Gtiff'
    else:
        _format = request.args['format']
        if _format not in format_drivers:
            return jsonify({'Error': 'format driver not valid' + _format})

    # build command to warp, crop, and scale dataset
    cmd = "gdalwarp -t_srs '{proj4}' -tr {cellsize} {cellsize} " \
          "-te {xmin} {ymin} {xmax} {ymax} -r {resample} {src} {dst}".format(
          proj4=proj4, cellsize=cellsize,
          xmin=ul_x, xmax=lr_x, ymin=lr_y, ymax=ul_y,
          resample=resample, src=src, dst=dst)

    # delete destination file if it exists
    if os.path.exists(dst):
        os.remove(dst)

    with open(dst + '.cmd', 'w') as fp:
        fp.write(cmd)

    # run command, check_output returns standard output
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    output = p.stdout \
              .read() \
              .decode('utf-8') \
              .replace('\n','|')

    # check to see if file was created
    if not os.path.exists(dst):
        return jsonify({'Error': 'gdalwarp failed unexpectedly',
                        'cmd': cmd,
                        'stdout': output})

    # gdaldem processing
    dst2 = None
    gdaldem = None
    if 'gdaldem' in request.args:
        if dataset not in ['ned1']:
            return jsonify({'Error': 'gdaldem cannot be applied to dataset'})

        gdaldem = request.args['gdaldem'].lower()
        if gdaldem not in gdaldem_modes:
            return jsonify({'Error': 'Invalid gdaldem mode: %s' % gdaldem})

        fn_uuid2 = str(uuid4().hex) + '.tif'
        dst2 = os.path.join('/var/www/WMesque/FlaskApp/static', fn_uuid)

        cmd2 = 'gdaldem %s %s %s' % (gdaldem, dst, dst2)

        output2 = subprocess.Popen(cmd2, shell=True, stdout=subprocess.PIPE).stdout.read()
        output2 = output.replace('\n','|')

        # check to see if file was created
        if not os.path.exists(dst2):
            return jsonify({'Error': 'gdaldem failed unexpectedly',
                            'cmd2': cmd2,
                            'stdout2': output2})

    # build response
    dst_final = (dst, dst2)[dst2 != None]
    if layer == '':
        fname = '%s_%s%s' % (dataset, year, ext_d[_format])
    else:
        fname = '%s_%s_%s%s' % (dataset, year, layer, ext_d[_format])

    if _format != 'GTiff':
        dst3 = format_convert(dst, _format)
        if dst3 == None:
            return jsonify({'Error': 'failed to convert to output format'})
        else:
            dst_final = dst3

    response = make_response(send_file(dst_final))

    if _format == 'AAIGrid':
        response.headers['Content-Type'] = 'text/plain'
    elif _format == 'PNG':
        response.headers['Content-Type'] = 'text/png'
    elif _format == 'ENVI':
        response.headers['Content-Type'] = 'application/octet-stream'
    else:
        response.headers['Content-Type'] = 'image/tiff'

    response.headers['Content-Disposition'] = 'attachment; filename=' + fname
    response.headers['Meta'] = {'bbox': bbox,
                                'cache': dst,
                                'dataset': dataset,
                                'year': year,
                                'cellsize': cellsize,
                                'ul': {'ul_x':ul_x,
                                       'ul_y':ul_y,
                                       'utm_number':utm_number,
                                       'utm_letter':utm_letter},
                                'proj4': proj4,
                                'cmd': cmd,
                                'url': request.url,
                                'stdout': output}

    if gdaldem != None:
        response.headers['Meta-gdaldem'] = {'mode': gdaldem,
                                            'cmd': cmd2,
                                            'stdout': output2,
                                            'cache': dst2}

    # return response
    return response


if __name__ == '__main__':
    import sys

    if 'build' in sys.argv[-1]:
        build_catalog('/geodata')

    else:
        app.run()
