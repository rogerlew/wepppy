from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import Omni, ScenarioDef


class OmniBuildRouter:
    """Route Omni build/report facade calls to orchestration implementations."""

    def build_contrasts(
        self,
        omni: "Omni",
        *,
        control_scenario_def: Optional["ScenarioDef"],
        contrast_scenario_def: Optional["ScenarioDef"],
        obj_param: str,
        contrast_cumulative_obj_param_threshold_fraction: float,
        contrast_hillslope_limit: Optional[int],
        hill_min_slope: Optional[float],
        hill_max_slope: Optional[float],
        select_burn_severities: Optional[List[int]],
        select_topaz_ids: Optional[List[int]],
        contrast_pairs: Optional[List[Dict[str, str]]],
    ) -> None:
        omni._build_contrasts_router_impl(
            control_scenario_def=control_scenario_def,
            contrast_scenario_def=contrast_scenario_def,
            obj_param=obj_param,
            contrast_cumulative_obj_param_threshold_fraction=contrast_cumulative_obj_param_threshold_fraction,
            contrast_hillslope_limit=contrast_hillslope_limit,
            hill_min_slope=hill_min_slope,
            hill_max_slope=hill_max_slope,
            select_burn_severities=select_burn_severities,
            select_topaz_ids=select_topaz_ids,
            contrast_pairs=contrast_pairs,
        )

    def build_contrasts_dry_run_report(
        self,
        omni: "Omni",
        *,
        control_scenario_def: Optional["ScenarioDef"],
        contrast_scenario_def: Optional["ScenarioDef"],
        obj_param: str,
        contrast_cumulative_obj_param_threshold_fraction: float,
        contrast_hillslope_limit: Optional[int],
        hill_min_slope: Optional[float],
        hill_max_slope: Optional[float],
        select_burn_severities: Optional[List[int]],
        select_topaz_ids: Optional[List[int]],
        contrast_pairs: Optional[List[Dict[str, str]]],
    ) -> Dict[str, Any]:
        return omni._build_contrasts_dry_run_report_impl(
            control_scenario_def=control_scenario_def,
            contrast_scenario_def=contrast_scenario_def,
            obj_param=obj_param,
            contrast_cumulative_obj_param_threshold_fraction=contrast_cumulative_obj_param_threshold_fraction,
            contrast_hillslope_limit=contrast_hillslope_limit,
            hill_min_slope=hill_min_slope,
            hill_max_slope=hill_max_slope,
            select_burn_severities=select_burn_severities,
            select_topaz_ids=select_topaz_ids,
            contrast_pairs=contrast_pairs,
        )

    def contrast_status_report(self, omni: "Omni") -> Dict[str, Any]:
        return omni._contrast_status_report_impl()
