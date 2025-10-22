from __future__ import annotations

from typing import Optional, Sequence

_hostname: str
REDIS_HOST: str
RQ_DB: int
TIMEOUT: int
DEFAULT_ZOOM: int

def test_run_rq(runid: str) -> tuple[str, ...]: ...

def set_run_readonly_rq(runid: str, readonly: bool) -> None: ...

def init_sbs_map_rq(runid: str, sbs_map: str) -> None: ...

def fetch_dem_rq(
    runid: str,
    extent: Sequence[float],
    center: Optional[Sequence[float]],
    zoom: Optional[int],
) -> None: ...

def build_channels_rq(
    runid: str,
    csa: float,
    mcl: float,
    wbt_fill_or_breach: Optional[str],
    wbt_blc_dist: Optional[int],
) -> None: ...

def fetch_dem_and_build_channels_rq(
    runid: str,
    extent: Sequence[float],
    center: Optional[Sequence[float]],
    zoom: Optional[int],
    csa: float,
    mcl: float,
    wbt_fill_or_breach: Optional[str],
    wbt_blc_dist: Optional[int],
    set_extent_mode: int,
    map_bounds_text: str,
) -> None: ...

def set_outlet_rq(runid: str, outlet_lng: float, outlet_lat: float) -> None: ...

def build_subcatchments_rq(runid: str) -> None: ...

def abstract_watershed_rq(runid: str) -> None: ...

def build_subcatchments_and_abstract_watershed_rq(runid: str) -> None: ...

def build_landuse_rq(runid: str) -> None: ...

def build_soils_rq(runid: str) -> None: ...

def build_climate_rq(runid: str) -> None: ...

def run_ash_rq(
    runid: str,
    fire_date: str,
    ini_white_ash_depth_mm: float,
    ini_black_ash_depth_mm: float,
) -> None: ...

def run_debris_flow_rq(runid: str, *, payload: Optional[dict[str, object]] = ...) -> None: ...

def run_rhem_rq(runid: str) -> None: ...

def _finish_fork_rq(runid: str) -> None: ...

def _clean_env_for_system_tools() -> dict[str, str]: ...

def fork_rq(runid: str, new_runid: str, undisturbify: bool = ...) -> None: ...

def archive_rq(runid: str, comment: Optional[str] = ...) -> None: ...

def restore_archive_rq(runid: str, archive_name: str) -> None: ...

def fetch_and_analyze_rap_ts_rq(runid: str) -> None: ...
