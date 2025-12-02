# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""Watershed abstraction and subcatchment management.

This module provides the Watershed NoDb controller for watershed delineation,
abstraction, and management of subcatchments and channel networks. It integrates
with multiple watershed delineation backends including TOPAZ, Peridot (Rust),
and WhiteboxTools.

Key Components:
    Watershed: NoDb controller for watershed abstraction
    Outlet: Watershed outlet point specification
    DelineationBackend: Enum for watershed delineation method selection
    
Delineation Backends:
    - TOPAZ: Legacy Fortran watershed delineation
    - Peridot: Rust-based watershed abstraction engine
    - WhiteboxTools: Custom TOPAZ implementation in Rust
    
Data Products:
    - Subcatchment polygons (GeoJSON)
    - Channel network topology (GeoJSON)
    - Hillslope parameters (Parquet)
    - Channel parameters (Parquet)
    - WEPP input files (.slp, structure)

Example:
    >>> from wepppy.nodb.core import Watershed, Outlet
    >>> watershed = Watershed.getInstance('/wc1/runs/my-run')
    >>> watershed.outlet = Outlet(lat=46.8, lng=-116.8)
    >>> watershed.abstract_watershed()
    >>> print(f"Subcatchments: {watershed.num_subcatchments}")
    
See Also:
    - wepppy.topo.watershed_abstraction: Watershed abstraction algorithms
    - wepppy.topo.peridot: Rust watershed engine
    - wepppy.topo.wbt: WhiteboxTools integration
    - wepppy.nodb.core.topaz: TOPAZ controller (legacy)

Note:
    Watershed abstraction is a prerequisite for WEPP simulation.
    All subcatchments are assigned unique topaz_id and wepp_id values.
    
Warning:
    Watershed outlet must not touch DEM boundary edges. Use
    WatershedBoundaryTouchesEdgeError handling for validation.
"""

from typing import Generator, Dict, Union, Tuple, Optional, List, Any

import time
import os
import inspect
import math

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
from wepppy.topo.peridot.peridot_runner import (
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

from wepppy.topo.watershed_collection import WatershedFeature
from wepppy.topo.watershed_abstraction import SlopeFile
from wepppy.topo.watershed_abstraction.support import HillSummary, ChannelSummary, identify_edge_hillslopes
from wepppy.topo.watershed_abstraction.slope_file import mofe_distance_fractions
from wepppy.topo.wbt import WhiteboxToolsTopazEmulator
from wepppy.all_your_base.geo import read_raster, haversine
from wepppy.nodb.duckdb_agents import get_watershed_chns_summary

from wepppy.nodb.base import NoDbBase, TriggerEvents, nodb_setter
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.query_engine import update_catalog_entry

from wepppy.nodb.duckdb_agents import (
    get_watershed_subs_summary,
    get_watershed_sub_summary,
    get_watershed_chn_summary
)

from .topaz import Topaz

from wepppy.all_your_base import NCPU

NCPU = multiprocessing.cpu_count() - 2

# Debris-flow routines need the portion of the basin with slopes steeper than 30%.
# `hillslopes.parquet` stores slope as a rise/run ratio, so 30% equals 0.30.
_SLOPE_RATIO_THRESHOLD = 0.30

__all__ = [
    'NCPU',
    'DelineationBackend',
    'WatershedNotAbstractedError',
    'WatershedNoDbLockedException',
    'process_channel',
    'process_subcatchment',
    'TRANSIENT_FIELDS',
    'Watershed',
    'Outlet',
]
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
def process_channel(args: Tuple[WatershedAbstraction, int]) -> Tuple[int, ChannelSummary, Any]:
    wat_abs, chn_id = args
    chn_summary, chn_paths = wat_abs.abstract_channel(chn_id)
    return chn_id, chn_summary, chn_paths


@deprecated
def process_subcatchment(args: Tuple[WatershedAbstraction, int, bool, float, int]) -> Tuple[int, HillSummary, Dict[str, Any]]:
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

    filename = 'watershed.nodb'
    
    def __init__(self, wd: str, cfg_fn: str, run_group: Optional[str] = None, group_name: Optional[str] = None) -> None:
        super(Watershed, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            self._subs_summary: Optional[Dict[str, Any]] = None  # deprecated watershed/hillslopes.csv
            self._fps_summary: Optional[Dict[str, Any]] = None  # deprecated watershed/flowpaths.csv
            self._structure: Optional[str] = None
            self._chns_summary: Optional[Dict[str, Any]] = None  # deprecated watershed/channels.csv
            self._wsarea: Optional[float] = None
            self._impoundment_n: int = 0
            self._centroid: Optional[Tuple[float, float]] = None
            self._outlet_top_id: Optional[str] = None
            self._outlet: Optional['Outlet'] = None
            self._set_extent_mode: int = 0
            self._map_bounds_text: str = ""

            self._wepp_chn_type: str = self.config_get_str("soils", "wepp_chn_type")

            self._clip_hillslope_length: float = self.config_get_float(
                "watershed", "clip_hillslope_length"
            )
            self._clip_hillslopes: bool = self.config_get_bool("watershed", "clip_hillslopes")
            self._bieger2015_widths: bool = self.config_get_bool(
                "watershed", "bieger2015_widths"
            )
            self._walk_flowpaths: bool = self.config_get_bool("watershed", "walk_flowpaths")
            self._max_points: Optional[int] = self.config_get_int("watershed", "max_points", None)

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
                self._csa = self.config_get_float("watershed.wbt", "csa", 5)
                self._mcl = self.config_get_float("watershed.wbt", "mcl", 60)
                self._wbt_fill_or_breach = self.config_get_str(
                    "watershed.wbt", "fill_or_breach", "breach_least_cost"
                )
                self._wbt_blc_dist = self.config_get_int(
                    "watershed.wbt", "blc_dist", 1000
                )
                self._wbt: Optional[WhiteboxToolsTopazEmulator] = None

            else:
                self._delineation_backend = DelineationBackend.TOPAZ

            self._abstraction_backend: str = self.config_get_str(
                "watershed", "abstraction_backend", "peridot"
            )

            wat_dir = self.wat_dir
            if not _exists(wat_dir):
                os.mkdir(wat_dir)

            self._mofe_nsegments: Optional[Dict[str, int]] = None
            self._mofe_target_length: float = self.config_get_float(
                "watershed", "mofe_target_length"
            )
            self._mofe_buffer: bool = self.config_get_bool("watershed", "mofe_buffer")
            self._mofe_buffer_length: float = self.config_get_float(
                "watershed", "mofe_buffer_length"
            )
            self._mofe_max_ofes: int = self.config_get_int("watershed", "mofe_max_ofes", 19)

    @property
    def set_extent_mode(self) -> int:
        if not hasattr(self, "_set_extent_mode"):
            return 0
        return self._set_extent_mode
    
    @set_extent_mode.setter
    @nodb_setter
    def set_extent_mode(self, value: int) -> None:
        _value = int(value)
        assert _value in [0, 1], f"Invalid set_extent_mode value: {_value}"
        self._set_extent_mode = _value

    @property
    def map_bounds_text(self) -> str:
        if not hasattr(self, "_map_bounds_text"):
            return ""
        return self._map_bounds_text
    
    @map_bounds_text.setter
    @nodb_setter
    def map_bounds_text(self, value: str) -> None:
        _value = str(value)
        self._map_bounds_text = _value

    @classmethod
    def _decode_jsonpickle(cls, json_text: str) -> 'Watershed':
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
    def _decode_watershed_safe(s: str) -> 'Watershed':
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
    def delineation_backend(self) -> DelineationBackend:
        delineation_backend = getattr(self, "_delineation_backend", None)
        if delineation_backend is None:
            return DelineationBackend.TOPAZ
        return delineation_backend

    @property
    def delineation_backend_is_topaz(self) -> bool:
        delineation_backend = getattr(self, "_delineation_backend", None)
        if delineation_backend is None:
            return True
        return delineation_backend == DelineationBackend.TOPAZ

    @property
    def wbt_fill_or_breach(self) -> str:
        return getattr(self, "_wbt_fill_or_breach", "fill")

    @wbt_fill_or_breach.setter
    @nodb_setter
    def wbt_fill_or_breach(self, value: str) -> None:
        assert value in [
            "fill",
            "breach",
            "breach_least_cost",
        ], f"Invalid wbt_fill_or_breach value: {value}"
        self._wbt_fill_or_breach = value

    @property
    def wbt_blc_dist(self) -> int:
        return getattr(self, "_wbt_blc_dist", 1000)

    @wbt_blc_dist.setter
    @nodb_setter
    def wbt_blc_dist(self, value: int) -> None:
        self._wbt_blc_dist = value

    @property
    def max_points(self) -> int:
        pts = getattr(self, "_max_points", None)
        if pts is None:
            return 99
        return pts

    @property
    def abstraction_backend(self) -> str:
        return getattr(self, "_abstraction_backend", "topaz")

    @property
    def abstraction_backend_is_peridot(self) -> bool:
        return self.abstraction_backend == "peridot"

    @property
    def clip_hillslopes(self) -> bool:
        return getattr(self, "_clip_hillslopes", False) and not self.multi_ofe

    @clip_hillslopes.setter
    @nodb_setter
    def clip_hillslopes(self, value: bool) -> None:
        self._clip_hillslopes = value

    @property
    def clip_hillslope_length(self) -> float:
        return getattr(self, "_clip_hillslope_length", 300.0)

    @clip_hillslope_length.setter
    @nodb_setter
    def clip_hillslope_length(self, value: float) -> None:
        self._clip_hillslope_length = value

    @property
    def bieger2015_widths(self) -> bool:
        return getattr(self, "_bieger2015_widths", False)

    @bieger2015_widths.setter
    @nodb_setter
    def bieger2015_widths(self, value: bool) -> None:
        self._bieger2015_widths = value

    @property
    def walk_flowpaths(self) -> bool:
        return getattr(self, "_walk_flowpaths", True)

    @walk_flowpaths.setter
    @nodb_setter
    def walk_flowpaths(self, value: bool) -> None:
        self._walk_flowpaths = value

    @property
    def delineation_backend_is_taudem(self) -> bool:
        delineation_backend = getattr(self, "_delineation_backend", None)
        if delineation_backend is None:
            return False
        return delineation_backend == DelineationBackend.TauDEM

    @property
    def delineation_backend_is_wbt(self) -> bool:
        delineation_backend = getattr(self, "_delineation_backend", None)
        if delineation_backend is None:
            return False
        return delineation_backend == DelineationBackend.WBT

    def _ensure_wbt(self) -> WhiteboxToolsTopazEmulator:
        if not self.delineation_backend_is_wbt:
            raise RuntimeError("WhiteboxTools emulator requested for non-WBT backend")
        wbt = getattr(self, "_wbt", None)
        if wbt is None:
            wbt = WhiteboxToolsTopazEmulator(
                self.wbt_wd,
                self.dem_fn,
                logger=self.logger,
            )
            self._wbt = wbt
        return wbt

    @property
    def is_abstracted(self) -> bool:
        return self._subs_summary is not None and self._chns_summary is not None

    @property
    def wepp_chn_type(self) -> str:
        return getattr(
            self, "_wepp_chn_type", self.config_get_str("soils", "wepp_chn_type")
        )

    @property
    def subwta(self) -> str:
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "SUBWTA.ARC")
        elif self.delineation_backend_is_wbt:
            return _join(self.wbt_wd, "subwta.tif")
        else:
            return _join(self.taudem_wd, "subwta.tif")

    @property
    def discha(self) -> Optional[str]:
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "DISCHA.ARC")
        elif self.delineation_backend_is_wbt:
            return _join(self.wbt_wd, "discha.tif")
        else:
            raise NotImplementedError("taudem distance to channel map not specified")

    @property
    def subwta_shp(self) -> Optional[str]:
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "SUBCATCHMENTS.WGS.JSON")
        elif self.delineation_backend_is_wbt:
            return _join(self.wbt_wd, "subcatchments.WGS.geojson")
        else:
            return _join(self.taudem_wd, "subcatchments.WGS.geojson")

    @property
    def subwta_utm_shp(self) -> Optional[str]:
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "SUBCATCHMENTS.JSON")
        elif self.delineation_backend_is_wbt:
            return _join(self.wbt_wd, "subcatchments.geojson")
        else:
            return _join(self.taudem_wd, "subcatchments.geojson")

    @property
    def bound(self) -> Optional[str]:
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "BOUND.ARC")
        elif self.delineation_backend_is_wbt:
            return _join(self.wbt_wd, "bound.tif")
        else:
            return _join(self.taudem_wd, "bound.tif")

    @property
    def bound_shp(self) -> Optional[str]:
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "BOUND.WGS.JSON")
        elif self.delineation_backend_is_wbt:
            return _join(self.wbt_wd, "bound.WGS.geojson")
        else:
            return _join(self.taudem_wd, "bound.WGS.geojson")

    @property
    def bound_utm_shp(self) -> str:
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "BOUND.JSON")
        else:
            return _join(self.taudem_wd, "bound.geojson")

    @property
    def netful(self) -> Optional[str]:
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "NETFUL.ARC")
        elif self.delineation_backend_is_wbt:
            return _join(self.wbt_wd, "netful.tif")
        else:
            return _join(self.taudem_wd, "src.tif")

    @property
    def netful_shp(self) -> Optional[str]:
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "NETFUL.WGS.JSON")
        elif self.delineation_backend_is_wbt:
            return _join(self.wbt_wd, "netful.WGS.geojson")
        else:
            return _join(self.taudem_wd, "netful.WGS.geojson")

    @property
    def netful_utm_shp(self) -> Optional[str]:
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "NETFUL.JSON")
        elif self.delineation_backend_is_wbt:
            return _join(self.wbt_wd, "netful.geojson")
        else:
            return _join(self.taudem_wd, "netful.geojson")

    @property
    def channels_shp(self) -> Optional[str]:
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "CHANNELS.WGS.JSON")
        elif self.delineation_backend_is_wbt:
            return _join(self.wbt_wd, "channels.WGS.geojson")
        else:
            return _join(self.taudem_wd, "net.WGS.geojson")

    @property
    def channels_utm_shp(self) -> Optional[str]:
        if self.delineation_backend_is_topaz:
            return _join(self.topaz_wd, "CHANNELS.JSON")
        elif self.delineation_backend_is_wbt:
            return _join(self.wbt_wd, "channels.geojson")
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
    def area_gt30(self) -> Optional[float]:
        if self.delineation_backend_is_topaz:
            return Topaz.getInstance(self.wd).area_gt30
        cached = getattr(self, "_area_gt30", None)
        if cached is not None:
            return cached

        computed = self._compute_area_gt30_from_hillslopes()
        self._area_gt30 = computed
        return computed

    @property
    def ruggedness(self) -> Optional[float]:
        if self.delineation_backend_is_topaz:
            return Topaz.getInstance(self.wd).ruggedness
        cached = getattr(self, "_ruggedness", None)
        if cached is not None:
            return cached

        computed = self._compute_ruggedness_from_dem()
        self._ruggedness = computed
        return computed

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
    def structure(self) -> Any:
        structure_path = self._structure
        if structure_path is not None and _exists(_join(self.wat_dir, "structure.pkl")):
            import pickle

            with open(structure_path, "rb") as fp:
                return pickle.load(fp)

        return self._structure

    @property
    def csa(self) -> Optional[float]:
        csa = getattr(self, "_csa", None)
        if csa is None and self.delineation_backend_is_topaz:
            csa = Topaz.getInstance(self.wd).csa

        return csa

    @property
    def mcl(self) -> Optional[float]:
        mcl = getattr(self, "_mcl", None)
        if self.delineation_backend_is_topaz:

            if mcl is None:
                mcl = Topaz.getInstance(self.wd).mcl
            return mcl

        return mcl

    @property
    def outlet(self) -> Optional['Outlet']:
        if hasattr(self, "_outlet"):
            return self._outlet

        return Topaz.getInstance(self.wd).outlet

    @outlet.setter
    @nodb_setter
    def outlet(self, value: Optional['Outlet']) -> None:
        assert isinstance(value, Outlet) or value is None
        self._outlet = value

    @property
    def has_outlet(self) -> bool:
        return self.outlet is not None

    @property
    def has_channels(self) -> bool:
        netful_path = self.netful
        if netful_path is None:
            return False
        return _exists(netful_path)

    @property
    def has_subcatchments(self) -> bool:
        return _exists(self.subwta)

    @property
    def outlet_top_id(self) -> Optional[str]:
        return self._outlet_top_id

    @property
    def relief(self) -> Optional[str]:
        if self.delineation_backend_is_topaz:
            relief_path = _join(self.topaz_wd, "RELIEF.ARC")
        elif self.delineation_backend_is_wbt:
            relief_path = _join(self.wbt_wd, "relief.tif")
        else:
            return None

        return relief_path if _exists(relief_path) else None

    def translator_factory(self) -> WeppTopTranslator:
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
    def build_channels(self, csa: Optional[float] = None, mcl: Optional[float] = None) -> None:
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(f'{self.class_name}.{func_name}(csa={csa}, mcl={mcl})')

        assert not self.islocked()

        self.logger.info("Building Channels")

        if csa or mcl:
            with self.locked():
                if csa is not None:
                    self._csa = csa

                if mcl is not None:
                    self._mcl = mcl

        # Preserve outlet information during channel building
        preserved_outlet = self.outlet
        if preserved_outlet is not None:
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
            self._wbt = wbt

      
        if _exists(self.subwta):
            self.logger.info(f' Removing subcatchment: {self.subwta}')
            os.remove(self.subwta)

        prep = RedisPrep.getInstance(self.wd)
        prep.timestamp(TaskEnum.build_channels)

    @property
    def target_watershed_path(self) -> str:
        return _join(self.wd, 'dem', "target_watershed.tif")

    def find_outlet(self, watershed_feature: WatershedFeature) -> None:
        assert self.delineation_backend_is_wbt, "find_outlet only works with WBT delineation backend"
        
        wbt = self._ensure_wbt()

        # build raster mask from watershed feature
        watershed_feature.build_raster_mask(
            template_filepath=self.dem_fn, dst_filepath=self.target_watershed_path)
    
        wbt._wbt_runner.find_outlet(
            d8_pntr=wbt.flovec,
            streams=wbt.netful,
            watershed=self.target_watershed_path,
            output=wbt.outlet_geojson
        )

        outlet = wbt.set_outlet_from_geojson(logger=self.logger)
        self.outlet = outlet

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.find_outlet)
        except FileNotFoundError:
            pass

    #
    # set outlet
    #
    def set_outlet(self, lng: Optional[float] = None, lat: Optional[float] = None, da: float = 0.0) -> None:
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(f'{self.class_name}.{func_name}(lng={lng}, lat={lat}, da={da})')
        
        assert not self.islocked()
        self.logger.info("Setting Outlet")

        if lng is None or lat is None:
            raise ValueError("lng and lat must be provided")
        
        assert float(lng), lng
        assert float(lat), lat

        if self.delineation_backend_is_topaz:
            self.logger.info(f' delineation_backend_is_topaz')
            topaz = Topaz.getInstance(self.wd)
            topaz.set_outlet(lng=lng, lat=lat, da=da)
            _outlet = topaz.outlet
            if _outlet is None:
                raise ValueError("Failed to set outlet in Topaz")
            self.outlet = _outlet
        elif self.delineation_backend_is_wbt:
            self.logger.info(f' delineation_backend_is_wbt')
            wbt = self._ensure_wbt()
            _outlet = wbt.set_outlet(lng=lng, lat=lat, logger=self.logger)
            if _outlet is None:
                raise ValueError("Failed to set outlet in WBT")

            with self.locked():
                self._outlet = _outlet
                self._wbt = wbt
        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.set_outlet)
        except FileNotFoundError:
            pass

    def remove_outlet(self) -> None:
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(f'{self.class_name}.{func_name}()')

        self.outlet = None

    #
    # build subcatchments
    #
    def build_subcatchments(self, pkcsa: Optional[str] = None) -> None:
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(f'{self.class_name}.{func_name}(pkcsa={pkcsa})')

        assert not self.islocked()

        if self.delineation_backend_is_topaz:
            self.logger.info(f' delineation_backend_is_topaz')
            Topaz.getInstance(self.wd).build_subcatchments()
        elif self.delineation_backend_is_wbt:
            self.logger.info(f' delineation_backend_is_wbt')
            wbt = self._ensure_wbt()
            wbt.delineate_subcatchments(self.logger)
            self.identify_edge_hillslopes()
        else:
            self.logger.info(f' delineation_backend_is_taudem')
            with self.locked():
                if pkcsa is not None:
                    self._pkcsa = pkcsa
            self._taudem_build_subcatchments()

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.build_subcatchments)
        except FileNotFoundError:
            pass

    def identify_edge_hillslopes(self) -> None:
        """
        Identify edge hillslopes in the watershed.
        This is used to determine which hillslopes are at the edge of the watershed.
        """
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(f'{self.class_name}.{func_name}()')

        if self.readonly:
            self._edge_hillslopes = identify_edge_hillslopes(self.subwta, self.logger)
            return
            
        with self.locked():
            self._edge_hillslopes = identify_edge_hillslopes(self.subwta, self.logger)


    @property
    def edge_hillslopes(self) -> List[int]:
        """
        Get the edge hillslopes in the watershed.
        """
        if not hasattr(self, "_edge_hillslopes"):
            self.identify_edge_hillslopes()
        return self._edge_hillslopes

    @property
    def pkcsa(self) -> Optional[str]:
        return getattr(self, "_pkcsa", None)

    @property
    def network(self) -> Any:
        if self.abstraction_backend_is_peridot:
            network = read_network(_join(self.wat_dir, "network.txt"))
            return network
        else:
            raise NotImplementedError("network not implemented")

    #
    # abstract watershed
    #

    def abstract_watershed(self) -> None:
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

    def _peridot_post_abstract_watershed(self) -> None:
        self.logger.info("_peridot_post_abstract_watershed")

        with self.locked():
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

            try:
                update_catalog_entry(self.wd, 'watershed')
            except Exception as exc:
                self.logger.warning("Failed to refresh catalog for watershed outputs: %s", exc)

    @property
    def sub_area(self) -> float:
        sub_area = getattr(self, "_sub_area", None)

        if sub_area is None and self._subs_summary is not None:
            sub_area = sum(summary.area for summary in self._subs_summary.values())

        return sub_area if sub_area is not None else 0.0

    @property
    def chn_area(self) -> float:
        chn_area = getattr(self, "_chn_area", None)

        if chn_area is None and self._chns_summary is not None:
            chn_area = sum(summary.area for summary in self._chns_summary.values())

        return chn_area if chn_area is not None else 0.0

    @property
    def mofe_nsegments(self) -> Optional[Dict[str, int]]:
        return getattr(self, "_mofe_nsegments", None)

    @property
    def mofe_target_length(self) -> float:
        return getattr(self, "_mofe_target_length", 50)

    @mofe_target_length.setter
    @nodb_setter
    def mofe_target_length(self, value: float) -> None:
        self._mofe_target_length = value

    @property
    def mofe_buffer(self) -> bool:
        return getattr(self, "_mofe_buffer", False)

    @mofe_buffer.setter
    @nodb_setter
    def mofe_buffer(self, value: bool) -> None:
        self._mofe_buffer = bool(value)

    @property
    def mofe_max_ofes(self) -> int:
        return getattr(self, "_mofe_max_ofes", 19)

    @mofe_max_ofes.setter
    @nodb_setter
    def mofe_max_ofes(self, value: int) -> None:
        self._mofe_max_ofes = value

    @property
    def mofe_buffer_length(self) -> float:
        return getattr(self, "_mofe_buffer_length", 15)

    @mofe_buffer_length.setter
    @nodb_setter
    def mofe_buffer_length(self, value: float) -> None:
        self._mofe_buffer_length = value

    def _build_multiple_ofe(self) -> None:
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(f'{self.class_name}.{func_name}()')
        _mofe_nsegments: Dict[str, int] = {}
        for topaz_id, wat_ss in self.subs_summary.items():
            not_top = not str(topaz_id).endswith("1")

            if isinstance(wat_ss, HillSummary):
                slp_fn = _join(self.wat_dir, wat_ss.fname)
            elif isinstance(wat_ss, PeridotHillslope):
                slp_fn = _join(self.wat_dir, wat_ss.slp_rel_path)
            else:
                # Handle dict case
                slp_fn = _join(self.wat_dir, wat_ss.get('slp_rel_path', wat_ss.get('fname', '')))

            slp = SlopeFile(slp_fn)
            _mofe_nsegments[topaz_id] = slp.segmented_multiple_ofe(
                target_length=self.mofe_target_length,
                apply_buffer=self.mofe_buffer and not_top,
                buffer_length=self.mofe_buffer_length,
                max_ofes=self.mofe_max_ofes,
            )

        with self.locked():
            self._mofe_nsegments = _mofe_nsegments

        self._build_mofe_map()

    @property
    def mofe_map(self) -> str:
        return _join(self.wat_dir, "mofe.tif")

    def _build_mofe_map(self) -> None:
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(f'{self.class_name}.{func_name}()')
        subwta, transform_s, proj_s = read_raster(self.subwta, dtype=np.int32)
        discha_path = self.discha
        if discha_path is None:
            raise ValueError("discha path is None")
        discha, transform_d, proj_d = read_raster(discha_path, dtype=np.int32)
        mofe_nsegments = self.mofe_nsegments

        mofe_map = np.zeros(subwta.shape, np.int32)
        for topaz_id, wat_ss in self.subs_summary.items():
            indices = np.where(subwta == int(topaz_id))
            _discha_vals = discha[indices]
            max_discha = np.max(_discha_vals)

            if isinstance(wat_ss, HillSummary):
                slp_fn = _join(self.wat_dir, wat_ss.fname)
            elif isinstance(wat_ss, PeridotHillslope):
                slp_fn = _join(self.wat_dir, wat_ss.slp_rel_path)
            else:
                # Handle dict case
                slp_fn = _join(self.wat_dir, wat_ss.get('slp_rel_path', wat_ss.get('fname', '')))

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
        dst = driver.Create(self.mofe_map, num_cols, num_rows, 1, GDT_Byte)  # type: ignore[name-defined]

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
    def _topaz_abstract_watershed(self):
        with self.locked():
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

        ron = self.ron_instance
        if any(
            [
                "lt" in ron.mods,
                "portland" in ron.mods,
                "seattle" in ron.mods,
                "general" in ron.mods,
            ]
        ):
            from wepppy.nodb.core import Wepp

            wepp = Wepp.getInstance(self.wd)
            wepp.trigger(TriggerEvents.PREPPING_PHOSPHORUS)

        self.trigger(TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE)

    @property
    def report(self) -> Dict[str, Union[int, float]]:
        return dict(hillslope_n=self.sub_n, channel_n=self.chn_n, totalarea=self.wsarea)

    @property
    def centroid(self) -> Optional[Tuple[float, float]]:
        return self._centroid

    def sub_summary(self, topaz_id: Union[str, int]) -> Union[PeridotHillslope, Dict[str, Any], None]:
        if _exists(_join(self.wat_dir, "hillslopes.parquet")):
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
    def _deprecated_sub_summary(self, topaz_id: Union[str, int]) -> Union[Dict[str, Any], None]:
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
    def fps_summary(self) -> Optional[Dict[str, List[str]]]:
        if _exists(_join(self.wat_dir, "flowpaths.parquet")):
            import duckdb

            fps_summary: Dict[str, List[str]] = {}
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
        return None

    # gotcha: using __getitem__ breaks jinja's attribute lookup, so...
    def _(self, wepp_id: int) -> Union[HillSummary, ChannelSummary]:
        translator = self.translator_factory()
        topaz_id = str(translator.top(wepp=int(wepp_id)))

        if self._subs_summary is not None and topaz_id in self._subs_summary:
            return self._subs_summary[topaz_id]
        elif self._chns_summary is not None and topaz_id in self._chns_summary:
            return self._chns_summary[topaz_id]

        raise IndexError

    @property
    def subs_summary(self) -> Dict[str, Union[PeridotHillslope, Dict[str, Any]]]:
        if _exists(_join(self.wat_dir, "hillslopes.parquet")):

            summaries = get_watershed_subs_summary(self.wd)
            return {
                str(topaz_id): PeridotHillslope.from_dict(d)
                for topaz_id, d in summaries.items()
            }

        if self._subs_summary is None:
            return {}
        return {str(k): v.as_dict() for k, v in self._subs_summary.items()}

    def chn_summary(self, topaz_id: Union[str, int]) -> Union[PeridotChannel, Dict[str, Any], None]:
        if _exists(_join(self.wat_dir, "channels.parquet")):
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
    def _deprecated_chn_summary(self, topaz_id: Union[str, int]) -> Union[Dict[str, Any], None]:
        if self._chns_summary is None:
            return None
        if str(topaz_id) in self._chns_summary:
            d = self._chns_summary[str(topaz_id)]
            if isinstance(d, dict):
                return d
            else:
                return d.as_dict()
        else:
            return None

    @property
    def chns_summary(self) -> Dict[str, Union[PeridotChannel, Dict[str, Any]]]:
        if _exists(_join(self.wat_dir, "channels.parquet")):

            summaries = get_watershed_chns_summary(self.wd)
            return {
                topaz_id: PeridotChannel.from_dict(d)
                for topaz_id, d in summaries.items()
            }

        if self._chns_summary is None:
            return {}
        return {k: v.as_dict() for k, v in self._chns_summary.items()}

    def hillslope_area(self, topaz_id: Union[str, int]) -> float:
        if hasattr(self, "_sub_area_lookup"):
            sub_area_lookup: Dict[str, float] = self._sub_area_lookup  # type: ignore[has-type]
            return sub_area_lookup[str(topaz_id)]

        if _exists(_join(self.wat_dir, "hillslopes.parquet")):
            import duckdb

            with duckdb.connect() as con:
                parquet_fn = _join(self.wat_dir, "hillslopes.parquet")
                # lazy load self._sub_area_lookup with duckdb
                result = con.execute(
                    f"SELECT topaz_id, area FROM read_parquet('{parquet_fn}')"
                ).fetchall()
                self._sub_area_lookup: Dict[str, float] = {str(row[0]): row[1] for row in result}  # type: ignore[misc]
                return self._sub_area_lookup[str(topaz_id)]

        return self._deprecated_area_of(topaz_id)

    def hillslope_slope(self, topaz_id: Union[str, int]) -> float:
        if hasattr(self, "_sub_slope_lookup"):
            sub_slope_lookup: Dict[str, float] = self._sub_slope_lookup  # type: ignore[has-type]
            return sub_slope_lookup[str(topaz_id)]

        if _exists(_join(self.wat_dir, "hillslopes.parquet")):
            import duckdb

            with duckdb.connect() as con:
                parquet_fn = _join(self.wat_dir, "hillslopes.parquet")
                # lazy load self._sub_area_lookup with duckdb
                result = con.execute(
                    f"SELECT topaz_id, slope_scalar FROM read_parquet('{parquet_fn}')"
                ).fetchall()
                self._sub_slope_lookup: Dict[str, float] = {str(row[0]): row[1] for row in result}  # type: ignore[misc]
                return self._sub_slope_lookup[str(topaz_id)]

        raise Exception('Cannot find slope without hillslope.parquet file')

    def channel_area(self, topaz_id: Union[str, int]) -> float:
        if hasattr(self, "_chn_area_lookup"):
            chn_area_lookup: Dict[str, float] = self._chn_area_lookup  # type: ignore[has-type]
            return chn_area_lookup[str(topaz_id)]

        if _exists(_join(self.wat_dir, "channels.parquet")):
            import duckdb

            with duckdb.connect() as con:
                parquet_fn = _join(self.wat_dir, "channels.parquet")
                # lazy load self._sub_area_lookup with duckdb
                result = con.execute(
                    f"SELECT topaz_id, area FROM read_parquet('{parquet_fn}')"
                ).fetchall()
                self._chn_area_lookup: Dict[str, float] = {str(row[0]): row[1] for row in result}  # type: ignore[misc]
                return self._chn_area_lookup[str(topaz_id)]

        return self._deprecated_area_of(topaz_id)

    @deprecated
    def _deprecated_area_of(self, topaz_id: Union[str, int]) -> float:
        topaz_id_str = str(topaz_id)
        if self._chns_summary is None or self._subs_summary is None:
            raise ValueError("Summary data is None")
        if topaz_id_str.endswith("4"):
            return self._chns_summary[topaz_id_str].area
        else:
            return self._subs_summary[topaz_id_str].area

    def hillslope_length(self, topaz_id: Union[str, int]) -> float:
        if hasattr(self, "_sub_length_lookup"):
            sub_length_lookup: Dict[str, float] = self._sub_length_lookup  # type: ignore[has-type]
            return sub_length_lookup[str(topaz_id)]

        if _exists(_join(self.wat_dir, "hillslopes.parquet")):
            import duckdb

            with duckdb.connect() as con:
                parquet_fn = _join(self.wat_dir, "hillslopes.parquet")
                # lazy load self._sub_area_lookup with duckdb
                result = con.execute(
                    f"SELECT topaz_id, length FROM read_parquet('{parquet_fn}')"
                ).fetchall()
                self._sub_length_lookup: Dict[str, float] = {str(row[0]): row[1] for row in result}  # type: ignore[misc]
                return self._sub_length_lookup[str(topaz_id)]

        return self._deprecated_length_of(topaz_id)

    def _compute_area_gt30_from_hillslopes(self) -> float:
        """Determine basin area with slopes ≥30% using hillslopes parquet data."""
        parquet_fn = _join(self.wat_dir, "hillslopes.parquet")
        if not _exists(parquet_fn):
            raise FileNotFoundError(
                f"hillslopes.parquet not found at {parquet_fn}; cannot compute area_gt30"
            )

        import duckdb

        query = (
            f"SELECT COALESCE(SUM(area), 0.0) "
            f"FROM read_parquet('{parquet_fn}') "
            f"WHERE slope_scalar >= {_SLOPE_RATIO_THRESHOLD}"
        )

        try:
            with duckdb.connect() as con:
                result = con.execute(query).fetchone()
        except duckdb.duckdb.IOException:
            time.sleep(4)
            with duckdb.connect() as con:
                result = con.execute(query).fetchone()

        area = result[0] if result else 0.0
        return float(area or 0.0)

    def _compute_ruggedness_from_dem(self) -> float:
        """Approximate ruggedness using DEM statistics when TOPAZ values are absent."""
        dem_path = _join(self.wd, "dem", "dem.tif")
        if not _exists(dem_path):
            raise FileNotFoundError(f"dem.tif not found at {dem_path}; cannot compute ruggedness")

        dataset = gdal.Open(dem_path, GA_ReadOnly)
        if dataset is None:
            raise RuntimeError(f"Unable to open DEM at {dem_path}")

        try:
            band = dataset.GetRasterBand(1)
            if band is None:
                raise RuntimeError("DEM is missing band 1; cannot compute ruggedness")

            stats = band.GetStatistics(False, True)
            if not stats or stats[0] is None or stats[1] is None:
                raise RuntimeError("Failed to compute DEM statistics for ruggedness")

            min_z, max_z = float(stats[0]), float(stats[1])

            geotransform = dataset.GetGeoTransform()
            if geotransform is None:
                raise RuntimeError("DEM lacks geotransform; cannot derive pixel area")

            pixel_width = float(geotransform[1])
            pixel_height = float(geotransform[5])
            if pixel_width == 0.0 or pixel_height == 0.0:
                raise RuntimeError("DEM pixel size is zero; cannot compute area")

            pixel_area = abs(pixel_width * pixel_height)
            raster_area = pixel_area * dataset.RasterXSize * dataset.RasterYSize
            if raster_area <= 0.0:
                raise RuntimeError("Computed DEM area is non-positive; cannot compute ruggedness")

            return float((max_z - min_z) / math.sqrt(raster_area))
        finally:
            dataset = None

    def channel_length(self, topaz_id: Union[str, int]) -> float:
        if hasattr(self, "_chn_length_lookup"):
            chn_length_lookup: Dict[str, float] = self._chn_length_lookup  # type: ignore[has-type]
            return chn_length_lookup[str(topaz_id)]

        if _exists(_join(self.wat_dir, "channels.parquet")):
            import duckdb

            with duckdb.connect() as con:
                parquet_fn = _join(self.wat_dir, "channels.parquet")
                # lazy load self._chn_area_lookup with duckdb
                result = con.execute(
                    f"SELECT topaz_id, length FROM read_parquet('{parquet_fn}')"
                ).fetchall()
                self._chn_length_lookup: Dict[str, float] = {str(row[0]): row[1] for row in result}  # type: ignore[misc]
                return self._chn_length_lookup[str(topaz_id)]

        return self._deprecated_length_of(topaz_id)

    def hillslope_width(self, topaz_id: Union[str, int]) -> float:
        topaz_id_str = str(topaz_id)
        if hasattr(self, "_sub_width_lookup"):
            sub_width_lookup: Dict[str, float] = self._sub_width_lookup  # type: ignore[has-type]
            if topaz_id_str in sub_width_lookup:
                return sub_width_lookup[topaz_id_str]

        parquet_fn = _join(self.wat_dir, "hillslopes.parquet")
        if _exists(parquet_fn):
            import duckdb

            with duckdb.connect() as con:
                result = con.execute(
                    f"SELECT topaz_id, width FROM read_parquet('{parquet_fn}')"
                ).fetchall()
            self._sub_width_lookup = {str(row[0]): float(row[1]) for row in result}  # type: ignore[misc]
            if topaz_id_str in self._sub_width_lookup:  # type: ignore[attr-defined]
                return self._sub_width_lookup[topaz_id_str]  # type: ignore[index]
            return self._deprecated_width_of(topaz_id_str)

        csv_fn = _join(self.wat_dir, "hillslopes.csv")
        if _exists(csv_fn):
            import duckdb

            with duckdb.connect() as con:
                result = con.execute(
                    f"SELECT topaz_id, width FROM read_csv('{csv_fn}')"
                ).fetchall()
            self._sub_width_lookup = {str(row[0]): float(row[1]) for row in result}  # type: ignore[misc]
            if topaz_id_str in self._sub_width_lookup:  # type: ignore[attr-defined]
                return self._sub_width_lookup[topaz_id_str]  # type: ignore[index]
            return self._deprecated_width_of(topaz_id_str)

        return self._deprecated_width_of(topaz_id_str)

    def channel_width(self, topaz_id: Union[str, int]) -> float:
        topaz_id_str = str(topaz_id)
        if hasattr(self, "_chn_width_lookup"):
            chn_width_lookup: Dict[str, float] = self._chn_width_lookup  # type: ignore[has-type]
            if topaz_id_str in chn_width_lookup:
                return chn_width_lookup[topaz_id_str]

        parquet_fn = _join(self.wat_dir, "channels.parquet")
        if _exists(parquet_fn):
            import duckdb

            with duckdb.connect() as con:
                result = con.execute(
                    f"SELECT topaz_id, width FROM read_parquet('{parquet_fn}')"
                ).fetchall()
            self._chn_width_lookup = {str(row[0]): float(row[1]) for row in result}  # type: ignore[misc]
            if topaz_id_str in self._chn_width_lookup:  # type: ignore[attr-defined]
                return self._chn_width_lookup[topaz_id_str]  # type: ignore[index]
            return self._deprecated_width_of(topaz_id_str)

        csv_fn = _join(self.wat_dir, "channels.csv")
        if _exists(csv_fn):
            import duckdb

            with duckdb.connect() as con:
                result = con.execute(
                    f"SELECT topaz_id, width FROM read_csv('{csv_fn}')"
                ).fetchall()
            self._chn_width_lookup = {str(row[0]): float(row[1]) for row in result}  # type: ignore[misc]
            if topaz_id_str in self._chn_width_lookup:  # type: ignore[attr-defined]
                return self._chn_width_lookup[topaz_id_str]  # type: ignore[index]
            return self._deprecated_width_of(topaz_id_str)

        return self._deprecated_width_of(topaz_id_str)

    @deprecated
    def _deprecated_length_of(self, topaz_id: Union[str, int]) -> float:
        topaz_id_str = str(topaz_id)
        if self._chns_summary is None or self._subs_summary is None:
            raise ValueError("Summary data is None")
        if topaz_id_str.endswith("4"):
            return self._chns_summary[topaz_id_str].length
        else:
            return self._subs_summary[topaz_id_str].length

    @deprecated
    def _deprecated_width_of(self, topaz_id: Union[str, int]) -> float:
        topaz_id_str = str(topaz_id)
        if topaz_id_str.endswith("4"):
            if self._chns_summary is None:
                raise ValueError("Channel summary data is None")
            channel_summary = self._chns_summary[topaz_id_str]
            if isinstance(channel_summary, dict):
                return float(channel_summary["width"])
            return float(channel_summary.width)

        if self._subs_summary is None:
            raise ValueError("Hillslope summary data is None")
        hillslope_summary = self._subs_summary[topaz_id_str]
        if isinstance(hillslope_summary, dict):
            return float(hillslope_summary["width"])
        return float(hillslope_summary.width)

    def width_of(self, topaz_id: Union[str, int]) -> float:
        topaz_id_str = str(topaz_id)
        if topaz_id_str.endswith("4"):
            return self.channel_width(topaz_id)
        return self.hillslope_width(topaz_id)

    def hillslope_centroid_lnglat(self, topaz_id: Union[str, int]) -> Tuple[float, float]:
        if hasattr(self, "_sub_centroid_lookup"):
            sub_centroid_lookup: Dict[str, Tuple[float, float]] = self._sub_centroid_lookup  # type: ignore[has-type]
            return sub_centroid_lookup[str(topaz_id)]

        if _exists(_join(self.wat_dir, "hillslopes.parquet")):
            import duckdb

            with duckdb.connect() as con:
                parquet_fn = _join(self.wat_dir, "hillslopes.parquet")
                # lazy load self._sub_area_lookup with duckdb
                result = con.execute(
                    f"SELECT topaz_id, centroid_lon, centroid_lat FROM read_parquet('{parquet_fn}')"
                ).fetchall()
                self._sub_centroid_lookup: Dict[str, Tuple[float, float]] = {  # type: ignore[misc]
                    str(row[0]): (row[1], row[2]) for row in result
                }
                return self._sub_centroid_lookup[str(topaz_id)]

        if self._subs_summary is None:
            raise ValueError("subs_summary is None")
        wat_ss = self._subs_summary[str(topaz_id)]
        lng, lat = wat_ss.centroid.lnglat
        return lng, lat

    def hillslope_slp_fn(self, topaz_id: Union[str, int]) -> str:
        wat_ss = self.subs_summary[str(topaz_id)]
        if isinstance(wat_ss, HillSummary):  # deprecated
            slp_fn = _join(self.wat_dir, wat_ss.fname)
        elif isinstance(wat_ss, PeridotHillslope):
            slp_fn = _join(self.wat_dir, wat_ss.slp_rel_path)
        else:
            # Handle dict case
            slp_fn = _join(self.wat_dir, wat_ss.get('slp_rel_path', wat_ss.get('fname', '')))

        return slp_fn

    def centroid_hillslope_iter(self) -> Generator[Tuple[Union[str, int], Tuple[float, float]], None, None]:
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
    def _deprecated_centroid_hillslope_iter(self) -> Generator[Tuple[str, Tuple[float, float]], None, None]:
        if self._subs_summary is None:
            return
        i = 0
        for topaz_id, wat_ss in self._subs_summary.items():
            yield topaz_id, wat_ss.centroid.lnglat
            i += 1

        assert i == self.sub_n, (i, self.sub_n)

class Outlet(object):
    def __init__(
        self, 
        requested_loc: Tuple[float, float], 
        actual_loc: Tuple[float, float], 
        distance_from_requested: float, 
        pixel_coords: Tuple[int, int]
    ) -> None:
        self.requested_loc = requested_loc
        self.actual_loc = actual_loc
        self.distance_from_requested = distance_from_requested
        self.pixel_coords = pixel_coords

    def as_dict(self) -> Dict[str, float]:
        return dict(lng=self.actual_loc[0], lat=self.actual_loc[1])
