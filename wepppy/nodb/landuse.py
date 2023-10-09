# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard library
import csv
import json

import os
from os.path import join as _join
from os.path import exists as _exists
import shutil
from enum import IntEnum
import time

# non-standard
import jsonpickle
import numpy as np
import pandas as pd

# wepppy
from wepppy.landcover import LandcoverMap
from wepppy.wepp.management import get_management_summary
from wepppy.topo.watershed_abstraction.support import is_channel
from wepppy.all_your_base import isfloat
from wepppy.all_your_base.geo.webclients import wmesque_retrieve
from wepppy.all_your_base.geo import read_raster

# wepppy submodules
from .base import (
    NoDbBase,
    TriggerEvents,
)
from .ron import Ron
from .watershed import Watershed, WatershedNotAbstractedError
from .redis_prep import RedisPrep as Prep


try:
    import wepppyo3
    from wepppyo3.raster_characteristics import identify_mode_single_raster_key
    from wepppyo3.raster_characteristics import identify_mode_multiple_raster_key
except:
    wepppyo3 = None


class LanduseNoDbLockedException(Exception):
    pass


class LanduseMode(IntEnum):
    Undefined = -1
    Gridded = 0
    Single = 1
    RRED_Unburned = 2
    RRED_Burned = 3


def read_cover_defaults(fn):
    with open(fn) as fp:
        d = {}
        rdr = csv.DictReader(fp)
        for row in rdr:
            d[row['key']] = row

    return d


class Landuse(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'Landuse'

    def __init__(self, wd, cfg_fn):
        super(Landuse, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            self._mode = LanduseMode.Gridded
            self._single_selection = 0  # No Data
            self._single_man = None
            self.domlc_d = None  # topaz_id keys, ManagementSummary values
            self.managements = None
            cover_defaults_fn = self.config_get_path('landuse', 'cover_defaults')

            if cover_defaults_fn is not None:
                self.cover_defaults_d = read_cover_defaults(cover_defaults_fn)
            else:
                self.cover_defaults_d = None

            self._mapping = self.config_get_str('landuse', 'mapping')
            self._nlcd_db = self.config_get_path('landuse', 'nlcd_db')

            lc_dir = self.lc_dir
            if not _exists(lc_dir):
                os.mkdir(lc_dir)

            _landuse_map = self.config_get_path('landuse', 'landuse_map')
            if _landuse_map is not None:
                shutil.copyfile(_landuse_map, self.lc_fn)
                prj = _landuse_map[:-4] + '.prj'
                if _exists(prj):
                    shutil.copyfile(_landuse_map[:-4] + '.prj', self.lc_fn[:-4] + '.prj')

            self._landuse_map = _landuse_map

            self.domlc_mofe_d = None
            self._mofe_buffer_selection = self.config_get_int('landuse', 'mofe_buffer_selection')
            self._buffer_man = None

            self._fractionals = self.config_get_list('landuse', 'fractionals')

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd, allow_nonexistent=False, ignore_lock=False):
        filepath = _join(wd, 'landuse.nodb')

        if not os.path.exists(filepath):
            if allow_nonexistent:
                return None
            else:
                raise FileNotFoundError(f"'{filepath}' not found!")

        with open(filepath) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Landuse)

        if _exists(_join(wd, 'READONLY')) or ignore_lock:
            db.wd = os.path.abspath(wd)
            return db

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            db.wd = wd
            db.lock()
            db.dump_and_unlock()

        return db

    @property
    def _nodb(self):
        return _join(self.wd, 'landuse.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'landuse.nodb.lock')

    @property
    def mode(self):
        return self._mode

    @property
    def mapping(self):
        if hasattr(self, '_mapping'):
            return self._mapping

        ron = Ron.getInstance(self.wd)

        _mapping = None
        if self._mode in [LanduseMode.RRED_Unburned, LanduseMode.RRED_Burned]:
            _mapping = 'rred'
        elif self._mode == LanduseMode.Gridded and 'eu' in ron.locales:
            _mapping = 'esdac'
        elif self._mode == LanduseMode.Gridded and 'au' in ron.locales:
            _mapping = 'lu10v5ua'

        return _mapping

    @mode.setter
    def mode(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            if isinstance(value, LanduseMode):
                self._mode = value

            elif isinstance(value, int):
                self._mode = LanduseMode(value)

            else:
                raise ValueError('most be LanduseMode or int')

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def single_selection(self):
        """
        id of the selected management
        """
        return self._single_selection

    @single_selection.setter
    def single_selection(self, landuse_single_selection):
        self.lock()

        # noinspection PyBroadException
        try:
            k = landuse_single_selection
            self._single_selection = k
            self._single_man = get_management_summary(k)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def single_man(self):
        """
        management summary object
        """
        return self._single_man

    @property
    def mofe_buffer_selection(self):
        """
        id of the selected management
        """
        return getattr(self, '_mofe_buffer_selection', None)

    @mofe_buffer_selection.setter
    def mofe_buffer_selection(self, k):
        self.lock()

        # noinspection PyBroadException
        try:
            self._mofe_buffer_selection = str(k)
            self._buffer_man = get_management_summary(k)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def buffer_man(self):
        """
        management summary object
        """
        return getattr(self, '_buffer_man', None)

    @property
    def has_landuse(self):
        mode = self._mode

        if mode == LanduseMode.Undefined:
            return False

        else:
            return self.domlc_d is not None

    #
    # build
    #
    
    def clean(self):

        lc_dir = self.lc_dir
        if _exists(lc_dir):
            shutil.rmtree(lc_dir)
        os.mkdir(lc_dir)

    def _build_ESDAC(self):
        from wepppy.eu.soils.esdac import ESDAC
        esd = ESDAC()
        # _map = Ron.getInstance(self.wd).map

        domlc_d = {}

        watershed = Watershed.getInstance(self.wd)
        for topaz_id, summary in watershed.sub_iter():
            lng, lat = summary.centroid.lnglat
            d = esd.query(lng, lat, ['usedo'])
            assert 'usedom' in d, d
            dom = d['usedom'][1]
            domlc_d[topaz_id] = str(dom)

        for topaz_id, _ in watershed.chn_iter():
            lng, lat = summary.centroid.lnglat
            d = esd.query(lng, lat, ['usedo'])
            dom = d['usedom'][1]
            domlc_d[topaz_id] = str(dom)

        self.domlc_d = domlc_d

    def _build_lu10v5ua(self):
        from wepppy.au.landuse_201011 import Lu10v5ua
        lu = Lu10v5ua()
        # _map = Ron.getInstance(self.wd).map

        domlc_d = {}

        watershed = Watershed.getInstance(self.wd)
        for topaz_id, summary in watershed.sub_iter():
            lng, lat = summary.centroid.lnglat
            dom = lu.query_dom(lng, lat)
            domlc_d[topaz_id] = dom

        for topaz_id, _ in watershed.chn_iter():
            lng, lat = summary.centroid.lnglat
            dom = lu.query_dom(lng, lat)
            domlc_d[topaz_id] = dom

        self.domlc_d = domlc_d

    @property
    def fractionals(self):
        return getattr(self, '_fractionals', self.config_get_list('landuse', 'fractionals'))

    @fractionals.setter
    def fractionals(self, value):

        self.lock()

        # noinspection PyBroadException
        try:
            self._fractionals = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def nlcd_db(self):
        return getattr(self, '_nlcd_db', self.config_get_str('landuse', 'nlcd_db'))

    @nlcd_db.setter
    def nlcd_db(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._nlcd_db = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _build_NLCD(self):
        global wepppyo3

        _map = Ron.getInstance(self.wd).map

        # Get NLCD 2011 from wmesque webservice
        lc_fn = self.lc_fn
        wmesque_retrieve(self.nlcd_db, _map.extent, lc_fn, _map.cellsize)

        subwta_fn = Watershed.getInstance(self.wd).subwta

        if wepppyo3 is None:
            # create LandcoverMap instance
            lc = LandcoverMap(lc_fn)

            # build the grid
            # domlc_fn map is a property of NoDbBase
            # domlc_d is a dictionary with topaz_id keys
            self.domlc_d = lc.build_lcgrid(subwta_fn, None)
        else:
            domlc_d = identify_mode_single_raster_key(
                key_fn=subwta_fn, parameter_fn=lc_fn, ignore_channels=True, ignore_keys=set())
            self.domlc_d = {k: str(v) for k, v in domlc_d.items()}

    def _build_single_selection(self):
        assert self.single_selection is not None

        domlc_d = {}

        watershed = Watershed.getInstance(self.wd)
        for topaz_id, _ in watershed.sub_iter():
            domlc_d[topaz_id] = str(self.single_selection)

        for topaz_id, _ in watershed.chn_iter():
            domlc_d[topaz_id] = str(self.single_selection)

        self.domlc_d = domlc_d

    def build(self):
        wd = self.wd
        watershed = Watershed.getInstance(wd)
        if not watershed.is_abstracted:
            raise WatershedNotAbstractedError()

        if self._mode in [LanduseMode.RRED_Burned, LanduseMode.RRED_Unburned]:
            import wepppy
            rred = wepppy.nodb.mods.Rred.getInstance(wd)
            rred.build_landuse(self._mode)
            self = self.getInstance(wd)  # reload instance from .nodb
            self.build_managements()
            return

        self.lock()

        ron = Ron.getInstance(wd)

        # noinspection PyBroadException
        try:
            self.clean()

            if self._mode == LanduseMode.Gridded:
                if 'au' in ron.locales:
                    self._build_lu10v5ua()
                else:
                    self._build_NLCD()

            elif self._mode == LanduseMode.Single:
                self._build_single_selection()

            elif self._mode == LanduseMode.Undefined:
                raise Exception('LanduseMode is not set')

            self.dump_and_unlock()
            self.build_managements()

        except Exception:
            self.unlock('-f')
            raise

        if self.multi_ofe:
            self._build_multiple_ofe()

        self = Landuse.getInstance(wd)
        self.trigger(TriggerEvents.LANDUSE_DOMLC_COMPLETE)
        self = Landuse.getInstance(wd)
        self.build_managements()
        self.set_cover_defaults()

        self.dump_landuse_parquet()

        try:
            prep = Prep.getInstance(self.wd)
            prep.timestamp('build_landuse')
        except FileNotFoundError:
            pass

        self._build_fractionals()


    def _build_fractionals(self):
        global wepppyo3

        fractionals = self.fractionals
        frac_dir = _join(self.lc_dir, 'fractionals')

        if len(fractionals) == 0:
            return

        os.makedirs(frac_dir, exist_ok=True)

        _map = Ron.getInstance(self.wd).map
        subwta_fn = Watershed.getInstance(self.wd).subwta

        frac_d = {}
        dom_d = {}
        for frac in fractionals:
            lc_fn = _join(frac_dir, frac.replace('/', '_') + '.tif')
            wmesque_retrieve(frac, _map.extent, lc_fn, _map.cellsize)

            if wepppyo3 is None:
                lc = LandcoverMap(lc_fn)

                dom_d[frac] = lc.build_lcgrid(subwta_fn)
                frac_d[frac] = lc.calc_fractionals(subwta_fn)
            else:
                dom_d[frac] = identify_mode_single_raster_key(
                    key_fn=subwta_fn, parameter_fn=lc_fn, ignore_channels=True, ignore_keys=set())
                dom_d[frac] = {k: str(v) for k, v in dom_d[frac].items()}

                frac_d[frac] = identify_mode_single_raster_key(
                    key_fn=subwta_fn, parameter_fn=lc_fn, ignore_channels=True, ignore_keys=set())
                frac_d[frac] = {k: str(v) for k, v in frac_d[frac].items()}

        with open(_join(frac_dir, 'dom.json'), 'w') as fp:
            json.dump(dom_d, fp, indent=2)

        with open(_join(frac_dir, 'fractionals.json'), 'w') as fp:
            json.dump(frac_d, fp, indent=2)

    def _build_multiple_ofe(self):
        global wepppyo3

        from wepppy.wepp.management.utils import ManagementMultipleOfeSynth
        from wepppy.nodb.mods.disturbed import Disturbed

        wd = self.wd

        watershed = Watershed.getInstance(wd)

        try:
            disturbed = Disturbed.getInstance(wd)
            _land_soil_replacements_d = disturbed.land_soil_replacements_d 
        except:
            disturbed = None
            _land_soil_replacements_d = None

        if wepppyo3 is None:
            lc = LandcoverMap(self.lc_fn)
            domlc_d = lc.build_lcgrid(watershed.subwta, watershed.mofe_map)
        else:
            domlc_d = identify_mode_intersecting_raster_keys(
                key_fn=watershed.subwta,
                key2_fn=watershed.mofe_map,
                parameter_fn=self.lc_fn,
                ignore_channels=True,
                ignore_keys=set(),
                ignore_keys2=set(),
            )
            _domlc_d = {k: str(v) for k, v in domlc_d.items()}
            domlc_d = {}
            for topaz_fp_id, v in _domlc_d.items():
                topaz_id, fp_id = topaz_fp_id.split('-')
                if topaz_id not in domlc_d:
                    domlc_d[topaz_id] = {}
                domlc_d[topaz_id][fp_id] = v

        self.lock()
        self.__m_domlc_d = domlc_d
        self.dump_and_unlock()

        lc_dir = self.lc_dir
        managements = self.managements

        watershed = Watershed.getInstance(self.wd)
        for topaz_id, ss in watershed.sub_iter():

            nsegments = int(watershed.mofe_nsegments[str(topaz_id)])
            mofe_lc_fn = _join(lc_dir, f'hill_{topaz_id}.mofe.man')

            mofe_ids = sorted([_id for _id in domlc_d[str(topaz_id)]])
            #assert len(mofe_ids) == nsegments, (topaz_id, mofe_ids, nsegments, len(mofe_ids) )

            apply_buffer = watershed.mofe_buffer and not str(topaz_id).endswith('1')
            if apply_buffer:
                domlc_d[topaz_id][mofe_ids[-1]] = self.mofe_buffer_selection

            doms = [domlc_d[topaz_id][_id] for _id in mofe_ids]

            stack = []
            for dom in doms:
                if dom not in managements:
                    managements[dom] = get_management_summary(dom, self.mapping)

                management = managements[dom].get_management()
                disturbed_class = managements[dom].disturbed_class
                texid = 'sand loam'
               
                if disturbed_class is None:
                    rdmax = None
                    xmxlai = None
                else:
                    if (texid, disturbed_class) in _land_soil_replacements_d:
                        rdmax = _land_soil_replacements_d[(texid, disturbed_class)]['rdmax']
                        xmxlai = _land_soil_replacements_d[(texid, disturbed_class)]['xmxlai']

                if rdmax is not None:
                    if isfloat(rdmax):
                        management.set_rdmax(float(rdmax))

                if xmxlai is not None:
                    if isfloat(xmxlai):
                        management.set_xmxlai(float(xmxlai))

                stack.append(management)

            assert len(stack) > 0, topaz_id
            assert len(stack) == nsegments, (len(stack),  nsegments)

            if len(stack) == 1:
                with open(mofe_lc_fn, 'w') as pf:
                    pf.write(str(stack[0]))
            else:
                mofe_synth = ManagementMultipleOfeSynth()

                # just replicate the dom
                mofe_synth.stack = stack
                merged = mofe_synth.write(mofe_lc_fn)
                    
        self.lock()
        try:
            self.domlc_mofe_d = domlc_d
            self.managements = managements
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise


    def identify_burn_class(self, topaz_id):
        dom = self.domlc_d[str(topaz_id)]
        man = self.managements[dom]
        desc = man.desc.lower()
        
        if 'unburned' in desc:
            return 'Unburned'
        
        if 'sev' not in desc or 'fire' not in desc:
            return 'Unburned'
        
        if 'low' in desc or 'prescribed' in desc:
            return 'Low'
        
        elif 'mod' in desc:
            return 'Moderate'
        
        elif 'high' in desc:
            return 'High'
        
        return 'Unburned'
        
    def set_cover_defaults(self):

        defaults = self.cover_defaults_d

        if defaults is None:
            return

        time.sleep(0.5)
        self.lock()

        # noinspection PyBroadException
        try:
            for dom in self.managements:
                dom = str(dom)
                if dom in defaults:
                    for cover in ['cancov', 'inrcov', 'rilcov']:
                        self._modify_coverage(dom, cover, defaults[dom][cover])

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _modify_coverage(self, dom, cover, value):
        dom = str(dom)
        assert dom in self.managements

        assert cover in ['cancov', 'inrcov', 'rilcov']

        value = float(value)
        assert value >= 0.0
        assert value <= 1.0

        if cover == 'cancov':
            self.managements[dom].cancov_override = value
        elif cover == 'inrcov':
            self.managements[dom].inrcov_override = value
        elif cover == 'rilcov':
            self.managements[dom].rilcov_override = value

    def modify_coverage(self, dom, cover, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._modify_coverage(dom, cover, value)
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def modify_mapping(self, dom, newdom):
        self.lock()

        # noinspection PyBroadException
        try:
            dom = str(dom)
            newdom = str(newdom)
            assert dom in self.managements

            for topazid in self.domlc_d:
                if self.domlc_d[topazid] == dom:
                    self.domlc_d[topazid] = newdom

            self.dump_and_unlock()

            # noinspection PyMethodFirstArgAssignment
            self = self.getInstance(self.wd)  # reload instance from .nodb
            self.build_managements()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def landuseoptions(self):

        # TODO: filter landuse options for baer and for the landsoil map
        from wepppy.wepp import management

        landuseoptions = management.load_map(self.mapping).values()

        if all(isinstance(d['Key'], int) for d in landuseoptions):
            landuseoptions = sorted(landuseoptions, key=lambda d: int(d['Key']))
        else:
            landuseoptions = sorted(landuseoptions, key=lambda d: str(d['Key']))

        # landuseoptions = [opt for opt in landuseoptions if 'DisturbedWEPPManagement' not in opt['ManagementFile']]

        if 'baer' in self.mods:
            landuseoptions = [opt for opt in landuseoptions if 'Agriculture' not in opt['ManagementFile']]

        if "lt" in self.mods or "portland" in self.mods or "seattle" in self.mods:
            landuseoptions = [opt for opt in landuseoptions if 'Tahoe' in opt['ManagementFile']]

        if 'disturbed' in self.mods:
            import wepppy
            disturbed = wepppy.nodb.mods.Disturbed.getInstance(self.wd)
            _lookup = disturbed.land_soil_replacements_d
            landuseoptions = [opt for opt in landuseoptions if opt.get('DisturbedClass') != ''] 

        return landuseoptions

    def build_managements(self, _map=None):
        self.lock()

        if _map is None:
            _map = self.mapping

        # noinspection PyBroadException
        try:
            watershed = Watershed.getInstance(self.wd)
            ron = Ron.getInstance(self.wd)
            cell2 = ron.cellsize ** 2
            domlc_d = self.domlc_d

            subwta, transform, proj = read_raster(watershed.subwta, dtype=np.int32)
            if self.multi_ofe:
                mofe_map, transform_m, proj_m = \
                    read_raster(watershed.mofe_map, dtype=np.int32)

            # create a dictionary of management keys and
            # wepppy.landcover.ManagementSummary values
            managements = {}

            # while we are at it we will calculate the pct coverage
            # for the landcover types in the watershed
            total_area = 0.0
            for topaz_id, k in domlc_d.items():
                area = len(np.where(subwta == int(topaz_id))[0])
                area *= cell2 / 10000
                    
                if k not in managements:
                    man = get_management_summary(k, _map)
                    man.area = area
                    managements[k] = man
                else:
                    managements[k].area += area

                if self.multi_ofe:
                    managements[k].area = 0

                total_area += area

            if not hasattr(self, 'domlc_mofe_d'):
                self.domlc_mofe_d = None

            if self.multi_ofe and self.domlc_mofe_d is not None:
                total_area = 0.0
                for topaz_id in self.domlc_mofe_d:
                    for _id, k in self.domlc_mofe_d[topaz_id].items():
                        area = len(np.where((subwta == int(topaz_id)) &
                                            (mofe_map == int(_id)))[0])
                        area *= cell2 / 10000
                        
                        if k not in managements:
                            man = get_management_summary(k, _map)
                            man.area = area
                            managements[k] = man
                        else:
                            managements[k].area += area
                        total_area += area
     
            for k in managements:
                coverage = 100.0 * managements[k].area / total_area
                managements[k].pct_coverage = coverage
                        
            # store the managements dict
            self.managements = managements
            self.dump_and_unlock()

            self.trigger(TriggerEvents.LANDUSE_BUILD_COMPLETE)

        except Exception:
            self.unlock('-f')
            raise

    @property
    def report(self):
        """
        returns a list of managements sorted by coverage in
        descending order
        """
        used_mans = [dom for dom, man in self.managements.items() if man.area > 0]
        report = [self.managements[str(dom)] for dom in used_mans]
        report.sort(key=lambda x: x.pct_coverage, reverse=True)
        return [man.as_dict() for man in report]

    #
    # modify
    #
    def modify(self, topaz_ids, landuse):
        self.lock()

        # noinspection PyBroadException
        try:
            landuse = str(int(landuse))
            assert self.domlc_d is not None
            
            for topaz_id in topaz_ids:
                assert topaz_id in self.domlc_d
                self.domlc_d[topaz_id] = landuse
                
            self.dump_and_unlock()
            self.build_managements()
            self.set_cover_defaults()
            
        except Exception:
            self.unlock('-f')
            raise
            
    def _x_summary(self, topaz_id):
        domlc_d = self.domlc_d
        
        if domlc_d is None:
            return None
            
        if str(topaz_id) in domlc_d:
            dom = str(domlc_d[str(topaz_id)])
            return self.managements[dom].as_dict()
        else:
            return None

    @property
    def legend(self):
        doms = sorted(set(self.domlc_d.values()))
        mans = [self.managements[dom] for dom in doms]
        descs = [man.desc for man in mans]
        colors = [man.color for man in mans]

        return list(zip(doms, descs, colors))

    def sub_summary(self, topaz_id):
        return self._x_summary(topaz_id)
        
    def chn_summary(self, topaz_id):
        return self._x_summary(topaz_id)
       
    @property
    def subs_summary(self):
        """
        Returns a dictionary with topaz_id keys and dictionary soils values.
        """
        domlc_d = self.domlc_d
        mans = self.managements
        
        if domlc_d is None:
            return None
            
        man_dicts_cache = {dom: man.as_dict() for dom, man in mans.items()}

        # Compile the summary using cached soil dictionaries
        summary = {
            topaz_id: man_dicts_cache[dom] 
            for topaz_id, dom in domlc_d.items() 
            if not is_channel(topaz_id)
        }
        
        return summary
     
    def dump_landuse_parquet(self):
        """
        Dumps the subs_summary to a Parquet file using Pandas.
        """
        subs_summary = self.subs_summary
        assert subs_summary is not None
            
        df = pd.DataFrame.from_dict(subs_summary, orient='index')
        df.index.name = 'TopazID'
        df.reset_index(inplace=True)
        df['TopazID'] = df['TopazID'].astype(str).astype('int64')
        df.to_parquet(_join(self.lc_dir, 'landuse.parquet'))
   
    def sub_iter(self):
        domlc_d = self.domlc_d
        mans = self.managements
        
        assert mans is not None

        if domlc_d is not None:
            for topaz_id, k in domlc_d.items():
                if is_channel(topaz_id):
                    continue

                yield topaz_id, mans[k]
        
    @property
    def chns_summary(self):
        """
        returns a dictionary of topaz_id keys and jsonified 
        managements values
        """
        domlc_d = self.domlc_d
        mans = self.managements

        assert mans is not None
        
        summary = {}
        for topaz_id, k in domlc_d.items():
            if not is_channel(topaz_id):
                continue

            summary[topaz_id] = mans[k].as_dict()

        return summary

    def chn_iter(self):
        domlc_d = self.domlc_d
        mans = self.managements
        
        if domlc_d is not None:
            for topaz_id, k in domlc_d.items():
                if not is_channel(topaz_id):
                    continue

                yield topaz_id, mans[k]

    # gotcha: using __getitem__ breaks jinja's attribute lookup, so...
    def _(self, wepp_id):
        wd = self.wd
        
        translator = Watershed.getInstance(wd).translator_factory()
        topaz_id = str(translator.top(wepp=int(wepp_id)))
        domlc_d = self.domlc_d
        
        if topaz_id in domlc_d:
            key = domlc_d[topaz_id]
            return self.managements[key]
            
        raise IndexError
