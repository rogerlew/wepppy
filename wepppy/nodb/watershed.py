# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from typing import Generator, Dict, Union, Tuple

import time
import os
import inspect

from enum import IntEnum

from os.path import join as _join
from os.path import exists as _exists

import jsonpickle
import jsonpickle.ext.numpy as jsonpickle_numpy
jsonpickle_numpy.register_handlers()

import pandas as pd
import numpy as np

import multiprocessing

from osgeo import gdal, osr
from osgeo.gdalconst import *

from deprecated import deprecated

from wepppy.topo.watershed_abstraction import WatershedAbstraction, WeppTopTranslator
from wepppy.topo.taudem import TauDEMTopazEmulator
from wepppy.topo.peridot.runner import (
    run_peridot_abstract_watershed,
    run_peridot_wbt_abstract_watershed,
    post_abstract_watershed,
    read_network,
)
from wepppy.topo.peridot.flowpath import (
    PeridotFlowpath,
    PeridotHillslope,
    PeridotChannel,
)
from wepppy.topo.watershed_abstraction import SlopeFile
from wepppy.topo.watershed_abstraction.support import HillSummary, ChannelSummary, identify_edge_hillslopes
from wepppy.topo.watershed_abstraction.slope_file import mofe_distance_fractions
from wepppy.topo.wbt import WhiteboxToolsTopazEmulator
from wepppy.all_your_base.geo import read_raster, haversine

from .ron import Ron
from .base import NoDbBase, TriggerEvents
from .topaz import Topaz
from .redis_prep import RedisPrep, TaskEnum

from wepppy.all_your_base import NCPU

NCPU = multiprocessing.cpu_count() - 2


class DelineationBackend(IntEnum):
    TOPAZ = 1
    TauDEM = 2
    WBT = 3


class WatershedNotAbstractedError(Exception):
    """
    The watershed has not been abstracted. The watershed must be delineated
    to complete this operation.
    """

    __name__ = "WatershedNotAbstractedError"

    def __init__(self):
        pass


class WatershedNoDbLockedException(Exception):
    pass


@deprecated
def process_channel(args):
    wat_abs, chn_id = args
    chn_summary, chn_paths = wat_abs.abstract_channel(chn_id)
    return chn_id, chn_summary, chn_paths


@deprecated
def process_subcatchment(args):
    wat_abs, sub_id, clip_hillslopes, clip_hillslope_length, max_points = args

    sub_summary, fp_d = wat_abs.abstract_subcatchment(
        sub_id,
        clip_hillslopes=clip_hillslopes,
        clip_hillslope_length=clip_hillslope_length,
        max_points=max_points,
    )

    return sub_id, sub_summary, fp_d


TRANSIENT_FIELDS = ["_sub_area_lookup", "_sub_length_lookup", "_sub_centroid_lookup"]


class Watershed(NoDbBase):
    __name__ = "Watershed"
    filename = 'watershed.nodb'
    _js_decode_replacements = (
        (
            "wepppy.watershed_abstraction.support.HillSummary",
            "wepppy.topo.watershed_abstraction.support.HillSummary",
        ),
        (
            "wepppy.watershed_abstraction.support.ChannelSummary",
            "wepppy.topo.watershed_abstraction.support.ChannelSummary",
        ),
        (
            "wepppy.watershed_abstraction.support.CentroidSummary",
            "wepppy.topo.watershed_abstraction.support.CentroidSummary",
        ),
    )

    def __init__(self, wd, cfg_fn):
        super(Watershed, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            self._subs_summary = None  # deprecated watershed/hillslopes.csv
            self._fps_summary = None  # deprecated watershed/flowpaths.csv
            self._structure = None
            self._chns_summary = None  # deprecated watershed/channels.csv
            self._wsarea = None
            self._impoundment_n = 0
            self._centroid = None
            self._outlet_top_id = None
            self._outlet = None
            self._set_extent_mode = 0
            self._map_bounds_text = ""

            self._wepp_chn_type = self.config_get_str("soils", "wepp_chn_type")

            self._clip_hillslope_length = self.config_get_float(
                "watershed", "clip_hillslope_length"
            )
            self._clip_hillslopes = self.config_get_bool("watershed", "clip_hillslopes")
            self._bieger2015_widths = self.config_get_bool(
                "watershed", "bieger2015_widths"
            )
            self._walk_flowpaths = self.config_get_bool("watershed", "walk_flowpaths")
            self._max_points = self.config_get_int("watershed", "max_points", None)

            delineation_backend = self.config_get_str(
                "watershed", "delineation_backend"
            )
            if delineation_backend.lower().startswith("taudem"):
                self._delineation_backend = DelineationBackend.TauDEM
                taudem_wd = self.taudem_wd
                if not _exists(taudem_wd):
                    os.mkdir(taudem_wd)

                self._csa = self.config_get_float("taudem", "csa")
                self._pkcsa = self.config_get_str("taudem", "pkcsa")

            elif delineation_backend.lower().startswith("wbt"):
                self._delineation_backend = DelineationBackend.WBT
                wbt_dir = self.wbt_wd
                if not _exists(wbt_dir):
                    os.mkdir(wbt_dir)
                self._wbt = None
                self._csa = self.config_get_float("watershed.wbt", "csa", 5)
                self._mcl = self.config_get_float("watershed.wbt", "mcl", 60)
                self._wbt_fill_or_breach = self.config_get_str(
                    "watershed.wbt", "fill_or_breach", "breach_least_cost"
                )
                self._wbt_blc_dist = self.config_get_int(
                    "watershed.wbt", "blc_dist", 1000
                )

            else:
                self._delineation_backend = DelineationBackend.TOPAZ

            self._abstraction_backend = self.config_get_str(
                "watershed", "abstraction_backend", "peridot"
            )

            wat_dir = self.wat_dir
            if not _exists(wat_dir):
                os.mkdir(wat_dir)

            self._mofe_nsegments = None
            self._mofe_target_length = self.config_get_float(
                "watershed", "mofe_target_length"
            )
            self._mofe_buffer = self.config_get_bool("watershed", "mofe_buffer")
            self._mofe_buffer_length = self.config_get_float(
                "watershed", "mofe_buffer_length"
            )
            self._mofe_max_ofes = self.config_get_int("watershed", "mofe_max_ofes", 19)

            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    def __getstate__(self):
        state = super().__getstate__()

        for field in TRANSIENT_FIELDS:
            state.pop(field, None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    @property
    def set_extent_mode(self):
        if not hasattr(self, "_set_extent_mode"):
            return 0
        return self._set_extent_mode
    
    @set_extent_mode.setter
    def set_extent_mode(self, value: int):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')
        
        _value = int(value)
        self.lock()

        try:
            assert _value in [0, 1], f"Invalid set_extent_mode value: {_value}"
            self._set_extent_mode = _value
            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    @property
    def map_bounds_text(self):
        if not hasattr(self, "_map_bounds_text"):
            return ""
        return self._map_bounds_text
    
    @map_bounds_text.setter
    def map_bounds_text(self, value: str):
        _value = str(value)

        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name} -> {_value}')

        self.lock()

        try:
            self._map_bounds_text = _value
            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    @classmethod
    def _decode_jsonpickle(cls, json_text):
        try:
            return super()._decode_jsonpickle(json_text)
        except TypeError as e:
            if (
                "scalar() argument 1 must be numpy.dtype" in str(e)
                or "numpy" in str(e)
                or "dtype" in str(e)
            ):
                return cls._decode_watershed_safe(json_text)
            raise


    @staticmethod
    def _decode_watershed_safe(s: str):
        """
        Normalize jsonpickle payloads that contain NumPy scalars so they
        become plain Python numbers (floats/ints). Also strips read-only
        'dtype' fields that cause setattr errors during unpickling.
        """
        import json, base64, struct

        def _from_b64_f64(b64):
            try:
                return struct.unpack("<d", base64.b64decode(b64))[0]
            except Exception:
                return None

        def _decode_numpy_scalar_from_reduce(red):
            # [ {"py/function":"numpy.core.multiarray.scalar"},
            #   {"py/tuple": [ <dtype or {"py/id":n}>, <valSpec>] } ]
            if not (isinstance(red, list) and red and isinstance(red[0], dict)):
                return None, False
            if not str(red[0].get("py/function","")).endswith("multiarray.scalar"):
                return None, False
            args = red[1]
            tup = isinstance(args, dict) and args.get("py/tuple")
            if not (isinstance(tup, list) and len(tup) >= 2):
                return None, False
            val_spec = tup[1]
            if isinstance(val_spec, dict) and "py/b64" in val_spec:
                v = _from_b64_f64(val_spec["py/b64"])
                if v is not None:
                    return v, True
            # sometimes value is already numeric/stringy
            try:
                return float(val_spec), True
            except Exception:
                return val_spec, True

        def _maybe_cast_int(v):
            # optional: keep ints as ints if representable exactly
            try:
                fv = float(v)
                return int(fv) if fv.is_integer() else fv
            except Exception:
                return v

        def fix(o):
            if isinstance(o, dict):
                # Drop read-only dtype fields that will be assigned via setattr
                if "dtype" in o and not isinstance(o["dtype"], str):
                    o = {k: v for k, v in o.items() if k != "dtype"}

                # numpy scalar via py/reduce
                red = o.get("py/reduce")
                if isinstance(red, list):
                    val, matched = _decode_numpy_scalar_from_reduce(red)
                    if matched:
                        return _maybe_cast_int(val)

                # numpy scalar/object with value (e.g., {"py/object":"numpy.float64", "value": ...})
                pobj = o.get("py/object", "")
                if isinstance(pobj, str) and pobj.startswith("numpy."):
                    if "value" in o:
                        v = o["value"]
                        if isinstance(v, dict) and "py/b64" in v:
                            v = _from_b64_f64(v["py/b64"])
                        return _maybe_cast_int(v)
                    # also strip dtype here if present
                    if "dtype" in o:
                        o = {k: v for k, v in o.items() if k != "dtype"}

                # Recurse
                return {k: fix(v) for k, v in o.items()}

            if isinstance(o, list):
                return [fix(v) for v in o]
            return o

        data = json.loads(s)
        data = fix(data)
        # decode again, now free of problematic numpy scalars/dtype attrs
        import jsonpickle
        return jsonpickle.decode(json.dumps(data))



    @property
    def _status_channel(self):
        return f"{self.runid}:watershed"

    @property
    def status_log(self):
        return os.path.abspath(_join(self.wat_dir, "status.log"))

    @property
    def delineation_backend(self):
        delineation_backend = getattr(self, "_delineation_backend", None)
        if delineation_backend is None:
            return DelineationBackend.TOPAZ
        return delineation_backend

    @property
    def delineation_backend_is_topaz(self):
        delineation_backend = getattr(self, "_delineation_backend", None)
        if delineation_backend is None:
            return True
        return delineation_backend == DelineationBackend.TOPAZ

    @property
    def wbt_fill_or_breach(self):
        return getattr(self, "_wbt_fill_or_breach", "fill")

    @wbt_fill_or_breach.setter
    def wbt_fill_or_breach(self, value):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')

        self.lock()

        try:
            assert value in [
                "fill",
                "breach",
                "breach_least_cost",
            ], f"Invalid wbt_fill_or_breach value: {value}"
            self._wbt_fill_or_breach = value
            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    @property
    def wbt_blc_dist(self) -> int:
        return getattr(self, "_wbt_blc_dist", 1000)

    @wbt_blc_dist.setter
    def wbt_blc_dist(self, value: int):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')

        self.lock()

        try:
            self._wbt_blc_dist = value
            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    @property
    def max_points(self):
        pts = getattr(self, "_max_points", None)
        if pts is None:
            return 99
        return pts

    @property
    def abstraction_backend(self):
        return getattr(self, "_abstraction_backend", "topaz")

    @property
    def abstraction_backend_is_peridot(self):
        return self.abstraction_backend == "peridot"

    @property
    def clip_hillslopes(self):
        return getattr(self, "_clip_hillslopes", False) and not self.multi_ofe

    @clip_hillslopes.setter
    def clip_hillslopes(self, value):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')

        self.lock()

        # noinspection PyBroadException
        try:
            self._clip_hillslopes = value
            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    @property
    def clip_hillslope_length(self):
        return getattr(self, "_clip_hillslope_length", 300.0)

    @clip_hillslope_length.setter
    def clip_hillslope_length(self, value):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')

        self.lock()

        # noinspection PyBroadException
        try:
            self._clip_hillslope_length = value
            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    @property
    def bieger2015_widths(self):
        return getattr(self, "_bieger2015_widths", False)

    @bieger2015_widths.setter
    def bieger2015_widths(self, value):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')

        self.lock()

        # noinspection PyBroadException
        try:
            self._bieger2015_widths = value
            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    @property
    def walk_flowpaths(self):
        return getattr(self, "_walk_flowpaths", True)

    @walk_flowpaths.setter
    def walk_flowpaths(self, value):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')

        self.lock()

        # noinspection PyBroadException
        try:
            self._walk_flowpaths = value
            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    @property
    def delineation_backend_is_taudem(self):
        delineation_backend = getattr(self, "_delineation_backend", None)
        if delineation_backend is None:
            return False
        return delineation_backend == DelineationBackend.TauDEM

    @property
    def delineation_backend_is_wbt(self):
        delineation_backend = getattr(self, "_delineation_backend", None)
        if delineation_backend is None:
            return False
        return delineation_backend == DelineationBackend.WBT

    @property
    def is_abstracted(self):
        return self._subs_summary is not None and self._chns_summary is not None

    @property
    def _nodb(self):
        return _join(self.wd, "watershed.nodb")

    @property
    def _lock(self):
        return _join(self.wd, "watershed.nodb.lock")

    @property
    def wepp_chn_type(self):
        return getattr(
            self, "_wepp_chn_type", self.config_get_str("soils", "wepp_chn_type")
        )

    @property
    def subwta(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "SUBWTA.ARC")
        elif self.delineation_backend_is_wbt:
            return self.wbt.subwta
        else:
            return _join(self.taudem_wd, "subwta.tif")

    @property
    def discha(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "DISCHA.ARC")
        elif self.delineation_backend_is_wbt:
            if self.wbt is not None:
                return self.wbt.discha
            else:
                return None
        else:
            raise NotImplementedError("taudem distance to channel map not specified")

    @property
    def subwta_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "SUBCATCHMENTS.WGS.JSON")
        elif self.delineation_backend_is_wbt:
            if self.wbt is not None:
                return self.wbt.subcatchments_wgs_json
            else:
                return None
        else:
            return _join(self.taudem_wd, "subcatchments.WGS.geojson")

    @property
    def subwta_utm_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "SUBCATCHMENTS.JSON")
        elif self.delineation_backend_is_wbt:
            if self.wbt is not None:
                return self.wbt.subcatchments_json
            else:
                return None
        else:
            return _join(self.taudem_wd, "subcatchments.geojson")

    @property
    def bound(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "BOUND.ARC")
        elif self.delineation_backend_is_wbt:
            if self.wbt is not None:
                return self.wbt.bound
            else:
                return None
        else:
            return _join(self.taudem_wd, "bound.tif")

    @property
    def bound_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "BOUND.WGS.JSON")
        elif self.delineation_backend_is_wbt:
            if self.wbt is not None:
                return self.wbt.bound_wgs_json
            else:
                return None
        else:
            return _join(self.taudem_wd, "bound.WGS.geojson")

    @property
    def bound_utm_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "BOUND.JSON")
        else:
            return _join(self.taudem_wd, "bound.geojson")

    @property
    def netful(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "NETFUL.ARC")
        elif self.delineation_backend_is_wbt:
            if self.wbt is not None:
                return self.wbt.netful
            else:
                return None
        else:
            return _join(self.taudem_wd, "src.tif")

    @property
    def netful_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "NETFUL.WGS.JSON")
        elif self.delineation_backend_is_wbt:
            if self.wbt is not None:
                return self.wbt.netful_wgs_json
            else:
                return None
        else:
            return _join(self.taudem_wd, "netful.WGS.geojson")

    @property
    def netful_utm_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "NETFUL.JSON")
        elif self.delineation_backend_is_wbt:
            if self.wbt is not None:
                return self.wbt.netful_json
            else:
                return None
        else:
            return _join(self.taudem_wd, "netful.geojson")

    @property
    def channels_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "CHANNELS.WGS.JSON")
        elif self.delineation_backend_is_wbt:
            if self.wbt is not None:
                return self.wbt.channels_wgs_json
            else:
                return None
        else:
            return _join(self.taudem_wd, "net.WGS.geojson")

    @property
    def channels_utm_shp(self):
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "CHANNELS.JSON")
        elif self.delineation_backend_is_wbt:
            if self.wbt is not None:
                return self.wbt.channels_json
            else:
                return None
        else:
            return _join(self.taudem_wd, "net.geojson")

    @property
    def sub_n(self) -> int:
        if self._subs_summary is None:
            return 0

        return len(self._subs_summary)

    @property
    def greater300_n(self) -> int:
        if self._subs_summary is None:
            return 0

        # use duckdb
        if _exists(_join(self.wat_dir, "hillslopes.parquet")):
            import duckdb

            try:
                with duckdb.connect(_join(self.wat_dir, "hillslopes.parquet")) as con:
                    sql = "SELECT COUNT(*) FROM hillslopes WHERE length > 300"
                    result = con.execute(sql).fetchone()
                    return result[0]
            except duckdb.duckdb.IOException:
                time.sleep(4)  # fix for slow NAS after abstraction
                with duckdb.connect(_join(self.wat_dir, "hillslopes.parquet")) as con:
                    sql = "SELECT COUNT(*) FROM hillslopes WHERE length > 300"
                    result = con.execute(sql).fetchone()
                    return result[0]

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
        return getattr(self, "_wsarea", 1)

    @property
    def structure(self):
        if _exists(_join(self.wat_dir, "structure.pkl")):
            import pickle

            with open(self._structure, "rb") as fp:
                return pickle.load(fp)

        return self._structure

    @property
    def csa(self):
        csa = getattr(self, "_csa", None)
        if csa is None and self.delineation_backend_is_topaz:
            csa = Topaz.getInstance(self.wd).csa

        return csa

    @property
    def mcl(self):
        mcl = getattr(self, "_mcl", None)
        if self.delineation_backend_is_topaz:

            if mcl is None:
                mcl = Topaz.getInstance(self.wd).mcl
            return mcl

        return mcl

    @property
    def outlet(self):
        if hasattr(self, "_outlet"):
            return self._outlet

        return Topaz.getInstance(self.wd).outlet

    @outlet.setter
    def outlet(self, value):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')
        
        assert isinstance(value, Outlet) or value is None

        self.lock()

        # noinspection PyBroadException
        try:
            self._outlet = value
            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    @property
    def has_outlet(self):
        return self.outlet is not None

    @property
    def has_channels(self) -> bool:
        if self.delineation_backend_is_wbt and self.wbt is None:
            return False

        return _exists(self.netful)

    @property
    def has_subcatchments(self) -> bool:
        if self.delineation_backend_is_wbt and self.wbt is None:
            return False

        return _exists(self.subwta)

    @property
    def outlet_top_id(self):
        return self._outlet_top_id

    @property
    def relief(self):
        if self.delineation_backend_is_topaz:
            return Topaz.getInstance(self.wd).relief
        elif self.wbt is not None:
            return self.wbt.relief

        return None

    def translator_factory(self):
        if self._chns_summary is None:
            raise Exception("No chn_ids available for translator")

        if self._subs_summary is None:
            raise Exception("No sub_ids available for translator")

        return WeppTopTranslator(
            map(int, self._subs_summary.keys()), map(int, self._chns_summary.keys())
        )

    #
    # build channels
    #
    def build_channels(self, csa=None, mcl=None):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(csa={csa}, mcl={mcl})')

        assert not self.islocked()
        self.logger.info("Building Channels")

        if csa or mcl:
            self.lock()
            try:
                if csa is not None:
                    self._csa = csa

                if mcl is not None:
                    self._mcl = mcl

                self.dump_and_unlock()
            except:
                self.unlock("-f")
                raise

        if self.outlet is not None:
            self.remove_outlet()

        if self.delineation_backend_is_topaz:
            self.logger.info(f' delineation_backend_is_topaz')
            Topaz.getInstance(self.wd).build_channels(csa=self.csa, mcl=self.mcl)
        elif self.delineation_backend_is_wbt:
            self.logger.info(f' delineation_backend_is_wbt')
            wbt = WhiteboxToolsTopazEmulator(
                self.wbt_wd,
                self.dem_fn,
                logger=self.logger,
            )
            wbt.delineate_channels(
                csa=self.csa,
                mcl=self.mcl,
                fill_or_breach=self.wbt_fill_or_breach,
                blc_dist=self.wbt_blc_dist,
                logger=self.logger,
            )
            self.wbt = wbt

        else:
            self.logger.info(f' delineation_backend_is_taudem')
            TauDEMTopazEmulator(self.taudem_wd, self.dem_fn).build_channels(
                csa=self.csa
            )

        if _exists(self.subwta):
            self.logger.info(f' Removing subcatchment: {self.subwta}')
            os.remove(self.subwta)

        prep = RedisPrep.getInstance(self.wd)
        prep.timestamp(TaskEnum.build_channels)

    @property
    def wbt(self):
        return self._wbt

    @wbt.setter
    def wbt(self, value):
        assert isinstance(value, WhiteboxToolsTopazEmulator)

        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')
        
        self.lock()
        try:
            if value is None:
                self._wbt = None
            else:
                assert isinstance(value, WhiteboxToolsTopazEmulator)
                self._wbt = value
            self.dump_and_unlock()
        except Exception:
            self.unlock("-f")
            raise

    #
    # set outlet
    #
    def set_outlet(self, lng=None, lat=None, da=0.0):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(lng={lng}, lat={lat}, da={da})')
        
        assert not self.islocked()
        self.logger.info("Setting Outlet")

        assert float(lng), lng
        assert float(lat), lat

        if self.delineation_backend_is_topaz:
            self.logger.info(f' delineation_backend_is_topaz')
            topaz = Topaz.getInstance(self.wd)
            topaz.set_outlet(lng=lng, lat=lat, da=da)
            self.outlet = topaz.outlet
        elif self.delineation_backend_is_wbt:
            self.logger.info(f' delineation_backend_is_wbt')
            wbt = self.wbt
            self.outlet = wbt.set_outlet(lng=lng, lat=lat, logger=self.logger)
            self.wbt = wbt
        else:
            self.logger.info(f' delineation_backend_is_taudem')
            taudem = TauDEMTopazEmulator(self.taudem_wd, self.dem_fn)
            taudem.set_outlet(lng=lng, lat=lat)

            map = Ron.getInstance(self.wd).map
            o_x, o_y = map.lnglat_to_px(*taudem.outlet)
            distance = haversine((lng, lat), taudem.outlet) * 1000  # in m
            self.outlet = Outlet(
                requested_loc=(lng, lat),
                actual_loc=taudem.outlet,
                distance_from_requested=distance,
                pixel_coords=(o_x, o_y),
            )

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.set_outlet)
        except FileNotFoundError:
            pass

    def remove_outlet(self):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')

        self.outlet = None

    #
    # build subcatchments
    #
    def build_subcatchments(self, pkcsa=None):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(pkcsa={pkcsa})')

        assert not self.islocked()

        if self.delineation_backend_is_topaz:
            self.logger.info(f' delineation_backend_is_topaz')
            Topaz.getInstance(self.wd).build_subcatchments()
        elif self.delineation_backend_is_wbt:
            self.logger.info(f' delineation_backend_is_wbt')
            wbt = self.wbt
            wbt.delineate_subcatchments(self.logger)
            self.identify_edge_hillslopes()
        else:
            self.logger.info(f' delineation_backend_is_taudem')
            self.lock()
            try:
                if pkcsa is not None:
                    self._pkcsa = pkcsa

                self.dump_and_unlock()
            except:
                self.unlock("-f")
                raise
            self._taudem_build_subcatchments()

    def identify_edge_hillslopes(self):
        """
        Identify edge hillslopes in the watershed.
        This is used to determine which hillslopes are at the edge of the watershed.
        """
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')

        self.lock()
        try:
            self._edge_hillslopes = identify_edge_hillslopes(self.subwta, self.logger)
        except Exception:
            self.unlock("-f")
            raise
        else:
            self.dump_and_unlock()

    @property
    def edge_hillslopes(self):
        """
        Get the edge hillslopes in the watershed.
        """
        if not hasattr(self, "_edge_hillslopes"):
            self.identify_edge_hillslopes()
        return self._edge_hillslopes

    @property
    def pkcsa(self):
        return getattr(self, "_pkcsa", None)

    @property
    def pkcsa_drop_table_html(self):
        assert self.delineation_backend_is_taudem
        taudem = TauDEMTopazEmulator(self.taudem_wd, self.dem_fn)

        import pandas as pd

        df = pd.read_csv(taudem._drp, skipfooter=1, engine="python")
        return df.to_html(border=0, classes=["table"], index=False, index_names=False)

    @property
    def pkcsa_drop_analysis_threshold(self):
        assert self.delineation_backend_is_taudem
        taudem = TauDEMTopazEmulator(self.taudem_wd, self.dem_fn)
        return taudem.drop_analysis_threshold

    def _taudem_build_subcatchments(self):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')

        self.lock()

        # noinspection PyBroadException
        try:
            taudem = TauDEMTopazEmulator(self.taudem_wd, self.dem_fn)

            pkcsa = self.pkcsa
            if pkcsa == "auto":
                pkcsa = None
            taudem.build_subcatchments(threshold=pkcsa)
            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    @property
    def network(self):
        if self.abstraction_backend_is_peridot:
            network = read_network(_join(self.wat_dir, "network.txt"))
            return network
        else:
            raise NotImplementedError("network not implemented")

    #
    # abstract watershed
    #

    def abstract_watershed(self):
        assert not self.islocked()
        self.logger.info("Abstracting Watershed")

        if self.abstraction_backend_is_peridot:
            if self.delineation_backend_is_topaz:
                run_peridot_abstract_watershed(
                    self.wd,
                    clip_hillslopes=False,
                    clip_hillslope_length=self.clip_hillslope_length,
                    bieger2015_widths=self.bieger2015_widths,
                )
            elif self.delineation_backend_is_wbt:
                run_peridot_wbt_abstract_watershed(
                    self.wd,
                    clip_hillslopes=self.clip_hillslopes,
                    clip_hillslope_length=self.clip_hillslope_length,
                    bieger2015_widths=self.bieger2015_widths,
                )

            self._peridot_post_abstract_watershed()

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

    def _peridot_post_abstract_watershed(self):
        self.logger.info("_peridot_post_abstract_watershed")

        self.lock()
        try:
            sub_area, chn_area, ws_centroid, sub_ids, chn_ids = post_abstract_watershed(
                self.wd
            )
            self._centroid = ws_centroid
            self._sub_area = sub_area
            self._chn_area = chn_area
            self._wsarea = sub_area + chn_area

            # this is the shit you have to support projects over 8 years of CI/CD
            self._subs_summary = {str(topaz_id): None for topaz_id in sub_ids}
            self._chns_summary = {str(topaz_id): None for topaz_id in chn_ids}

            network = self.network
            structure_fn = _join(self.wat_dir, "structure.pkl")
            translator = self.translator_factory()
            translator.build_structure(network, pickle_fn=structure_fn)
            self._structure = structure_fn

            self.dump_and_unlock()
        except:
            self.unlock("-f")
            raise

    @property
    def sub_area(self):
        sub_area = getattr(self, "_sub_area", None)

        if sub_area is None:
            sub_area = sum(summary.area for summary in self._subs_summary.values())

        return sub_area

    @property
    def chn_area(self):
        chn_area = getattr(self, "_chn_area")

        if chn_area is None:
            chn_area = sum(summary.area for summary in self._chns_summary.values())

        return chn_area

    @property
    def mofe_nsegments(self):
        return getattr(self, "_mofe_nsegments", None)

    @property
    def mofe_target_length(self):
        return getattr(self, "_mofe_target_length", 50)

    @mofe_target_length.setter
    def mofe_target_length(self, value):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')

        self.lock()

        # noinspection PyBroadException
        try:
            self._mofe_target_length = value
            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    @property
    def mofe_buffer(self):
        return getattr(self, "_mofe_buffer", False)

    @mofe_buffer.setter
    def mofe_buffer(self, value):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')

        self.lock()

        # noinspection PyBroadException
        try:
            self._mofe_buffer = bool(value)
            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    @property
    def mofe_max_ofes(self):
        return getattr(self, "_mofe_max_ofes", 19)

    @mofe_max_ofes.setter
    def mofe_max_ofes(self, value):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')

        self.lock()

        # noinspection PyBroadException
        try:
            self._mofe_max_ofes = value
            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    @property
    def mofe_buffer_length(self):
        return getattr(self, "_mofe_buffer_length", 15)

    @mofe_buffer_length.setter
    def mofe_buffer_length(self, value):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')

        self.lock()

        # noinspection PyBroadException
        try:
            self._mofe_buffer_length = value
            self.dump_and_unlock()

        except Exception:
            self.unlock("-f")
            raise

    def _build_multiple_ofe(self):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')
        _mofe_nsegments = {}
        for topaz_id, wat_ss in self.subs_summary.items():
            not_top = not str(topaz_id).endswith("1")

            if isinstance(wat_ss, HillSummary):
                slp_fn = _join(self.wat_dir, wat_ss.fname)
            else:
                slp_fn = _join(self.wat_dir, wat_ss.slp_rel_path)

            slp = SlopeFile(slp_fn)
            _mofe_nsegments[topaz_id] = slp.segmented_multiple_ofe(
                target_length=self.mofe_target_length,
                apply_buffer=self.mofe_buffer and not_top,
                buffer_length=self.mofe_buffer_length,
                max_ofes=self.mofe_max_ofes,
            )

        self.lock()

        # noinspection PyBroadException
        try:
            self._mofe_nsegments = _mofe_nsegments
            self.dump_and_unlock()
        except Exception:
            self.unlock("-f")
            raise

        self._build_mofe_map()

    @property
    def mofe_map(self):
        return _join(self.wat_dir, "mofe.tif")

    def _build_mofe_map(self):
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')
        subwta, transform_s, proj_s = read_raster(self.subwta, dtype=np.int32)
        discha, transform_d, proj_d = read_raster(self.discha, dtype=np.int32)
        mofe_nsegments = self.mofe_nsegments

        mofe_map = np.zeros(subwta.shape, np.int32)
        for topaz_id, wat_ss in self.subs_summary.items():
            indices = np.where(subwta == int(topaz_id))
            _discha_vals = discha[indices]
            max_discha = np.max(_discha_vals)

            if isinstance(wat_ss, HillSummary):
                slp_fn = _join(self.wat_dir, wat_ss.fname)
            else:
                slp_fn = _join(self.wat_dir, wat_ss.slp_rel_path)

            mofe_slp_fn = _join(self.wat_dir, slp_fn.replace(".slp", ".mofe.slp"))
            d_fractions = mofe_distance_fractions(mofe_slp_fn)

            n_ofe = len(d_fractions) - 1
            if n_ofe == 1:
                mofe_indices = np.where(subwta == int(topaz_id))
                mofe_map[mofe_indices] = 1
            else:
                j = 1
                for i in range(n_ofe):
                    _max_pct = (1.0 - d_fractions[i]) * 100
                    _min_pct = (1.0 - d_fractions[i + 1]) * 100
                    _min = np.percentile(_discha_vals, _min_pct)
                    _max = np.percentile(_discha_vals, _max_pct)

                    mofe_indices = np.where(
                        (subwta == int(topaz_id))
                        & (mofe_map == 0)
                        & (discha >= _min)
                        & (discha <= _max)
                    )
                    if len(mofe_indices[0]) == 0:
                        target_value = (1.0 - d_fractions[i]) * max_discha
                        diff = np.abs(target_value - _discha_vals)
                        closest_index = np.argmin(diff)
                        mofe_indices = (
                            indices[0][closest_index],
                            indices[1][closest_index],
                        )

                    mofe_map[mofe_indices] = j
                    j += 1

            mofe_ids = set(mofe_map[indices])
            if 0 in mofe_ids:
                mofe_ids.remove(0)

            assert len(mofe_ids) == n_ofe, (topaz_id, mofe_ids)

        num_cols, num_rows = mofe_map.shape

        driver = gdal.GetDriverByName("GTiff")
        dst = driver.Create(self.mofe_map, num_cols, num_rows, 1, GDT_Byte)

        srs = osr.SpatialReference()
        srs.ImportFromProj4(proj_s)
        wkt = srs.ExportToWkt()

        dst.SetProjection(wkt)
        dst.SetGeoTransform(transform_s)
        band = dst.GetRasterBand(1)
        band.WriteArray(mofe_map.T)
        del dst  # Writes and closes file

        assert _exists(self.mofe_map)

    @deprecated
    def _taudem_abstract_watershed(self):
        from wepppy.nodb import Wepp

        self.lock()

        # noinspection PyBroadException
        try:
            taudem = TauDEMTopazEmulator(self.taudem_wd, self.dem_fn)
            taudem.abstract_watershed(
                wepp_chn_type=self.wepp_chn_type,
                clip_hillslopes=self.clip_hillslopes,
                clip_hillslope_length=self.clip_hillslope_length,
            )

            self._subs_summary = taudem.abstracted_subcatchments
            self._chns_summary = taudem.abstracted_channels

            ws_stats = taudem.calculate_watershed_statistics()

            self._fps_summary = None
            self._wsarea = ws_stats["wsarea"]
            self._sub_area = sum(
                summary.area for summary in self._subs_summary.values()
            )
            self._chn_area = sum(
                summary.area for summary in self._chns_summary.values()
            )
            self._minz = ws_stats["minz"]
            self._maxz = ws_stats["maxz"]
            self._ruggedness = ws_stats["ruggedness"]
            self._area_gt30 = ws_stats["area_gt30"]
            self._centroid = ws_stats["ws_centroid"]
            self._outlet_top_id = ws_stats["outlet_top_id"]

            taudem.write_slps(out_dir=self.wat_dir)

            self._structure = taudem.structure

            self.dump_and_unlock()

            ron = Ron.getInstance(self.wd)
            if any(
                [
                    "lt" in ron.mods,
                    "portland" in ron.mods,
                    "seattle" in ron.mods,
                    "general" in ron.mods,
                ]
            ):
                wepp = Wepp.getInstance(self.wd)
                wepp.trigger(TriggerEvents.PREPPING_PHOSPHORUS)

            self.trigger(TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE)

        except Exception:
            self.unlock("-f")
            raise

    @deprecated
    def _topaz_abstract_watershed(self):
        self.lock()

        # noinspection PyBroadException
        try:
            wat_dir = self.wat_dir
            assert _exists(wat_dir)

            topaz_wd = self.topaz_wd
            assert _exists(topaz_wd)

            # Create a list of WatershedAbstraction instances
            wat_abs_engines = [
                WatershedAbstraction(topaz_wd, wat_dir) for i in range(NCPU)
            ]
            pool = multiprocessing.Pool(NCPU)

            _abs = wat_abs_engines[0]

            # abstract channels
            chn_ids = wat_abs_engines[0].chn_ids
            args_list = [
                (wat_abs_engines[i % NCPU], chn_id) for i, chn_id in enumerate(chn_ids)
            ]
            results = pool.map(process_channel, args_list)

            # collect results
            chns_summary = {}
            chns_paths = {}
            for chn_id, chn_summary, chn_paths in results:
                chns_summary[chn_id] = chn_summary
                chns_paths[chn_id] = chn_paths

            # sync watershed abstraction instances with the updated channel summaries
            for i in range(NCPU):
                wat_abs_engines[i].watershed["channels"] = chns_summary
                wat_abs_engines[i].watershed["channel_paths"] = chns_paths

            # abstract subcatchments
            max_points = self.max_points
            sub_ids = wat_abs_engines[0].sub_ids
            args_list = [
                (
                    wat_abs_engines[i % NCPU],
                    sub_id,
                    self.clip_hillslopes,
                    self.clip_hillslope_length,
                    max_points,
                )
                for i, sub_id in enumerate(sub_ids)
            ]
            results = pool.map(process_subcatchment, args_list)

            # collect results
            subs_summary = {}
            fps_summary = {}
            for topaz_id, sub_summary, fp_d in results:
                subs_summary[topaz_id] = sub_summary
                fps_summary[topaz_id] = fp_d

            # sync watershed abstraction instances with the updated channel summaries
            for i in range(NCPU):
                _abs.watershed["hillslopes"] = subs_summary
                _abs.watershed["flowpaths"] = fps_summary

            _abs._write_flowpath_slps(self.wat_dir)

            # write slopes
            _abs.abstract_structure()
            _abs._make_channel_slps(self.wat_dir)
            _abs.write_channels_geojson(_join(topaz_wd, "channel_paths.wgs.json"))

            self._subs_summary = subs_summary
            self._chns_summary = chns_summary
            self._fps_summary = fps_summary
            self._wsarea = _abs.totalarea
            self._sub_area = sum(
                summary.area for summary in self._subs_summary.values()
            )
            self._chn_area = sum(
                summary.area for summary in self._chns_summary.values()
            )
            self._centroid = _abs.centroid.lnglat
            self._outlet_top_id = str(_abs.outlet_top_id)
            self._structure = _abs.structure

            del _abs
            pool.close()
            pool.join()

            self.dump_and_unlock()

            ron = Ron.getInstance(self.wd)
            if any(
                [
                    "lt" in ron.mods,
                    "portland" in ron.mods,
                    "seattle" in ron.mods,
                    "general" in ron.mods,
                ]
            ):
                from wepppy.nodb import Wepp

                wepp = Wepp.getInstance(self.wd)
                wepp.trigger(TriggerEvents.PREPPING_PHOSPHORUS)

            self.trigger(TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE)

        except Exception:
            self.unlock("-f")
            raise

    @property
    def report(self):
        return dict(hillslope_n=self.sub_n, channel_n=self.chn_n, totalarea=self.wsarea)

    @property
    def centroid(self) -> Tuple[float, float]:
        return self._centroid

    def sub_summary(self, topaz_id) -> Union[PeridotHillslope, None]:
        if _exists(_join(self.wat_dir, "hillslopes.parquet")):
            from .duckdb_agents import get_watershed_sub_summary

            return PeridotHillslope.from_dict(
                get_watershed_sub_summary(self.wd, topaz_id)
            )

        if _exists(_join(self.wat_dir, "hillslopes.csv")):
            import duckdb

            csv_fn = _join(self.wat_dir, "hillslopes.csv")
            with duckdb.connect() as con:
                result = con.execute(
                    f"SELECT * FROM read_csv('{csv_fn}') WHERE topaz_id = ?", [topaz_id]
                ).fetchall()

                columns = [desc[0] for desc in con.description]
                result = [dict(zip(columns, row)) for row in result]
                return result[0]

        return self._deprecated_sub_summary(topaz_id)

    @deprecated
    def _deprecated_sub_summary(self, topaz_id) -> Union[Dict, None]:
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

    @property
    def fps_summary(self):
        if _exists(_join(self.wat_dir, "flowpaths.parquet")):
            import duckdb

            fps_summary = {}
            with duckdb.connect() as con:
                result = con.execute(
                    f"SELECT topaz_id, fp_id FROM read_parquet('{self.wat_dir}/flowpaths.parquet')"
                ).fetchall()

                for row in result:
                    topaz_id = str(row[0])
                    fp_id = str(row[1])
                    if topaz_id not in fps_summary:
                        fps_summary[topaz_id] = []
                    fps_summary[topaz_id].append(fp_id)
            return fps_summary

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
        if _exists(_join(self.wat_dir, "hillslopes.parquet")):
            from .duckdb_agents import get_watershed_subs_summary

            summaries = get_watershed_subs_summary(self.wd)
            return {
                str(topaz_id): PeridotHillslope.from_dict(d)
                for topaz_id, d in summaries.items()
            }

        return {str(k): v.as_dict() for k, v in self._subs_summary.items()}

    def chn_summary(self, topaz_id) -> Union[Dict, None]:
        if _exists(_join(self.wat_dir, "channels.parquet")):
            from .duckdb_agents import get_watershed_chn_summary

            return PeridotChannel.from_dict(
                get_watershed_chn_summary(self.wd, topaz_id)
            )

        if _exists(_join(self.wat_dir, "channels.csv")):
            import duckdb

            csv_fn = _join(self.wat_dir, "channels.csv")
            with duckdb.connect() as con:
                result = con.execute(
                    f"SELECT * FROM read_csv('{csv_fn}') WHERE topaz_id = ?", [topaz_id]
                ).fetchall()

                columns = [desc[0] for desc in con.description]
                result = [dict(zip(columns, row)) for row in result]
                return result[0]

        return self._deprecated_chn_summary(topaz_id)

    @deprecated
    def _deprecated_chn_summary(self, topaz_id):
        if str(topaz_id) in self._chns_summary:
            d = self._chns_summary[str(topaz_id)]
            if isinstance(d, dict):
                return d
            else:
                return d.as_dict()
        else:
            return None

    @property
    def chns_summary(self) -> Dict[str, PeridotChannel]:
        if _exists(_join(self.wat_dir, "channels.parquet")):
            from .duckdb_agents import get_watershed_chns_summary

            summaries = get_watershed_chns_summary(self.wd)
            return {
                topaz_id: PeridotChannel.from_dict(d)
                for topaz_id, d in summaries.items()
            }

        return {k: v.as_dict() for k, v in self._chns_summary.items()}

    def hillslope_area(self, topaz_id):
        if hasattr(self, "_sub_area_lookup"):
            return self._sub_area_lookup[str(topaz_id)]

        if _exists(_join(self.wat_dir, "hillslopes.parquet")):
            import duckdb

            with duckdb.connect() as con:
                parquet_fn = _join(self.wat_dir, "hillslopes.parquet")
                # lazy load self._sub_area_lookup with duckdb
                result = con.execute(
                    f"SELECT topaz_id, area FROM read_parquet('{parquet_fn}')"
                ).fetchall()
                self._sub_area_lookup = {str(row[0]): row[1] for row in result}
                return self._sub_area_lookup[str(topaz_id)]

        return self._deprecated_area_of(topaz_id)

    def hillslope_slope(self, topaz_id):
        if hasattr(self, "_sub_slope_lookup"):
            return self._sub_slope_lookup[str(topaz_id)]

        if _exists(_join(self.wat_dir, "hillslopes.parquet")):
            import duckdb

            with duckdb.connect() as con:
                parquet_fn = _join(self.wat_dir, "hillslopes.parquet")
                # lazy load self._sub_area_lookup with duckdb
                result = con.execute(
                    f"SELECT topaz_id, slope_scalar FROM read_parquet('{parquet_fn}')"
                ).fetchall()
                self._sub_slope_lookup = {str(row[0]): row[1] for row in result}
                return self._sub_slope_lookup[str(topaz_id)]

        raise Exception('Cannot find slope without hillslope.parquet file')

    def channel_area(self, topaz_id):
        if hasattr(self, "_chn_area_lookup"):
            return self._chn_area_lookup[str(topaz_id)]

        if _exists(_join(self.wat_dir, "channels.parquet")):
            import duckdb

            with duckdb.connect() as con:
                parquet_fn = _join(self.wat_dir, "channels.parquet")
                # lazy load self._sub_area_lookup with duckdb
                result = con.execute(
                    f"SELECT topaz_id, area FROM read_parquet('{parquet_fn}')"
                ).fetchall()
                self._chn_area_lookup = {str(row[0]): row[1] for row in result}
                return self._chn_area_lookup[str(topaz_id)]

        return self._deprecated_area_of(topaz_id)

    @deprecated
    def _deprecated_area_of(self, topaz_id):
        topaz_id = str(topaz_id)
        if topaz_id.endswith("4"):
            return self._chns_summary[topaz_id].area
        else:
            return self._subs_summary[topaz_id].area

    def hillslope_length(self, topaz_id):
        if hasattr(self, "_sub_length_lookup"):
            return self._sub_length_lookup[str(topaz_id)]

        if _exists(_join(self.wat_dir, "hillslopes.parquet")):
            import duckdb

            with duckdb.connect() as con:
                parquet_fn = _join(self.wat_dir, "hillslopes.parquet")
                # lazy load self._sub_area_lookup with duckdb
                result = con.execute(
                    f"SELECT topaz_id, length FROM read_parquet('{parquet_fn}')"
                ).fetchall()
                self._sub_length_lookup = {str(row[0]): row[1] for row in result}
                return self._sub_length_lookup[str(topaz_id)]

        return self._deprecated_length_of(topaz_id)

    def channel_length(self, topaz_id):
        if hasattr(self, "_chn_length_lookup"):
            return self._chn_length_lookup[str(topaz_id)]

        if _exists(_join(self.wat_dir, "channels.parquet")):
            import duckdb

            with duckdb.connect() as con:
                parquet_fn = _join(self.wat_dir, "channels.parquet")
                # lazy load self._chn_area_lookup with duckdb
                result = con.execute(
                    f"SELECT topaz_id, length FROM read_parquet('{parquet_fn}')"
                ).fetchall()
                self._chn_length_lookup = {str(row[0]): row[1] for row in result}
                return self._chn_length_lookup[str(topaz_id)]

        return self._deprecated_length_of(topaz_id)

    @deprecated
    def _deprecated_length_of(self, topaz_id):
        topaz_id = str(topaz_id)
        if topaz_id.endswith("4"):
            return self._chns_summary[topaz_id].length
        else:
            return self._subs_summary[topaz_id].length

    def hillslope_centroid_lnglat(self, topaz_id):
        if hasattr(self, "_sub_centroid_lookup"):
            return self._sub_centroid_lookup[str(topaz_id)]

        if _exists(_join(self.wat_dir, "hillslopes.parquet")):
            import duckdb

            with duckdb.connect() as con:
                parquet_fn = _join(self.wat_dir, "hillslopes.parquet")
                # lazy load self._sub_area_lookup with duckdb
                result = con.execute(
                    f"SELECT topaz_id, centroid_lon, centroid_lat FROM read_parquet('{parquet_fn}')"
                ).fetchall()
                self._sub_centroid_lookup = {
                    str(row[0]): (row[1], row[2]) for row in result
                }
                return self._sub_centroid_lookup[str(topaz_id)]

        wat_ss = self._subs_summary[topaz_id]
        lng, lat = wat_ss.centroid.lnglat
        return lng, lat

    def hillslope_slp_fn(self, topaz_id):
        wat_ss = self.subs_summary[topaz_id]
        if isinstance(wat_ss, HillSummary):  # deprecated
            slp_fn = _join(self.wat_dir, wat_ss.fname)
        elif isinstance(wat_ss, PeridotHillslope):
            slp_fn = _join(self.wat_dir, wat_ss.slp_rel_path)

        return slp_fn

    def centroid_hillslope_iter(self):
        if _exists(_join(self.wat_dir, "hillslopes.parquet")):
            import duckdb

            with duckdb.connect() as con:
                parquet_fn = _join(self.wat_dir, "hillslopes.parquet")
                # lazy load self._sub_area_lookup with duckdb
                result = con.execute(
                    f"SELECT topaz_id, centroid_lon, centroid_lat FROM read_parquet('{parquet_fn}')"
                ).fetchall()
                for topaz_id, lon, lat in result:
                    yield topaz_id, (lon, lat)

        else:
            yield from self._deprecated_centroid_hillslope_iter()

    @deprecated
    def _deprecated_centroid_hillslope_iter(self):
        i = 0
        for topaz_id, wat_ss in self._subs_summary.items():
            yield topaz_id, wat_ss.centroid.lnglat
            i += 1

        assert i == self.sub_n, (i, self.sub_n)


class Outlet(object):
    def __init__(
        self, requested_loc, actual_loc, distance_from_requested, pixel_coords
    ):
        self.requested_loc = requested_loc
        self.actual_loc = actual_loc
        self.distance_from_requested = distance_from_requested
        self.pixel_coords = pixel_coords

    def as_dict(self):
        return dict(lng=self.actual_loc[0], lat=self.actual_loc[1])
