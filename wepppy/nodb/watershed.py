# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from typing import Generator, Dict, Union, Tuple

import os
from enum import IntEnum

from os.path import join as _join
from os.path import exists as _exists

import jsonpickle
import numpy as np

import multiprocessing

from osgeo import gdal, osr
from osgeo.gdalconst import *

from wepppy.topo.watershed_abstraction import (
    WatershedAbstraction,
    WeppTopTranslator
)
from wepppy.topo.taudem import TauDEMTopazEmulator
from wepppy.topo.peridot.runner import run_peridot_abstract_watershed, post_abstract_watershed, read_network
from wepppy.topo.watershed_abstraction import SlopeFile
from wepppy.topo.watershed_abstraction.support import HillSummary, ChannelSummary
from wepppy.topo.watershed_abstraction.slope_file import mofe_distance_fractions
from wepppy.all_your_base.geo import read_raster, haversine

from .ron import Ron
from .base import NoDbBase, TriggerEvents
from .topaz import Topaz
from .redis_prep import RedisPrep, TaskEnum
from .mixins.log_mixin import LogMixin

from wepppy.all_your_base import (
    NCPU
)


# https://dev.wepp.cloud/weppcloud/runs/combatant-fixer/disturbed9002/
# https://dev.wepp.cloud/weppcloud/runs/waking-clang/disturbed9002/


NCPU = multiprocessing.cpu_count() - 2

class DelineationBackend(IntEnum):
    TOPAZ = 1
    TauDEM = 2


class WatershedNotAbstractedError(Exception):
    """
    The watershed has not been abstracted. The watershed must be delineated
    to complete this operation.
    """

    __name__ = 'WatershedNotAbstractedError'

    def __init__(self):
        pass


class WatershedNoDbLockedException(Exception):
    pass


def process_channel(args):
    wat_abs, chn_id = args
    chn_summary, chn_paths = wat_abs.abstract_channel(chn_id)
    return chn_id, chn_summary, chn_paths


def process_subcatchment(args):
    wat_abs, sub_id, clip_hillslopes, clip_hillslope_length, max_points  = args

    sub_summary, fp_d = wat_abs.abstract_subcatchment(
        sub_id, 
        clip_hillslopes=clip_hillslopes, 
        clip_hillslope_length=clip_hillslope_length,
        max_points=max_points)

    return sub_id, sub_summary, fp_d


class Watershed(NoDbBase, LogMixin):
    __name__ = 'Watershed'

    def __init__(self, wd, cfg_fn):
        super(Watershed, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            self._subs_summary = None
            self._fps_summary = None
            self._structure = None
            self._chns_summary = None
            self._wsarea = None
            self._impoundment_n = 0
            self._centroid = None
            self._outlet_top_id = None
            self._outlet = None

            self._wepp_chn_type = self.config_get_str('soils', 'wepp_chn_type')

            self._clip_hillslope_length = self.config_get_float('watershed', 'clip_hillslope_length')
            self._clip_hillslopes = self.config_get_bool('watershed', 'clip_hillslopes')
            self._bieger2015_widths = self.config_get_bool('watershed', 'bieger2015_widths')
            self._walk_flowpaths = self.config_get_bool('watershed', 'walk_flowpaths')
            self._max_points = self.config_get_int('watershed', 'max_points', None)

            delineation_backend = self.config_get_str('watershed', 'delineation_backend')
            if delineation_backend.lower().startswith('taudem'):
                self._delineation_backend = DelineationBackend.TauDEM
                taudem_wd = self.taudem_wd
                if not _exists(taudem_wd):
                    os.mkdir(taudem_wd)

                self._csa = self.config_get_float('taudem', 'csa')
                self._pkcsa = self.config_get_str('taudem', 'pkcsa')

            else:
                self._delineation_backend = DelineationBackend.TOPAZ

            self._abstraction_backend = self.config_get_str('watershed', 'abstraction_backend', 'peridot')

            wat_dir = self.wat_dir
            if not _exists(wat_dir):
                os.mkdir(wat_dir)

            self._mofe_nsegments = None
            self._mofe_target_length = self.config_get_float('watershed', 'mofe_target_length')
            self._mofe_buffer = self.config_get_bool('watershed', 'mofe_buffer')
            self._mofe_buffer_length = self.config_get_float('watershed', 'mofe_buffer_length')

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
        filepath = _join(wd, 'watershed.nodb')

        if not os.path.exists(filepath):
            if allow_nonexistent:
                return None
            else:
                raise FileNotFoundError(f"'{filepath}' not found!")

        with open(filepath) as fp:
            _json = fp.read()
            _json = _json.replace("wepppy.watershed_abstraction.support.HillSummary",
                                  "wepppy.topo.watershed_abstraction.support.HillSummary") \
                         .replace("wepppy.watershed_abstraction.support.ChannelSummary",
                                  "wepppy.topo.watershed_abstraction.support.ChannelSummary") \
                         .replace("wepppy.watershed_abstraction.support.CentroidSummary",
                                  "wepppy.topo.watershed_abstraction.support.CentroidSummary")
            db = jsonpickle.decode(_json)
            assert isinstance(db, Watershed)

        if _exists(_join(wd, 'READONLY')) or ignore_lock:
            db.wd = os.path.abspath(wd)
            return db

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            db.wd = wd
            db.lock()
            db.dump_and_unlock()

        return db

    @staticmethod
    def getInstanceFromRunID(runid, allow_nonexistent=False, ignore_lock=False):
        from wepppy.weppcloud.utils.helpers import get_wd
        return Watershed.getInstance(
            get_wd(runid, allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock))

    @property
    def _status_channel(self):
        return f'{self.runid}:watershed'

    @property
    def status_log(self):
        return os.path.abspath(_join(self.wat_dir, 'status.log'))

    @property
    def delineation_backend(self):
        delineation_backend = getattr(self, '_delineation_backend', None)
        if delineation_backend is None:
            return DelineationBackend.TOPAZ
        return delineation_backend

    @property
    def delineation_backend_is_topaz(self):
        delineation_backend = getattr(self, '_delineation_backend', None)
        if delineation_backend is None:
            return True
        return delineation_backend == DelineationBackend.TOPAZ

    @property
    def max_points(self):
        pts = getattr(self, '_max_points', None)
        if pts is None:
            return 99
        return pts

    @property
    def abstraction_backend(self):
        return getattr(self, '_abstraction_backend', 'topaz')

    @property
    def abstraction_backend_is_peridot(self):
        return self.abstraction_backend == 'peridot'

    @property
    def clip_hillslopes(self):
        return getattr(self, '_clip_hillslopes', False) and not self.multi_ofe

    @clip_hillslopes.setter
    def clip_hillslopes(self, value):

        self.lock()

        # noinspection PyBroadException
        try:
            self._clip_hillslopes = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def clip_hillslope_length(self):
        return getattr(self, '_clip_hillslope_length', 300.0)

    @clip_hillslope_length.setter
    def clip_hillslope_length(self, value):

        self.lock()

        # noinspection PyBroadException
        try:
            self._clip_hillslope_length = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def bieger2015_widths(self):
        return getattr(self, '_bieger2015_widths', False)

    @bieger2015_widths.setter
    def bieger2015_widths(self, value):

        self.lock()

        # noinspection PyBroadException
        try:
            self._bieger2015_widths = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def walk_flowpaths(self):
        return getattr(self, '_walk_flowpaths', True)

    @walk_flowpaths.setter
    def walk_flowpaths(self, value):

        self.lock()

        # noinspection PyBroadException
        try:
            self._walk_flowpaths = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
        
    @property
    def delineation_backend_is_taudem(self):
        delineation_backend = getattr(self, '_delineation_backend', None)
        if delineation_backend is None:
            return False
        return delineation_backend == DelineationBackend.TauDEM

    @property
    def is_abstracted(self):
        return self._subs_summary is not None and self._chns_summary is not None

    @property
    def _nodb(self):
        return _join(self.wd, 'watershed.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'watershed.nodb.lock')

    @property
    def wepp_chn_type(self):
        return getattr(self, '_wepp_chn_type', self.config_get_str('soils', 'wepp_chn_type'))

    @property
    def subwta(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, 'SUBWTA.ARC')
        else:
            return _join(self.taudem_wd, 'subwta.tif')

    @property
    def discha(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, 'DISCHA.ARC')
        else:
            raise NotImplementedError('taudem distance to channel map not specified')
            return None # _join(self.taudem_wd, 'subwta.tif')

    @property
    def subwta_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, 'SUBCATCHMENTS.WGS.JSON')
        else:
            return _join(self.taudem_wd, 'subcatchments.WGS.geojson')

    @property
    def subwta_utm_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, 'SUBCATCHMENTS.JSON')
        else:
            return _join(self.taudem_wd, 'subcatchments.geojson')

    @property
    def bound(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, 'BOUND.ARC')
        else:
            return _join(self.taudem_wd, 'bound.tif')

    @property
    def bound_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, 'BOUND.WGS.JSON')
        else:
            return _join(self.taudem_wd, 'bound.WGS.geojson')

    @property
    def bound_utm_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, 'BOUND.JSON')
        else:
            return _join(self.taudem_wd, 'bound.geojson')

    @property
    def netful(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, 'NETFUL.ARC')
        else:
            return _join(self.taudem_wd, 'src.tif')

    @property
    def netful_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, 'NETFUL.WGS.JSON')
        else:
            return _join(self.taudem_wd, 'netful.WGS.geojson')

    @property
    def netful_utm_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, 'NETFUL.JSON')
        else:
            return _join(self.taudem_wd, 'netful.geojson')

    @property
    def channels_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, 'CHANNELS.WGS.JSON')
        else:
            return _join(self.taudem_wd, 'net.WGS.geojson')

    @property
    def channels_utm_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, 'CHANNELS.JSON')
        else:
            return _join(self.taudem_wd, 'net.geojson')

    @property
    def sub_n(self) -> int:
        if self._subs_summary is None:
            return 0

        return len(self._subs_summary)

    @property
    def greater300_n(self) -> int:
        if self._subs_summary is None:
            return 0

        return sum(sub.length > 300 for sub in self._subs_summary.values())

    @property
    def area_gt30(self):
        if self.delineation_backend_is_topaz:
            return Topaz.getInstance(self.wd).area_gt30 
        else:
            return self._area_gt30

    @property
    def ruggedness(self):
        if self.delineation_backend_is_topaz:
            return Topaz.getInstance(self.wd).ruggedness
        else:
            return self._ruggedness

    @property
    def impoundment_n(self) -> int:
        return self._impoundment_n

    @property
    def chn_n(self) -> int:
        if self._chns_summary is None:
            return 0

        return len(self._chns_summary)

    @property
    def wsarea(self) -> float:
        return getattr(self, '_wsarea', 1)

    @property
    def structure(self):
        return self._structure

    @property
    def csa(self):
        csa = getattr(self, '_csa', None)
        if csa is None:
            csa = Topaz.getInstance(self.wd).csa
        return csa

    @property
    def mcl(self):
        
        if self.delineation_backend_is_topaz:
            mcl = getattr(self, '_mcl', None)
            if mcl is None:
                mcl = Topaz.getInstance(self.wd).mcl
            return mcl
        
        return None

    @property
    def outlet(self):
        if hasattr(self, '_outlet'):
            return self._outlet

        return Topaz.getInstance(self.wd).outlet

    @outlet.setter
    def outlet(self, value):
        assert isinstance(value, Outlet) or value is None

        self.lock()

        # noinspection PyBroadException
        try:
            self._outlet = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def has_outlet(self):
        return self.outlet is not None

    @property
    def has_channels(self):
        return _exists(self.netful)

    @property
    def has_subcatchments(self):
        return _exists(self.subwta)

    @property
    def outlet_top_id(self):
        return self._outlet_top_id

    def translator_factory(self):
        if self._chns_summary is None:
            raise Exception('No chn_ids available for translator')

        if self._subs_summary is None:
            raise Exception('No sub_ids available for translator')

        return WeppTopTranslator(map(int, self._subs_summary.keys()),
                                 map(int, self._chns_summary.keys()))

    #
    # build channels
    #
    def build_channels(self, csa=None, mcl=None):
        assert not self.islocked()
        self.log('Building Channels')

        if csa or mcl:
            self.lock()
            try:
                if csa is not None:
                    self._csa = csa

                if mcl is not None:
                    self._mcl = mcl

                self.dump_and_unlock()
            except:
                self.unlock('-f')
                raise

        if self.outlet is not None:
            self.remove_outlet()

        if self.delineation_backend_is_topaz:      
            Topaz.getInstance(self.wd).build_channels(csa=self.csa, mcl=self.mcl)
        else:
            TauDEMTopazEmulator(self.taudem_wd, self.dem_fn).build_channels(csa=self.csa)

        if _exists(self.subwta):
            os.remove(self.subwta)

        prep = RedisPrep.getInstance(self.wd)
        prep.timestamp(TaskEnum.build_channels)

    #
    # set outlet
    #
    def set_outlet(self, lng=None, lat=None, da=0.0):
        assert not self.islocked()
        self.log('Setting Outlet')

        assert float(lng), lng
        assert float(lat), lat

        if self.delineation_backend_is_topaz:
            topaz = Topaz.getInstance(self.wd)
            topaz.set_outlet(lng=lng, lat=lat, da=da)
            self.outlet = topaz.outlet
        else:
            taudem = TauDEMTopazEmulator(self.taudem_wd, self.dem_fn)
            taudem.set_outlet(lng=lng, lat=lat)

            map = Ron.getInstance(self.wd).map
            o_x, o_y = map.lnglat_to_px(*taudem.outlet)
            distance = haversine((lng, lat), taudem.outlet) * 1000  # in m
            self.outlet = Outlet(requested_loc=(lng, lat), actual_loc=taudem.outlet,
                                  distance_from_requested=distance, pixel_coords=(o_x, o_y))

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.set_outlet)
        except FileNotFoundError:
            pass

    def remove_outlet(self):
        self.outlet = None

    #
    # build subcatchments
    #
    def build_subcatchments(self, pkcsa=None):
        assert not self.islocked()
        self.log('Building Subcatchments')

        if self.delineation_backend_is_topaz:
            Topaz.getInstance(self.wd).build_subcatchments()
        else:
            self.lock()
            try:
                if pkcsa is not None:
                    self._pkcsa = pkcsa

                self.dump_and_unlock()
            except:
                self.unlock('-f')
                raise
            self._taudem_build_subcatchments()

    @property
    def pkcsa(self):
        return getattr(self, '_pkcsa', None)

    @property
    def pkcsa_drop_table_html(self):
        assert self.delineation_backend_is_taudem
        taudem = TauDEMTopazEmulator(self.taudem_wd, self.dem_fn)

        import pandas as pd
        df = pd.read_csv(taudem._drp, skipfooter=1, engine='python')
        return df.to_html(border=0, classes=['table'], index=False, index_names=False)

    @property
    def pkcsa_drop_analysis_threshold(self):
        assert self.delineation_backend_is_taudem
        taudem = TauDEMTopazEmulator(self.taudem_wd, self.dem_fn)
        return taudem.drop_analysis_threshold

    def _taudem_build_subcatchments(self):

        self.lock()

        # noinspection PyBroadException
        try:
            taudem = TauDEMTopazEmulator(self.taudem_wd, self.dem_fn)

            pkcsa = self.pkcsa
            if pkcsa == 'auto':
                pkcsa = None
            taudem.build_subcatchments(threshold=pkcsa)
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def network(self):
        if self.abstraction_backend_is_peridot:
            network = read_network(_join(self.wat_dir, 'network.txt'))
            return network
        else:
            raise NotImplementedError('network not implemented')
        
    #
    # abstract watershed
    #

    def abstract_watershed(self):
        assert not self.islocked()
        self.log('Abstracting Watershed')

        if self.abstraction_backend_is_peridot:
            assert self.delineation_backend_is_topaz
            run_peridot_abstract_watershed(self.wd,
                                           clip_hillslopes=False,
                                           clip_hillslope_length=self.clip_hillslope_length,
                                           bieger2015_widths=self.bieger2015_widths)

            self.lock()
            try:
                self._subs_summary, self._chns_summary, self._fps_summary = post_abstract_watershed(self.wd)

                lnglat = np.array([summary.centroid.lnglat for summary in self._subs_summary.values()])
                lnglat = np.mean(lnglat, axis=0)
                self._centroid = [float(x) for x in lnglat]

                self._wsarea = sum(summary.area for summary in self._subs_summary.values()) + \
                               sum(summary.area for summary in self._chns_summary.values())

                network = self.network
                translator = self.translator_factory()
                self._structure = translator.build_structure(network)

                self.dump_and_unlock()
            except:
                self.unlock('-f')
                raise

        else:
            if self.delineation_backend_is_topaz:
                self._topaz_abstract_watershed()
            else:
                self._taudem_abstract_watershed()

        if self.multi_ofe:
            self._build_multiple_ofe()
       
        try: 
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.abstract_watershed)
        except FileNotFoundError:
            pass


    @property
    def sub_area(self):
        sub_area = getattr(self, '_sub_area', None)

        if sub_area is None:
            sub_area = sum(summary.area for summary in self._subs_summary.values())

        return sub_area

    @property
    def chn_area(self):
        chn_area = getattr(self, '_chn_area')

        if chn_area is None:
            chn_area = sum(summary.area for summary in self._chns_summary.values())

        return chn_area

    @property
    def mofe_nsegments(self):
        return getattr(self, '_mofe_nsegments', None)

    @property
    def mofe_target_length(self):
        return getattr(self, '_mofe_target_length', 50)

    @mofe_target_length.setter
    def mofe_target_length(self, value):

        self.lock()

        # noinspection PyBroadException
        try:
            self._mofe_target_length = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def mofe_buffer(self):
        return getattr(self, '_mofe_buffer', False)

    @mofe_buffer.setter
    def mofe_buffer(self, value):

        self.lock()

        # noinspection PyBroadException
        try:
            self._mofe_buffer = bool(value)
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def mofe_buffer_length(self):
        return getattr(self, '_mofe_buffer_length', 15)

    @mofe_buffer_length.setter
    def mofe_buffer_length(self, value):

        self.lock()

        # noinspection PyBroadException
        try:
            self._mofe_buffer_length = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def _build_multiple_ofe(self):
        _mofe_nsegments = {}
        for topaz_id, sub in self.sub_iter():
            not_top = not str(topaz_id).endswith('1')

            slp = SlopeFile(_join(self.wat_dir, sub.fname))
            _mofe_nsegments[topaz_id] = slp.segmented_multiple_ofe(
                target_length=self.mofe_target_length,
                apply_buffer=self.mofe_buffer and not_top,
                buffer_length=self.mofe_buffer_length)
            
        self.lock()

        # noinspection PyBroadException
        try:
            self._mofe_nsegments = _mofe_nsegments
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

        self._build_mofe_map()

    @property
    def mofe_map(self):
        return _join(self.wat_dir, 'mofe.tif')

    def _build_mofe_map(self):
        subwta, transform_s, proj_s = read_raster(self.subwta, dtype=np.int32)
        discha, transform_d, proj_d = read_raster(self.discha, dtype=np.int32)
        mofe_nsegments = self.mofe_nsegments

        mofe_map = np.zeros(subwta.shape, np.int32)
        for topaz_id, sub in self.sub_iter():
            indices = np.where(subwta == int(topaz_id))
            _discha_vals = discha[indices]
            max_discha = np.max(_discha_vals)

            mofe_slp_fn = _join(self.wat_dir, sub.fname.replace('.slp', '.mofe.slp'))
            d_fractions = mofe_distance_fractions(mofe_slp_fn)

            n_ofe = len(d_fractions) - 1
            if n_ofe == 1:
                mofe_indices = np.where(subwta == int(topaz_id))
                mofe_map[mofe_indices] = 1
            else:
                j = 1
                for i in range(n_ofe):
                    _max_pct = (1.0 - d_fractions[i]) * 100
                    _min_pct = (1.0 - d_fractions[i+1]) * 100
                    _min = np.percentile(_discha_vals, _min_pct)
                    _max = np.percentile(_discha_vals, _max_pct)

                    mofe_indices = np.where((subwta == int(topaz_id)) &
                                            (mofe_map == 0) &
                                            (discha >= _min) & (discha <= _max))
                    if len(mofe_indices[0]) == 0:
                        target_value = (1.0 - d_fractions[i]) * max_discha
                        diff = np.abs(target_value - _discha_vals)
                        closest_index = np.argmin(diff)
                        mofe_indices = (indices[0][closest_index], indices[1][closest_index])

                    mofe_map[mofe_indices] = j
                    j += 1

            mofe_ids = set(mofe_map[indices])
            if 0 in mofe_ids:
                mofe_ids.remove(0)

            assert len(mofe_ids) == n_ofe, (topaz_id, mofe_ids)

        num_cols, num_rows = mofe_map.shape

        driver = gdal.GetDriverByName("GTiff")
        dst = driver.Create(self.mofe_map, num_cols, num_rows,
                            1, GDT_Byte)

        srs = osr.SpatialReference()
        srs.ImportFromProj4(proj_s)
        wkt = srs.ExportToWkt()

        dst.SetProjection(wkt)
        dst.SetGeoTransform(transform_s)
        band = dst.GetRasterBand(1)
        band.WriteArray(mofe_map.T)
        del dst  # Writes and closes file

        assert _exists(self.mofe_map)

#        mofe_map2, transform_m, proj_m = read_raster(self.mofe_map)
#        assert subwta.shape == mofe_map2.shape


    def _taudem_abstract_watershed(self):
        from wepppy.nodb import Wepp

        self.lock()

        # noinspection PyBroadException
        try:
            taudem = TauDEMTopazEmulator(self.taudem_wd, self.dem_fn)
            taudem.abstract_watershed(wepp_chn_type=self.wepp_chn_type,
                                      clip_hillslopes=self.clip_hillslopes,
                                      clip_hillslope_length=self.clip_hillslope_length)

            self._subs_summary = taudem.abstracted_subcatchments
            self._chns_summary = taudem.abstracted_channels

            ws_stats = taudem.calculate_watershed_statistics()

            self._fps_summary = None
            self._wsarea = ws_stats['wsarea']
            self._sub_area = sum(summary.area for summary in self._subs_summary.values())
            self._chn_area = sum(summary.area for summary in self._chns_summary.values())
            self._minz = ws_stats['minz']
            self._maxz = ws_stats['maxz']
            self._ruggedness = ws_stats['ruggedness']
            self._area_gt30 = ws_stats['area_gt30']
            self._centroid = ws_stats['ws_centroid']
            self._outlet_top_id = ws_stats['outlet_top_id']

            taudem.write_slps(out_dir=self.wat_dir)

            self._structure = taudem.structure

            self.dump_and_unlock()

            ron = Ron.getInstance(self.wd)
            if any(['lt' in ron.mods, 
                    'portland' in ron.mods, 
                    'seattle' in ron.mods, 
                    'general' in ron.mods]):
                wepp = Wepp.getInstance(self.wd)
                wepp.trigger(TriggerEvents.PREPPING_PHOSPHORUS)

            self.trigger(TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE)

        except Exception:
            self.unlock('-f')
            raise

    def _topaz_abstract_watershed(self):
        self.lock()

        # noinspection PyBroadException
        try:
            wat_dir = self.wat_dir
            assert _exists(wat_dir)

            topaz_wd = self.topaz_wd
            assert _exists(topaz_wd)

            # Create a list of WatershedAbstraction instances
            wat_abs_engines = [WatershedAbstraction(topaz_wd, wat_dir) for i in range(NCPU)]
            pool = multiprocessing.Pool(NCPU)

            _abs = wat_abs_engines[0]

            # abstract channels
            chn_ids = wat_abs_engines[0].chn_ids
            args_list = [(wat_abs_engines[i % NCPU], chn_id) for i, chn_id in enumerate(chn_ids)]
            results = pool.map(process_channel, args_list)

            # collect results
            chns_summary = {}
            chns_paths = {}
            for chn_id, chn_summary, chn_paths in results:
                chns_summary[chn_id] = chn_summary
                chns_paths[chn_id] = chn_paths

            # sync watershed abstraction instances with the updated channel summaries
            for i in range(NCPU):
                wat_abs_engines[i].watershed['channels'] = chns_summary
                wat_abs_engines[i].watershed['channel_paths'] = chns_paths

            # abstract subcatchments
            max_points = self.max_points
            sub_ids = wat_abs_engines[0].sub_ids
            args_list = [(wat_abs_engines[i % NCPU], sub_id, self.clip_hillslopes, self.clip_hillslope_length, max_points)
                         for i, sub_id in enumerate(sub_ids)]
            results = pool.map(process_subcatchment, args_list)

            # collect results
            subs_summary = {}
            fps_summary = {}
            for topaz_id, sub_summary, fp_d in results:
                subs_summary[topaz_id] = sub_summary
                fps_summary[topaz_id] = fp_d

            # sync watershed abstraction instances with the updated channel summaries
            for i in range(NCPU):
                _abs.watershed['hillslopes'] = subs_summary
                _abs.watershed['flowpaths'] = fps_summary

            _abs._write_flowpath_slps(self.wat_dir)

            # write slopes
            _abs.abstract_structure()
            _abs._make_channel_slps(self.wat_dir)
            _abs.write_channels_geojson(_join(topaz_wd, 'channel_paths.wgs.json'))

            self._subs_summary = subs_summary
            self._chns_summary = chns_summary
            self._fps_summary = fps_summary
            self._wsarea = _abs.totalarea
            self._sub_area = sum(summary.area for summary in self._subs_summary.values())
            self._chn_area = sum(summary.area for summary in self._chns_summary.values())
            self._centroid = _abs.centroid.lnglat
            self._outlet_top_id = str(_abs.outlet_top_id)
            self._structure = _abs.structure

            del _abs
            pool.close()
            pool.join()

            self.dump_and_unlock()

            ron = Ron.getInstance(self.wd)
            if any(['lt' in ron.mods, 
                    'portland' in ron.mods, 
                    'seattle' in ron.mods, 
                    'general' in ron.mods]):
                from wepppy.nodb import Wepp
                wepp = Wepp.getInstance(self.wd)
                wepp.trigger(TriggerEvents.PREPPING_PHOSPHORUS)

            self.trigger(TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE)

        except Exception:
            self.unlock('-f')
            raise

    @property
    def report(self):
        return dict(hillslope_n=self.sub_n,
                    channel_n=self.chn_n,
                    totalarea=self.wsarea)

    @property
    def centroid(self) -> Tuple[float, float]:
        return self._centroid

    def sub_summary(self, topaz_id) -> Union[Dict, None]:
        if self._subs_summary is None:
            return None

        if str(topaz_id) in self._subs_summary:
            d = self._subs_summary[str(topaz_id)]
            if isinstance(d, dict):
                return d
            else:
                return d.as_dict()
        else:
            return None

    def fps_summary(self, topaz_id):
        if self._fps_summary is None:
            return None

        if str(topaz_id) in self._fps_summary:
            return self._fps_summary[str(topaz_id)]
        else:
            return None

    # gotcha: using __getitem__ breaks jinja's attribute lookup, so...
    def _(self, wepp_id) -> Union[HillSummary, ChannelSummary]:
        translator = self.translator_factory()
        topaz_id = str(translator.top(wepp=int(wepp_id)))

        if topaz_id in self._subs_summary:
            return self._subs_summary[topaz_id]
        elif topaz_id in self._chns_summary:
            return self._chns_summary[topaz_id]

        raise IndexError

    @property
    def subs_summary(self) -> Dict[str, Dict]:
        return {k: v.as_dict() for k, v in self._subs_summary.items()}

    def sub_iter(self) -> Generator[HillSummary, None, None]:
        if self.sub_n > 0:
            for topaz_id, v in self._subs_summary.items():
                yield topaz_id, v

    def chn_summary(self, topaz_id) -> Union[Generator[ChannelSummary, None, None], None]:
        if str(topaz_id) in self._chns_summary:
            d =  self._chns_summary[str(topaz_id)]
            if isinstance(d, dict):
                return d
            else:
                return d.as_dict()
        else:
            return None

    @property
    def chns_summary(self) -> Dict[str, Dict]:
        return {k: v.as_dict() for k, v in self._chns_summary.items()}

    def chn_iter(self) -> Generator[ChannelSummary, None, None]:
        if self.chn_n > 0:
            for topaz_id, v in self._chns_summary.items():
                yield topaz_id, v

    def area_of(self, topaz_id):
        topaz_id = str(topaz_id)
        if topaz_id.endswith('4'):
            return self._chns_summary[topaz_id].area
        else:
            return self._subs_summary[topaz_id].area


class Outlet(object):
    def __init__(self,
                 requested_loc,
                 actual_loc,
                 distance_from_requested,
                 pixel_coords):
        self.requested_loc = requested_loc
        self.actual_loc = actual_loc
        self.distance_from_requested = distance_from_requested
        self.pixel_coords = pixel_coords

    def as_dict(self):
        return dict(lng=self.actual_loc[0],
                    lat=self.actual_loc[1])
