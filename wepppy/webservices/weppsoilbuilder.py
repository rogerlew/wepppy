#!/usr/bin/python

# Copyright (c) 2016, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import join as _join
from os.path import exists as _exists
import sys
import uuid
import math
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, Response
from pyproj import Proj, transform

sys.path.append('/home/roger')
from wepppy.ssurgo import *
from wepppy.all_your_base import isint
import array
import sys
import os
from bisect import bisect_left
from subprocess import Popen, PIPE
        
geodata_dir = '/geodata'
soil_dir = _join(geodata_dir, 'ssurgo', '201703', 'weppsoils')
static_dir = None


def isint(x):
    try:
        return float(int(x)) == float(x)
    except:
        return False


def isfloat(x):
    try:
        float(x)
        return True
    except:
        return False


def safe_float_parse(x):
    """
    Tries to parse {x} as a float. Returns None if it fails.
    """
    try:
        return float(x)
    except:
        return None


def round_pt5(x):
    return math.ceil(x*2.0)/2.0


def extract_desc(fn_contents):
    lines = fn_contents.split('\n')
    for L in lines:
        if L.startswith("'"):
            return L.split("'")[1]
            
    return None


class WeppSoil_db(object):
    """
    Provides fast querying of the whether a weppsoil exist for a particular
    mukey.
    
    The mukeys.dat and mukeys_mask are arrays of mukeys and validity states
    packed with struct.pack. The mukeys in the dat array are sorted allowing
    for the use of bisect search.
    
    The .dat files are built with scripts in wepppy.webservices.weppsoilbuildutils
    """
    def __init__(self, db_dir='./'):
        d_fn = _join(db_dir, 'mukeys.dat')
        m_fn = _join(db_dir, 'mukeys_mask.dat')

        n = int(os.stat(d_fn).st_size / 4)
        m = int(os.stat(m_fn).st_size)
        assert n == m, (n, m)

        self.mukeys = array.array('i')
        self.mukeys.fromfile(open(d_fn, 'rb'), n)
        self.mask = array.array('b')
        self.mask.fromfile(open(m_fn, 'rb'), n)
        
    def stat(self, m):
        a = self.mukeys
        x = int(m)
        i = bisect_left(a, x)
        if i != len(a) and a[i] == x:
            return self.mask[i] == 1
        return None


app = Flask(__name__)


@app.route('/')
def root():
    return jsonify({'Error': 'no mukey provided or location provided'})


@app.route('/validatemukeys', methods=['GET', 'POST'])
@app.route('/validatemukeys/', methods=['GET', 'POST'])
def validatemukeys():
    """
    http://wepp1.nkn.uidaho.edu/webservices/weppsoilbuilder/validatemukeys/?mukeys=100000,100001,100003,400016,400017,200153,200545,200
    # 200153,200545 are invalid
    # 200 is unknown
    """
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if request.method == 'GET':
        mukeys = request.args.get('mukeys', None)
    else: # POST
        d = request.get_json()
        mukeys = d.get('mukeys', None)
    if mukeys is None:
        return jsonify({'Error': 'mukeys not supplied'})

    mukeys = mukeys.split(',')
    mukeys = [int(v) for v in mukeys]
    
    weppsoil_db = WeppSoil_db(soil_dir)
    
    valid = []
    invalid = []
    unknown = []
    
    for m in sorted(mukeys):
        s = weppsoil_db.stat(m)
        if s is True:
            valid.append(m)
        elif s is False:
            invalid.append(m)
        else:
            unknown.append(m)
    
    return jsonify({'Valid': valid,
                    'Invalid': invalid,
                    'Unknown': unknown})


@app.route('/identifymukey', methods=['GET', 'POST'])
@app.route('/identifymukey/', methods=['GET', 'POST'])
def identifymukey():
    """
    http://wepp1.nkn.uidaho.edu/webservices/weppsoilbuilder/identifymukey/?lng=-116&lat=47
    # mukey is 2396861
    """
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if request.method == 'GET':
        lat = request.args.get('lat', None)
        lng = request.args.get('lng', None)
        srs = request.args.get('srs', None)
    else: # POST
        d = request.get_json()
        lat = d.get('lat', None)
        lng = d.get('lng', None)
        srs = d.get('srs', None)

    lat = safe_float_parse(lat)
    lng = safe_float_parse(lng)

    if lat is None or lng is None:
        return jsonify({'Error': 'Both lat and lng must be supplied for point location'})

    if srs is not None:
        from pyproj import Proj, transform
        try:
            p1 = Proj(init=srs)
        except:
            return jsonify({'Error': 'could not initialize projection'})

        p2 = Proj('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
        lng, lat = transform(p1, p2, lng, lat)

    # done validating
    img = '201703_n%0.1f_w%0.1f_.tif' % (round_pt5(lat), round_pt5(abs(lng)))
    src = _join(geodata_dir, 'ssurgo', '201703', 'rasters', img)
    
    if lat is None or lng is None:
        return jsonify({'Error': 'Could not find source dataset "%s"' % src})
        
    cmd = ['gdallocationinfo', '-geoloc', '-valonly', src, str(lng), str(lat)]
    p = Popen(cmd, stdout=PIPE)
    p.wait()
    mukey = p.stdout.read().strip()

    if not isint(mukey):
        return jsonify({'Error': ' '.join(cmd)})
        
    return jsonify({'Latitude':lat,
                    'Longitude': lng,
                    'SRS': srs,
                    'Mukey': int(mukey)})

@app.route('/identifymukeys', methods=['GET', 'POST'])
@app.route('/identifymukeys/', methods=['GET', 'POST'])
def identifymukeys():
    """
    http://wepp1.nkn.uidaho.edu/webservices/weppsoilbuilder/identifymukeys/?bounds=-116.1,46,-116,46.1
    """
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if request.method == 'GET':
        bounds = request.args.get('bounds', None)
        srs = request.args.get('srs', None)
    else: # POST
        d = request.get_json()
        bounds = d.get('bounds', None)
        srs = d.get('srs', None)

    # validate bounds
    bounds = [v.strip() for v in bounds.split(',')]
    
    if len(bounds) != 4:
        return jsonify({'Error': 'Expecting bounds in left,bottom,right,top'})
        
    if not all([isfloat(v) for v in bounds]):
        return jsonify({'Error': 'Could not parse bound parameters'})
        
    L, b, r, t = [float(v) for v in bounds]
     
    if r <= L or t <= b:
        return jsonify({'Error': 'Expecting bounds in left,bottom,right,top'})

    # proces srs
    if srs is not None:
        from pyproj import Proj, transform
        try:
            p1 = Proj(init=srs)
        except:
            return jsonify({'Error': 'could not initialize projection'})

        p2 = Proj('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
        L, b = transform(p1, p2, L, b)
        r, t = transform(p1, p2, r, t)

    # extract data from map
    src = _join(geodata_dir, 'ssurgo', '201703', '.vrt')
    _uuid =  str(uuid.uuid4())
    os.mkdir(_join(static_dir, _uuid))
    dst = _join(static_dir, _uuid, 'ssurgomap.tif')
    log_fn = _join(static_dir, _uuid, 'gdal_translate.log')
    
    # build command to warp, crop, and scale dataset
    cmd = ['gdal_translate', '-projwin', L, t, r, b, src, dst]
    cmd = [str(v) for v in cmd]

    # delete destination file if it exists
    if _exists(dst):
        os.remove(dst)

    # run command, check_output returns standard output
    _log = open(log_fn, "w")
    p = Popen(cmd, stdout=_log, stderr=_log)
    p.wait()
    _log.close()
    output = open(log_fn).read()

    # check to see if file was created
    if not _exists(dst):
        return jsonify({'Error': 'gdal_translate failed unexpectedly',
                        'cmd': cmd,
                        'stdout': output})
    sm = SurgoMap(dst)
    
    return jsonify({'Bounds': [L, b, r, t],
                    'SRS': srs,
                    'Mukeys': [int(v) for v in sm.mukeys]})

@app.route('/fetchsoils', methods=['GET', 'POST'])
@app.route('/fetchsoils/', methods=['GET', 'POST'])
def fetchsoils():
    """
    http://wepp1.nkn.uidaho.edu/webservices/weppsoilbuilder/fetchsoils/?mukeys=100000,100001,100003,400016,400017,200153,200545,200
    """
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if request.method == 'GET':
        mukeys = request.args.get('mukeys', None)
    else: # POST
        d = request.get_json()
        mukeys = d.get('mukeys', None)

    mukeys = mukeys.split(',')
    if not all([isint(v) for v in mukeys]):
        return jsonify({'Error': 'mukeys must be integers'})
        
    result = []
    for mukey in mukeys:
        fn = '%s.sol' % mukey
        fn_cache = _join(soil_dir, 'cache', fn[:3], fn)
        fn_invalid = _join(soil_dir, 'invalid', fn[:3], mukey)
        
        mukey = int(mukey)
        if _exists(fn_cache):
            fn_contents = open(fn_cache).read()
            desc = extract_desc(fn_contents)
            result.append({'Mukey': mukey,
                            'Status': 'valid',
                            'BuildDate': str(datetime.fromtimestamp(os.path.getmtime(fn_cache))),
                            'Description': desc,
                            'FileName': fn,
                            'FileContents': fn_contents})
                                       
        # check to see if sol is invalid
        elif _exists(fn_invalid):
            result.append({'Mukey': mukey,
                           'Status': 'invalid',
                           'BuildAttemptDate': str(datetime.fromtimestamp(os.path.getmtime(fn_invalid)))})
        else:
            result.append({'Mukey': mukey,
                           'Status': 'unknown'})
        
        
    return jsonify(result)
    
@app.route('/fetchsoil/<mukey>')
@app.route('/fetchsoil/<mukey>/')
def fetchsoil(mukey):
    """
    http://wepp1.nkn.uidaho.edu/webservices/weppsoilbuilder/fetchsoil/100000/
    """
    fn = '%s.sol' % mukey
    fn_cache = _join(soil_dir, 'cache', fn[:3], fn)
    fn_invalid = _join(soil_dir, 'invalid', fn[:3], mukey)
    
    if _exists(fn_cache):
        result = open(fn_cache).read()
                                   
    # check to see if sol is invalid
    elif _exists(fn_invalid):
        result = 'INVALID'
    else:
        result = 'UNKNOWN'
        
    r = Response(response=result, status=200, mimetype="text/plain")
    r.headers["Content-Type"] = "text/plain; charset=utf-8"
    return r
    
    """
    # build soil if it doesn't exist
    if not _exists(fn_cache):
        ssurgo_c = SurgoSoilCollection([int(mukey)])
        ssurgo_c.makeWeppSoils()
        
        if len(ssurgo_c.weppSoils) != 1:
            with open(fn_invalid, 'w') as fp:
                fp.write(str(datetime.now()))
            return jsonify({'Error': 'Could not build weppsoil for mukey = %s' % mukey})
        
        txt = ssurgo_c.weppSoils.values()[0] \
                      .build_file_contents()
        
        with open(fn_cache, 'w') as fp:
            fp.write(txt)
    """
    
if __name__ == '__main__':
    app.run()

""" 
curl -sS 'http://127.0.0.1:5000/monthly/?lat=47&lng=-116&dataset=prism/ppt'
"""
