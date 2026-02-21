from __future__ import annotations

import json
import os
from os.path import exists as _exists
from os.path import join as _join
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Set, Tuple

import pandas as pd

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import Omni, Ron


class OmniArtifactExportService:
    """Own Omni artifact/report exports while preserving facade call contracts."""

    def build_contrast_ids_geojson(self, omni: "Omni") -> Optional[str]:
        from wepppy.nodb.core import Watershed

        selection_mode = self._normalize_selection_mode(getattr(omni, "_contrast_selection_mode", None))
        report_entries = omni._load_contrast_build_report()
        selections, stream_groups = self._collect_geojson_sources(selection_mode, report_entries)

        output_path = omni._contrast_ids_geojson_path()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if selection_mode == "stream_order":
            return self._build_stream_order_contrast_geojson(
                omni,
                watershed_cls=Watershed,
                output_path=output_path,
                stream_groups=stream_groups,
                selection_mode=selection_mode,
            )

        if selection_mode == "user_defined_areas":
            return self._build_user_defined_area_contrast_geojson(
                omni,
                watershed_cls=Watershed,
                output_path=output_path,
                selections=selections,
                selection_mode=selection_mode,
            )

        if not selections:
            self._write_feature_collection(output_path, [])
            return output_path

        try:
            import geopandas as gpd
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError("geopandas is required for contrast overlay GeoJSON.") from exc

        watershed = Watershed.getInstance(omni.wd)
        hillslope_path = getattr(watershed, "subwta_shp", None)
        if not hillslope_path or not _exists(hillslope_path):
            raise FileNotFoundError("Hillslope polygons not found for contrast overlay GeoJSON.")

        hillslope_gdf = gpd.read_file(hillslope_path)
        if hillslope_gdf.empty:
            raise ValueError("No hillslope polygons available for contrast overlay GeoJSON.")

        id_column = None
        for candidate in ("TopazID", "topaz_id", "TOPAZ_ID"):
            if candidate in hillslope_gdf.columns:
                id_column = candidate
                break
        if id_column is None:
            raise ValueError("Hillslope polygons missing a TopazID field.")

        hillslope_lookup: Dict[str, Any] = {}
        for _, row in hillslope_gdf.iterrows():
            topaz_raw = row.get(id_column)
            if topaz_raw in (None, ""):
                continue
            topaz_id = str(topaz_raw)
            if topaz_id == "0" or topaz_id.endswith("4"):
                continue
            geom = row.geometry
            if geom is None or getattr(geom, "is_empty", False):
                continue
            hillslope_lookup[topaz_id] = geom

        if not hillslope_lookup:
            raise ValueError("No valid hillslope polygons available for contrast overlay GeoJSON.")

        from shapely.geometry import mapping
        from shapely.ops import unary_union

        features: List[Dict[str, Any]] = []
        missing_topaz: Set[str] = set()
        for label, topaz_ids, extra in selections:
            geoms = []
            for topaz_id in topaz_ids:
                geom = hillslope_lookup.get(topaz_id)
                if geom is None:
                    missing_topaz.add(topaz_id)
                    continue
                geoms.append(geom)
            if not geoms:
                continue
            merged = unary_union(geoms)
            if merged is None or getattr(merged, "is_empty", False):
                continue
            props = {"contrast_label": label, "label": label, "selection_mode": selection_mode}
            props.update(extra)
            features.append(
                {
                    "type": "Feature",
                    "properties": props,
                    "geometry": mapping(merged),
                }
            )

        if missing_topaz:
            omni.logger.info(
                "Contrast overlay GeoJSON skipped %d hillslopes missing geometry.",
                len(missing_topaz),
            )

        self._write_feature_collection(output_path, features)
        return output_path

    def _build_stream_order_contrast_geojson(
        self,
        omni: "Omni",
        *,
        watershed_cls: Any,
        output_path: str,
        stream_groups: Dict[int, Dict[str, Any]],
        selection_mode: str,
    ) -> str:
        if not stream_groups:
            self._write_feature_collection(output_path, [])
            return output_path

        try:
            import rasterio
            from rasterio.features import shapes
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError("rasterio is required for stream-order contrast overlay GeoJSON.") from exc
        try:
            from shapely.geometry import shape
            from shapely.ops import unary_union
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError("shapely is required for stream-order contrast overlay GeoJSON.") from exc

        watershed = watershed_cls.getInstance(omni.wd)
        order_reduction_passes = omni._resolve_order_reduction_passes()
        wbt_dir = Path(getattr(watershed, "wbt_wd", _join(omni.wd, "dem", "wbt")))
        subwta_pruned_path = wbt_dir / f"subwta.strahler_pruned_{order_reduction_passes}.tif"
        if not subwta_pruned_path.exists():
            raise FileNotFoundError(f"Missing stream-order subwta raster: {subwta_pruned_path}")

        group_values: Dict[int, int] = {}
        for group_id in self._sorted_keys(stream_groups.keys()):
            try:
                group_id_int = int(group_id)
            except (TypeError, ValueError):
                continue
            raw_value = group_id_int // 10 if group_id_int % 10 == 0 else group_id_int
            if raw_value <= 0:
                continue
            group_values[raw_value] = group_id_int
        if not group_values:
            self._write_feature_collection(output_path, [])
            return output_path

        geometries: Dict[int, List[Any]] = {key: [] for key in group_values}
        crs = None
        with rasterio.open(subwta_pruned_path) as dataset:
            data = dataset.read(1, masked=True)
            transform = dataset.transform
            crs = dataset.crs
            mask = None
            if hasattr(data, "mask"):
                mask = ~data.mask
            for geom, value in shapes(data, mask=mask, transform=transform):
                try:
                    value_int = int(value)
                except (TypeError, ValueError):
                    continue
                if value_int not in group_values:
                    continue
                geometries[value_int].append(shape(geom))

        features: List[Dict[str, Any]] = []
        for raw_value in self._sorted_keys(group_values.keys()):
            geoms = geometries.get(raw_value, [])
            if not geoms:
                continue
            merged = unary_union(geoms)
            if merged is None or getattr(merged, "is_empty", False):
                continue
            group_id = group_values[raw_value]
            label = str(group_id)
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "contrast_label": label,
                        "label": label,
                        "selection_mode": selection_mode,
                        "subcatchments_group": group_id,
                    },
                    "geometry": merged.__geo_interface__,
                }
            )

        self._write_projected_feature_collection(output_path, features, crs=crs)
        return output_path

    def _build_user_defined_area_contrast_geojson(
        self,
        omni: "Omni",
        *,
        watershed_cls: Any,
        output_path: str,
        selections: List[Tuple[str, Set[str], Dict[str, Any]]],
        selection_mode: str,
    ) -> str:
        if not selections:
            self._write_feature_collection(output_path, [])
            return output_path

        try:
            import numpy as np
            import rasterio
            from rasterio.features import shapes
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError("rasterio is required for user-defined contrast overlay GeoJSON.") from exc
        try:
            from shapely.geometry import shape
            from shapely.ops import unary_union
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError("shapely is required for user-defined contrast overlay GeoJSON.") from exc

        watershed = watershed_cls.getInstance(omni.wd)
        subwta_path = getattr(watershed, "subwta", None)
        if not subwta_path or not _exists(subwta_path):
            raise FileNotFoundError("Hillslope raster not found for user-defined contrast overlay GeoJSON.")

        with rasterio.open(subwta_path) as dataset:
            data = dataset.read(1, masked=True)
            transform = dataset.transform
            crs = dataset.crs
            data_array = data
            base_mask = None
            if hasattr(data, "mask"):
                base_mask = ~data.mask
                data_array = data.data

        features: List[Dict[str, Any]] = []
        for label, topaz_ids, extra in selections:
            topaz_values: List[int] = []
            for topaz_id in topaz_ids:
                try:
                    topaz_values.append(int(topaz_id))
                except (TypeError, ValueError):
                    continue
            if not topaz_values:
                continue
            mask = np.isin(data_array, topaz_values)
            if base_mask is not None:
                mask = mask & base_mask
            if not mask.any():
                continue
            geoms = [shape(geom) for geom, _ in shapes(data_array, mask=mask, transform=transform)]
            if not geoms:
                continue
            merged = unary_union(geoms)
            if merged is None or getattr(merged, "is_empty", False):
                continue
            props = {"contrast_label": label, "label": label, "selection_mode": selection_mode}
            props.update(extra)
            features.append(
                {
                    "type": "Feature",
                    "properties": props,
                    "geometry": merged.__geo_interface__,
                }
            )

        self._write_projected_feature_collection(output_path, features, crs=crs)
        return output_path

    def _collect_geojson_sources(
        self,
        selection_mode: str,
        report_entries: List[Dict[str, Any]],
    ) -> Tuple[List[Tuple[str, Set[str], Dict[str, Any]]], Dict[int, Dict[str, Any]]]:
        selections: List[Tuple[str, Set[str], Dict[str, Any]]] = []
        stream_groups: Dict[int, Dict[str, Any]] = {}

        if selection_mode == "user_defined_areas":
            feature_map: Dict[Any, Tuple[str, Set[str], Dict[str, Any]]] = {}
            for entry in report_entries:
                if entry.get("selection_mode") != "user_defined_areas":
                    continue
                feature_index = entry.get("feature_index")
                if feature_index in (None, ""):
                    continue
                try:
                    feature_key: Any = int(feature_index)
                except (TypeError, ValueError):
                    feature_key = str(feature_index)
                if feature_key in feature_map:
                    continue
                topaz_ids = entry.get("topaz_ids") or []
                topaz_set = {str(item) for item in topaz_ids if item not in (None, "")}
                if not topaz_set:
                    continue
                label = str(feature_key)
                feature_map[feature_key] = (label, topaz_set, {"feature_index": feature_key})
            for key in self._sorted_keys(feature_map.keys()):
                selections.append(feature_map[key])
            return selections, stream_groups

        if selection_mode == "user_defined_hillslope_groups":
            group_map: Dict[Any, Tuple[str, Set[str], Dict[str, Any]]] = {}
            for entry in report_entries:
                if entry.get("selection_mode") != "user_defined_hillslope_groups":
                    continue
                group_index = entry.get("group_index")
                if group_index in (None, ""):
                    continue
                try:
                    group_key: Any = int(group_index)
                except (TypeError, ValueError):
                    group_key = str(group_index)
                if group_key in group_map:
                    continue
                topaz_ids = entry.get("topaz_ids") or []
                topaz_set = {str(item) for item in topaz_ids if item not in (None, "")}
                if not topaz_set:
                    continue
                label = str(group_key)
                group_map[group_key] = (label, topaz_set, {"group_index": group_key})
            for key in self._sorted_keys(group_map.keys()):
                selections.append(group_map[key])
            return selections, stream_groups

        if selection_mode == "stream_order":
            group_map: Dict[Any, Dict[str, Any]] = {}
            for entry in report_entries:
                if entry.get("selection_mode") != "stream_order":
                    continue
                group_value = entry.get("subcatchments_group")
                if group_value in (None, ""):
                    continue
                try:
                    group_key: Any = int(group_value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Invalid subcatchments_group: {group_value!r}") from exc
                if group_key in group_map:
                    continue
                if entry.get("status") == "skipped" or entry.get("n_hillslopes") in (None, 0, 0.0):
                    continue
                group_map[group_key] = entry
            for key in self._sorted_keys(group_map.keys()):
                stream_groups[int(key)] = group_map[key]
            return selections, stream_groups

        seen: Set[str] = set()
        for entry in report_entries:
            entry_mode = entry.get("selection_mode")
            if entry_mode not in (None, "", "cumulative"):
                continue
            topaz_id = entry.get("topaz_id")
            if topaz_id in (None, ""):
                continue
            label = str(topaz_id)
            if label in seen:
                continue
            seen.add(label)
            try:
                topaz_value: Any = int(topaz_id)
            except (TypeError, ValueError):
                topaz_value = label
            selections.append((label, {label}, {"topaz_id": topaz_value}))
        return selections, stream_groups

    @staticmethod
    def _normalize_selection_mode(raw_selection_mode: Optional[str]) -> str:
        selection_mode = (raw_selection_mode or "cumulative").strip().lower()
        if selection_mode in {"stream_order_pruning", "stream-order-pruning"}:
            return "stream_order"
        if selection_mode in {"user-defined-hillslope-groups", "user-defined-hillslope-group"}:
            return "user_defined_hillslope_groups"
        return selection_mode

    @staticmethod
    def _sorted_keys(values: Iterable[Any]) -> List[Any]:
        try:
            return sorted(values, key=lambda item: int(item))
        except (TypeError, ValueError):
            return sorted(values, key=lambda item: str(item))

    @staticmethod
    def _write_feature_collection(output_path: str, features: List[Dict[str, Any]]) -> None:
        with open(output_path, "w", encoding="ascii", newline="\n") as fp:
            json.dump({"type": "FeatureCollection", "features": features}, fp, ensure_ascii=True)

    def _write_projected_feature_collection(
        self,
        output_path: str,
        features: List[Dict[str, Any]],
        *,
        crs: Any,
    ) -> None:
        utm_path = output_path.replace(".wgs.geojson", ".utm.geojson")
        payload: Dict[str, Any] = {"type": "FeatureCollection", "features": features}
        if crs:
            payload["crs"] = {"type": "name", "properties": {"name": str(crs)}}
        with open(utm_path, "w", encoding="ascii", newline="\n") as fp:
            json.dump(payload, fp, ensure_ascii=True)
        from wepppy.topo.watershed_abstraction.support import json_to_wgs

        wgs_path = json_to_wgs(utm_path, s_srs=str(crs) if crs else None)
        if wgs_path != output_path:
            os.replace(wgs_path, output_path)

    def scenarios_report(self, omni: "Omni") -> pd.DataFrame:
        from wepppy.nodb.mods.omni.omni import OMNI_REL_DIR

        parquet_files = {}
        base_legacy_path = _join(omni.wd, "wepp", "output", "loss_pw0.out.parquet")
        if _exists(base_legacy_path):
            parquet_files = {str(omni.base_scenario): base_legacy_path}
        base_interchange_path = _join(omni.wd, "wepp", "output", "interchange", "loss_pw0.out.parquet")
        if _exists(base_interchange_path):
            parquet_files = {str(omni.base_scenario): base_interchange_path}

        from wepppy.nodb.mods.omni.omni import _scenario_name_from_scenario_definition

        for scenario_def in omni.scenarios:
            scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            legacy_path = _join(
                omni.wd,
                OMNI_REL_DIR,
                "scenarios",
                scenario_name,
                "wepp",
                "output",
                "loss_pw0.out.parquet",
            )
            if _exists(legacy_path):
                parquet_files[scenario_name] = legacy_path
                continue
            interchange_path = _join(
                omni.wd,
                OMNI_REL_DIR,
                "scenarios",
                scenario_name,
                "wepp",
                "output",
                "interchange",
                "loss_pw0.out.parquet",
            )
            if _exists(interchange_path):
                parquet_files[scenario_name] = interchange_path
                continue

        dfs = []
        for scenario, path in parquet_files.items():
            if not os.path.isfile(path):
                continue
            df = pd.read_parquet(path)
            df["scenario"] = str(scenario)
            dfs.append(df)

        if not dfs:
            return pd.DataFrame(columns=["key", "v", "units", "scenario"])

        combined = pd.concat(dfs, ignore_index=True)
        out_path = _join(omni.omni_dir, "scenarios.out.parquet")
        combined.to_parquet(out_path)
        omni._refresh_catalog(os.path.relpath(out_path, omni.wd))
        return combined

    def contrasts_report(self, omni: "Omni") -> pd.DataFrame:
        from wepppy.nodb.mods.omni.omni import OMNI_REL_DIR

        def _resolve_loss_out_parquet(output_dir: str) -> str:
            interchange_path = _join(output_dir, "interchange", "loss_pw0.out.parquet")
            legacy_path = _join(output_dir, "loss_pw0.out.parquet")
            return interchange_path if _exists(interchange_path) else legacy_path

        def _ensure_value_columns(frame: pd.DataFrame) -> pd.DataFrame:
            needs_v = "v" not in frame.columns and "value" in frame.columns
            needs_value = "value" not in frame.columns and "v" in frame.columns
            if not (needs_v or needs_value):
                return frame
            frame = frame.copy()
            if needs_v:
                frame["v"] = frame["value"]
            if needs_value:
                frame["value"] = frame["v"]
            return frame

        parquet_entries: List[Tuple[int, str, str]] = []
        if not omni.contrast_names:
            return pd.DataFrame(
                columns=["key", "value", "v", "units", "control_scenario", "contrast_topaz_id", "contrast"]
            )

        for contrast_id, contrast_name in enumerate(omni.contrast_names or [], start=1):
            if not contrast_name:
                continue
            output_dir = _join(omni.wd, OMNI_REL_DIR, "contrasts", str(contrast_id), "wepp", "output")
            parquet_entries.append((contrast_id, contrast_name, _resolve_loss_out_parquet(output_dir)))

        dfs = []
        selection_mode = (omni._contrast_selection_mode or "cumulative").strip().lower()
        if selection_mode in {"stream_order_pruning", "stream-order-pruning"}:
            selection_mode = "stream_order"
        if selection_mode in {"user-defined-hillslope-groups", "user-defined-hillslope-group"}:
            selection_mode = "user_defined_hillslope_groups"
        contrast_labels = getattr(omni, "_contrast_labels", None) or {}

        for contrast_id, contrast_name, path in parquet_entries:
            if not os.path.isfile(path):
                continue

            try:
                control_part, contrast_scenario = contrast_name.split("__to__")
                control_scenario, topaz_id = control_part.split(",", maxsplit=1)
            except ValueError:
                continue

            df = _ensure_value_columns(pd.read_parquet(path))
            base_control = control_scenario == "None"
            if base_control:
                control_scenario = str(omni.base_scenario)
            df["control_scenario"] = control_scenario
            if selection_mode == "cumulative":
                df["contrast_topaz_id"] = topaz_id
            if selection_mode == "user_defined_areas":
                label = contrast_labels.get(contrast_id)
                if label is None:
                    label = contrast_labels.get(str(contrast_id))
                df["contrast"] = label or str(contrast_id)
            elif selection_mode == "user_defined_hillslope_groups":
                label = contrast_labels.get(contrast_id)
                if label is None:
                    label = contrast_labels.get(str(contrast_id))
                label_value = label or str(contrast_id)
                df["contrast"] = label_value
                try:
                    df["group_index"] = int(label_value)
                except (TypeError, ValueError):
                    df["group_index"] = label_value
            else:
                df["contrast"] = contrast_name
            df["_contrast_name"] = str(contrast_name)
            df["contrast_id"] = contrast_id

            if selection_mode == "stream_order":
                ctrl_df = df[["key", "v", "units"]].drop_duplicates(subset=["key"])
            else:
                if base_control:
                    ctrl_output_dir = _join(omni.wd, "wepp", "output")
                else:
                    ctrl_output_dir = _join(
                        omni.wd,
                        OMNI_REL_DIR,
                        "scenarios",
                        control_scenario,
                        "wepp",
                        "output",
                    )
                ctrl_parquet = _resolve_loss_out_parquet(ctrl_output_dir)
                if not _exists(ctrl_parquet):
                    raise FileNotFoundError(f"Control scenario parquet file '{ctrl_parquet}' does not exist!")
                ctrl_df = _ensure_value_columns(pd.read_parquet(ctrl_parquet))

            ctrl = (
                ctrl_df[["key", "v", "units"]]
                .drop_duplicates(subset=["key"])
                .rename(columns={"v": "control_v", "units": "control_units"})
            )
            df = df.merge(ctrl, on="key", how="left")

            bad = df[df["control_units"].notna() & (df["units"] != df["control_units"])]
            if not bad.empty:
                omni.logger.info(
                    "WARNING[contrasts_report]: units mismatch for keys -> %s\n",
                    sorted(bad["key"].unique()),
                )

            df["control-contrast_v"] = df["control_v"] - df["v"]
            dfs.append(df)

        if not dfs:
            return pd.DataFrame(columns=["key", "value", "v", "units", "contrast"])

        combined = pd.concat(dfs, ignore_index=True)
        out_path = _join(omni.omni_dir, "contrasts.out.parquet")
        combined.to_parquet(out_path)
        omni._refresh_catalog(os.path.relpath(out_path, omni.wd))
        return combined

    def compile_hillslope_summaries(self, omni: "Omni") -> pd.DataFrame:
        from wepppy.nodb.core import Ron, Wepp
        from wepppy.nodb.mods.omni.omni import OMNI_REL_DIR, _scenario_name_from_scenario_definition
        from wepppy.wepp.reports import HillSummaryReport

        scenario_wds = {str(omni.base_scenario): omni.wd}
        for scenario_def in omni.scenarios:
            scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            scenario_wds[scenario_name] = _join(omni.wd, OMNI_REL_DIR, "scenarios", scenario_name)

        readonly_rons: List[Ron] = []
        try:
            for wd in scenario_wds.values():
                ron = Ron.getInstance(wd)
                if ron.readonly:
                    ron.readonly = False
                    readonly_rons.append(ron)

            dfs = []
            for scenario, wd in scenario_wds.items():
                loss = Wepp.getInstance(wd).report_loss()
                hill_rpt = HillSummaryReport(loss)
                df = hill_rpt.to_dataframe()
                df["scenario"] = scenario
                dfs.append(df)
        finally:
            for ron in readonly_rons:
                try:
                    ron.readonly = True
                except Exception as exc:  # pragma: no cover - best effort restore
                    omni.logger.warning("Failed to restore readonly flag for %s: %s", ron.wd, exc)

        combined = pd.concat(dfs, ignore_index=True)
        combined["Runoff (m^3)"] = combined["Runoff Depth (mm/yr)"] * combined["Landuse Area (ha)"] * 10
        combined["Lateral Flow (m^3)"] = (
            combined["Lateral Flow Depth (mm/yr)"] * combined["Landuse Area (ha)"] * 10
        )
        combined["Baseflow (m^3)"] = combined["Baseflow Depth (mm/yr)"] * combined["Landuse Area (ha)"] * 10

        combined["Soil Loss (t)"] = (
            combined["Soil Loss Density (kg/ha/yr)"] * combined["Landuse Area (ha)"] / 1_000
        )
        combined["Sediment Deposition (t)"] = (
            combined["Sediment Deposition Density (kg/ha/yr)"] * combined["Landuse Area (ha)"] / 1_000
        )
        combined["Sediment Yield (t)"] = (
            combined["Sediment Yield Density (kg/ha/yr)"] * combined["Landuse Area (ha)"] / 1_000
        )
        combined["NTU (g/L)"] = (
            combined["Sediment Yield (t)"] * 1_000
        ) / (combined["Runoff (m^3)"] + combined["Baseflow (m^3)"])

        out_path = _join(omni.omni_dir, "scenarios.hillslope_summaries.parquet")
        combined.to_parquet(out_path)
        omni._refresh_catalog(os.path.relpath(out_path, omni.wd))
        return combined

    def compile_channel_summaries(self, omni: "Omni") -> pd.DataFrame:
        from wepppy.nodb.core import Ron, Wepp
        from wepppy.nodb.mods.omni.omni import OMNI_REL_DIR, _scenario_name_from_scenario_definition
        from wepppy.wepp.reports import ChannelSummaryReport

        scenario_wds = {str(omni.base_scenario): omni.wd}
        for scenario_def in omni.scenarios:
            scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            scenario_wds[scenario_name] = _join(omni.wd, OMNI_REL_DIR, "scenarios", scenario_name)

        readonly_rons: List[Ron] = []
        try:
            for wd in scenario_wds.values():
                ron = Ron.getInstance(wd)
                if ron.readonly:
                    ron.readonly = False
                    readonly_rons.append(ron)

            dfs = []
            for scenario, wd in scenario_wds.items():
                loss = Wepp.getInstance(wd).report_loss()
                channel_rpt = ChannelSummaryReport(loss)
                df = channel_rpt.to_dataframe()
                df["scenario"] = scenario
                dfs.append(df)
        finally:
            for ron in readonly_rons:
                try:
                    ron.readonly = True
                except Exception as exc:  # pragma: no cover - best effort restore
                    omni.logger.warning("Failed to restore readonly flag for %s: %s", ron.wd, exc)

        if not dfs:
            return pd.DataFrame()

        combined = pd.concat(dfs, ignore_index=True)
        out_path = _join(omni.omni_dir, "scenarios.channel_summaries.parquet")
        combined.to_parquet(out_path)
        omni._refresh_catalog(os.path.relpath(out_path, omni.wd))
        return combined
