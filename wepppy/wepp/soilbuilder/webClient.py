# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from os.path import join as _join
from os.path import exists as _exists

import requests
from posixpath import join as urljoin

from wepppy.ssurgo import SoilSummary

_soilbuilder_url = "https://wepp1.nkn.uidaho.edu/webservices/weppsoilbuilder/"


def validatemukeys(mukeys):

    global _soilbuilder_url
    
    r = requests.post(urljoin(_soilbuilder_url, 'validatemukeys'), 
                      params=dict(mukeys=','.join([str(v) for v in mukeys])))
        
    if r.status_code != 200:
        raise Exception("Encountered error retrieving from weppsoilbuilder")

    # noinspection PyBroadException
    try:
        _json = r.json()
    except Exception:
        _json = None
    
    if _json is None:
        raise Exception("Cannot parse json from weppsoilbuilder response")
        
    return _json


def fetchsoils(mukeys, dst_dir):
    """
    retrieves soils from a wepppy.webservices.weppsoilbuilder webservice
    """
    global _soilbuilder_url
    assert _exists(dst_dir)
    
    r = requests.post(urljoin(_soilbuilder_url, 'fetchsoils'), 
                      params=dict(mukeys=','.join([str(v) for v in mukeys])))
        
    if r.status_code != 200:
        raise Exception("Encountered error retrieving from weppsoilbuilder")

    # noinspection PyBroadException
    try:
        _json = r.json()
    except Exception:
        _json = None
    
    if _json is None:
        raise Exception("Cannot parse json from weppsoilbuilder response")
        
    for data in _json:
        fn = _join(dst_dir, data['FileName'])
        contents = data['FileContents']
        data['soils_dir'] = dst_dir
        
        with open(fn, 'w') as fp:
            fp.write(contents)
            
    return dict(zip(mukeys, [SoilSummary(**data) for data in _json]))


if __name__ == "__main__":
    from pprint import pprint
    _mukeys = [100000, 100001, 100003, 400016,
               400017, 200153, 200545, 200]
    
    pprint(validatemukeys(_mukeys))
    
    fetchsoils(_mukeys, './')
