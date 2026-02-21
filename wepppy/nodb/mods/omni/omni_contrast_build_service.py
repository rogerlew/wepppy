from __future__ import annotations

import json
import os
import shutil
from os.path import exists as _exists
from os.path import join as _join
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

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

    @staticmethod
    def _build_top2wepp_mapping(translator: Any) -> Dict[str, str]:
        return {
            str(k): str(v)
            for k, v in translator.top2wepp.items()
            if not (str(k).endswith("4") or int(k) == 0)
        }

    def _stream_order_contract_refs(
        self,
    ) -> Tuple[str, Any, Callable[..., Any], Callable[..., Any]]:
        from wepppy.nodb.mods.omni.omni import (
            OMNI_REL_DIR,
            _OMNI_MODE_BUILD_SERVICES,
            _enforce_user_defined_contrast_limit,
            _prune_stream_order,
        )

        return (
            OMNI_REL_DIR,
            _OMNI_MODE_BUILD_SERVICES,
            _prune_stream_order,
            _enforce_user_defined_contrast_limit,
        )

    def _stream_order_context(
        self,
        omni: "Omni",
    ) -> Tuple[Any, List[Dict[str, Any]], int, Path]:
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

        return watershed, contrast_pairs, order_reduction_passes, wbt_dir

    def _stream_order_source_paths(self, wbt_dir: Path) -> Dict[str, Path]:
        return {
            "flovec": self._resolve_wbt_raster(wbt_dir, "flovec"),
            "netful": self._resolve_wbt_raster(wbt_dir, "netful"),
            "relief": self._resolve_wbt_raster(wbt_dir, "relief"),
            "chnjnt": self._resolve_wbt_raster(wbt_dir, "chnjnt"),
            "bound": self._resolve_wbt_raster(wbt_dir, "bound"),
            "subwta": self._resolve_wbt_raster(wbt_dir, "subwta"),
            "outlet": wbt_dir / "outlet.geojson",
        }

    @staticmethod
    def _validate_stream_order_source_paths(paths: Dict[str, Path]) -> None:
        for key, label in (
            ("flovec", "flow vector"),
            ("netful", "stream network"),
            ("relief", "relief"),
            ("chnjnt", "channel junctions"),
            ("bound", "watershed boundary"),
            ("subwta", "subwta"),
            ("outlet", "outlet"),
        ):
            required_path = paths[key]
            if not required_path.exists():
                raise FileNotFoundError(f"Missing WBT {label} file: {required_path}")

    @staticmethod
    def _stream_order_build_timestamp(omni: "Omni") -> Optional[float]:
        prep = RedisPrep.getInstance(omni.wd)
        return prep[TaskEnum.build_subcatchments]

    @staticmethod
    def _stream_order_generated_paths(
        netful_path: Path,
        wbt_dir: Path,
        order_reduction_passes: int,
    ) -> Dict[str, Path]:
        return {
            "strahler": netful_path.with_name("netful.strahler.tif"),
            "pruned_streams": netful_path.with_name(f"netful.pruned_{order_reduction_passes}.tif"),
            "subwta_pruned": wbt_dir / f"subwta.strahler_pruned_{order_reduction_passes}.tif",
            "netw_pruned": wbt_dir / f"netw.strahler_pruned_{order_reduction_passes}.tsv",
            "order_pruned": wbt_dir / f"netful.strahler_pruned_{order_reduction_passes}.tif",
            "chnjnt_pruned": wbt_dir / f"chnjnt.strahler_pruned_{order_reduction_passes}.tif",
        }

    def _stream_order_needs_prune(
        self,
        generated_paths: Dict[str, Path],
        build_subcatchments_ts: Optional[float],
    ) -> bool:
        strahler_path = generated_paths["strahler"]
        pruned_streams_path = generated_paths["pruned_streams"]
        return (
            not strahler_path.exists()
            or not pruned_streams_path.exists()
            or self._is_stale(strahler_path, build_subcatchments_ts)
            or self._is_stale(pruned_streams_path, build_subcatchments_ts)
        )

    @staticmethod
    def _maybe_prune_stream_order(
        prune_stream_order: Callable[..., Any],
        source_paths: Dict[str, Path],
        order_reduction_passes: int,
        needs_prune: bool,
    ) -> None:
        if not needs_prune:
            return
        prune_stream_order(
            source_paths["flovec"],
            source_paths["netful"],
            order_reduction_passes,
            overwrite_netful=False,
        )

    @staticmethod
    def _ensure_stream_order_prune_outputs(generated_paths: Dict[str, Path]) -> None:
        strahler_path = generated_paths["strahler"]
        if not strahler_path.exists():
            raise FileNotFoundError(f"Missing Strahler order raster: {strahler_path}")

        pruned_streams_path = generated_paths["pruned_streams"]
        if not pruned_streams_path.exists():
            raise FileNotFoundError(f"Missing pruned stream raster: {pruned_streams_path}")

    def _stream_order_needs_hillslopes(
        self,
        generated_paths: Dict[str, Path],
        needs_prune: bool,
        build_subcatchments_ts: Optional[float],
    ) -> bool:
        return (
            needs_prune
            or not generated_paths["subwta_pruned"].exists()
            or not generated_paths["netw_pruned"].exists()
            or self._is_stale(generated_paths["subwta_pruned"], build_subcatchments_ts)
            or self._is_stale(generated_paths["netw_pruned"], build_subcatchments_ts)
        )

    def _maybe_rebuild_stream_order_hillslopes(
        self,
        *,
        wbt_dir: Path,
        source_paths: Dict[str, Path],
        generated_paths: Dict[str, Path],
        needs_prune: bool,
        build_subcatchments_ts: Optional[float],
        needs_hillslopes: bool,
    ) -> None:
        if not needs_hillslopes:
            return

        from whitebox_tools import WhiteboxTools

        wbt = WhiteboxTools(verbose=False, raise_on_error=True)
        wbt.set_working_dir(str(wbt_dir))

        rebuild_order = (
            needs_prune
            or not generated_paths["order_pruned"].exists()
            or self._is_stale(generated_paths["order_pruned"], build_subcatchments_ts)
        )
        if rebuild_order:
            self._run_strahler_stream_order(wbt, source_paths, generated_paths)

        rebuild_chnjnt = (
            needs_prune
            or not generated_paths["chnjnt_pruned"].exists()
            or self._is_stale(generated_paths["chnjnt_pruned"], build_subcatchments_ts)
        )
        if rebuild_chnjnt:
            self._run_stream_junction_identifier(wbt, source_paths, generated_paths)

        self._run_hillslopes_topaz(wbt, source_paths, generated_paths)

    @staticmethod
    def _run_strahler_stream_order(
        wbt: Any,
        source_paths: Dict[str, Path],
        generated_paths: Dict[str, Path],
    ) -> None:
        flovec_path = source_paths["flovec"]
        pruned_streams_path = generated_paths["pruned_streams"]
        order_pruned_path = generated_paths["order_pruned"]
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

    @staticmethod
    def _run_stream_junction_identifier(
        wbt: Any,
        source_paths: Dict[str, Path],
        generated_paths: Dict[str, Path],
    ) -> None:
        flovec_path = source_paths["flovec"]
        pruned_streams_path = generated_paths["pruned_streams"]
        chnjnt_pruned_path = generated_paths["chnjnt_pruned"]
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

    @staticmethod
    def _run_hillslopes_topaz(
        wbt: Any,
        source_paths: Dict[str, Path],
        generated_paths: Dict[str, Path],
    ) -> None:
        ret = wbt.hillslopes_topaz(
            dem=str(source_paths["relief"]),
            d8_pntr=str(source_paths["flovec"]),
            streams=str(generated_paths["pruned_streams"]),
            pour_pts=str(source_paths["outlet"]),
            watershed=str(source_paths["bound"]),
            chnjnt=str(generated_paths["chnjnt_pruned"]),
            subwta=str(generated_paths["subwta_pruned"]),
            order=str(generated_paths["order_pruned"]),
            netw=str(generated_paths["netw_pruned"]),
        )
        if ret != 0:
            raise RuntimeError(
                "hillslopes_topaz failed "
                f"(subwta={generated_paths['subwta_pruned']}, netw={generated_paths['netw_pruned']})"
            )

    @staticmethod
    def _ensure_stream_order_hillslope_outputs(generated_paths: Dict[str, Path]) -> None:
        subwta_pruned_path = generated_paths["subwta_pruned"]
        if not subwta_pruned_path.exists():
            raise FileNotFoundError(f"Missing stream-order subwta raster: {subwta_pruned_path}")

        netw_pruned_path = generated_paths["netw_pruned"]
        if not netw_pruned_path.exists():
            raise FileNotFoundError(f"Missing stream-order netw table: {netw_pruned_path}")

    @staticmethod
    def _collect_stream_order_group_assignments(
        source_paths: Dict[str, Path],
        generated_paths: Dict[str, Path],
    ) -> Tuple[Dict[str, Any], Iterable[Any]]:
        from wepppyo3.raster_characteristics import identify_mode_single_raster_key
        import numpy as np
        import rasterio

        group_assignments = identify_mode_single_raster_key(
            key_fn=str(source_paths["subwta"]),
            parameter_fn=str(generated_paths["subwta_pruned"]),
            ignore_channels=True,
        )

        with rasterio.open(generated_paths["subwta_pruned"]) as dataset:
            data = dataset.read(1, masked=True)
        unique_values = np.unique(data.compressed()) if data is not None else []
        return group_assignments, unique_values

    @staticmethod
    def _seed_stream_order_group_map(unique_values: Iterable[Any]) -> Dict[int, List[str]]:
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
        return group_map

    @staticmethod
    def _populate_stream_order_group_map(
        group_map: Dict[int, List[str]],
        group_assignments: Dict[str, Any],
        valid_topaz: Set[str],
    ) -> None:
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
            group_map.setdefault(group_id * 10, []).append(topaz_key)

    def _build_stream_order_group_map(
        self,
        watershed: Any,
        source_paths: Dict[str, Path],
        generated_paths: Dict[str, Path],
    ) -> Tuple[Dict[int, List[str]], Dict[str, str]]:
        group_assignments, unique_values = self._collect_stream_order_group_assignments(
            source_paths,
            generated_paths,
        )

        group_map = self._seed_stream_order_group_map(unique_values)

        translator = watershed.translator_factory()
        top2wepp = self._build_top2wepp_mapping(translator)
        self._populate_stream_order_group_map(group_map, group_assignments, set(top2wepp.keys()))

        return group_map, top2wepp

    @staticmethod
    def _reset_stream_order_build_state(omni: "Omni", order_reduction_passes: int) -> None:
        with omni.locked():
            omni._contrast_order_reduction_passes = order_reduction_passes
            omni._contrasts = None
            omni._contrast_names = []
            omni._contrast_labels = {}

    @staticmethod
    def _prepare_report_paths(omni: "Omni", omni_rel_dir: str) -> str:
        sidecar_dir = omni._contrast_sidecar_dir()
        if _exists(sidecar_dir):
            shutil.rmtree(sidecar_dir)
        os.makedirs(sidecar_dir, exist_ok=True)

        contrasts_dir = _join(omni.wd, omni_rel_dir, "contrasts")
        os.makedirs(contrasts_dir, exist_ok=True)
        return _join(contrasts_dir, "build_report.ndjson")

    @staticmethod
    def _append_contrast_name_slot(contrast_names: List[Optional[str]], contrast_id: int) -> None:
        while len(contrast_names) < contrast_id:
            contrast_names.append(None)

    @staticmethod
    def _stream_order_report_entry(
        *,
        contrast_id: int,
        control_key: str,
        contrast_key: str,
        group_id: int,
        n_hillslopes: int,
    ) -> Dict[str, Any]:
        return {
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

    def _write_stream_order_report(
        self,
        *,
        omni: "Omni",
        report_fn: str,
        contrast_pairs: List[Dict[str, Any]],
        group_map: Dict[int, List[str]],
        top2wepp: Dict[str, str],
        mode_build_services: Any,
    ) -> List[Optional[str]]:
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
                    self._append_contrast_name_slot(contrast_names, contrast_id)

                    report_entry = self._stream_order_report_entry(
                        contrast_id=contrast_id,
                        control_key=control_key,
                        contrast_key=contrast_key,
                        group_id=group_id,
                        n_hillslopes=n_hillslopes,
                    )

                    if n_hillslopes == 0:
                        report_entry["status"] = "skipped"
                        report_fp.write(json.dumps(report_entry) + "\n")
                        continue

                    contrast_name, contrast = mode_build_services.build_contrast_mapping(
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

        return contrast_names

    def build_contrasts_stream_order(self, omni: "Omni") -> None:
        (
            omni_rel_dir,
            mode_build_services,
            prune_stream_order,
            enforce_user_defined_contrast_limit,
        ) = self._stream_order_contract_refs()

        watershed, contrast_pairs, order_reduction_passes, wbt_dir = self._stream_order_context(omni)

        source_paths = self._stream_order_source_paths(wbt_dir)
        self._validate_stream_order_source_paths(source_paths)

        build_subcatchments_ts = self._stream_order_build_timestamp(omni)
        generated_paths = self._stream_order_generated_paths(
            source_paths["netful"],
            wbt_dir,
            order_reduction_passes,
        )

        needs_prune = self._stream_order_needs_prune(generated_paths, build_subcatchments_ts)
        self._maybe_prune_stream_order(
            prune_stream_order,
            source_paths,
            order_reduction_passes,
            needs_prune,
        )
        self._ensure_stream_order_prune_outputs(generated_paths)

        needs_hillslopes = self._stream_order_needs_hillslopes(
            generated_paths,
            needs_prune,
            build_subcatchments_ts,
        )
        self._maybe_rebuild_stream_order_hillslopes(
            wbt_dir=wbt_dir,
            source_paths=source_paths,
            generated_paths=generated_paths,
            needs_prune=needs_prune,
            build_subcatchments_ts=build_subcatchments_ts,
            needs_hillslopes=needs_hillslopes,
        )
        self._ensure_stream_order_hillslope_outputs(generated_paths)

        group_map, top2wepp = self._build_stream_order_group_map(
            watershed,
            source_paths,
            generated_paths,
        )
        enforce_user_defined_contrast_limit(
            "stream_order",
            len(contrast_pairs),
            len(group_map),
            group_label="stream-order groups",
        )

        self._reset_stream_order_build_state(omni, order_reduction_passes)
        report_fn = self._prepare_report_paths(omni, omni_rel_dir)

        contrast_names = self._write_stream_order_report(
            omni=omni,
            report_fn=report_fn,
            contrast_pairs=contrast_pairs,
            group_map=group_map,
            top2wepp=top2wepp,
            mode_build_services=mode_build_services,
        )

        with omni.locked():
            omni._contrasts = None
            omni._contrast_names = contrast_names

    def _user_defined_contract_refs(
        self,
    ) -> Tuple[str, Any, Callable[..., Any]]:
        from wepppy.nodb.mods.omni.omni import (
            OMNI_REL_DIR,
            _OMNI_MODE_BUILD_SERVICES,
            _enforce_user_defined_contrast_limit,
        )

        return OMNI_REL_DIR, _OMNI_MODE_BUILD_SERVICES, _enforce_user_defined_contrast_limit

    @staticmethod
    def _require_user_defined_inputs(omni: "Omni") -> Tuple[str, List[Dict[str, Any]]]:
        geojson_path = getattr(omni, "_contrast_geojson_path", None)
        if not geojson_path:
            raise ValueError("omni_contrast_geojson_path is required for user_defined_areas mode")
        if not _exists(geojson_path):
            raise FileNotFoundError(f"Contrast GeoJSON not found: {geojson_path}")

        contrast_pairs = omni._normalize_contrast_pairs(getattr(omni, "_contrast_pairs", None))
        if not contrast_pairs:
            raise ValueError("omni_contrast_pairs is required for user_defined_areas mode")

        return geojson_path, contrast_pairs

    @staticmethod
    def _ignored_user_defined_filters(omni: "Omni") -> List[str]:
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
        return ignored_fields

    @staticmethod
    def _require_geopandas() -> Any:
        try:
            import geopandas as gpd
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError("geopandas is required for user-defined contrast selection") from exc
        return gpd

    @staticmethod
    def _load_hillslope_gdf(omni: "Omni", gpd: Any) -> Tuple[Any, Any]:
        watershed = Watershed.getInstance(omni.wd)
        hillslope_path = watershed.subwta_utm_shp
        if not hillslope_path or not _exists(hillslope_path):
            raise FileNotFoundError("Hillslope polygons not found for user-defined contrasts.")

        hillslope_gdf = gpd.read_file(hillslope_path)
        if hillslope_gdf.empty:
            raise ValueError("No hillslope polygons available for user-defined contrasts.")

        return watershed, hillslope_gdf

    @staticmethod
    def _resolve_target_crs(omni: "Omni", hillslope_gdf: Any) -> Tuple[Any, str]:
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

        if target_crs is None:
            raise ValueError("Target CRS unavailable for user-defined contrasts.")

        return hillslope_gdf, target_crs

    @staticmethod
    def _load_user_defined_gdf(
        omni: "Omni",
        gpd: Any,
        geojson_path: str,
        target_crs: str,
    ) -> Any:
        user_gdf = gpd.read_file(geojson_path)
        if user_gdf.empty:
            raise ValueError("Contrast GeoJSON contains no features.")

        if user_gdf.crs is None:
            user_gdf = user_gdf.set_crs(epsg=4326)
            omni.logger.info("Contrast GeoJSON missing CRS; assuming WGS84 (EPSG:4326).")

        return user_gdf.to_crs(target_crs)

    @staticmethod
    def _resolve_topaz_id_column(hillslope_gdf: Any) -> str:
        for candidate in ("TopazID", "topaz_id", "TOPAZ_ID"):
            if candidate in hillslope_gdf.columns:
                return candidate
        raise ValueError("Hillslope polygons missing a TopazID field.")

    def _build_hillslope_lookup(
        self,
        omni: "Omni",
        hillslope_gdf: Any,
        id_column: str,
        top2wepp: Dict[str, str],
    ) -> Dict[int, Dict[str, Any]]:
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

        return hillslope_lookup

    @staticmethod
    def _reset_user_defined_build_state(omni: "Omni") -> None:
        with omni.locked():
            omni._contrasts = None
            omni._contrast_names = []
            omni._contrast_labels = {}

    @staticmethod
    def _resolve_feature_label(row: Any, name_key: Optional[str], feature_index: int) -> str:
        label = None
        if name_key:
            raw_label = row.get(name_key)
            if raw_label not in (None, ""):
                label = str(raw_label).strip()
        if not label:
            label = str(feature_index)
        return label

    @staticmethod
    def _resolve_or_create_contrast_id(
        existing_signature_map: Dict[str, int],
        signature: str,
        next_id: int,
    ) -> Tuple[int, int]:
        contrast_id = existing_signature_map.get(signature)
        if contrast_id is None:
            contrast_id = next_id
            next_id += 1
            existing_signature_map[signature] = contrast_id
        return contrast_id, next_id

    @staticmethod
    def _selected_topaz_ids_for_feature(
        *,
        geom: Any,
        sindex: Any,
        hill_indices: List[int],
        hillslope_lookup: Dict[int, Dict[str, Any]],
        logger: Any,
        feature_index: int,
    ) -> Set[str]:
        selected_topaz: Set[str] = set()
        if geom is None or getattr(geom, "is_empty", False):
            return selected_topaz

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
            logger.info(
                "Failed to evaluate contrast feature %s: %s",
                feature_index,
                exc,
            )

        return selected_topaz

    def _user_defined_report_entry(
        self,
        *,
        contrast_id: int,
        control_key: str,
        contrast_key: str,
        feature_index: int,
        label: str,
        selected_topaz: Set[str],
        pair_index: int,
    ) -> Dict[str, Any]:
        return {
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

    def _write_user_defined_report(
        self,
        *,
        omni: "Omni",
        report_fn: str,
        contrast_pairs: List[Dict[str, Any]],
        user_gdf: Any,
        top2wepp: Dict[str, str],
        mode_build_services: Any,
        existing_signature_map: Dict[str, int],
        next_id: int,
        name_key: Optional[str],
        sindex: Any,
        hill_indices: List[int],
        hillslope_lookup: Dict[int, Dict[str, Any]],
    ) -> Tuple[List[Optional[str]], Dict[int, str]]:
        contrast_names: List[Optional[str]] = []
        contrast_labels: Dict[int, str] = {}

        with open(report_fn, "w", encoding="ascii") as report_fp:
            for pair_index, pair in enumerate(contrast_pairs, start=1):
                control_key = omni._normalize_scenario_key(pair.get("control_scenario"))
                contrast_key = omni._normalize_scenario_key(pair.get("contrast_scenario"))
                control_scenario = None if control_key == str(omni.base_scenario) else control_key
                contrast_scenario = None if contrast_key == str(omni.base_scenario) else contrast_key

                for feature_index, (_, row) in enumerate(user_gdf.iterrows(), start=1):
                    label = self._resolve_feature_label(row, name_key, feature_index)

                    signature = omni._contrast_pair_signature(control_key, contrast_key, label)
                    contrast_id, next_id = self._resolve_or_create_contrast_id(
                        existing_signature_map,
                        signature,
                        next_id,
                    )

                    contrast_labels[contrast_id] = label
                    self._append_contrast_name_slot(contrast_names, contrast_id)

                    selected_topaz = self._selected_topaz_ids_for_feature(
                        geom=row.geometry,
                        sindex=sindex,
                        hill_indices=hill_indices,
                        hillslope_lookup=hillslope_lookup,
                        logger=omni.logger,
                        feature_index=feature_index,
                    )

                    report_entry = self._user_defined_report_entry(
                        contrast_id=contrast_id,
                        control_key=control_key,
                        contrast_key=contrast_key,
                        feature_index=feature_index,
                        label=label,
                        selected_topaz=selected_topaz,
                        pair_index=pair_index,
                    )

                    if not selected_topaz:
                        report_entry["status"] = "skipped"
                        report_fp.write(json.dumps(report_entry) + "\n")
                        continue

                    contrast_name, contrast = mode_build_services.build_contrast_mapping(
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

        return contrast_names, contrast_labels

    def build_contrasts_user_defined_areas(self, omni: "Omni") -> None:
        (
            omni_rel_dir,
            mode_build_services,
            enforce_user_defined_contrast_limit,
        ) = self._user_defined_contract_refs()

        geojson_path, contrast_pairs = self._require_user_defined_inputs(omni)

        ignored_fields = self._ignored_user_defined_filters(omni)
        if ignored_fields:
            omni.logger.info(
                "User-defined contrast selection ignores filters: %s",
                ", ".join(ignored_fields),
            )

        gpd = self._require_geopandas()

        watershed, hillslope_gdf = self._load_hillslope_gdf(omni, gpd)
        hillslope_gdf, target_crs = self._resolve_target_crs(omni, hillslope_gdf)
        user_gdf = self._load_user_defined_gdf(omni, gpd, geojson_path, target_crs)

        enforce_user_defined_contrast_limit(
            "user_defined_areas",
            len(contrast_pairs),
            len(user_gdf),
            group_label="areas",
        )

        translator = watershed.translator_factory()
        top2wepp = self._build_top2wepp_mapping(translator)

        id_column = self._resolve_topaz_id_column(hillslope_gdf)
        hillslope_lookup = self._build_hillslope_lookup(omni, hillslope_gdf, id_column, top2wepp)
        sindex = getattr(hillslope_gdf, "sindex", None)
        hill_indices = list(hillslope_lookup.keys())

        existing_signature_map = omni._load_user_defined_signature_map()
        next_id = max(existing_signature_map.values(), default=0) + 1
        name_key = getattr(omni, "_contrast_geojson_name_key", None)

        self._reset_user_defined_build_state(omni)
        report_fn = self._prepare_report_paths(omni, omni_rel_dir)

        contrast_names, contrast_labels = self._write_user_defined_report(
            omni=omni,
            report_fn=report_fn,
            contrast_pairs=contrast_pairs,
            user_gdf=user_gdf,
            top2wepp=top2wepp,
            mode_build_services=mode_build_services,
            existing_signature_map=existing_signature_map,
            next_id=next_id,
            name_key=name_key,
            sindex=sindex,
            hill_indices=hill_indices,
            hillslope_lookup=hillslope_lookup,
        )

        with omni.locked():
            omni._contrasts = None
            omni._contrast_names = contrast_names
            omni._contrast_labels = contrast_labels
