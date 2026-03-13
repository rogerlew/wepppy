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
    watershed_mixins: Internal mixin classes that hold operation/lookup methods
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
import json

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
from wepppy.topo.watershed_abstraction.support import (
    ChannelSummary,
    HillSummary,
    identify_edge_hillslopes,
    json_to_wgs,
    polygonize_netful,
)
from wepppy.topo.watershed_abstraction.slope_file import mofe_distance_fractions
from wepppy.topo.wbt import WhiteboxToolsTopazEmulator
from wepppy.all_your_base.geo import read_raster, haversine
from wepppy.all_your_base.geo.vrt import build_windowed_vrt_from_window
from wepppy.nodb.duckdb_agents import get_watershed_chns_summary

from wepppy.runtime_paths.parquet_sidecars import pick_existing_parquet_path
from wepppy.nodb.base import NoDbBase, TriggerEvents, nodb_setter
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.query_engine import update_catalog_entry

from wepppy.nodb.duckdb_agents import (
    get_watershed_subs_summary,
    get_watershed_sub_summary,
    get_watershed_chn_summary
)

from .topaz import Topaz
from .watershed_mixins import WatershedOperationsMixin, WatershedLookupMixin

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
    'NoOutletFoundError',
    'process_channel',
    'process_subcatchment',
    'TRANSIENT_FIELDS',
    'Watershed',
    'Outlet',
]
class DelineationBackend(IntEnum):
    TOPAZ = 1
    TauDEM = 2  # Deprecated
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


class NoOutletFoundError(Exception):
    """Raised when find_outlet cannot locate a valid outlet stream cell.

    This typically occurs when the stream network is too sparse after pruning
    and no stream cells intersect with the watershed mask.
    """

    def __init__(self, message: str = "No outlet stream cell found for watershed"):
        self.message = message
        super().__init__(self.message)


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


class Watershed(WatershedOperationsMixin, WatershedLookupMixin, NoDbBase):
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
            self._uploaded_dem_filename: Optional[str] = None

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
                self._flovec_netful_relief_chnjnt_are_vrt = False

            else:
                self._delineation_backend = DelineationBackend.TOPAZ

            self._abstraction_backend: str = self.config_get_str(
                "watershed", "abstraction_backend", "peridot"
            )

            self._mofe_nsegments: Optional[Dict[str, int]] = None
            self._mofe_target_length: float = self.config_get_float(
                "watershed", "mofe_target_length"
            )
            self._mofe_buffer: bool = self.config_get_bool("watershed", "mofe_buffer")
            self._mofe_buffer_length: float = self.config_get_float(
                "watershed", "mofe_buffer_length"
            )
            self._mofe_max_ofes: int = self.config_get_int("watershed", "mofe_max_ofes", 19)

    def __getstate__(self) -> Dict[str, Any]:
        """Exclude live WhiteboxTools instances from persisted NoDb payloads."""
        state = super().__getstate__()
        state.pop("_wbt", None)
        return state

    @property
    def set_extent_mode(self) -> int:
        if not hasattr(self, "_set_extent_mode"):
            return 0
        return self._set_extent_mode
    
    @set_extent_mode.setter
    @nodb_setter
    def set_extent_mode(self, value: int) -> None:
        _value = int(value)
        assert _value in [0, 1, 2, 3], f"Invalid set_extent_mode value: {_value}"
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

    @property
    def uploaded_dem_filename(self) -> Optional[str]:
        if not hasattr(self, "_uploaded_dem_filename"):
            return None
        return self._uploaded_dem_filename

    @uploaded_dem_filename.setter
    @nodb_setter
    def uploaded_dem_filename(self, value: Optional[str]) -> None:
        if value is None or value == "":
            self._uploaded_dem_filename = None
            return
        self._uploaded_dem_filename = str(value)

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
    def skip_flowpaths(self) -> bool:
        """Skip flowpath generation in peridot to reduce memory usage."""
        return getattr(self, "_skip_flowpaths", False)

    @skip_flowpaths.setter
    @nodb_setter
    def skip_flowpaths(self, value: bool) -> None:
        self._skip_flowpaths = value

    @property
    def representative_flowpath(self) -> bool:
        """Use representative flowpath mode for WBT peridot abstractions."""
        return getattr(self, "_representative_flowpath", False)

    @representative_flowpath.setter
    @nodb_setter
    def representative_flowpath(self, value: bool) -> None:
        self._representative_flowpath = value

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

    @property
    def flovec_netful_relief_chnjnt_are_vrt(self) -> bool:
        return bool(getattr(self, "_flovec_netful_relief_chnjnt_are_vrt", False))

    def _ensure_wbt(self) -> WhiteboxToolsTopazEmulator:
        if not self.delineation_backend_is_wbt:
            raise RuntimeError("WhiteboxTools emulator requested for non-WBT backend")
        wbt = getattr(self, "_wbt", None)
        if wbt is None:
            ron = self.ron_instance
            wbt = WhiteboxToolsTopazEmulator(
                self.wbt_wd,
                ron.dem_fn,
                logger=self.logger,
            )
            wbt.flovec_netful_relief_are_vrt = self.flovec_netful_relief_chnjnt_are_vrt
            self._wbt = wbt
        return wbt

    @property
    def is_abstracted(self) -> bool:
        # Check legacy in-memory summaries first
        if self._subs_summary is not None and self._chns_summary is not None:
            return True
        # Fall back to parquet files (post-migration state)
        hillslopes_parquet = pick_existing_parquet_path(
            self.wd, "watershed/hillslopes.parquet"
        )
        channels_parquet = pick_existing_parquet_path(
            self.wd, "watershed/channels.parquet"
        )
        return hillslopes_parquet is not None and channels_parquet is not None

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
            ext = "vrt" if self.flovec_netful_relief_chnjnt_are_vrt else "tif"
            return _join(self.wbt_wd, f"netful.{ext}")
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
            # Try loading count from parquet if available
            hillslopes_parquet = pick_existing_parquet_path(
                self.wd, "watershed/hillslopes.parquet"
            )
            if hillslopes_parquet is not None:
                import duckdb
                try:
                    con = duckdb.connect()
                    result = con.execute(f"SELECT COUNT(*) FROM read_parquet('{hillslopes_parquet}')").fetchone()
                    con.close()
                    return result[0]
                except Exception:
                    pass
            return 0

        return len(self._subs_summary)

    @property
    def greater300_n(self) -> int:
        if self._subs_summary is None:
            return 0

        # use duckdb
        hillslopes_parquet = pick_existing_parquet_path(
            self.wd, "watershed/hillslopes.parquet"
        )
        if hillslopes_parquet is not None:
            import duckdb

            try:
                con = duckdb.connect()
                sql = f"SELECT COUNT(*) FROM read_parquet('{hillslopes_parquet}') WHERE length > 300"
                result = con.execute(sql).fetchone()
                con.close()
                return result[0]
            except duckdb.duckdb.IOException:
                time.sleep(4)  # fix for slow NAS after abstraction
                con = duckdb.connect()
                sql = f"SELECT COUNT(*) FROM read_parquet('{hillslopes_parquet}') WHERE length > 300"
                result = con.execute(sql).fetchone()
                con.close()
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
            # Try loading count from parquet if available
            channels_parquet = pick_existing_parquet_path(
                self.wd, "watershed/channels.parquet"
            )
            if channels_parquet is not None:
                import duckdb
                try:
                    con = duckdb.connect()
                    result = con.execute(f"SELECT COUNT(*) FROM read_parquet('{channels_parquet}')").fetchone()
                    con.close()
                    return result[0]
                except Exception:
                    pass
            return 0

        return len(self._chns_summary)

    @property
    def wsarea(self) -> float:
        return getattr(self, "_wsarea", 1)

    def _structure_json_path(self) -> str:
        return _join(self.wat_dir, "structure.json")

    def _load_structure_json(self, path: str) -> List[List[int]]:
        with open(path, "r", encoding="utf-8") as fp:
            payload = json.load(fp)

        if not isinstance(payload, list):
            raise ValueError("structure.json must contain a list of rows")
        structure: List[List[int]] = []
        for row in payload:
            if not isinstance(row, list):
                raise ValueError("structure.json rows must be lists")
            structure.append([int(value) for value in row])
        return structure

    def _write_structure_json(self, structure: List[List[int]]) -> str:
        path = self._structure_json_path()
        tmp_path = f"{path}.tmp"
        os.makedirs(self.wat_dir, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as fp:
            json.dump(structure, fp)
        os.replace(tmp_path, path)
        return path

    def _build_structure_from_network(self) -> Optional[List[List[int]]]:
        network_path = _join(self.wat_dir, "network.txt")
        if not _exists(network_path):
            return None
        try:
            network = read_network(network_path)
        except Exception as exc:
            self.logger.warning("Failed to read network.txt for structure rebuild: %s", exc)
            return None

        try:
            translator = self.translator_factory()
        except Exception as exc:
            self.logger.warning("Failed to build translator for structure rebuild: %s", exc)
            return None

        try:
            return translator.build_structure(network)
        except Exception as exc:
            self.logger.warning("Failed to rebuild structure from network: %s", exc)
            return None

    @property
    def structure(self) -> Any:
        structure_data = self._structure

        if isinstance(structure_data, list):
            if not _exists(self._structure_json_path()):
                try:
                    self._write_structure_json(structure_data)
                except Exception as exc:
                    self.logger.debug("Failed to persist structure.json: %s", exc)
            return structure_data

        if isinstance(structure_data, str):
            if structure_data.endswith(".json") and _exists(structure_data):
                return self._load_structure_json(structure_data)

        structure_json = self._structure_json_path()
        if _exists(structure_json):
            return self._load_structure_json(structure_json)

        rebuilt = self._build_structure_from_network()
        if rebuilt is not None:
            try:
                self._write_structure_json(rebuilt)
            except Exception as exc:
                self.logger.debug("Failed to persist rebuilt structure.json: %s", exc)
            return rebuilt

        if structure_data is not None:
            self.logger.warning(
                "structure.json missing for %s; run watershed migration to regenerate structure data.",
                self.wd,
            )
        return None

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
    def dem_fn(self) -> str:
        return self.ron_instance.dem_fn

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
            ext = "vrt" if self.flovec_netful_relief_chnjnt_are_vrt else "tif"
            relief_path = _join(self.wbt_wd, f"relief.{ext}")
        else:
            return None

        return relief_path if _exists(relief_path) else None


    def find_outlet(
        self, watershed_feature: Optional[WatershedFeature] = None
    ) -> None:
        assert self.delineation_backend_is_wbt, "find_outlet only works with WBT delineation backend"

        wbt = self._ensure_wbt()
        ron = self.ron_instance

        # build raster mask from watershed feature
        if watershed_feature is not None:
            watershed_feature.build_raster_mask(
                template_filepath=ron.dem_fn, dst_filepath=self.target_watershed_path)
        elif not _exists(self.target_watershed_path):
            raise FileNotFoundError(
                f"Target watershed raster not found: {self.target_watershed_path}"
            )

        try:
            wbt.wbt.find_outlet(
                d8_pntr=wbt.flovec,
                streams=wbt.netful,
                watershed=self.target_watershed_path,
                output=wbt.outlet_geojson
            )
        except Exception as e:
            error_msg = str(e)
            # Check for sparse network error from WhiteBox tools
            if "Failed to identify an outlet stream cell" in error_msg:
                runid = watershed_feature.runid if watershed_feature else self.runid
                raise NoOutletFoundError(
                    f"Stream network too sparse for watershed (runid={runid}): {error_msg}"
                ) from e
            raise  # Re-raise other exceptions

        outlet = wbt.set_outlet_from_geojson(logger=self.logger)
        self.outlet = outlet

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.find_outlet)
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

            # Handle minimal watershed case (1 hillslope, 1 channel) where network.txt may not exist
            network_path = _join(self.wat_dir, "network.txt")
            if not _exists(network_path) and len(sub_ids) == 1 and len(chn_ids) == 1:
                self.logger.info("Minimal watershed (1 hillslope, 1 channel) - skipping structure.json")
                self._structure = None
            else:
                network = self.network
                translator = self.translator_factory()
                structure = translator.build_structure(network)
                if structure is not None:
                    self._write_structure_json(structure)
                    self._structure = structure
                else:
                    self._structure = None

            try:
                update_catalog_entry(self.wd, 'watershed')
            except Exception as exc:
                self.logger.warning("Failed to refresh catalog for watershed outputs: %s", exc)

    @property
    def sub_area(self) -> float:
        sub_area = getattr(self, "_sub_area", None)

        if sub_area is None and self._subs_summary is not None:
            sub_area = sum(summary.area for summary in self._subs_summary.values())
        
        # Fall back to parquet if in-memory summary not available
        if sub_area is None:
            hillslopes_parquet = pick_existing_parquet_path(
                self.wd, "watershed/hillslopes.parquet"
            )
            if hillslopes_parquet is not None:
                import duckdb
                try:
                    con = duckdb.connect()
                    result = con.execute(f"SELECT SUM(area) FROM read_parquet('{hillslopes_parquet}')").fetchone()
                    con.close()
                    sub_area = result[0] if result[0] is not None else 0.0
                except Exception:
                    pass

        return sub_area if sub_area is not None else 0.0

    @property
    def chn_area(self) -> float:
        chn_area = getattr(self, "_chn_area", None)

        if chn_area is None and self._chns_summary is not None:
            chn_area = sum(summary.area for summary in self._chns_summary.values())
        
        # Fall back to parquet if in-memory summary not available
        if chn_area is None:
            channels_parquet = pick_existing_parquet_path(
                self.wd, "watershed/channels.parquet"
            )
            if channels_parquet is not None:
                import duckdb
                try:
                    con = duckdb.connect()
                    result = con.execute(f"SELECT SUM(area) FROM read_parquet('{channels_parquet}')").fetchone()
                    con.close()
                    chn_area = result[0] if result[0] is not None else 0.0
                except Exception:
                    pass

        return chn_area if chn_area is not None else 0.0


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
            structure = _abs.structure
            if structure is not None:
                try:
                    self._write_structure_json(structure)
                except Exception as exc:
                    self.logger.debug("Failed to persist structure.json: %s", exc)
                self._structure = structure
            else:
                self._structure = None

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
