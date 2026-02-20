from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import Omni, ObjectiveParameter


class OmniScalingService:
    """Normalize selection/scaling inputs and apply contrast candidate filters."""

    def normalize_selection_mode(self, value: Any) -> str:
        selection_mode = (value or "cumulative").strip().lower()
        if selection_mode in {"stream_order_pruning", "stream-order-pruning"}:
            selection_mode = "stream_order"
        if selection_mode in {"user-defined-hillslope-groups", "user-defined-hillslope-group"}:
            selection_mode = "user_defined_hillslope_groups"
        return selection_mode

    def normalize_hillslope_limit(
        self,
        omni: "Omni",
        *,
        selection_mode: str,
        contrast_hillslope_limit: Optional[Any],
    ) -> Tuple[Optional[int], Optional[int]]:
        contrast_hillslope_limit_max = 100 if selection_mode == "cumulative" else None
        if contrast_hillslope_limit is None:
            return None, contrast_hillslope_limit_max

        try:
            parsed_limit = int(contrast_hillslope_limit)
        except (TypeError, ValueError) as exc:
            raise ValueError("omni_contrast_hillslope_limit must be an integer") from exc

        if parsed_limit <= 0:
            raise ValueError("omni_contrast_hillslope_limit must be >= 1")

        if contrast_hillslope_limit_max is not None and parsed_limit > contrast_hillslope_limit_max:
            omni.logger.warning(
                "omni_contrast_hillslope_limit capped at %d (requested %d).",
                contrast_hillslope_limit_max,
                parsed_limit,
            )
            parsed_limit = contrast_hillslope_limit_max

        return parsed_limit, contrast_hillslope_limit_max

    def normalize_filter_inputs(
        self,
        *,
        contrast_hill_min_slope: Any,
        contrast_hill_max_slope: Any,
        contrast_select_burn_severities: Any,
        contrast_select_topaz_ids: Any,
    ) -> Tuple[Optional[float], Optional[float], Optional[Set[int]], Optional[Set[int]]]:
        normalized_min = self._normalize_slope(
            contrast_hill_min_slope,
            "omni_contrast_hill_min_slope",
        )
        normalized_max = self._normalize_slope(
            contrast_hill_max_slope,
            "omni_contrast_hill_max_slope",
        )
        if (
            normalized_min is not None
            and normalized_max is not None
            and normalized_min > normalized_max
        ):
            raise ValueError("omni_contrast_hill_min_slope must be <= omni_contrast_hill_max_slope")

        burn_set = self._normalize_int_set(
            contrast_select_burn_severities,
            "omni_contrast_select_burn_severities",
        )
        topaz_set = self._normalize_int_set(
            contrast_select_topaz_ids,
            "omni_contrast_select_topaz_ids",
        )
        return normalized_min, normalized_max, burn_set, topaz_set

    def apply_advanced_filters(
        self,
        omni: "Omni",
        *,
        watershed: Any,
        control_scenario: Optional[str],
        obj_param_descending: List["ObjectiveParameter"],
        contrast_hill_min_slope: Optional[float],
        contrast_hill_max_slope: Optional[float],
        contrast_select_burn_severities: Optional[Set[int]],
        contrast_select_topaz_ids: Optional[Set[int]],
    ) -> Tuple[List["ObjectiveParameter"], float]:
        original_count = len(obj_param_descending)
        topaz_filter = None
        if contrast_select_topaz_ids is not None:
            topaz_filter = {str(topaz_id) for topaz_id in contrast_select_topaz_ids}

        slope_lookup: Dict[str, float] = {}
        burn_lookup: Dict[str, int] = {}
        burn_set = contrast_select_burn_severities
        landuse = None
        if burn_set is not None:
            burn_set = set(burn_set)
            invalid = [val for val in burn_set if val not in {0, 1, 2, 3}]
            if invalid:
                raise ValueError(
                    f"omni_contrast_select_burn_severities must be 0-3; got {sorted(invalid)}"
                )
            from wepppy.nodb.core import Landuse
            from wepppy.nodb.mods.omni.omni import OMNI_REL_DIR

            control_wd = omni.wd if control_scenario is None else (
                f"{omni.wd}/{OMNI_REL_DIR}/scenarios/{control_scenario}"
            )
            landuse = Landuse.getInstance(control_wd)

        def _burn_value(label: Optional[str]) -> int:
            name = (label or "Unburned").strip().lower()
            mapping = {
                "unburned": 0,
                "low": 1,
                "moderate": 2,
                "mod": 2,
                "high": 3,
            }
            if name not in mapping:
                raise ValueError(f"Unknown burn class '{label}' while filtering contrasts")
            return mapping[name]

        filtered: List["ObjectiveParameter"] = []
        for item in obj_param_descending:
            topaz_id = str(item.topaz_id)
            if topaz_filter is not None and topaz_id not in topaz_filter:
                continue
            if contrast_hill_min_slope is not None or contrast_hill_max_slope is not None:
                slope = slope_lookup.get(topaz_id)
                if slope is None:
                    slope = watershed.hillslope_slope(topaz_id)
                    slope_lookup[topaz_id] = slope
                if contrast_hill_min_slope is not None and slope < contrast_hill_min_slope:
                    continue
                if contrast_hill_max_slope is not None and slope > contrast_hill_max_slope:
                    continue
            if burn_set is not None and landuse is not None:
                burn_class = burn_lookup.get(topaz_id)
                if burn_class is None:
                    burn_class = _burn_value(landuse.identify_burn_class(topaz_id))
                    burn_lookup[topaz_id] = burn_class
                if burn_class not in burn_set:
                    continue
            filtered.append(item)

        omni.logger.info(
            "  contrast filters reduced candidates from %d to %d",
            original_count,
            len(filtered),
        )
        total_erosion_kg = float(sum(item.value for item in filtered))
        return filtered, total_erosion_kg

    def resolve_order_reduction_passes(self, omni: "Omni") -> int:
        raw_value = getattr(omni, "_contrast_order_reduction_passes", None)
        if raw_value in (None, ""):
            raw_value = omni.config_get_int("omni", "order_reduction_passes", 1)
        try:
            passes = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("order_reduction_passes must be an integer") from exc
        if passes == 0:
            return 1
        if passes < 0:
            raise ValueError("order_reduction_passes must be >= 1")
        return passes

    def _normalize_int_set(self, value: Any, label: str) -> Optional[Set[int]]:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            raw_items = [item.strip() for item in value.split(",") if item.strip()]
        elif isinstance(value, (list, tuple, set)):
            raw_items = list(value)
        else:
            raw_items = [value]
        parsed: Set[int] = set()
        for item in raw_items:
            if item is None or item == "":
                continue
            try:
                parsed.add(int(item))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{label} entries must be integers") from exc
        return parsed or None

    def _normalize_slope(self, value: Any, label: str) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            slope = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} must be a number") from exc
        if slope < 0:
            raise ValueError(f"{label} must be >= 0")
        if slope > 1.0:
            slope = slope / 100.0
        return slope
