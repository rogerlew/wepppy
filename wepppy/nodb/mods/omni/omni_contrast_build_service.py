from __future__ import annotations

import json
import os
import shutil
from os.path import exists as _exists
from os.path import join as _join
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Set

from wepppy.nodb.core import Ron, Watershed
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import Omni


class OmniContrastBuildService:
    """Own high-complexity contrast builders while preserving facade contracts."""

    @staticmethod
    def _resolve_wbt_raster(wbt_dir: Path, stem: str) -> Path:
        tif_path = wbt_dir / f"{stem}.tif"
        vrt_path = wbt_dir / f"{stem}.vrt"
        if tif_path.exists():
            return tif_path
        if vrt_path.exists():
            return vrt_path
        return tif_path

    @staticmethod
    def _sorted_values(values: Iterable[Any]) -> List[Any]:
        try:
            return sorted(values, key=lambda item: int(item))
        except (TypeError, ValueError):
            return sorted(values)

    @staticmethod
    def _is_stale(path: Path, build_subcatchments_ts: Optional[float]) -> bool:
        if build_subcatchments_ts is None:
            return False
        try:
            return path.stat().st_mtime < build_subcatchments_ts
        except FileNotFoundError:
            return True

    def build_contrasts_stream_order(self, omni: "Omni") -> None:
        from wepppy.nodb.mods.omni.omni import (
            OMNI_REL_DIR,
            _OMNI_MODE_BUILD_SERVICES,
            _prune_stream_order,
            _enforce_user_defined_contrast_limit,
        )

        watershed = Watershed.getInstance(omni.wd)
        if not watershed.delineation_backend_is_wbt:
            raise ValueError("Stream-order pruning requires the WBT delineation backend.")

        contrast_pairs = omni._normalize_contrast_pairs(getattr(omni, "_contrast_pairs", None))
        if not contrast_pairs:
            raise ValueError("omni_contrast_pairs is required for stream-order pruning")

        order_reduction_passes = omni._resolve_order_reduction_passes()

        wbt_dir = Path(getattr(watershed, "wbt_wd", _join(omni.wd, "dem", "wbt")))
        if not wbt_dir.exists():
            raise FileNotFoundError(f"WBT workspace not found: {wbt_dir}")

        flovec_path = self._resolve_wbt_raster(wbt_dir, "flovec")
        netful_path = self._resolve_wbt_raster(wbt_dir, "netful")
        relief_path = self._resolve_wbt_raster(wbt_dir, "relief")
        chnjnt_path = self._resolve_wbt_raster(wbt_dir, "chnjnt")
        bound_path = self._resolve_wbt_raster(wbt_dir, "bound")
        subwta_path = self._resolve_wbt_raster(wbt_dir, "subwta")
        outlet_path = wbt_dir / "outlet.geojson"

        for required_path, label in (
            (flovec_path, "flow vector"),
            (netful_path, "stream network"),
            (relief_path, "relief"),
            (chnjnt_path, "channel junctions"),
            (bound_path, "watershed boundary"),
            (subwta_path, "subwta"),
            (outlet_path, "outlet"),
        ):
            if not required_path.exists():
                raise FileNotFoundError(f"Missing WBT {label} file: {required_path}")

        prep = RedisPrep.getInstance(omni.wd)
        build_subcatchments_ts = prep[TaskEnum.build_subcatchments]

        strahler_path = netful_path.with_name("netful.strahler.tif")
        pruned_streams_path = netful_path.with_name(
            f"netful.pruned_{order_reduction_passes}.tif"
        )
        needs_prune = (
            not strahler_path.exists()
            or not pruned_streams_path.exists()
            or self._is_stale(strahler_path, build_subcatchments_ts)
            or self._is_stale(pruned_streams_path, build_subcatchments_ts)
        )
        if needs_prune:
            _prune_stream_order(
                flovec_path,
                netful_path,
                order_reduction_passes,
                overwrite_netful=False,
            )

        if not strahler_path.exists():
            raise FileNotFoundError(f"Missing Strahler order raster: {strahler_path}")
        if not pruned_streams_path.exists():
            raise FileNotFoundError(f"Missing pruned stream raster: {pruned_streams_path}")

        subwta_pruned_path = wbt_dir / f"subwta.strahler_pruned_{order_reduction_passes}.tif"
        netw_pruned_path = wbt_dir / f"netw.strahler_pruned_{order_reduction_passes}.tsv"
        order_pruned_path = wbt_dir / f"netful.strahler_pruned_{order_reduction_passes}.tif"
        chnjnt_pruned_path = wbt_dir / f"chnjnt.strahler_pruned_{order_reduction_passes}.tif"
        needs_hillslopes = (
            needs_prune
            or not subwta_pruned_path.exists()
            or not netw_pruned_path.exists()
            or self._is_stale(subwta_pruned_path, build_subcatchments_ts)
            or self._is_stale(netw_pruned_path, build_subcatchments_ts)
        )
        if needs_hillslopes:
            from whitebox_tools import WhiteboxTools

            wbt = WhiteboxTools(verbose=False, raise_on_error=True)
            wbt.set_working_dir(str(wbt_dir))
            rebuild_order = (
                needs_prune
                or not order_pruned_path.exists()
                or self._is_stale(order_pruned_path, build_subcatchments_ts)
            )
            if rebuild_order:
                ret = wbt.strahler_stream_order(
                    d8_pntr=str(flovec_path),
                    streams=str(pruned_streams_path),
                    output=str(order_pruned_path),
                    esri_pntr=False,
                    zero_background=False,
                )
                if ret != 0 or not order_pruned_path.exists():
                    raise RuntimeError(
                        "StrahlerStreamOrder failed "
                        f"(flovec={flovec_path}, streams={pruned_streams_path}, output={order_pruned_path})"
                    )
            rebuild_chnjnt = (
                needs_prune
                or not chnjnt_pruned_path.exists()
                or self._is_stale(chnjnt_pruned_path, build_subcatchments_ts)
            )
            if rebuild_chnjnt:
                ret = wbt.stream_junction_identifier(
                    d8_pntr=str(flovec_path),
                    streams=str(pruned_streams_path),
                    output=str(chnjnt_pruned_path),
                )
                if ret != 0 or not chnjnt_pruned_path.exists():
                    raise RuntimeError(
                        "StreamJunctionIdentifier failed "
                        f"(flovec={flovec_path}, streams={pruned_streams_path}, output={chnjnt_pruned_path})"
                    )
            ret = wbt.hillslopes_topaz(
                dem=str(relief_path),
                d8_pntr=str(flovec_path),
                streams=str(pruned_streams_path),
                pour_pts=str(outlet_path),
                watershed=str(bound_path),
                chnjnt=str(chnjnt_pruned_path),
                subwta=str(subwta_pruned_path),
                order=str(order_pruned_path),
                netw=str(netw_pruned_path),
            )
            if ret != 0:
                raise RuntimeError(
                    "hillslopes_topaz failed "
                    f"(subwta={subwta_pruned_path}, netw={netw_pruned_path})"
                )
        if not subwta_pruned_path.exists():
            raise FileNotFoundError(f"Missing stream-order subwta raster: {subwta_pruned_path}")
        if not netw_pruned_path.exists():
            raise FileNotFoundError(f"Missing stream-order netw table: {netw_pruned_path}")

        from wepppyo3.raster_characteristics import identify_mode_single_raster_key
        import numpy as np
        import rasterio

        group_assignments = identify_mode_single_raster_key(
            key_fn=str(subwta_path),
            parameter_fn=str(subwta_pruned_path),
            ignore_channels=True,
        )

        with rasterio.open(subwta_pruned_path) as dataset:
            data = dataset.read(1, masked=True)
        unique_values = np.unique(data.compressed()) if data is not None else []

        group_map: Dict[int, List[str]] = {}
        for raw_value in unique_values:
            try:
                group_value = int(raw_value)
            except (TypeError, ValueError):
                continue
            if group_value <= 0:
                continue
            if str(group_value).endswith("4"):
                continue
            group_map[group_value * 10] = []

        translator = watershed.translator_factory()
        top2wepp = {
            str(k): str(v)
            for k, v in translator.top2wepp.items()
            if not (str(k).endswith("4") or int(k) == 0)
        }
        valid_topaz = set(top2wepp.keys())

        for topaz_id, group_value in group_assignments.items():
            topaz_key = str(topaz_id)
            if topaz_key not in valid_topaz:
                continue
            try:
                group_id = int(group_value)
            except (TypeError, ValueError):
                continue
            if group_id <= 0:
                continue
            if str(group_id).endswith("4"):
                continue
            group_id = group_id * 10
            group_map.setdefault(group_id, []).append(topaz_key)

        _enforce_user_defined_contrast_limit(
            "stream_order",
            len(contrast_pairs),
            len(group_map),
            group_label="stream-order groups",
        )

        with omni.locked():
            omni._contrast_order_reduction_passes = order_reduction_passes
            omni._contrasts = None
            omni._contrast_names = []
            omni._contrast_labels = {}

        sidecar_dir = omni._contrast_sidecar_dir()
        if _exists(sidecar_dir):
            shutil.rmtree(sidecar_dir)
        os.makedirs(sidecar_dir, exist_ok=True)

        contrasts_dir = _join(omni.wd, OMNI_REL_DIR, "contrasts")
        os.makedirs(contrasts_dir, exist_ok=True)
        report_fn = _join(contrasts_dir, "build_report.ndjson")

        contrast_names: List[Optional[str]] = []
        contrast_id = 0

        with open(report_fn, "w", encoding="ascii") as report_fp:
            for group_id in self._sorted_values(group_map.keys()):
                topaz_ids = group_map.get(group_id, [])
                n_hillslopes = len(topaz_ids)
                topaz_set = set(topaz_ids)

                for pair in contrast_pairs:
                    control_key = omni._normalize_scenario_key(pair.get("control_scenario"))
                    contrast_key = omni._normalize_scenario_key(pair.get("contrast_scenario"))
                    control_scenario = None if control_key == str(omni.base_scenario) else control_key
                    contrast_scenario = None if contrast_key == str(omni.base_scenario) else contrast_key

                    contrast_id += 1
                    while len(contrast_names) < contrast_id:
                        contrast_names.append(None)

                    report_entry = {
                        "contrast_id": contrast_id,
                        "control_scenario": control_key,
                        "contrast_scenario": contrast_key,
                        "wepp_id": None,
                        "topaz_id": None,
                        "obj_param": None,
                        "running_obj_param": None,
                        "pct_cumulative": None,
                        "selection_mode": "stream_order",
                        "n_hillslopes": n_hillslopes,
                        "subcatchments_group": group_id,
                    }

                    if n_hillslopes == 0:
                        report_entry["status"] = "skipped"
                        report_fp.write(json.dumps(report_entry) + "\n")
                        continue

                    contrast_name, contrast = _OMNI_MODE_BUILD_SERVICES.build_contrast_mapping(
                        omni,
                        top2wepp=top2wepp,
                        selected_topaz_ids=topaz_set,
                        control_scenario=control_scenario,
                        contrast_scenario=contrast_scenario,
                        contrast_id=contrast_id,
                        control_label=control_key,
                        contrast_label=contrast_key,
                    )

                    contrast_names[contrast_id - 1] = contrast_name
                    omni._write_contrast_sidecar(contrast_id, contrast)
                    report_fp.write(json.dumps(report_entry) + "\n")

        with omni.locked():
            omni._contrasts = None
            omni._contrast_names = contrast_names

    def build_contrasts_user_defined_areas(self, omni: "Omni") -> None:
        from wepppy.nodb.mods.omni.omni import (
            OMNI_REL_DIR,
            _OMNI_MODE_BUILD_SERVICES,
            _enforce_user_defined_contrast_limit,
        )

        geojson_path = getattr(omni, "_contrast_geojson_path", None)
        if not geojson_path:
            raise ValueError("omni_contrast_geojson_path is required for user_defined_areas mode")
        if not _exists(geojson_path):
            raise FileNotFoundError(f"Contrast GeoJSON not found: {geojson_path}")

        contrast_pairs = omni._normalize_contrast_pairs(getattr(omni, "_contrast_pairs", None))
        if not contrast_pairs:
            raise ValueError("omni_contrast_pairs is required for user_defined_areas mode")

        ignored_fields = []
        if omni._contrast_hillslope_limit is not None:
            ignored_fields.append("omni_contrast_hillslope_limit")
        if omni._contrast_hill_min_slope is not None:
            ignored_fields.append("omni_contrast_hill_min_slope")
        if omni._contrast_hill_max_slope is not None:
            ignored_fields.append("omni_contrast_hill_max_slope")
        if omni._contrast_select_burn_severities is not None:
            ignored_fields.append("omni_contrast_select_burn_severities")
        if omni._contrast_select_topaz_ids is not None:
            ignored_fields.append("omni_contrast_select_topaz_ids")
        if ignored_fields:
            omni.logger.info(
                "User-defined contrast selection ignores filters: %s",
                ", ".join(ignored_fields),
            )

        try:
            import geopandas as gpd
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError("geopandas is required for user-defined contrast selection") from exc

        watershed = Watershed.getInstance(omni.wd)
        hillslope_path = watershed.subwta_utm_shp
        if not hillslope_path or not _exists(hillslope_path):
            raise FileNotFoundError("Hillslope polygons not found for user-defined contrasts.")

        hillslope_gdf = gpd.read_file(hillslope_path)
        if hillslope_gdf.empty:
            raise ValueError("No hillslope polygons available for user-defined contrasts.")

        ron = Ron.getInstance(omni.wd)
        project_srid = getattr(ron, "srid", None)
        target_crs = hillslope_gdf.crs
        if target_crs is None:
            if project_srid:
                target_crs = f"EPSG:{project_srid}"
                hillslope_gdf = hillslope_gdf.set_crs(target_crs)
                omni.logger.info(
                    "Hillslope GeoJSON missing CRS; setting to project CRS EPSG:%s",
                    project_srid,
                )
            else:
                raise ValueError("Project CRS unavailable; cannot align contrast GeoJSON.")

        user_gdf = gpd.read_file(geojson_path)
        if user_gdf.empty:
            raise ValueError("Contrast GeoJSON contains no features.")
        if user_gdf.crs is None:
            user_gdf = user_gdf.set_crs(epsg=4326)
            omni.logger.info("Contrast GeoJSON missing CRS; assuming WGS84 (EPSG:4326).")
        if target_crs is None:
            raise ValueError("Target CRS unavailable for user-defined contrasts.")
        user_gdf = user_gdf.to_crs(target_crs)
        _enforce_user_defined_contrast_limit(
            "user_defined_areas",
            len(contrast_pairs),
            len(user_gdf),
            group_label="areas",
        )

        translator = watershed.translator_factory()
        top2wepp = {
            str(k): str(v)
            for k, v in translator.top2wepp.items()
            if not (str(k).endswith("4") or int(k) == 0)
        }

        id_column = None
        for candidate in ("TopazID", "topaz_id", "TOPAZ_ID"):
            if candidate in hillslope_gdf.columns:
                id_column = candidate
                break
        if id_column is None:
            raise ValueError("Hillslope polygons missing a TopazID field.")

        hillslope_lookup: Dict[int, Dict[str, Any]] = {}
        missing_topaz = 0
        for idx, row in hillslope_gdf.iterrows():
            topaz_raw = row.get(id_column)
            if topaz_raw in (None, ""):
                continue
            topaz_id = str(topaz_raw)
            if topaz_id.endswith("4") or topaz_id == "0":
                continue
            if topaz_id not in top2wepp:
                missing_topaz += 1
                continue
            geom = row.geometry
            if geom is None or getattr(geom, "is_empty", False):
                continue
            area = float(getattr(geom, "area", 0.0) or 0.0)
            if area <= 0.0:
                continue
            hillslope_lookup[idx] = {
                "topaz_id": topaz_id,
                "geometry": geom,
                "area": area,
            }

        if missing_topaz:
            omni.logger.info(
                "Skipped %d hillslopes with Topaz IDs missing from translator.",
                missing_topaz,
            )
        if not hillslope_lookup:
            raise ValueError("No valid hillslopes available for user-defined contrasts.")

        sindex = getattr(hillslope_gdf, "sindex", None)
        hill_indices = list(hillslope_lookup.keys())

        existing_signature_map = omni._load_user_defined_signature_map()
        next_id = max(existing_signature_map.values(), default=0) + 1

        name_key = getattr(omni, "_contrast_geojson_name_key", None)

        with omni.locked():
            omni._contrasts = None
            omni._contrast_names = []
            omni._contrast_labels = {}

        sidecar_dir = omni._contrast_sidecar_dir()
        if _exists(sidecar_dir):
            shutil.rmtree(sidecar_dir)
        os.makedirs(sidecar_dir, exist_ok=True)

        contrasts_dir = _join(omni.wd, OMNI_REL_DIR, "contrasts")
        os.makedirs(contrasts_dir, exist_ok=True)
        report_fn = _join(contrasts_dir, "build_report.ndjson")

        contrast_names: List[Optional[str]] = []
        contrast_labels: Dict[int, str] = {}

        with open(report_fn, "w", encoding="ascii") as report_fp:
            for pair_index, pair in enumerate(contrast_pairs, start=1):
                control_key = omni._normalize_scenario_key(pair.get("control_scenario"))
                contrast_key = omni._normalize_scenario_key(pair.get("contrast_scenario"))
                control_scenario = None if control_key == str(omni.base_scenario) else control_key
                contrast_scenario = None if contrast_key == str(omni.base_scenario) else contrast_key

                for feature_index, (_, row) in enumerate(user_gdf.iterrows(), start=1):
                    label = None
                    if name_key:
                        raw_label = row.get(name_key)
                        if raw_label not in (None, ""):
                            label = str(raw_label).strip()
                    if not label:
                        label = str(feature_index)

                    signature = omni._contrast_pair_signature(control_key, contrast_key, label)
                    contrast_id = existing_signature_map.get(signature)
                    if contrast_id is None:
                        contrast_id = next_id
                        next_id += 1
                        existing_signature_map[signature] = contrast_id
                    contrast_labels[contrast_id] = label
                    while len(contrast_names) < contrast_id:
                        contrast_names.append(None)

                    geom = row.geometry
                    selected_topaz: Set[str] = set()
                    if geom is not None and not getattr(geom, "is_empty", False):
                        try:
                            if sindex is not None:
                                candidate_indices = list(sindex.intersection(geom.bounds))
                            else:
                                candidate_indices = hill_indices
                            for idx in candidate_indices:
                                hill = hillslope_lookup.get(idx)
                                if not hill:
                                    continue
                                hill_area = hill["area"]
                                if hill_area <= 0.0:
                                    continue
                                inter_area = float(geom.intersection(hill["geometry"]).area)
                                if inter_area / hill_area >= 0.5:
                                    selected_topaz.add(hill["topaz_id"])
                        except Exception as exc:  # Boundary: malformed user geometry should not abort all features.
                            omni.logger.info(
                                "Failed to evaluate contrast feature %s: %s",
                                feature_index,
                                exc,
                            )

                    report_entry = {
                        "contrast_id": contrast_id,
                        "control_scenario": control_key,
                        "contrast_scenario": contrast_key,
                        "wepp_id": None,
                        "topaz_id": None,
                        "obj_param": None,
                        "running_obj_param": None,
                        "pct_cumulative": None,
                        "selection_mode": "user_defined_areas",
                        "feature_index": feature_index,
                        "area_label": label,
                        "n_hillslopes": len(selected_topaz),
                        "topaz_ids": self._sorted_values(selected_topaz),
                        "pair_index": pair_index,
                    }

                    if not selected_topaz:
                        report_entry["status"] = "skipped"
                        report_fp.write(json.dumps(report_entry) + "\n")
                        continue

                    contrast_name, contrast = _OMNI_MODE_BUILD_SERVICES.build_contrast_mapping(
                        omni,
                        top2wepp=top2wepp,
                        selected_topaz_ids=selected_topaz,
                        control_scenario=control_scenario,
                        contrast_scenario=contrast_scenario,
                        contrast_id=contrast_id,
                    )

                    contrast_names[contrast_id - 1] = contrast_name
                    omni._write_contrast_sidecar(contrast_id, contrast)
                    report_fp.write(json.dumps(report_entry) + "\n")

        with omni.locked():
            omni._contrasts = None
            omni._contrast_names = contrast_names
            omni._contrast_labels = contrast_labels
