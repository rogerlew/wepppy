from __future__ import annotations

import os
from os.path import exists as _exists
from os.path import join as _join
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import pandas as pd

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import Omni, Ron


class OmniArtifactExportService:
    """Own Omni artifact/report exports while preserving facade call contracts."""

    def build_contrast_ids_geojson(self, omni: "Omni") -> Optional[str]:
        # GeoJSON build remains in facade helpers for now; keep collaborator seam stable.
        return omni._build_contrast_ids_geojson_impl()

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
