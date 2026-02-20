from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Set, Tuple

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import ContrastDependencies, Omni, OmniScenario, ScenarioDef


class OmniStationCatalogService:
    """Resolve Omni scenario/catalog paths and dependency metadata through facade seams."""

    def normalize_landuse_key(self, omni: "Omni", value: Any) -> Optional[str]:
        return omni._normalize_landuse_key_impl(value)

    def load_landuse_key_map(self, omni: "Omni", landuse_wd: str) -> Optional[Dict[int, Optional[str]]]:
        return omni._load_landuse_key_map_impl(landuse_wd)

    def contrast_landuse_skip_reason(
        self,
        omni: "Omni",
        contrast_id: int,
        contrast_name: str,
        *,
        landuse_cache: Optional[Dict[str, Optional[Dict[int, Optional[str]]]]] = None,
    ) -> Optional[str]:
        return omni._contrast_landuse_skip_reason_impl(
            contrast_id,
            contrast_name,
            landuse_cache=landuse_cache,
        )

    def normalize_scenario_key(self, omni: "Omni", name: Optional[Any]) -> str:
        return omni._normalize_scenario_key_impl(name)

    def loss_pw0_path_for_scenario(self, omni: "Omni", scenario_name: Optional[Any]) -> str:
        return omni._loss_pw0_path_for_scenario_impl(scenario_name)

    def interchange_class_data_path_for_scenario(self, omni: "Omni", scenario_name: Optional[Any]) -> str:
        return omni._interchange_class_data_path_for_scenario_impl(scenario_name)

    def year_set_for_scenario(self, omni: "Omni", scenario_name: Optional[Any]) -> Optional[Set[int]]:
        return omni._year_set_for_scenario_impl(scenario_name)

    def scenario_signature(self, omni: "Omni", scenario_def: "ScenarioDef") -> str:
        return omni._scenario_signature_impl(scenario_def)

    def scenario_dependency_target(
        self,
        omni: "Omni",
        scenario: "OmniScenario",
        scenario_def: "ScenarioDef",
    ) -> Optional[str]:
        return omni._scenario_dependency_target_impl(scenario, scenario_def)

    def contrast_dependencies(self, omni: "Omni", contrast_name: str) -> "ContrastDependencies":
        return omni._contrast_dependencies_impl(contrast_name)

    def contrast_scenario_keys(self, omni: "Omni", contrast_name: str) -> Tuple[str, str]:
        return omni._contrast_scenario_keys_impl(contrast_name)
