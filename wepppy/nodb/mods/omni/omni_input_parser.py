from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import Omni, OmniScenario, ScenarioDef


class OmniInputParsingService:
    """Parse and normalize Omni scenario and contrast payloads for the facade."""

    def parse_scenarios(
        self,
        omni: "Omni",
        parsed_inputs: Iterable[Tuple["OmniScenario", "ScenarioDef"]],
    ) -> None:
        with omni.locked():
            omni._scenarios = []

            for scenario_enum, params in parsed_inputs:
                scenario_type = params.get("type")
                scenario_key = str(scenario_enum)

                if scenario_key == "thinning":
                    canopy_cover = params.get("canopy_cover")
                    ground_cover = params.get("ground_cover")
                    if not canopy_cover or not ground_cover:
                        raise ValueError("Thinning requires canopy_cover and ground_cover")
                    omni._scenarios.append(
                        {
                            "type": scenario_type,
                            "canopy_cover": canopy_cover,
                            "ground_cover": ground_cover,
                        }
                    )
                elif scenario_key == "mulch":
                    ground_cover_increase = params.get("ground_cover_increase")
                    base_scenario = params.get("base_scenario")
                    if not ground_cover_increase or not base_scenario:
                        raise ValueError("Mulching requires ground_cover_increase and base_scenario")

                    omni._scenarios.append(
                        {
                            "type": scenario_type,
                            "ground_cover_increase": ground_cover_increase,
                            "base_scenario": base_scenario,
                        }
                    )
                elif scenario_key == "sbs_map":
                    sbs_file_path = params.get("sbs_file_path")
                    if not sbs_file_path:
                        raise ValueError("SBS Map requires a file path")
                    omni._scenarios.append(
                        {
                            "type": scenario_type,
                            "sbs_file_path": sbs_file_path,
                        }
                    )
                else:
                    omni._scenarios.append({"type": scenario_type})

    def parse_inputs(self, omni: "Omni", kwds: Dict[str, Any]) -> None:
        with omni.locked():
            control_scenario = kwds.get("omni_control_scenario", None)
            if control_scenario is not None:
                omni._control_scenario = self._normalize_scenario_value(control_scenario)

            contrast_scenario = kwds.get("omni_contrast_scenario", None)
            if contrast_scenario is not None:
                omni._contrast_scenario = self._normalize_scenario_value(contrast_scenario)

            objective_parameter = kwds.get("omni_contrast_objective_parameter", None)
            if objective_parameter is not None:
                omni._contrast_object_param = objective_parameter

            threshold_fraction = kwds.get("omni_contrast_cumulative_obj_param_threshold_fraction", None)
            if threshold_fraction is not None:
                omni._contrast_cumulative_obj_param_threshold_fraction = threshold_fraction

            hillslope_limit = kwds.get("omni_contrast_hillslope_limit", None)
            if hillslope_limit is not None:
                omni._contrast_hillslope_limit = hillslope_limit

            hill_min_slope = kwds.get("omni_contrast_hill_min_slope", None)
            if hill_min_slope is not None:
                omni._contrast_hill_min_slope = hill_min_slope

            hill_max_slope = kwds.get("omni_contrast_hill_max_slope", None)
            if hill_max_slope is not None:
                omni._contrast_hill_max_slope = hill_max_slope

            select_burn_severities = kwds.get("omni_contrast_select_burn_severities", None)
            if select_burn_severities is not None:
                omni._contrast_select_burn_severities = select_burn_severities

            select_topaz_ids = kwds.get("omni_contrast_select_topaz_ids", None)
            if select_topaz_ids is not None:
                omni._contrast_select_topaz_ids = select_topaz_ids

            contrast_selection_mode = kwds.get("omni_contrast_selection_mode", None)
            if contrast_selection_mode is not None:
                omni._contrast_selection_mode = str(contrast_selection_mode)

            contrast_geojson_path = kwds.get("omni_contrast_geojson_path", None)
            if contrast_geojson_path is not None:
                omni._contrast_geojson_path = str(contrast_geojson_path)

            contrast_geojson_name_key = kwds.get("omni_contrast_geojson_name_key", None)
            if contrast_geojson_name_key is not None:
                omni._contrast_geojson_name_key = str(contrast_geojson_name_key)

            contrast_hillslope_groups = kwds.get("omni_contrast_hillslope_groups", None)
            if contrast_hillslope_groups is not None:
                omni._contrast_hillslope_groups = contrast_hillslope_groups

            order_reduction_passes = kwds.get("order_reduction_passes", None)
            if order_reduction_passes is not None:
                omni._contrast_order_reduction_passes = order_reduction_passes

            contrast_pairs = kwds.get("omni_contrast_pairs", None)
            if contrast_pairs is None:
                contrast_pairs = kwds.get("contrast_pairs", None)
            if contrast_pairs is not None:
                omni._contrast_pairs = self.normalize_contrast_pairs(omni, contrast_pairs)

            if "omni_contrast_output_chan_out" in kwds:
                value = self._normalize_bool(kwds.get("omni_contrast_output_chan_out"))
                omni._contrast_output_chan_out = value if value is not None else False
            if "omni_contrast_output_tcr_out" in kwds:
                value = self._normalize_bool(kwds.get("omni_contrast_output_tcr_out"))
                omni._contrast_output_tcr_out = value if value is not None else False
            if "omni_contrast_output_chnwb" in kwds:
                value = self._normalize_bool(kwds.get("omni_contrast_output_chnwb"))
                omni._contrast_output_chnwb = value if value is not None else False
            if "omni_contrast_output_soil_pw0" in kwds:
                value = self._normalize_bool(kwds.get("omni_contrast_output_soil_pw0"))
                omni._contrast_output_soil_pw0 = value if value is not None else False
            if "omni_contrast_output_plot_pw0" in kwds:
                value = self._normalize_bool(kwds.get("omni_contrast_output_plot_pw0"))
                omni._contrast_output_plot_pw0 = value if value is not None else False
            if "omni_contrast_output_ebe_pw0" in kwds:
                value = self._normalize_bool(kwds.get("omni_contrast_output_ebe_pw0"))
                omni._contrast_output_ebe_pw0 = value if value is not None else True

    def normalize_contrast_pairs(self, omni: "Omni", value: Any) -> List[Dict[str, str]]:
        if value in (None, ""):
            return []
        if isinstance(value, dict):
            candidates = [value]
        elif isinstance(value, (list, tuple)):
            candidates = list(value)
        else:
            return []

        normalized: List[Dict[str, str]] = []
        seen: Set[str] = set()
        for entry in candidates:
            if not isinstance(entry, dict):
                continue
            control_raw = entry.get("control_scenario")
            contrast_raw = entry.get("contrast_scenario")
            if control_raw in (None, "") or contrast_raw in (None, ""):
                continue
            control_key = omni._normalize_scenario_key(control_raw)
            contrast_key = omni._normalize_scenario_key(contrast_raw)
            pair_key = f"{control_key}::{contrast_key}"
            if pair_key in seen:
                continue
            normalized.append(
                {
                    "control_scenario": control_key,
                    "contrast_scenario": contrast_key,
                }
            )
            seen.add(pair_key)
        return normalized

    @staticmethod
    def _normalize_scenario_value(value: Any) -> Optional[str]:
        if value is None:
            return None
        from wepppy.nodb.mods.omni.omni import OmniScenario

        if isinstance(value, OmniScenario):
            return str(value)
        if isinstance(value, int):
            try:
                return str(OmniScenario(value))
            except ValueError:
                return str(value)
        return str(value)

    @staticmethod
    def _normalize_bool(value: Any) -> Optional[bool]:
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            token = value.strip().lower()
            if token in {"1", "true", "yes", "on"}:
                return True
            if token in {"0", "false", "no", "off"}:
                return False
        return None
