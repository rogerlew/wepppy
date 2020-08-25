# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
import json
import csv

from copy import deepcopy
from os.path import join as _join
from os.path import exists as _exists

import jsonpickle

# from wepppy.all_your_base import RasterDatasetInterpolator

from ...landuse import Landuse
from ...soils import Soils
from ...watershed import Watershed
from ...wepp import Wepp
from wepppy.wepp.soils.utils import read_lc_file, soil_specialization
from ...base import NoDbBase, TriggerEvents

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


class LakeTahoeNoDbLockedException(Exception):
    pass


class LakeTahoe(NoDbBase):
    __name__ = 'LakeTahoe'

    def __init__(self, wd, config):
        super(LakeTahoe, self).__init__(wd, config)

        self.lock()

        # noinspection PyBroadException
        try:

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
            
    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd):
        with open(_join(wd, 'lt.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, LakeTahoe), db

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'lt.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'lt.nodb.lock')

    def on(self, evt):
        if evt == TriggerEvents.LANDUSE_DOMLC_COMPLETE:
            self.remap_landuse()
        if evt == TriggerEvents.LANDUSE_BUILD_COMPLETE:
            pass
        elif evt == TriggerEvents.SOILS_BUILD_COMPLETE:
            self.modify_soils()
        elif evt == TriggerEvents.PREPPING_PHOSPHORUS:
            self.determine_phosphorus()

    @property
    def lt_doms(self):
        lc_dict = read_lc_file(_join(_data_dir, 'landSoilLookup.csv'))
        return set([lc_dict[k].LndcvrID for k in lc_dict])

    def remap_landuse(self):

        with open(_join(_data_dir, 'landcover_map.json')) as fp:
            lc_map = json.load(fp)

        lt_doms = self.lt_doms

        landuse = Landuse.getInstance(self.wd)
        landuse.lock()

        # noinspection PyBroadException
        try:
            for topaz_id, dom in landuse.domlc_d.items():
                if int(dom) not in lt_doms:
                    landuse.domlc_d[topaz_id] = lc_map[dom]
            
            landuse.dump_and_unlock()
            
        except Exception:
            landuse.unlock('-f')
            raise

    def modify_soils(self, default_wepp_type='Volcanic', lc_lookup_fn='landSoilLookup.csv'):
        wd = self.wd
        soils_dir = self.soils_dir
        
        lc_dict = read_lc_file(_join(_data_dir, lc_lookup_fn))
        with open(_join(_data_dir, 'lc_soiltype_map.json')) as fp:
            soil_type_map = json.load(fp)
        
        soils = Soils.getInstance(wd)
        soils.lock()

        # noinspection PyBroadException
        try:
            domsoil_d = soils.domsoil_d

            assert sum([(0, 1)[str(k).endswith('4')] for k in domsoil_d.keys()]) > 0, 'no soils in domsoil_d'
            
            landuse = Landuse.getInstance(wd)
            domlc_d = landuse.domlc_d
            
            _soils = {}
            for topaz_id, mukey in domsoil_d.items():
                dom = domlc_d[topaz_id]
                wepp_type = soil_type_map.get(mukey, default_wepp_type)
                
                replacements = lc_dict[(dom, wepp_type)]
                k = '%s-%s-%s' % (mukey, wepp_type, dom)
                src_fn = _join(soils_dir, '%s.sol' % mukey)
                dst_fn = _join(soils_dir, '%s.sol' % k)

                if k not in _soils:
                    soil_specialization(src_fn, dst_fn, replacements)
                    _soils[k] = deepcopy(soils.soils[mukey])
                    _soils[k].mukey = k
                    _soils[k].fname = '%s.sol' % k
                    _soils[k].area = 0.0
                    
                domsoil_d[topaz_id] = k
                    
            # need to recalculate the pct_coverages
            watershed = Watershed.getInstance(self.wd)
            for topaz_id, k in domsoil_d.items():
                _soils[k].area += watershed.area_of(topaz_id)

            for k in _soils:
                coverage = 100.0 * _soils[k].area / watershed.totalarea
                _soils[k].pct_coverage = coverage

            assert sum([(0, 1)[str(k).endswith('4')] for k in domsoil_d.keys()]) > 0, 'lost channels in domsoil_d'

            soils.soils = _soils            
            soils.domsoil_d = domsoil_d
            soils.dump_and_unlock()
        
        except Exception:
            soils.unlock('-f')
            raise
            
    def determine_phosphorus(self):
        # watershed = Watershed.getInstance(self.wd)
        # lng, lat = watershed.centroid

        wepp = Wepp.getInstance(self.wd)

        # d = {}
        # for opt in ['runoff', 'lateral', 'baseflow', 'sediment']:
        #    fn = _join(_data_dir, 'phosphorus', 'p_%s.tif' % opt)
        #    assert _exists(fn), fn
        #    raster = RasterDatasetInterpolator(fn)
        #    d[opt] = raster.get_location_info(lng, lat)

        d = dict(surf_runoff=0.004,
                 lateral_flow=0.005,
                 baseflow=0.006,
                 sediment=800)

        # noinspection PyBroadException
        try:
            wepp.lock()
            wepp.phosphorus_opts.parse_inputs(d)
            wepp.dump_and_unlock()
        except Exception:
            wepp.unlock('-f')
            raise
