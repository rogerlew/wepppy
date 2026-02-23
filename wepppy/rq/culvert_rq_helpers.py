from __future__ import annotations

import json
import math
import os
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Dict, Optional

import rasterio

from wepppy.topo.watershed_collection import WatershedFeature


def _resolve_batch_root(culvert_batch_uuid: str) -> Path:
    culverts_root = Path(os.getenv("CULVERTS_ROOT", "/wc1/culverts")).resolve()
    return culverts_root / culvert_batch_uuid


def _load_payload_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Missing payload file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Payload JSON must be an object: {path}")
    return payload


def _get_dem_cellsize_m(
    payload_metadata: Dict[str, Any],
    dem_path: Path,
) -> Optional[float]:
    dem_meta = payload_metadata.get("dem")
    if isinstance(dem_meta, dict):
        value = dem_meta.get("resolution_m")
        if value is not None:
            try:
                parsed = float(value)
                if parsed > 0:
                    return parsed
            except (TypeError, ValueError):
                pass
    if not dem_path.exists():
        return None
    try:
        with rasterio.open(dem_path) as src:
            res_x, res_y = src.res
            cellsize = abs(res_x) if res_x else abs(res_y)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/culvert_rq_helpers.py:53", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return None
    if cellsize <= 0:
        return None
    return float(cellsize)


def _get_model_param_int(
    model_parameters: Optional[Dict[str, Any]],
    key: str,
) -> Optional[int]:
    if not model_parameters:
        return None
    value = model_parameters.get(key)
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _map_order_reduction_passes(
    *,
    cellsize_m: Optional[float],
    flow_accum_threshold: Optional[int],
) -> Optional[int]:
    if cellsize_m is None or cellsize_m <= 0:
        return None
    if flow_accum_threshold is None or flow_accum_threshold <= 0:
        flow_accum_threshold = 100
    effective_cellsize = cellsize_m * math.sqrt(flow_accum_threshold / 100.0)
    if effective_cellsize <= 1.0:
        return 3
    if effective_cellsize <= 4.0:
        return 2
    return 1


def _watershed_area_m2(feature: Optional[WatershedFeature]) -> Optional[float]:
    if feature is None:
        return None
    props = feature.properties or {}
    value = props.get("area_sqm")
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    return float(feature.area_m2)


def _watershed_area_sqm_property(
    feature: Optional[WatershedFeature],
) -> Optional[float]:
    if feature is None:
        return None
    props = feature.properties or {}
    if "area_sqm" not in props:
        return None
    value = props.get("area_sqm")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _minimum_watershed_area_error(
    *,
    run_id: str,
    watershed_feature: Optional[WatershedFeature],
    minimum_watershed_area_m2: Optional[float],
    error_type_name: str = "WatershedAreaBelowMinimumError",
) -> Optional[dict[str, str]]:
    if minimum_watershed_area_m2 is None or minimum_watershed_area_m2 <= 0:
        return None
    area_sqm = _watershed_area_sqm_property(watershed_feature)
    if area_sqm is None:
        return None
    if area_sqm >= minimum_watershed_area_m2:
        return None
    return {
        "type": error_type_name,
        "message": (
            f"Watershed area {area_sqm:.2f} m^2 below minimum "
            f"{minimum_watershed_area_m2:.2f} m^2 (Point_ID {run_id})"
        ),
    }


def _select_watershed_label(feature: Optional[WatershedFeature]) -> Optional[str]:
    if feature is None:
        return None
    props = feature.properties or {}
    candidates = (
        "watershed_",
        "watershed",
        "Watershed",
        "watershed_name",
        "WatershedName",
        "name",
        "Name",
        "label",
        "Label",
        "id",
        "ID",
    )
    for key in candidates:
        value = props.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    if feature.id is not None:
        text = str(feature.id).strip()
        if text:
            return text
    return None


def _get_wepppy_version() -> Optional[str]:
    try:
        return importlib_metadata.version("wepppy")
    except importlib_metadata.PackageNotFoundError:
        return None

