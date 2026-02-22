from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from wepppy.nodb.mods.omni.omni_contrast_status_report_service import (
    OmniContrastStatusReportService,
)

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import Omni, ScenarioDef


_OMNI_CONTRAST_STATUS_REPORT_SERVICE = OmniContrastStatusReportService()


class OmniBuildRouter:
    """Route Omni build/report facade calls while preserving facade contracts."""

    _SCENARIO_OPTIONAL_SELECTION_MODES = {
        "user_defined_areas",
        "stream_order",
        "user_defined_hillslope_groups",
    }

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
        from wepppy.nodb.mods.omni.omni import (
            _OMNI_SCALING_SERVICE,
            _scenario_name_from_scenario_definition,
        )

        omni.logger.info("build_contrasts")

        selection_mode = _OMNI_SCALING_SERVICE.normalize_selection_mode(
            getattr(omni, "_contrast_selection_mode", None)
        )

        control_scenario = (
            _scenario_name_from_scenario_definition(control_scenario_def)
            if control_scenario_def is not None
            else None
        )
        contrast_scenario = (
            _scenario_name_from_scenario_definition(contrast_scenario_def)
            if contrast_scenario_def is not None
            else None
        )
        if selection_mode not in self._SCENARIO_OPTIONAL_SELECTION_MODES and (
            control_scenario is None
            or contrast_scenario is None
        ):
            raise ValueError(
                "control_scenario_def and contrast_scenario_def are required for contrast builds"
            )

        # Keep persistence ownership at the facade lock boundary.
        with omni.locked():
            omni._contrast_scenario = contrast_scenario
            omni._control_scenario = control_scenario
            omni._contrast_object_param = obj_param
            omni._contrast_cumulative_obj_param_threshold_fraction = (
                contrast_cumulative_obj_param_threshold_fraction
            )
            omni._contrast_hillslope_limit = contrast_hillslope_limit
            omni._contrast_hill_min_slope = hill_min_slope
            omni._contrast_hill_max_slope = hill_max_slope
            omni._contrast_select_burn_severities = select_burn_severities
            omni._contrast_select_topaz_ids = select_topaz_ids
            if contrast_pairs is not None:
                omni._contrast_pairs = omni._normalize_contrast_pairs(contrast_pairs)

        omni._build_contrasts()
        omni._build_contrast_ids_geojson()

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
        # Call through the facade method so existing monkeypatch seams stay stable.
        omni.build_contrasts(
            control_scenario_def=control_scenario_def,
            contrast_scenario_def=contrast_scenario_def,
            obj_param=obj_param,
            contrast_cumulative_obj_param_threshold_fraction=(
                contrast_cumulative_obj_param_threshold_fraction
            ),
            contrast_hillslope_limit=contrast_hillslope_limit,
            hill_min_slope=hill_min_slope,
            hill_max_slope=hill_max_slope,
            select_burn_severities=select_burn_severities,
            select_topaz_ids=select_topaz_ids,
            contrast_pairs=contrast_pairs,
        )
        return self.contrast_status_report(omni)

    def contrast_status_report(self, omni: "Omni") -> Dict[str, Any]:
        return _OMNI_CONTRAST_STATUS_REPORT_SERVICE.contrast_status_report(omni)
