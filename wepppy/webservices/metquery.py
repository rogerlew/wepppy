# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import math
import os
from os.path import join as _join
from os.path import exists as _exists
from subprocess import Popen, PIPE
from flask import Flask, jsonify, request
from wepppy.all_your_base import RasterDatasetInterpolator

geodata_dir = '/geodata/'

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
}

def safe_float_parse(x):
    """
    Tries to parse {x} as a float. Returns None if it fails.
    """
    try:
        return float(x)
    except:
        return None

app = Flask(__name__)

@app.route('/monthly/catalog')
@app.route('/monthly/catalog/')
def query_monthly_catalog():
    """
    https://wepp1.nkn.uidaho.edu/webservices/metquery/monthly/catalog/
    """
    return jsonify(monthly_catalog)

@app.route('/monthly', methods=['GET', 'POST'])
@app.route('/monthly/', methods=['GET', 'POST'])
def query_monthly():
    """
    https://wepp1.nkn.uidaho.edu/webservices/metquery/monthly/?dataset=prism/ppt&lng=-116&lat=45
    https://wepp1.nkn.uidaho.edu/webservices/metquery/monthly/?dataset=daymet/prcp/mean&lng=-116&lat=45
    """
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if request.method == 'GET':
        lat = request.args.get('lat', None)
        lng = request.args.get('lng', None)
        dataset = request.args.get('dataset', None)
        method = request.args.get('method', None)
    else: # POST
        d = request.get_json()
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
        
    rds = RasterDatasetInterpolator(fname)
    data = rds.get_location_info(lng, lat, method)
    
    assert len(data) == 12
    
    return jsonify({'Latitude' : lat,
                    'Longitude' : lng,
                    'Dataset' : dataset,
                    'Description' : monthly_catalog[dataset]['Description'],
                    'Units' : monthly_catalog[dataset]['Units'],
                    'Method': method,
                    'MonthlyValues': data})

if __name__ == '__main__':
    app.run()

""" 
curl -sS 'http://127.0.0.1:5000/monthly/?lat=47&lng=-116&dataset=prism/ppt'
"""
