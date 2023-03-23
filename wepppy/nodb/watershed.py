# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from typing import Generator, Dict, Union, Tuple

import os
import json
from enum import IntEnum

from os.path import join as _join
from os.path import exists as _exists

import jsonpickle
import utm
import numpy as np

from osgeo import gdal, osr
from osgeo.gdalconst import *

import wepppy
from wepppy.watershed_abstraction import (
    WatershedAbstraction,
    WeppTopTranslator
)
from wepppy.taudem import TauDEMTopazEmulator
from wepppy.watershed_abstraction import SlopeFile
from wepppy.watershed_abstraction.support import HillSummary, ChannelSummary
from wepppy.all_your_base.geo import read_raster, haversine

from .ron import Ron
from .base import NoDbBase, TriggerEvents
from .topaz import Topaz
from .prep import Prep


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


class Watershed(NoDbBase):
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

            delineation_backend = self.config_get_str('watershed', 'delineation_backend')
            if delineation_backend.lower().startswith('taudem'):
                self._delineation_backend = DelineationBackend.TauDEM
                taudem_wd = self.taudem_wd
                if not _exists(taudem_wd):
                    os.mkdir(taudem_wd)

                self._csa = self.config_get_float('watershed', 'csa')
                self._pkcsa = self.config_get_str('watershed', 'pkcsa')

            else:
                self._delineation_backend = DelineationBackend.TOPAZ

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
    def getInstance(wd):
        with open(_join(wd, 'watershed.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Watershed)

            if _exists(_join(wd, 'READONLY')):
                db.wd = os.path.abspath(wd)
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

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
        assert isinstance(value, Outlet)

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

        if self.delineation_backend_is_topaz:      
            Topaz.getInstance(self.wd).build_channels(csa=self.csa, mcl=self.mcl)
        else:
            TauDEMTopazEmulator(self.taudem_wd, self.dem_fn).build_channels(csa=self.csa)

        if _exists(self.subwta):
            os.remove(self.subwta)

        try:
            prep = Prep.getInstance(self.wd)
            prep.timestamp('build_channels')
        except FileNotFoundError:
            pass

    #
    # set outlet
    #
    def set_outlet(self, lng=None, lat=None, da=0.0):
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
            prep = Prep.getInstance(self.wd)
            prep.timestamp('set_outlet')
        except FileNotFoundError:
            pass
        
    #
    # build subcatchments
    #
    def build_subcatchments(self, pkcsa=None):
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

    #
    # abstract watershed
    #
    def abstract_watershed(self):

        if self.delineation_backend_is_topaz:
            self._topaz_abstract_watershed()
        else:
            self._taudem_abstract_watershed()

        
        if self.multi_ofe:
            self._build_multiple_ofe()
       
        try: 
            prep = Prep.getInstance(self.wd)
            prep.timestamp('abstract_watershed')
        except FileNotFoundError:
            pass

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
        return getattr(self, '_mofe_target_length', False)

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

            mofe_slp_fn = _join(self.wat_dir, f'hill_{topaz_id}.mofe.slp')
            d_fractions = SlopeFile.mofe_distance_fractions(mofe_slp_fn)

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
                                            (discha >= _min) & (discha <= _max)) 
                    mofe_map[mofe_indices] = j
                    j += 1             

            mofe_ids = set(mofe_map[indices])
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
            self._minz = ws_stats['minz']
            self._maxz = ws_stats['maxz']
            self._ruggedness = ws_stats['ruggedness']
            self._area_gt30 = ws_stats['area_gt30']
            self._centroid = ws_stats['ws_centroid']
            self._outlet_top_id = ws_stats['outlet_top_id']

            taudem.write_slps(out_dir=self.wat_dir)

            self._structure = taudem.structure

            self.dump_and_unlock()

            ron = wepppy.Ron.getInstance(self.wd)
            if any(['lt' in ron.mods, 
                    'portland' in ron.mods, 
                    'seattle' in ron.mods, 
                    'general' in ron.mods]):
                wepp = wepppy.nodb.Wepp.getInstance(self.wd)
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

            _abs = WatershedAbstraction(topaz_wd, wat_dir)
            _abs.abstract(wepp_chn_type=self.wepp_chn_type,
                          clip_hillslopes=self.clip_hillslopes,
                          clip_hillslope_length=self.clip_hillslope_length)
            _abs.write_slps()

            chns_summary = {}
            for k, v in _abs.watershed['channels'].items():
                topaz_id = int(k.replace('chn_', ''))
                chns_summary[topaz_id] = v

            subs_summary = {}
            fps_summary = {}
            for k, v in _abs.watershed['hillslopes'].items():
                topaz_id = int(k.replace('hill_', ''))
                subs_summary[topaz_id] = v
                fps_summary[topaz_id] = _abs.watershed['flowpaths'][k]

            self._subs_summary = subs_summary
            self._chns_summary = chns_summary
            self._fps_summary = fps_summary
            self._wsarea = _abs.totalarea
            self._centroid = _abs.centroid.lnglat
            self._outlet_top_id = str(_abs.outlet_top_id)
            self._structure = _abs.structure

            _abs.write_channels_geojson(_join(topaz_wd, 'channel_paths.wgs.json'))

            del _abs

            self.dump_and_unlock()

            ron = wepppy.nodb.Ron.getInstance(self.wd)
            if any(['lt' in ron.mods, 
                    'portland' in ron.mods, 
                    'seattle' in ron.mods, 
                    'general' in ron.mods]):
                wepp = wepppy.nodb.Wepp.getInstance(self.wd)
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
            return self._subs_summary[str(topaz_id)].as_dict()
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
            return self._chns_summary[str(topaz_id)].as_dict()
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
