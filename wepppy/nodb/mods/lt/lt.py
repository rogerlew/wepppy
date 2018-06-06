# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
import json
import csv
import shutil

from copy import deepcopy
from collections import namedtuple
from os.path import join as _join
from os.path import exists as _exists

import jsonpickle

from wepppy.all_your_base import RasterDatasetInterpolator

from ...landuse import Landuse
from ...soils import Soils
from ...watershed import Watershed
from ...wepp import Wepp
from ...base import NoDbBase, TriggerEvents

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')

Landcover = namedtuple('Landcover', 
                       ['Code', 'LndcvrID', 'WEPP_Type', 'New_WEPPman', 'ManName', 'Albedo',
                        'iniSatLev', 'interErod', 'rillErod', 'critSh', 'effHC', 'soilDepth',
                        'Sand', 'Clay', 'OM', 'CEC'], verbose=False)
         
                        
def read_lc_file(fname):
    """
    Reads a file containing landcover parameters and returns a dictionary
    with tuple keys (LndcvrID, WEPP_Type) and namedtuple values with fields:
        Code, LndcvrID, WEPP_Type, New_WEPPman, ManName, Albedo, iniSatLev,
        interErod, rillErod, critSh, effHC, soilDepth, Sand, Clay, OM, CEC
    """
    d = {}
    
    with open(fname) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row['Code'] = int(row['Code'])
            row['LndcvrID'] = int(row['LndcvrID'])
            d[(str(row['LndcvrID']), row['WEPP_Type'])] = Landcover(**row)

    return d


def soil_specialization(src, dst, replacements):
    """
    Creates a new soil file based on soil_in_fname and makes replacements
    from the provided replacements namedtuple
    """
    # read the soil_in_fname file
    with open(src) as f:
        lines = f.readlines()

    header = [L for L in lines if L.startswith('#')]
    lines = [L for L in lines if not L.startswith('#')]
        
    line4 = lines[3]
    line4 = line4.split()
    line4[-5] = replacements.Albedo
    line4[-4] = replacements.iniSatLev
    line4[-3] = replacements.interErod
    line4[-2] = replacements.rillErod
    line4[-1] = replacements.critSh
    line4 = ' '.join(line4) + '\n'

    line5 = lines[4]
    line5 = line5.split()
    line5[2] = replacements.effHC

    if len(line5) < 5:  # no horizons (e.g. rock)
        shutil.copyfile(src, dst)
        return

    if "rock" not in lines[3].lower() and \
       "water" not in lines[3].lower():
        line5[6] = replacements.Sand
        line5[7] = replacements.Clay
        line5[8] = replacements.OM
        line5[9] = replacements.CEC
    line5 = ' '.join(line5) + '\n'

    # Create new soil files
    with open(dst, 'w') as f:
        f.writelines(header)
        f.writelines(lines[:3])
        f.writelines(line4)
        f.writelines(line5)
        if len(lines) > 5:
            f.writelines(lines[5:])


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
        elif evt == TriggerEvents.SOILS_BUILD_COMPLETE:
            self.modify_soils()
        elif evt == TriggerEvents.PREPPING_PHOSPHORUS:
            self.determine_phosphorus()

    def remap_landuse(self):

        with open(_join(_data_dir, 'landcover_map.json')) as fp:
            lc_map = json.load(fp)

        landuse = Landuse.getInstance(self.wd)
        landuse.lock()

        # noinspection PyBroadException
        try:
                
            for topaz_id, dom in landuse.domlc_d.items():
                landuse.domlc_d[topaz_id] = lc_map[dom]
            
            landuse.dump_and_unlock()
            
        except Exception:
            landuse.unlock('-f')
            raise
        
    def modify_soils(self, default_wepp_type='Granitic'):
        wd = self.wd
        soils_dir = self.soils_dir
        
        lc_dict = read_lc_file(_join(_data_dir, 'landSoilLookup.csv'))
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
                k = '%s-%s' % (mukey, wepp_type)
                src_fn = _join(soils_dir, '%s.sol' % mukey)
                dst_fn = _join(soils_dir, '%s.sol' % k)
                
                if k not in _soils:
                    soil_specialization(src_fn, dst_fn, replacements)
                    _soils[k] = deepcopy(soils.soils[mukey])
                    _soils[k].mukey = k
                    _soils[k].area = 0.0
                    
                domsoil_d[topaz_id] = k
                    
            # need to recalculate the pct_coverages
            watershed = Watershed.getInstance(self.wd)
            for topaz_id, k in domsoil_d.items():
                summary = watershed.sub_summary(str(topaz_id))
                if summary is not None:
                    _soils[k].area += summary["area"]

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
        watershed = Watershed.getInstance(self.wd)
        lng, lat = watershed.centroid
        wepp = Wepp.getInstance(self.wd)
        
        d = {}
        for opt in ['surf_runoff', 'lateral_flow', 'baseflow', 'sediment']:
            fn = _join(_data_dir, 'phosphorus', 'P_%s.tif' % opt)
            assert _exists(fn), fn
            raster = RasterDatasetInterpolator(fn)
            d[opt] = raster.get_location_info(lng, lat)

        # noinspection PyBroadException
        try:
            wepp.lock()
            wepp.phosphorus_opts.parse_inputs(d)
            wepp.dump_and_unlock()
        except Exception:
            wepp.unlock('-f')
            raise
