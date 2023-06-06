import hashlib
import json
import string
from os.path import split as _split
from os.path import join as _join
from os.path import exists as _exists

from glob import glob
from datetime import datetime
from copy import deepcopy

from multiprocessing import Pool
import math

from wepppy.soils.ssurgo import SoilSummary
from wepppy.all_your_base.geo import RasterDatasetInterpolator
from wepppy.eu.soils.esdac import ESDAC

from wepppy.all_your_base import NCPU
NCPU = math.ceil(NCPU * 0.6)


def _build_esdac_soil(kwargs):
    topaz_id = kwargs['topaz_id']
    lng = kwargs['lng']
    lat = kwargs['lat']
    soils_dir = kwargs['soils_dir']
    res_lyr_ksat_threshold = kwargs['res_lyr_ksat_threshold']

    esd = ESDAC()
    key, h0, desc = esd.build_wepp_soil(lng, lat, soils_dir, res_lyr_ksat_threshold)

    return topaz_id, key, h0, desc


def build_esdac_soils(orders, soils_dir, res_lyr_ksat_threshold=2.0):

    args = []
    for topaz_id, (lng, lat) in orders:
        args.append(dict(topaz_id=topaz_id, lng=lng, lat=lat, soils_dir=soils_dir, 
                         res_lyr_ksat_threshold=res_lyr_ksat_threshold))
    
    pool = Pool(processes=NCPU)
    results = pool.map(_build_esdac_soil, args)
    pool.close()
    pool.join()

    soils = {}
    domsoil_d = {}
    for topaz_id, key, h0, desc in results:
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
