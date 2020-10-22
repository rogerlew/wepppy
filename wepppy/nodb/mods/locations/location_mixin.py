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
from os.path import split as _split
from os.path import exists as _exists

import jsonpickle

# from wepppy.all_your_base import RasterDatasetInterpolator

from ...landuse import Landuse
from ...soils import Soils
from ...watershed import Watershed
from ...wepp import Wepp
from wepppy.wepp.soils.utils import read_lc_file, soil_specialization, soil_is_water
from ...base import NoDbBase, TriggerEvents

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


class LocationMixin(object):

    @property
    def location_doms(self):
        data_dir = self.data_dir

        lc_dict = read_lc_file(_join(data_dir, self.lc_lookup_fn))
        return set([lc_dict[k].LndcvrID for k in lc_dict])

    def remap_landuse(self):
        data_dir = self.data_dir

        with open(_join(data_dir, 'landcover_map.json')) as fp:
            lc_map = json.load(fp)

        location_doms = self.location_doms

        landuse = Landuse.getInstance(self.wd)
        landuse.lock()

        # noinspection PyBroadException
        try:
            for topaz_id, dom in landuse.domlc_d.items():
                if int(dom) not in location_doms:
                    landuse.domlc_d[topaz_id] = lc_map[dom]

            landuse.dump_and_unlock()

        except Exception:
            landuse.unlock('-f')
            raise

    def modify_soils(self, default_wepp_type=None, lc_lookup_fn=None):
        data_dir = self.data_dir
        wd = self.wd
        soils_dir = self.soils_dir

        if default_wepp_type is None:
            default_wepp_type = self.default_wepp_type

        if lc_lookup_fn is None:
            lc_lookup_fn = self.lc_lookup_fn

        lc_dict = read_lc_file(_join(data_dir, lc_lookup_fn))
        with open(_join(data_dir, 'lc_soiltype_map.json')) as fp:
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

                is_water = soil_is_water(src_fn)
                if is_water:
                    _soils[mukey] = deepcopy(soils.soils[mukey])
                    _soils[mukey].area = 0.0

                else:
                    if k not in _soils:
                        caller = ':'.join(_split(self._nodb)[-1].split('.')[::-1])
                        soil_specialization(src_fn, dst_fn, replacements, caller=caller)
                        _soils[k] = deepcopy(soils.soils[mukey])
                        _soils[k].mukey = k
                        _soils[k].fname = '%s.sol' % k
                        _soils[k].area = 0.0

                if not is_water:
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
