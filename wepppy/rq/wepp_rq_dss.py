from __future__ import annotations

import contextlib
import json
import os
import shutil
from datetime import datetime
from glob import glob
from os.path import exists as _exists
from os.path import join as _join
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from wepppy.nodb.core import Watershed
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.wepp.interchange.hec_ras_boundary import build_boundary_condition_features
from wepppy.wepp.interchange.hec_ras_buffer import write_hec_buffer_gml

_DSS_CHANNELS_RELATIVE_PATH = ("export", "dss", "dss_channels.geojson")
_FEATURE_TOPAZ_KEYS = ("TopazID", "topaz_id", "topazId", "topaz", "id", "ID")
_BOUNDARY_CONDITION_WIDTH_M = 100.0


def _safe_int(value: Any) -> int | None:
    try:
        candidate = int(str(value))
    except (TypeError, ValueError):
        return None
    return candidate


def _safe_relpath(base: str, target: str | os.PathLike[str]) -> str:
    try:
        return os.path.relpath(str(target), base)
    except (ValueError, TypeError):
        return str(target)


def _cleanup_dss_export_dir(wd: str) -> None:
    dss_export_dir = _join(wd, "export", "dss")
    if _exists(dss_export_dir):
        with contextlib.suppress(OSError):
            shutil.rmtree(dss_export_dir, ignore_errors=False)


def _copy_dss_readme(wd: str, status_channel: Optional[str] = None) -> None:
    """Copy the DSS export README alongside generated artifacts."""
    source = Path(__file__).resolve().parent.parent / "wepp" / "interchange" / "README.dss_export.md"
    if not source.exists():
        return
    dest_dir = Path(wd) / "export" / "dss"
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest_dir / "README.dss_export.md")
        if status_channel is not None:
            StatusMessenger.publish(status_channel, "copied DSS export README\n")
    except OSError:
        # Non-fatal; leave a breadcrumb if the status channel is available.
        if status_channel is not None:
            StatusMessenger.publish(status_channel, "warning: unable to write DSS README\n")


def _resolve_downstream_channel_ids(network: Any, seeds: Iterable[int]) -> set[int]:
    resolved: set[int] = set()
    for seed in seeds:
        numeric = _safe_int(seed)
        if numeric is None or numeric <= 0:
            continue
        resolved.add(numeric)
    if not isinstance(network, dict):
        return resolved

    downstream_map: dict[int, set[int]] = {}
    for downstream_raw, upstream_values in network.items():
        downstream_id = _safe_int(downstream_raw)
        if downstream_id is None or downstream_id <= 0:
            continue
        for upstream_raw in upstream_values or []:
            upstream_id = _safe_int(upstream_raw)
            if (
                upstream_id is None
                or upstream_id <= 0
                or upstream_id == downstream_id
            ):
                continue
            downstream_map.setdefault(upstream_id, set()).add(downstream_id)

    stack = list(resolved)
    while stack:
        current = stack.pop()
        for downstream_id in downstream_map.get(current, ()):
            if downstream_id not in resolved:
                resolved.add(downstream_id)
                stack.append(downstream_id)

    return resolved


def _extract_channel_topaz_id(feature: Dict[str, Any]) -> int | None:
    props = feature.get("properties")
    if not isinstance(props, dict):
        return None
    for key in _FEATURE_TOPAZ_KEYS:
        topaz_id = _safe_int(props.get(key))
        if topaz_id is not None:
            return topaz_id
    return None


def _write_dss_channel_geojson(
    wd: str,
    channel_ids: Optional[list[int]],
    *,
    boundary_width_m: float = _BOUNDARY_CONDITION_WIDTH_M,
) -> None:
    dest_path = _join(wd, *_DSS_CHANNELS_RELATIVE_PATH)

    if channel_ids is not None and not channel_ids:
        with contextlib.suppress(OSError):
            os.remove(dest_path)
        return

    try:
        watershed = Watershed.getInstance(wd)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq_dss.py:125", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return

    channels_geojson = getattr(watershed, "channels_shp", None)
    if not channels_geojson or not _exists(channels_geojson):
        return

    try:
        with open(channels_geojson, "r", encoding="utf-8") as source_fp:
            source_geojson = json.load(source_fp)
    except (OSError, json.JSONDecodeError):
        return

    try:
        network = watershed.network
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq_dss.py:140", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        network = None

    include_ids: set[int]
    downstream_ids: Iterable[int]
    if channel_ids is None:
        include_ids = set()
    else:
        downstream_ids = _resolve_downstream_channel_ids(network, channel_ids)
        include_ids = set(downstream_ids)

    source_features = source_geojson.get("features", [])
    filtered_features = []
    selected_topaz_ids: set[int] = set()
    for feature in source_features:
        topaz_id = _extract_channel_topaz_id(feature)
        if topaz_id is None:
            continue
        if channel_ids is None:
            filtered_features.append(feature)
            include_ids.add(topaz_id)
            selected_topaz_ids.add(topaz_id)
        elif topaz_id in include_ids:
            filtered_features.append(feature)
            selected_topaz_ids.add(topaz_id)

    if not filtered_features:
        with contextlib.suppress(OSError):
            os.remove(dest_path)
        return

    boundary_dir = _join(wd, "export", "dss", "boundaries")
    target_boundary_ids = sorted(include_ids) if include_ids else sorted(selected_topaz_ids)

    boundary_features = build_boundary_condition_features(
        watershed,
        target_boundary_ids,
        boundary_dir,
        boundary_width_m=boundary_width_m,
    )
    boundary_shapefiles: list[str] = []
    if boundary_features:
        pattern = os.path.join(boundary_dir, "bc_*.shp")
        for shp_path in sorted(glob(pattern)):
            boundary_shapefiles.append(_safe_relpath(wd, shp_path))
    buffer_info = None
    if target_boundary_ids:
        boundary_filter = set(channel_ids or []) or None
        buffer_info = write_hec_buffer_gml(
            watershed,
            target_boundary_ids,
            _join(wd, "export", "dss"),
            boundary_channel_ids=boundary_filter,
        )

    output_geojson = dict(source_geojson)
    output_geojson["features"] = filtered_features + boundary_features
    metadata = output_geojson.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    metadata.update(
        {
            "selected_topaz_ids": None if channel_ids is None else sorted(set(channel_ids)),
            "downstream_topaz_ids": sorted(include_ids),
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "boundary_condition_width_m": boundary_width_m,
            "boundary_feature_count": len(boundary_features),
        }
    )
    if boundary_shapefiles:
        metadata["boundary_shapefiles"] = boundary_shapefiles
    if buffer_info:
        metadata["channel_buffer"] = buffer_info
        metadata["floodplain_polygon"] = buffer_info.get("buffer_gml")
        if buffer_info.get("buffer_shapefile"):
            metadata["floodplain_polygon_shp"] = buffer_info["buffer_shapefile"]
    output_geojson["metadata"] = metadata

    dest_dir = os.path.dirname(dest_path)
    os.makedirs(dest_dir, exist_ok=True)
    tmp_path = dest_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as dest_fp:
            json.dump(output_geojson, dest_fp)
        os.replace(tmp_path, dest_path)
    except OSError:
        with contextlib.suppress(OSError):
            os.remove(tmp_path)
