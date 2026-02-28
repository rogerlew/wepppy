# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""Run Object Node (RON) controller.

This module coordinates project metadata, base map preparation, and activation
of supporting NoDb controllers. ``Ron`` reads the run configuration, provisions
digital elevation models, and primes DuckDB summary agents so the web
application can report watershed health immediately after initialization.

Key Components:
    Map: View model describing map extent, UTM geometry, and pixel sizing.
    Ron: NoDb controller orchestrating project setup and downstream services.
    RonViewModel: Serializes run state for web clients.
    RonNoDbLockedException: Raised when concurrent access cannot be acquired.

Responsibilities:
    - Parse configuration values for map extent, DEM sources, and locales.
    - Copy or download DEM assets (OpenTopography, prebuilt rasters) into the
      working directory.
    - Instantiate watershed, land use, soils, climate, and WEPP controllers so
      their ``*.nodb`` snapshots exist for subsequent requests.
    - Register project tasks with Redis and activate the query engine catalog.
    - Provide Leaflet ready map bounds, summaries, and export utilities via the
      DuckDB agents.

External Services:
    - OpenTopography and WMEsque endpoints for raster acquisition.
    - Redis (``RedisPrep``) for task bookkeeping and telemetry.
    - Query engine catalog managed through ``activate_query_engine``.

Example:
    >>> from wepppy.nodb.core import Ron
    >>> from wepppy.nodb.base import TriggerEvents
    >>> ron = Ron.getInstance('/runs/example')
    >>> ron.map.bounds_str  # serialized Leaflet bounds
    >>> ron.trigger(TriggerEvents.ON_INIT_FINISH)

See Also:
    - ``wepppy.nodb.core.watershed`` for delineation after RON setup.
    - ``wepppy.nodb.base.NoDbBase`` for locking and persistence details.
"""

# standard libraries
import os
import ast
import json
import math
import re
import time

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from os.path import isdir
from typing import Optional, Tuple, List, Any, Dict

import shutil
import inspect
import utm
import requests
import redis

from wepppy.nodb.version import read_version
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.all_your_base.geo.webclients import wmesque_retrieve
from wepppy.all_your_base.geo import (
    RasterDatasetInterpolator,
    haversine,
    read_raster,
    utm_srid,
)
from wepppy.all_your_base.geo.vrt import build_windowed_vrt_from_window

from wepppy.locales.earth.copernicus import (
    CopernicusConfigurationError,
    CopernicusRetryableError,
    copernicus_retrieve,
)
from wepppy.locales.earth.opentopography import opentopo_retrieve

from wepppy.nodb.base import (
    NoDbBase,
    TriggerEvents,
    nodb_setter,
)

from wepppy.nodb.duckdb_agents import (
    get_landuse_sub_summary,
    get_soil_sub_summary,
    get_watershed_chn_summary,
    get_watershed_chns_summary,
    get_watershed_sub_summary,
    get_watershed_subs_summary, 
    get_soil_subs_summary, 
    get_landuse_subs_summary
)
from wepppy.runtime_paths.parquet_sidecars import pick_existing_parquet_path

from wepppy.query_engine.activate import activate_query_engine, update_catalog_entry

DEFAULT_MAP_CENTER = [44.0, -116.0]
_COPERNICUS_DEFAULT_OPENTOPO_FALLBACK_DATASET = "srtmgl1_e"
_OPENTOPO_BLOCK_UNTIL_KEY = "opentopo:rate_limit:block_until"
_OPENTOPO_MINUTE_KEY_PREFIX = "opentopo:rate_limit:minute"
_OPENTOPO_STATUS_RE = re.compile(r"(?:status(?:[_\s]?code)?\s*[=:]?\s*)(\d{3})", re.IGNORECASE)
_OPENTOPO_DEFAULT_MAX_REQUESTS_PER_MINUTE = 1
_OPENTOPO_DEFAULT_BLOCK_SECONDS = 150
_OPENTOPO_DEFAULT_PENALTY_BLOCK_SECONDS = 600
_OPENTOPO_THROTTLE_STATUS_CODES = frozenset({401, 429})
_OPENTOPO_BLOCK_UNTIL_MAX_LUA = """
local key = KEYS[1]
local requested = tonumber(ARGV[1]) or 0
local current_raw = redis.call("GET", key)
local current = tonumber(current_raw) or 0
local blocked_until = requested
if current > blocked_until then
    blocked_until = current
end
local blocked_str = string.format("%.3f", blocked_until)
redis.call("SET", key, blocked_str)
return blocked_str
"""

__all__ = [
    'Map',
    'RonNoDbLockedException',
    'Ron',
    'RonViewModel',
]

_thisdir = os.path.dirname(__file__)


class Map(object):
    def __init__(
        self, 
        extent: List[float], 
        center: List[float], 
        zoom: float, 
        cellsize: float = 30.0
    ) -> None:
        assert len(extent) == 4

        _extent = [float(v) for v in extent]
        l, b, r, t = _extent
        assert l < r
        assert b < t

        self.extent: List[float] = [float(v) for v in _extent]  # in decimal degrees
        self.center: List[float] = [float(v) for v in center]
        self.zoom: float = float(zoom)
        self.cellsize: float = cellsize

        # e.g. (395201.3103811303, 5673135.241182375, 32, 'U')
        ul_x, ul_y, zone_number, zone_letter = utm.from_latlon(latitude=t, longitude=l)
        ul_x = float(ul_x)
        ul_y = float(ul_y)
        self.utm: Tuple[float, float, int, str] = ul_x, ul_y, zone_number, zone_letter

        lr_x, lr_y, _, _ = utm.from_latlon(longitude=r, latitude=b, force_zone_number=zone_number)
        self._ul_x: float = float(ul_x)  # in utm
        self._ul_y: float = float(ul_y)
        self._lr_x: float = float(lr_x)
        self._lr_y: float = float(lr_y)

        self._num_cols: int = int(round((lr_x - ul_x) / cellsize))
        self._num_rows: int = int(round((ul_y - lr_y) / cellsize))

    @classmethod
    def from_payload(
        cls,
        payload: Any,
        default_cellsize: Optional[float] = None,
    ) -> "Map":
        """Hydrate a Map instance from a JSON/dict payload."""

        def _unwrap_py_tuple(value: Any) -> Any:
            if isinstance(value, dict) and "py/tuple" in value:
                return value.get("py/tuple")
            return value

        def _coerce_sequence(value: Any, label: str, expected_len: int) -> List[float]:
            seq = _unwrap_py_tuple(value)
            if not isinstance(seq, (list, tuple)):
                raise ValueError(f"{label} must be a list or tuple.")
            if len(seq) != expected_len:
                raise ValueError(f"{label} must contain {expected_len} values.")
            result: List[float] = []
            for part in seq:
                try:
                    result.append(float(part))
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Could not parse numeric values for {label}.") from exc
            return result

        def _coerce_int(value: Any, label: str) -> int:
            try:
                return int(float(value))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Could not parse integer value for {label}.") from exc

        def _coerce_float(value: Any, label: str, *, allow_none: bool = False) -> Optional[float]:
            if value is None and allow_none:
                return None
            try:
                return float(value)
            except (TypeError, ValueError) as exc:
                if allow_none:
                    return None
                raise ValueError(f"Could not parse numeric value for {label}.") from exc

        def _apply_optional_fields(map_obj: "Map", data: Dict[str, Any]) -> None:
            utm_raw = _unwrap_py_tuple(data.get("utm"))
            if utm_raw is not None:
                if not isinstance(utm_raw, (list, tuple)) or len(utm_raw) != 4:
                    raise ValueError("utm must be a 4-element tuple of (ul_x, ul_y, zone, letter).")
                try:
                    map_obj.utm = (  # type: ignore[attr-defined]
                        float(utm_raw[0]),
                        float(utm_raw[1]),
                        int(float(utm_raw[2])),
                        str(utm_raw[3]),
                    )
                except (TypeError, ValueError) as exc:
                    raise ValueError("Invalid utm tuple values.") from exc

            for key in ("_ul_x", "_ul_y", "_lr_x", "_lr_y"):
                val = _coerce_float(data.get(key), key, allow_none=True)
                if val is not None:
                    setattr(map_obj, key, float(val))
            for key in ("_num_cols", "_num_rows"):
                val = _coerce_int(data.get(key), key) if data.get(key) not in (None, "") else None
                if val is not None:
                    setattr(map_obj, key, int(val))

        if payload is None:
            raise ValueError("Map payload is required.")

        data: Any = payload
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise ValueError("Map payload must be valid JSON.") from exc

        if isinstance(data, cls):
            payload_dict = data.__dict__
        elif isinstance(data, dict):
            payload_dict = data
        else:
            raise ValueError("Map payload must be a JSON object.")

        extent = _coerce_sequence(payload_dict.get("extent"), "extent", 4)
        center = _coerce_sequence(payload_dict.get("center"), "center", 2)
        zoom = _coerce_float(payload_dict.get("zoom"), "zoom")
        cellsize_raw = payload_dict.get("cellsize")
        if cellsize_raw in (None, ""):
            cellsize_raw = default_cellsize if default_cellsize is not None else 30.0
        cellsize = _coerce_float(cellsize_raw, "cellsize")
        if cellsize is None or cellsize <= 0:
            raise ValueError("cellsize must be positive.")

        map_obj = cls(extent, center, zoom, cellsize)
        _apply_optional_fields(map_obj, payload_dict)
        return map_obj

    def to_payload(self) -> Dict[str, Any]:
        """Serialize the map to a json-friendly payload matching ron.nodb structure."""
        payload: Dict[str, Any] = {
            "py/object": f"{self.__module__}.{type(self).__name__}",
            "extent": [float(v) for v in self.extent],
            "center": [float(v) for v in self.center],
            "zoom": float(self.zoom),
            "cellsize": float(self.cellsize),
        }
        utm_tuple = getattr(self, "utm", None)
        if utm_tuple is not None:
            payload["utm"] = {"py/tuple": [float(utm_tuple[0]), float(utm_tuple[1]), int(utm_tuple[2]), str(utm_tuple[3])]}
        for key in ("_ul_x", "_ul_y", "_lr_x", "_lr_y"):
            if hasattr(self, key):
                payload[key] = float(getattr(self, key))
        for key in ("_num_cols", "_num_rows"):
            if hasattr(self, key):
                payload[key] = int(getattr(self, key))
        return payload

    @staticmethod
    def zoom_for_extent(
        extent: List[float],
        *,
        map_px: Tuple[int, int] = (1200, 800),
        tile_px: int = 256,
        min_zoom: float = 1.0,
        max_zoom: float = 20.0,
    ) -> float:
        """Return a Web Mercator zoom that fits the extent in the viewport."""
        west, south, east, north = extent

        def _mercator_lat(lat: float) -> float:
            lat = max(min(lat, 85.05112878), -85.05112878)
            return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))

        lat_fraction = (_mercator_lat(north) - _mercator_lat(south)) / (2 * math.pi)
        lng_fraction = (east - west) / 360.0

        lat_fraction = max(lat_fraction, 1e-9)
        lng_fraction = max(lng_fraction, 1e-9)

        width_px, height_px = map_px
        zoom_lat = math.log(height_px / tile_px / lat_fraction, 2)
        zoom_lng = math.log(width_px / tile_px / lng_fraction, 2)
        zoom = min(zoom_lat, zoom_lng)

        return max(min_zoom, min(max_zoom, zoom))

    @property
    def utm_zone(self) -> int:
        return self.utm[2]

    @property
    def zone_letter(self) -> str:
        return self.utm[3]

    @property
    def srid(self) -> int:
        return utm_srid(self.utm_zone, self.northern)

    @property
    def northern(self) -> bool:
        return self.extent[3] > 0.0

    @property
    def ul_x(self) -> float:
        if hasattr(self, '_ul_x'):
            return self._ul_x

        l, b, r, t = self.extent
        ul_x, ul_y, zone_number, zone_letter = utm.from_latlon(latitude=t, longitude=l)
        self._ul_x = float(ul_x)
        self._ul_y = float(ul_y)

        return ul_x

    @property
    def ul_y(self) -> float:
        if hasattr(self, '_ul_y'):
            return self._ul_y

        l, b, r, t = self.extent
        ul_x, ul_y, zone_number, zone_letter = utm.from_latlon(latitude=t, longitude=l)
        self._ul_x = float(ul_x)
        self._ul_y = float(ul_y)

        return ul_y

    @property
    def lr_x(self) -> float:
        if hasattr(self, '_lr_x'):
            return self._lr_x

        l, b, r, t = self.extent
        lr_x, lr_y, zone_number, zone_letter = utm.from_latlon(latitude=b, longitude=r)
        self._lr_x = float(lr_x)
        self._lr_y = float(lr_y)

        return lr_x

    @property
    def lr_y(self) -> float:
        if hasattr(self, '_lr_y'):
            return self._lr_y

        l, b, r, t = self.extent
        lr_x, lr_y, zone_number, zone_letter = utm.from_latlon(latitude=b, longitude=r)
        self._lr_x = float(lr_x)
        self._lr_y = float(lr_y)

        return lr_y

    @property
    def utm_extent(self) -> Tuple[float, float, float, float]:
        return self.ul_x, self.lr_y, self.lr_x, self.ul_y

    @property
    def num_cols(self) -> int:
        if hasattr(self, '_num_cols'):
            return self._num_cols

        self._num_cols = int(round((self.lr_x - self.ul_x) / self.cellsize))
        return self._num_cols

    @property
    def num_rows(self) -> int:
        if hasattr(self, '_num_rows'):
            return self._num_rows
            
        self._num_rows = int(round((self.ul_y - self.lr_y) / self.cellsize))
        return self._num_rows

    @property
    def shape(self) -> Tuple[int, int]:
        l, b, r, t = self.extent
        px_w = int(haversine((l, b), (l, t)) * 1000 / self.cellsize)
        px_h = int(haversine((l, b), (r, b)) * 1000 / self.cellsize)
        return px_w, px_h

    @property
    def bounds_str(self) -> str:
        """
        returns extent formatted leaflet
        """
        l, b, r, t = self.extent
        sw = [b, l]
        ne = [t, r]
        return str([sw, ne])

    def utm_to_px(self, easting: float, northing: float) -> Tuple[int, int]:
        """
        return the utm coords from pixel coords
        """

        # unpack variables for instance
        cellsize, num_cols, num_rows = self.cellsize, self.num_cols, self.num_rows
        ul_x, ul_y, lr_x, lr_y = self.ul_x, self.ul_y, self.lr_x, self.lr_y

        x = int(round((easting - ul_x) / cellsize))
        y = int(round((northing - ul_y) / -cellsize))

        assert 0 <= y < num_rows, (y, (num_rows, num_cols))
        assert 0 <= x < num_cols, (x, (num_rows, num_cols))

        return x, y

    def lnglat_to_px(self, lng: float, lat: float) -> Tuple[int, int]:
        """
        return the x,y pixel coords of long, lat
        """

        # unpack variables for instance
        cellsize, num_cols, num_rows = self.cellsize, self.num_cols, self.num_rows
        ul_x, ul_y, lr_x, lr_y = self.ul_x, self.ul_y, self.lr_x, self.lr_y

        # find easting and northing
        x, y, _, _ = utm.from_latlon(lat, lng, self.utm_zone)

        # assert this makes sense with the stored extent
        assert round(x) >= round(ul_x), (x, ul_x)
        assert round(x) <= round(lr_x), (x, lr_x)
        assert round(y) >= round(lr_y), (y, lr_y)
        assert round(y) <= round(y), (y, ul_y)

        # determine pixel coords
        _x = int(round((x - ul_x) / cellsize))
        _y = int(round((ul_y - y) / cellsize))

        # sanity check on the coords
        assert 0 <= _x < num_cols, str(x)
        assert 0 <= _y < num_rows, str(y)

        return _x, _y

    def px_to_utm(self, x: int, y: int) -> Tuple[float, float]:
        """
        return the utm coords from pixel coords
        """

        # unpack variables for instance
        cellsize, num_cols, num_rows = self.cellsize, self.num_cols, self.num_rows
        ul_x, ul_y, lr_x, lr_y = self.ul_x, self.ul_y, self.lr_x, self.lr_y

        assert 0 <= x < num_cols
        assert 0 <= y < num_rows

        easting = ul_x + cellsize * x
        northing = ul_y - cellsize * y

        return easting, northing

    def lnglat_to_utm(self, lng: float, lat: float) -> Tuple[float, float]:
        """
        return the utm coords from lnglat coords
        """
        x, y, _, _ = utm.from_latlon(latitude=lat, longitude=lng, force_zone_number=self.utm_zone)
        return float(x), float(y)

    def px_to_lnglat(self, x: int, y: int) -> Tuple[float, float]:
        """
        return the long/lat (WGS84) coords from pixel coords
        """

        easting, northing = self.px_to_utm(x, y)
        lat, lng, _, _ = utm.to_latlon(easting=easting, northing=northing,
                                       zone_number=self.utm_zone, northern=self.northern)
        return float(lng), float(lat)

    def raster_intersection(
        self, 
        extent: List[float], 
        raster_fn: str, 
        discard: Optional[Any] = None
    ) -> List:
        """
        returns the subset of pixel values of raster_fn that are within the extent
        :param extent: l, b, r, t in decimal degrees
        :param raster_fn: path to a thematic raster with the same extent, projection, and cellsize as this instance
        :param None or iterable, throwaway these values before returning

        :return:  sorted list of the values
        """
        if not _exists(raster_fn):
            return []

        assert extent[0] < extent[2]
        assert extent[1] < extent[3]

        x0, y0 = self.lnglat_to_px(extent[0], extent[3])
        xend, yend = self.lnglat_to_px(extent[2], extent[1])

        # Handle edge case: very small extents (e.g., 25-30m bbox from UI selections)
        # can round to the same pixel or reversed coordinates due to int(round(...))
        # in lnglat_to_px. Ensure we always have at least a 1-pixel window to query.
        # This prevents AssertionError when users draw tiny selection boxes on the map.
        if x0 >= xend:
            xend = x0 + 1
        if y0 >= yend:
            yend = y0 + 1

        data, transform, proj = read_raster(raster_fn)
        the_set = set(data[x0:xend, y0:yend].flatten())
        if discard is not None:
            for val in discard:
                the_set.discard(val)
        return sorted(the_set)


class RonNoDbLockedException(Exception):
    pass


class Ron(NoDbBase):
    """
    Run Object Node

    tracks high level project details and intializes other NoDb singletons
    """
    __name__ = 'Ron'

    __exclude__ = ('_w3w', 
                   '_locales', 
                   '_enable_landuse_change',
                   '_dem_db',
                   '_boundary')

    filename = 'ron.nodb'

    @staticmethod
    def _normalize_center(value: Any) -> List[float]:
        """
        Normalize map center definitions to [lat, lon] floats.
        Handles lists, tuples, and legacy serialized strings.
        """
        center = value
        if center is None or center == '':
            return DEFAULT_MAP_CENTER.copy()

        if isinstance(center, str):
            center = center.strip()
            if center == '':
                return DEFAULT_MAP_CENTER.copy()
            try:
                center = ast.literal_eval(center)
            except (ValueError, SyntaxError):
                return DEFAULT_MAP_CENTER.copy()

        if isinstance(center, tuple):
            center = list(center)

        if isinstance(center, list) and len(center) >= 2:
            try:
                lat = float(center[0])
                lon = float(center[1])
                return [lat, lon]
            except (TypeError, ValueError):
                return DEFAULT_MAP_CENTER.copy()

        return DEFAULT_MAP_CENTER.copy()

    def __init__(
        self, 
        wd: str, 
        cfg_fn: str = '0.cfg', 
        run_group: Optional[str] = None, 
        group_name: Optional[str] = None
    ) -> None:
        from wepppy.nodb.base import iter_nodb_mods_subclasses
        from wepppy.nodb.core.watershed import DelineationBackend
        from wepppy.nodb.core.watershed import Watershed
        from wepppy.nodb.core.topaz import Topaz
        from wepppy.nodb.core.landuse import Landuse
        from wepppy.nodb.core.soils import Soils
        from wepppy.nodb.core.climate import Climate
        from wepppy.nodb.core.wepp import Wepp
        from wepppy.nodb.unitizer import Unitizer
        from wepppy.nodb.mods.observed import Observed

        super(Ron, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            self._configname = self.config_get_str('general', 'name')

            # Map
            self._cellsize = self.config_get_float('general', 'cellsize')
            raw_center = self.config_get_raw('map', 'center0')
            self._center0 = self._normalize_center(raw_center)
            self._zoom0 = self.config_get_int('map', 'zoom0')

            _boundary = self.config_get_path('map', 'boundary')
            self._boundary = _boundary

            # DEM
            dem_dir = self.dem_dir
            if not _exists(dem_dir):
                os.mkdir(dem_dir)

            self._dem_is_vrt = False
            self._dem_db = self.config_get_str('general', 'dem_db')

            _dem_map = self.config_get_path('general', 'dem_map')
            self._dem_map = _dem_map

            if self.dem_map is not None:
                shutil.copyfile(self.dem_map, self.dem_fn)

            # Landuse
            self._enable_landuse_change = self.config_get_bool('landuse', 'enable_landuse_change')

            self._profile_recorder_assembler_enabled = self.config_get_bool('recorder', 'profile_recorder_assembler_enabled', False)

            # Project
            self._name = ''
            self._scenario = ''
            self._map = None
            self._w3w = None

            self._locales = self.config_get_list('general', 'locales')

            export_dir = self.export_dir
            if not _exists(export_dir):
                os.mkdir(export_dir)

            # initialize the other controllers here
            # this will create the other .nodb files

            # gotcha: need to import the nodb submodules
            # through wepppy to avoid circular references
            watershed = Watershed(wd, cfg_fn, run_group=run_group, group_name=group_name)
            if watershed.delineation_backend == DelineationBackend.TOPAZ:
                Topaz(wd, cfg_fn, run_group=run_group, group_name=group_name)

            Landuse(wd, cfg_fn, run_group=run_group, group_name=group_name)
            Soils(wd, cfg_fn, run_group=run_group, group_name=group_name)
            Climate(wd, cfg_fn, run_group=run_group, group_name=group_name)
            Wepp(wd, cfg_fn, run_group=run_group, group_name=group_name)
            Observed(wd, cfg_fn, run_group=run_group, group_name=group_name)
            Unitizer(wd, cfg_fn, run_group=run_group, group_name=group_name)
            prep = RedisPrep(wd, cfg_fn)
            prep.timestamp(TaskEnum.project_init)

            # Initialize mods
            mods_to_init = self.mods or ()
            for mod in mods_to_init:
                type(self)._import_mod_module(mod)

            mods_registry = {mod: cls for mod, cls in iter_nodb_mods_subclasses()}

            for mod in mods_to_init:
                if mod not in mods_registry:
                    raise Exception(f'unknown mod {mod}')
                mod_instance = mods_registry[mod](wd, cfg_fn, run_group=run_group, group_name=group_name)

                if mod in ['baer', 'disturbed']:
                    if mod == 'baer':
                        prep.sbs_required = True

                    sbs_map = self.config_get_path('landuse', 'sbs_map')
                    if sbs_map is not None:
                        self.init_sbs_map(sbs_map, mod_instance)
                        
        
        activate_query_engine(self.wd, run_interchange=False)
        self.trigger(TriggerEvents.ON_INIT_FINISH)

    @property
    def profile_recorder_assembler_enabled(self) -> bool:
        return getattr(self, '_profile_recorder_assembler_enabled', False)

    @profile_recorder_assembler_enabled.setter
    @nodb_setter
    def profile_recorder_assembler_enabled(self, value: bool) -> None:
        self._profile_recorder_assembler_enabled = value

    def clean_export_dir(self) -> None:
        with self.timed("Cleaning export directory"):
            export_dir = self.export_dir
            if _exists(export_dir):
                shutil.rmtree(export_dir)

            os.mkdir(export_dir)

    # this is here because it makes it agnostic to the modules
    # that use it. e.g. it doesn't depend on Disturbed or Baer, or ...
    def init_sbs_map(self, sbs_map: str, baer: Any) -> None:
        with self.timed("Initializing SBS map"):
            sbs_name = _split(sbs_map)[1]
            sbs_path = _join(baer.baer_dir, sbs_name)

            if sbs_map.startswith('http'):
                r = requests.get(sbs_map)
                r.raise_for_status()

                with open(sbs_path, 'wb') as f:
                    f.write(r.content)
                baer.validate(_split(sbs_path)[-1], mode=0)
            else:
                from wepppy.nodb.mods import MODS_DIR, EXTENDED_MODS_DATA
                sbs_map = (
                    sbs_map.replace('MODS_DIR', MODS_DIR)
                    .replace('EXTENDED_MODS_DATA', EXTENDED_MODS_DATA)
                )

                # sbs_map = _join(_thisdir, sbs_map)
                assert _exists(sbs_map), (sbs_map, os.path.abspath(sbs_map))
                assert not isdir(sbs_map)

                shutil.copyfile(sbs_map, sbs_path)

                baer.validate(_split(sbs_path)[-1], mode=0)

    @property
    def configname(self) -> str:
        return self._configname

    @property
    def max_map_dimension_px(self) -> int:
        """
        Maximum map dimension in pixels.
        """
        return 8192

    @property
    def enable_landuse_change(self) -> bool:
        return self._enable_landuse_change

    def remove_mod(self, mod_name: str) -> None:
        from wepppy.nodb.base import iter_nodb_mods_subclasses, clear_locks, clear_nodb_file_cache

        mod_relpath = f'{mod_name}.nodb'
        # Only clear locks/cache for the target mod to avoid disrupting in-flight jobs.
        clear_locks(self.runid, pup_relpath=mod_relpath)
        if mod_name in self.mods:
            with self.locked():
                self._mods.remove(mod_name)

        mod_nodb_fn = _join(self.wd, mod_relpath)
        if _exists(mod_nodb_fn):
            os.remove(mod_nodb_fn)

        for mod, cls in iter_nodb_mods_subclasses():
            mod_instance = cls.tryGetInstance(self.wd)
            if mod_instance is not None:
                if mod_name in self.mods:
                    with mod_instance.locked():
                        self._mods.remove(mod_name)

        clear_nodb_file_cache(self.runid, pup_relpath=mod_relpath)

    #
    # map
    #
    @property
    def center0(self) -> List[float]:
        if self.map is None:
            normalized = self._normalize_center(getattr(self, '_center0', None))
            if normalized != getattr(self, '_center0', None):
                self._center0 = normalized
            return normalized
        else:
            return self.map.center[::-1]

    @property
    def zoom0(self) -> int:
        if self.map is None:
            return self._zoom0
        else:
            return self.map.zoom

    @property
    def cellsize(self) -> float:
        return self._cellsize

    @property
    def boundary(self) -> Optional[str]:  # url to a geojson file
        return self._boundary
    
    @property
    def boundary_color(self) -> str:
        return getattr(self, '_boundary_color', '#FF0000')

    @property
    def boundary_name(self) -> str:
        return getattr(self, '_boundary_name', 'boundary')

    
    @property
    def map(self) -> Optional[Map]:
        return self._map

    def set_map(
        self, 
        extent: List[float], 
        center: List[float], 
        zoom: float
    ) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(extent={extent}, center={center}, zoom={zoom}')

        with self.locked():
            self._map = Map(extent, center, zoom, self.cellsize)
            lng, lat = self.map.center
            self._w3w = None

    def set_map_object(self, map_object: Any) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(map_object=provided)')

        map_instance = map_object if isinstance(map_object, Map) else Map.from_payload(
            map_object,
            default_cellsize=self.cellsize,
        )

        with self.locked():
            self._map = map_instance
            lng, lat = self.map.center
            self._w3w = None

    @property
    def w3w(self) -> str:
        if hasattr(self, '_w3w'):
            if self._w3w is not None:
                return self._w3w.get('words', '')

        return ''

    @property
    def location_hash(self) -> str:
        wd = self.wd
        watershed = self.watershed_instance
        w3w = self.w3w
        sub_n = watershed.sub_n
        is_topaz = int(watershed.delineation_backend_is_topaz)
        return f'{w3w}_{is_topaz}_{sub_n}'
       
    @property
    def extent(self) -> Optional[List[float]]:
        if self.map is None:
            return None

        return self.map.extent

    #
    # name
    #
    @property
    def name(self) -> str:
        return self._name

    @name.setter
    @nodb_setter
    def name(self, value: str) -> None:
        if value is None:
            self._name = ''
            return
        self._name = str(value)

    #
    # scenario
    #
    @property
    def scenario(self) -> str:
        return getattr(self, '_scenario', '')

    @scenario.setter
    @nodb_setter
    def scenario(self, value: str) -> None:
        if value is None:
            self._scenario = ''
            return
        self._scenario = str(value)

    @property
    def has_ash_results(self) -> bool:
        if 'ash' not in self.mods:
            return False

        from wepppy.nodb.mods import Ash
        ash = Ash.getInstance(self.wd)
        return ash.has_ash_results

    @property
    def dem_db(self) -> str:
        return getattr(self, '_dem_db', self.config_get_str('general', 'dem_db'))

    @dem_db.setter
    @nodb_setter
    def dem_db(self, value: str) -> None:
        self._dem_db = value

    @property
    def dem_map(self) -> Optional[str]:
        if not hasattr(self, '_dem_map'):
            return None

        return self._dem_map

    @dem_map.setter
    @nodb_setter
    def dem_map(self, value: str) -> None:
        self._dem_map = value

    @property
    def dem_is_vrt(self) -> bool:
        return bool(getattr(self, "_dem_is_vrt", False))

    @property
    def dem_fn(self) -> str:
        ext = "vrt" if self.dem_is_vrt else "tif"
        return _join(self.dem_dir, f"dem.{ext}")

    @property
    def crop_window(self) -> Optional[Tuple[int, int, int, int]]:
        return getattr(self, "_crop_window", None)

    @property
    def crop_reference_geotransform(self) -> Optional[Tuple[float, float, float, float, float, float]]:
        return getattr(self, "_crop_reference_geotransform", None)

    @property
    def crop_reference_shape(self) -> Optional[Tuple[int, int]]:
        return getattr(self, "_crop_reference_shape", None)

    #
    # dem
    #
    def fetch_dem(self) -> None:
        assert self.map is not None
        self._dem_is_vrt = False

        dem_db = self.dem_db.strip()
        dem_db_l = dem_db.lower()

        if dem_db_l.startswith("copernicus://"):
            self._fetch_copernicus_dem()
        elif dem_db_l.startswith('opentopo://'):
            self._fetch_opentopo_dem()
        else:
            wmesque_retrieve(self.dem_db, self.map.extent,
                             self.dem_fn, self.map.cellsize,
                             v=self.wmesque_version, wmesque_endpoint=self.wmesque_endpoint)

        assert _exists(self.dem_fn)
        update_catalog_entry(self.wd, self.dem_fn)

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.fetch_dem)
        except FileNotFoundError:
            pass

    def _fetch_copernicus_dem(self) -> None:
        assert self.map is not None

        copernicus_error_message: Optional[str] = None

        try:
            copernicus_retrieve(
                self.map.extent,
                self.dem_fn,
                self.map.cellsize,
                dataset=self.dem_db,
                resample='bilinear',
            )
            return
        except CopernicusConfigurationError:
            raise
        except CopernicusRetryableError as exc:
            fallback_dataset = self._parse_nonempty_str_env(
                "COPERNICUS_OPENTOPO_FALLBACK_DATASET",
                _COPERNICUS_DEFAULT_OPENTOPO_FALLBACK_DATASET,
            )
            fallback_dem_db = f"opentopo://{fallback_dataset}"
            copernicus_error_message = str(exc)
            self.logger.warning(
                "Copernicus DEM retrieval failed for dem_db=%s (run=%s, error=%s). "
                "Falling back to OpenTopography dataset=%s.",
                self.dem_db,
                self.wd,
                exc,
                fallback_dem_db,
            )

        try:
            self._fetch_opentopo_dem(dem_db_override=fallback_dem_db)
        except (RuntimeError, AssertionError, OSError) as fallback_exc:
            raise RuntimeError(
                "Copernicus DEM retrieval failed and OpenTopography fallback failed "
                f"(copernicus_error={copernicus_error_message}, "
                f"fallback_dem_db={fallback_dem_db}, fallback_error={fallback_exc})."
            ) from fallback_exc

    def _fetch_opentopo_dem(self, dem_db_override: Optional[str] = None) -> None:
        assert self.map is not None

        effective_dem_db = dem_db_override or self.dem_db

        max_requests_per_minute = self._parse_positive_int_env(
            "OPENTOPO_MAX_REQUESTS_PER_MINUTE",
            _OPENTOPO_DEFAULT_MAX_REQUESTS_PER_MINUTE,
        )
        base_block_seconds = self._parse_positive_int_env(
            "OPENTOPO_BLOCK_SECONDS",
            _OPENTOPO_DEFAULT_BLOCK_SECONDS,
        )
        penalty_block_seconds = self._parse_positive_int_env(
            "OPENTOPO_PENALTY_BLOCK_SECONDS",
            _OPENTOPO_DEFAULT_PENALTY_BLOCK_SECONDS,
        )

        conn_kwargs = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
        redis_conn = redis.Redis(**conn_kwargs)
        try:
            self._wait_for_opentopo_slot(
                redis_conn,
                max_requests_per_minute=max_requests_per_minute,
                base_block_seconds=base_block_seconds,
            )
            self.logger.info(
                "OpenTopography rate gate passed (run=%s, dem_db=%s, max_per_min=%s, block_s=%s).",
                self.wd,
                effective_dem_db,
                max_requests_per_minute,
                base_block_seconds,
            )
            try:
                opentopo_retrieve(
                    self.map.extent,
                    self.dem_fn,
                    self.map.cellsize,
                    dataset=effective_dem_db,
                    resample='bilinear',
                )
            except RuntimeError as exc:
                status_code = self._extract_status_code(exc)
                # OpenTopography has been observed returning 401 for throttling
                # responses where 429 would normally be expected.
                if status_code in _OPENTOPO_THROTTLE_STATUS_CODES:
                    now_ts = time.time()
                    blocked_until = self._set_opentopo_block_until(
                        redis_conn,
                        requested_until=now_ts + float(penalty_block_seconds),
                    )
                    self.logger.error(
                        "OpenTopography returned status=%s; applying penalty backoff for %.1fs "
                        "(until=%.3f, run=%s, dem_db=%s, note=401_may_indicate_rate_limit).",
                        status_code,
                        max(0.0, blocked_until - now_ts),
                        blocked_until,
                        self.wd,
                        effective_dem_db,
                    )
                raise
        finally:
            close_fn = getattr(redis_conn, "close", None)
            if callable(close_fn):
                close_fn()

    def _wait_for_opentopo_slot(
        self,
        redis_conn: redis.Redis,
        *,
        max_requests_per_minute: int,
        base_block_seconds: int,
    ) -> None:
        while True:
            now_ts = time.time()
            blocked_until = self._read_blocked_until(redis_conn)
            if blocked_until > now_ts:
                wait_seconds = blocked_until - now_ts
                self.logger.warning(
                    "OpenTopography currently blocked for %.1fs (until=%.3f, run=%s).",
                    wait_seconds,
                    blocked_until,
                    self.wd,
                )
                time.sleep(min(wait_seconds, 30.0))
                continue

            minute_key = f"{_OPENTOPO_MINUTE_KEY_PREFIX}:{int(now_ts // 60)}"
            current_count = int(redis_conn.incr(minute_key))
            if current_count == 1:
                redis_conn.expire(minute_key, 180)

            if current_count <= max_requests_per_minute:
                return

            blocked_until = self._set_opentopo_block_until(
                redis_conn,
                requested_until=now_ts + float(base_block_seconds),
            )
            self.logger.warning(
                "OpenTopography request cap exceeded (%s > %s per minute); blocking for %.1fs "
                "(until=%.3f, run=%s).",
                current_count,
                max_requests_per_minute,
                max(0.0, blocked_until - now_ts),
                blocked_until,
                self.wd,
            )

    def _read_blocked_until(self, redis_conn: redis.Redis) -> float:
        raw = redis_conn.get(_OPENTOPO_BLOCK_UNTIL_KEY)
        if raw in (None, ""):
            return 0.0
        try:
            blocked_until = float(raw)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(blocked_until) or blocked_until <= 0.0:
            return 0.0
        return blocked_until

    def _set_opentopo_block_until(self, redis_conn: redis.Redis, requested_until: float) -> float:
        requested = float(requested_until)
        raw_result = redis_conn.eval(
            _OPENTOPO_BLOCK_UNTIL_MAX_LUA,
            1,
            _OPENTOPO_BLOCK_UNTIL_KEY,
            f"{requested:.3f}",
        )
        try:
            return float(raw_result)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"Unexpected Redis response while updating OpenTopography block key: {raw_result!r}"
            ) from exc

    @staticmethod
    def _parse_positive_int_env(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return default
        return value if value > 0 else default

    @staticmethod
    def _parse_nonempty_str_env(name: str, default: str) -> str:
        raw = os.getenv(name)
        if raw is None:
            return default
        value = raw.strip()
        return value if value else default

    @staticmethod
    def _extract_status_code(exc: Exception) -> Optional[int]:
        def _coerce_http_status(value: Any) -> Optional[int]:
            try:
                status_code = int(value)
            except (TypeError, ValueError):
                return None
            if 100 <= status_code <= 599:
                return status_code
            return None

        status_code = _coerce_http_status(getattr(exc, "status_code", None))
        if status_code is not None:
            return status_code

        response = getattr(exc, "response", None)
        status_code = _coerce_http_status(getattr(response, "status_code", None))
        if status_code is not None:
            return status_code

        match = _OPENTOPO_STATUS_RE.search(str(exc))
        if not match:
            return None
        try:
            return int(match.group(1))
        except (TypeError, ValueError):
            return None

    def symlink_dem(
        self,
        dem_fn: str,
        *,
        as_cropped_vrt: bool = False,
        crop_window: Optional[Tuple[int, int, int, int]] = None,
    ) -> None:
        dem_src = os.path.abspath(dem_fn)
        if not _exists(dem_src):
            raise FileNotFoundError(f"DEM file does not exist: {dem_src}")

        os.makedirs(self.dem_dir, exist_ok=True)

        use_vrt = bool(as_cropped_vrt)
        if use_vrt:
            if crop_window is None:
                crop_window = self.crop_window
            if crop_window is None:
                raise ValueError("Crop window cannot be identified for as_cropped_vrt=True")
            if dem_src.lower().endswith('.vrt'):
                raise ValueError("Cannot create cropped VRT from source DEM that is already a VRT.")

        self._dem_is_vrt = use_vrt
        if use_vrt:
            # Use .vrt extension so WhiteboxTools recognizes the format
            dest = _join(self.dem_dir, "dem.vrt")
            rdi_src = RasterDatasetInterpolator(dem_src)
            src_window = build_windowed_vrt_from_window(
                dem_src,
                dest,
                crop_window,
            )
            crop_reference_geotransform = rdi_src.ds.GetGeoTransform()
            crop_reference_shape = (rdi_src.ds.RasterXSize, rdi_src.ds.RasterYSize)
        else:
            # Use .tif extension for symlinks
            dest = _join(self.dem_dir, "dem.tif")

            if os.path.lexists(dest):
                if os.path.islink(dest):
                    existing = os.path.realpath(dest)
                    if existing != dem_src:
                        os.unlink(dest)
                else:
                    if os.path.samefile(dest, dem_src):
                        pass
                    else:
                        raise FileExistsError(
                            f"DEM path already exists and is not a symlink: {dest}"
                        )

            if not os.path.lexists(dest):
                os.symlink(dem_src, dest)

            src_window = None
            crop_reference_geotransform = None
            crop_reference_shape = None

        rdi = RasterDatasetInterpolator(dest)
        cellsize = abs(rdi.transform[1])
        if cellsize <= 0:
            raise ValueError(f"Invalid DEM cellsize: {cellsize}")
        extent = list(rdi.extent)
        center = [(extent[0] + extent[2]) / 2.0, (extent[1] + extent[3]) / 2.0]
        zoom = getattr(self, "_zoom0", None)
        zoom = int(zoom) if isinstance(zoom, int) else 11

        with self.locked():
            self._cellsize = cellsize
            self._map = Map(extent, center, zoom, cellsize)
            self._w3w = None
            self._crop_window = src_window
            self._crop_reference_geotransform = crop_reference_geotransform
            self._crop_reference_shape = crop_reference_shape

        base = os.path.abspath(self.wd)
        if os.path.commonpath([base, dem_src]) == base:
            update_catalog_entry(self.wd, dest)
        else:
            self.logger.info(
                "Skipping catalog update for external DEM symlink: %s", dem_src
            )

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.fetch_dem)
        except FileNotFoundError:
            pass


    @property
    def has_dem(self) -> bool:
        return _exists(self.dem_fn)

    #
    # summary
    #
    def subs_summary(self, abbreviated: bool = False) -> Dict:
        wd = self.wd
        climate = self.climate_instance

        has_watershed = pick_existing_parquet_path(wd, "watershed/hillslopes.parquet") is not None
        has_soils = pick_existing_parquet_path(wd, "soils/soils.parquet") is not None
        has_landuse = pick_existing_parquet_path(wd, "landuse/landuse.parquet") is not None

        if has_watershed and has_soils and has_landuse:
            
            _watershed_summaries =  get_watershed_subs_summary(wd, return_as_df=False)
            _soils_summaries = get_soil_subs_summary(wd, return_as_df=False)
            _landuse_summaries = get_landuse_subs_summary(wd, return_as_df=False)

            summaries = []
            for topaz_id, wat_ss in _watershed_summaries.items():
                soils_d = _soils_summaries[topaz_id]
                landuse_d = _landuse_summaries[topaz_id]

                summaries.append(
                    dict(meta=dict(hill_type='Hillslope',
                                   topaz_id=topaz_id,
                                   wepp_id=wat_ss['wepp_id']),
                         watershed=wat_ss,
                         soil=soils_d,
                         climate=climate.sub_summary(topaz_id),
                         landuse=landuse_d))
                
            return summaries
        
        # slower deprecated option
        watershed = self.watershed_instance
        translator = watershed.translator_factory()
        soils = self.soils_instance
        climate = self.climate_instance
        landuse = self.landuse_instance

        summaries = []
        for wepp_id in translator.iter_wepp_sub_ids():
            topaz_id = translator.top(wepp=wepp_id)

            summaries.append(
                dict(meta=dict(hill_type='Hillslope',
                               topaz_id=topaz_id,
                               wepp_id=wepp_id),
                     watershed=watershed.sub_summary(topaz_id),
                     soil=soils.sub_summary(topaz_id, abbreviated=abbreviated),
                     climate=climate.sub_summary(topaz_id),
                     landuse=landuse.sub_summary(topaz_id)))

        return summaries

    def sub_summary(
        self, 
        topaz_id: Optional[str] = None, 
        wepp_id: Optional[str] = None
    ) -> Dict:

        wd = self.wd

        _watershed = None
        # use parquet if availablem they are faster and have topaz_id and wepp_id
        if pick_existing_parquet_path(wd, "watershed/hillslopes.parquet") is not None:
            _watershed = get_watershed_sub_summary(wd, topaz_id=topaz_id)

            wepp_id = str(_watershed['wepp_id'])
        else:
            # get Watershed instance
            # and translator to get topaz_id and wepp_id
            watershed = self.watershed_instance
            translator = watershed.translator_factory()

            if topaz_id is None:
                topaz_id = translator.top(wepp=wepp_id)

            if wepp_id is None:
                wepp_id = translator.wepp(top=topaz_id)

            # get watershed summary from hillslopes.csv if it exists
            if _exists(_join(wd, 'watershed/hillslopes.csv')):
                import duckdb
                csv_fn = _join(wd, 'watershed/hillslopes.csv')
                with duckdb.connect() as con:
                    result = con.execute(f"SELECT * FROM read_csv('{csv_fn}') WHERE topaz_id = ?", [topaz_id]).fetchall()
                    
                    columns = [desc[0] for desc in con.description]
                    result = [dict(zip(columns, row)) for row in result]
                    _watershed = result[0]

            # slowest option, but works for all projects
            else:
                _watershed = watershed.sub_summary(topaz_id)

        _soils = None
        if pick_existing_parquet_path(wd, "soils/soils.parquet") is not None:
            _soils = get_soil_sub_summary(wd, topaz_id=topaz_id)
        else:
            soils = self.soils_instance
            _soils = soils.sub_summary(topaz_id)


        _landuse = None
        if pick_existing_parquet_path(wd, "landuse/landuse.parquet") is not None:
            _landuse = get_landuse_sub_summary(wd, topaz_id=topaz_id)
        else:
            landuse = self.landuse_instance
            _landuse = landuse.sub_summary(topaz_id)        

        climate = self.climate_instance

        if not isinstance(_watershed, dict):
            _watershed = _watershed.as_dict()
        return dict(
            meta=dict(hill_type='Hillslope', topaz_id=topaz_id,
                      wepp_id=wepp_id),
            watershed=_watershed,
            soil=_soils,
            climate=climate.sub_summary(topaz_id),
            landuse=_landuse
        )

    def chns_summary(self, abbreviated: bool = False) -> List[Dict]:
        wd = self.wd

        # use parquet if available, they are faster and have topaz_id and wepp_id
        if pick_existing_parquet_path(wd, "watershed/channels.parquet") is not None:
            chns_summary =  get_watershed_chns_summary(wd)

            summaries = []
            for d in chns_summary.values():
                summaries.append(
                    dict(meta=dict(hill_type='Channel',
                               topaz_id=d['topaz_id'],
                               wepp_id=d['wepp_id'],
                               chn_enum=d['chn_enum']),
                     watershed=d
                    )
                )
            return summaries


        # slower deprecated option
        watershed = self.watershed_instance
        translator = watershed.translator_factory()

        summaries = []
        for wepp_id in translator.iter_wepp_chn_ids():
            topaz_id = translator.top(wepp=wepp_id)
            chn_enum = translator.chn_enum(top=topaz_id)

            summaries.append(
                dict(meta=dict(hill_type='Channel',
                               topaz_id=topaz_id,
                               wepp_id=wepp_id,
                               chn_enum=chn_enum),
                     watershed=watershed.chn_summary(topaz_id),
                     soil=None,
                     climate=None,
                     landuse=None)
            )

        return summaries

    def chn_summary(
        self, 
        topaz_id: Optional[str] = None, 
        wepp_id: Optional[str] = None
    ) -> Dict:
        wd = self.wd
        _watershed = None
        if pick_existing_parquet_path(wd, "watershed/channels.parquet") is not None:
            _watershed = get_watershed_chn_summary(wd, topaz_id=topaz_id)
            chn_enum = _watershed['chn_enum']
            wepp_id = _watershed['wepp_id']
        else:
            watershed = self.watershed_instance
            translator = watershed.translator_factory()

            if topaz_id is None:
                topaz_id = translator.top(wepp=wepp_id)

            if wepp_id is None:
                wepp_id = translator.wepp(top=topaz_id)

            elif _exists(_join(wd, 'watershed/channels.csv')): # provide support for older projects without parquet files
                import duckdb
                csv_fn = _join(wd, 'watershed/channels.csv')
                with duckdb.connect() as con:
                    result = con.execute(f"SELECT * FROM read_csv('{csv_fn}') WHERE topaz_id = ?", [topaz_id]).fetchall()
                    
                    columns = [desc[0] for desc in con.description]
                    result = [dict(zip(columns, row)) for row in result]
                    _watershed = result[0]

            else:
                _watershed = watershed.sub_summary(topaz_id)
            
            chn_enum = translator.chn_enum(top=topaz_id)

        return dict(
            meta=dict(hill_type='Channel', topaz_id=topaz_id,
                      wepp_id=wepp_id, chn_enum=chn_enum),
            watershed=_watershed,
            landuse=None,
            soil=None,
            climate=None)
        

def _try_str(x: Any) -> str:
    try:
        return str(x)
    except (TypeError, ValueError):
        return ''

def _try_bool(x: Any) -> bool:
    try:
        return bool(int(x))
    except (TypeError, ValueError, OverflowError):
        return False

# for jinja views
class RonViewModel(object):
    def __init__(self, ron: Ron) -> None:
        self.runid = _try_str(ron.runid)
        self.name = _try_str(ron.name)
        self.scenario = _try_str(ron.scenario)
        self.config_stem = _try_str(ron.config_stem)
        self.readonly = _try_bool(ron.readonly)
        self.public = _try_bool(ron.public)
        self.pup_relpath = ron.pup_relpath
        self.mods = [mod for mod in ron.mods]
        self.nodb_version = read_version(ron.wd)

    @classmethod
    def getInstanceFromRunID(cls, runid: str) -> 'RonViewModel':
        ron = Ron.load_detached_from_runid(runid)
        return cls(ron)
