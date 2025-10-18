from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Tuple

from wepppy.nodb.core.watershed import Outlet

_outlet_template_geojson: str
_multi_outlet_template_geojson: str
_point_template_geojson: str


def isfloat(value: Any) -> bool: ...

def remove_if_exists(path: str) -> None: ...

def build_step(step_name: Optional[str] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...


class WhiteboxToolsTopazEmulator:
    wbt_wd: str
    verbose: bool
    mcl: Optional[float]
    csa: Optional[float]
    cellsize: float
    num_cols: int
    num_rows: int
    epsg: int
    utm_zone: int
    hemisphere: str
    transform: list[float]
    minimum_elevation: float
    maximum_elevation: float
    ul_x: float
    ul_y: float
    ur_x: float
    ur_y: float
    lr_x: float
    lr_y: float
    ll_x: float
    ll_y: float

    def __init__(
        self,
        wbt_wd: str,
        dem_fn: Optional[str] = None,
        verbose: bool = True,
        raise_on_error: bool = True,
        logger: Optional[logging.Logger] = None,
    ) -> None: ...

    @property
    def raise_on_error(self) -> bool: ...

    @raise_on_error.setter
    def raise_on_error(self, value: bool) -> None: ...

    def register_build_hook(self, step_name: str, hook: Callable[..., None]) -> Callable[..., None]: ...

    def clear_build_hooks(self, step_name: Optional[str] = None) -> None: ...

    @property
    def build_hooks(self) -> Dict[str, Tuple[Callable[..., None], ...]]: ...

    def _execute_build_hooks(
        self,
        step_name: str,
        *,
        result: Any = ...,
        args: tuple[Any, ...] = ...,
        kwargs: Optional[Dict[str, Any]] = ..., 
    ) -> None: ...

    @property
    def wbt(self) -> Any: ...

    @property
    def dem(self) -> str: ...

    @property
    def relief(self) -> str: ...

    @property
    def flovec(self) -> str: ...

    @property
    def floaccum(self) -> str: ...

    @property
    def netful0(self) -> str: ...

    @property
    def netful(self) -> str: ...

    @property
    def netful_json(self) -> str: ...

    @property
    def netful_wgs_json(self) -> str: ...

    @property
    def chnjnt(self) -> str: ...

    @property
    def outlet_geojson(self) -> str: ...

    @property
    def bound(self) -> str: ...

    @property
    def bound_json(self) -> str: ...

    @property
    def bound_wgs_json(self) -> str: ...

    @property
    def aspect(self) -> str: ...

    @property
    def discha(self) -> str: ...

    @property
    def fvslop(self) -> str: ...

    @property
    def netw0(self) -> str: ...

    @property
    def strahler(self) -> str: ...

    @property
    def subwta(self) -> str: ...

    @property
    def netw_tab(self) -> str: ...

    def _parse_dem(self, dem_fn: str, logger: Optional[logging.Logger] = None) -> None: ...

    def _create_relief(
        self,
        fill_or_breach: str = ...,
        blc_dist: Optional[int] = ...,
        logger: Optional[logging.Logger] = None,
    ) -> None: ...

    def _create_flow_vector(self, logger: Optional[logging.Logger] = None) -> None: ...

    def _create_flow_accumulation(self, logger: Optional[logging.Logger] = None) -> None: ...

    def _extract_streams(self, logger: Optional[logging.Logger] = None) -> None: ...

    def _identify_stream_junctions(self, logger: Optional[logging.Logger] = None) -> None: ...

    def delineate_channels(
        self,
        csa: float = ...,
        mcl: float = ...,
        fill_or_breach: str = ...,
        blc_dist: Optional[int] = ...,
        logger: Optional[logging.Logger] = None,
    ) -> None: ...

    def _make_outlet_geojson(
        self,
        dst: Optional[str] = ...,
        easting: Optional[float] = ...,
        northing: Optional[float] = ...,
        logger: Optional[logging.Logger] = None,
    ) -> str: ...

    def _make_multiple_outlets_geojson(
        self,
        dst: str,
        en_points_dict: Dict[int, Tuple[float, float]],
        logger: Optional[logging.Logger] = None,
    ) -> str: ...

    def set_outlet(
        self,
        lng: float,
        lat: float,
        pixelcoords: bool = False,
        logger: Optional[logging.Logger] = None,
    ) -> Outlet: ...

    def set_outlet_from_geojson(
        self,
        geojson_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ) -> Outlet: ...

    def find_closest_channel2(
        self,
        lng: float,
        lat: float,
        pixelcoords: bool = False,
        logger: Optional[logging.Logger] = None,
    ) -> Tuple[Optional[Tuple[int, int]], float]: ...

    def lnglat_to_pixel(
        self,
        lng: float,
        lat: float,
        logger: Optional[logging.Logger] = None,
    ) -> Tuple[int, int]: ...

    def pixel_to_utm(
        self,
        col: int,
        row: int,
        centre: bool = True,
        logger: Optional[logging.Logger] = None,
    ) -> Tuple[float, float]: ...

    def pixel_to_lnglat(
        self,
        x: int,
        y: int,
        logger: Optional[logging.Logger] = None,
    ) -> Tuple[float, float]: ...

    def _create_bound(self, logger: Optional[logging.Logger] = None) -> str: ...

    def _create_aspect(self, logger: Optional[logging.Logger] = None) -> str: ...

    def _create_flow_vector_slope(self, logger: Optional[logging.Logger] = None) -> str: ...

    def _create_netw0(self, logger: Optional[logging.Logger] = None) -> str: ...

    def _create_distance_to_channel(self, logger: Optional[logging.Logger] = None) -> str: ...

    def _create_strahler_order(self, logger: Optional[logging.Logger] = None) -> str: ...

    def _create_subcatchments(self, logger: Optional[logging.Logger] = None) -> str: ...

    @property
    def subwta_json(self) -> str: ...

    @property
    def subcatchments_json(self) -> str: ...

    @property
    def subcatchments_wgs_json(self) -> str: ...

    @property
    def channels_json(self) -> str: ...

    @property
    def channels_wgs_json(self) -> str: ...

    def delineate_subcatchments(self, logger: Optional[logging.Logger] = None) -> None: ...

    def generate_documentation(self, to_readme_md: bool = True, logger: Optional[logging.Logger] = None) -> str: ...

    def _read_chn_order_from_netw_tab(self, logger: Optional[logging.Logger] = None) -> Dict[str, int]: ...

    def _polygonize_channels(self, logger: Optional[logging.Logger] = None) -> None: ...
