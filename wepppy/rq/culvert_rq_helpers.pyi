from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from wepppy.topo.watershed_collection import WatershedFeature

def _resolve_batch_root(culvert_batch_uuid: str) -> Path: ...

def _load_payload_json(path: Path) -> dict[str, Any]: ...

def _get_dem_cellsize_m(
    payload_metadata: Dict[str, Any],
    dem_path: Path,
) -> Optional[float]: ...

def _get_model_param_int(
    model_parameters: Optional[Dict[str, Any]],
    key: str,
) -> Optional[int]: ...

def _map_order_reduction_passes(
    *,
    cellsize_m: Optional[float],
    flow_accum_threshold: Optional[int],
) -> Optional[int]: ...

def _watershed_area_m2(feature: Optional[WatershedFeature]) -> Optional[float]: ...

def _watershed_area_sqm_property(
    feature: Optional[WatershedFeature],
) -> Optional[float]: ...

def _minimum_watershed_area_error(
    *,
    run_id: str,
    watershed_feature: Optional[WatershedFeature],
    minimum_watershed_area_m2: Optional[float],
    error_type_name: str = ...,
) -> Optional[dict[str, str]]: ...

def _select_watershed_label(feature: Optional[WatershedFeature]) -> Optional[str]: ...

def _get_wepppy_version() -> Optional[str]: ...

