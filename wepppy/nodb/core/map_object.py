"""NoDb map geometry model used by RON and outlet validation paths.

This module isolates the map extent/UTM/pixel conversion logic so callers can
import a focused type rather than the full Ron controller.
"""

from __future__ import annotations

import json
import math
from os.path import exists as _exists
from typing import Any, Dict, List, Optional, Tuple

import utm

from wepppy.all_your_base.geo import haversine, read_raster, utm_srid

__all__ = ["Map"]

_LEGACY_MAP_OBJECT_PATH = "wepppy.nodb.core.ron.Map"


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
            # Preserve legacy object path for serialized compatibility across
            # existing run artifacts and browser payload consumers.
            "py/object": _LEGACY_MAP_OBJECT_PATH,
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

