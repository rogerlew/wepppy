import hashlib
import json
import string
from os.path import split as _split
from os.path import join as _join
from os.path import exists as _exists

from glob import glob
from datetime import datetime
from copy import deepcopy

from wepppy.soils.ssurgo import SoilSummary
from wepppy.all_your_base.geo import RasterDatasetInterpolator

from wepppy.eu.soils.esdac import ESDAC

def build_esdac_soils(orders, soils_dir, res_lyr_ksat_threshold=2.0):
    esd = ESDAC()

    soils = {}
    domsoil_d = {}

    for topaz_id, (lng, lat) in orders:
        key, h0, desc = esd.build_wepp_soil(lng, lat, soils_dir, res_lyr_ksat_threshold)
            
        if key not in soils:
            fname = key + '.sol'
            soils[key] = SoilSummary(
                mukey=key,
                fname=fname,
                soils_dir=soils_dir,
                build_date=str(datetime.now),
                desc=desc)
        domsoil_d[topaz_id] = key

    return soils, domsoil_d
