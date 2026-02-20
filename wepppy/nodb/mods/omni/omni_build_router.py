from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import Omni, ScenarioDef


class OmniBuildRouter:
    """Route Omni build/report facade calls while preserving facade contracts."""

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
        if selection_mode not in {"user_defined_areas", "stream_order", "user_defined_hillslope_groups"} and (
            control_scenario is None
            or contrast_scenario is None
        ):
            raise ValueError("control_scenario_def and contrast_scenario_def are required for contrast builds")

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
            contrast_cumulative_obj_param_threshold_fraction=contrast_cumulative_obj_param_threshold_fraction,
            contrast_hillslope_limit=contrast_hillslope_limit,
            hill_min_slope=hill_min_slope,
            hill_max_slope=hill_max_slope,
            select_burn_severities=select_burn_severities,
            select_topaz_ids=select_topaz_ids,
            contrast_pairs=contrast_pairs,
        )
        return self.contrast_status_report(omni)

    def contrast_status_report(self, omni: "Omni") -> Dict[str, Any]:
        selection_mode = (omni._contrast_selection_mode or "cumulative").strip().lower()
        if selection_mode in {"stream_order_pruning", "stream-order-pruning"}:
            selection_mode = "stream_order"
        if selection_mode in {"user-defined-hillslope-groups", "user-defined-hillslope-group"}:
            selection_mode = "user_defined_hillslope_groups"
        if selection_mode not in {
            "cumulative",
            "user_defined_areas",
            "user_defined_hillslope_groups",
            "stream_order",
        }:
            raise ValueError(f'Contrast selection mode "{selection_mode}" is not implemented yet.')
        contrast_names = omni.contrast_names or []
        landuse_cache: Dict[str, Optional[Dict[int, Optional[str]]]] = {}

        if selection_mode == "user_defined_areas":
            report_entries = {}
            for entry in omni._load_contrast_build_report():
                if entry.get("selection_mode") != "user_defined_areas":
                    continue
                contrast_id = entry.get("contrast_id")
                if isinstance(contrast_id, str):
                    try:
                        contrast_id = int(contrast_id)
                    except ValueError:
                        continue
                if isinstance(contrast_id, int):
                    report_entries[contrast_id] = entry

            control_scenario = omni._normalize_scenario_key(omni._control_scenario)
            contrast_scenario = omni._normalize_scenario_key(omni._contrast_scenario)
            contrast_labels = getattr(omni, "_contrast_labels", None) or {}

            items: List[Dict[str, Any]] = []
            max_id = max(report_entries.keys(), default=0)
            if len(contrast_names) > max_id:
                max_id = len(contrast_names)
            for contrast_id in range(1, max_id + 1):
                contrast_name = contrast_names[contrast_id - 1] if contrast_id - 1 < len(contrast_names) else None
                report_entry = report_entries.get(contrast_id, {})
                label = report_entry.get("area_label")
                if not label:
                    label = contrast_labels.get(contrast_id) or contrast_labels.get(str(contrast_id))
                if not label:
                    label = str(contrast_id)

                raw_count = report_entry.get("n_hillslopes")
                if raw_count is None:
                    topaz_ids = report_entry.get("topaz_ids")
                    if isinstance(topaz_ids, list):
                        raw_count = len(topaz_ids)
                try:
                    n_hillslopes = int(raw_count) if raw_count is not None else 0
                except (TypeError, ValueError):
                    n_hillslopes = 0

                skipped = (
                    not contrast_name
                    or report_entry.get("status") == "skipped"
                    or n_hillslopes == 0
                )
                if skipped:
                    run_status = "skipped"
                    skip_status = {"skipped": True, "reason": "no_hillslopes"}
                else:
                    skip_reason = omni._contrast_landuse_skip_reason(
                        contrast_id,
                        contrast_name,
                        landuse_cache=landuse_cache,
                    )
                    if skip_reason:
                        run_status = "skipped"
                        skip_status = {"skipped": True, "reason": skip_reason}
                    else:
                        run_status = omni._contrast_run_status(contrast_id, contrast_name)
                        skip_status = {"skipped": False, "reason": None}

                items.append(
                    {
                        "contrast_id": contrast_id,
                        "control_scenario": report_entry.get("control_scenario") or control_scenario,
                        "contrast_scenario": report_entry.get("contrast_scenario") or contrast_scenario,
                        "area_label": label,
                        "n_hillslopes": n_hillslopes,
                        "skip_status": skip_status,
                        "run_status": run_status,
                    }
                )

            return {"selection_mode": selection_mode, "items": items}

        if selection_mode == "user_defined_hillslope_groups":
            report_entries = {}
            for entry in omni._load_contrast_build_report():
                if entry.get("selection_mode") != "user_defined_hillslope_groups":
                    continue
                contrast_id = entry.get("contrast_id")
                if isinstance(contrast_id, str):
                    try:
                        contrast_id = int(contrast_id)
                    except ValueError:
                        continue
                if isinstance(contrast_id, int):
                    report_entries[contrast_id] = entry

            contrast_labels = getattr(omni, "_contrast_labels", None) or {}

            items: List[Dict[str, Any]] = []
            max_id = max(report_entries.keys(), default=0)
            if len(contrast_names) > max_id:
                max_id = len(contrast_names)
            for contrast_id in range(1, max_id + 1):
                contrast_name = contrast_names[contrast_id - 1] if contrast_id - 1 < len(contrast_names) else None
                report_entry = report_entries.get(contrast_id, {})

                control_scenario = report_entry.get("control_scenario")
                contrast_scenario = report_entry.get("contrast_scenario")
                if (control_scenario is None or contrast_scenario is None) and contrast_name:
                    try:
                        control_part, target_part = contrast_name.split("__to__", maxsplit=1)
                        control_scenario = control_part.split(",", maxsplit=1)[0]
                        contrast_scenario = target_part
                    except ValueError:
                        control_scenario = control_scenario or None
                        contrast_scenario = contrast_scenario or None

                group_index = report_entry.get("group_index")
                if group_index in (None, ""):
                    group_index = contrast_labels.get(contrast_id) or contrast_labels.get(str(contrast_id))

                raw_count = report_entry.get("n_hillslopes")
                if raw_count is None:
                    topaz_ids = report_entry.get("topaz_ids")
                    if isinstance(topaz_ids, list):
                        raw_count = len(topaz_ids)
                try:
                    n_hillslopes = int(raw_count) if raw_count is not None else 0
                except (TypeError, ValueError):
                    n_hillslopes = 0

                skipped = (
                    not contrast_name
                    or report_entry.get("status") == "skipped"
                    or n_hillslopes == 0
                )
                if skipped:
                    run_status = "skipped"
                    skip_status = {"skipped": True, "reason": "no_hillslopes"}
                else:
                    skip_reason = omni._contrast_landuse_skip_reason(
                        contrast_id,
                        contrast_name,
                        landuse_cache=landuse_cache,
                    )
                    if skip_reason:
                        run_status = "skipped"
                        skip_status = {"skipped": True, "reason": skip_reason}
                    else:
                        run_status = omni._contrast_run_status(contrast_id, contrast_name)
                        skip_status = {"skipped": False, "reason": None}

                items.append(
                    {
                        "contrast_id": contrast_id,
                        "control_scenario": control_scenario,
                        "contrast_scenario": contrast_scenario,
                        "group_index": group_index,
                        "n_hillslopes": n_hillslopes,
                        "skip_status": skip_status,
                        "run_status": run_status,
                    }
                )

            return {"selection_mode": selection_mode, "items": items}

        if selection_mode == "stream_order":
            report_entries = {}
            for entry in omni._load_contrast_build_report():
                if entry.get("selection_mode") != "stream_order":
                    continue
                contrast_id = entry.get("contrast_id")
                if isinstance(contrast_id, str):
                    try:
                        contrast_id = int(contrast_id)
                    except ValueError:
                        continue
                if isinstance(contrast_id, int):
                    report_entries[contrast_id] = entry

            items: List[Dict[str, Any]] = []
            max_id = max(report_entries.keys(), default=0)
            if len(contrast_names) > max_id:
                max_id = len(contrast_names)
            for contrast_id in range(1, max_id + 1):
                contrast_name = contrast_names[contrast_id - 1] if contrast_id - 1 < len(contrast_names) else None
                report_entry = report_entries.get(contrast_id, {})

                control_scenario = report_entry.get("control_scenario")
                contrast_scenario = report_entry.get("contrast_scenario")
                if (control_scenario is None or contrast_scenario is None) and contrast_name:
                    try:
                        control_part, target_part = contrast_name.split("__to__", maxsplit=1)
                        control_scenario = control_part.split(",", maxsplit=1)[0]
                        contrast_scenario = target_part
                    except ValueError:
                        control_scenario = control_scenario or None
                        contrast_scenario = contrast_scenario or None

                raw_count = report_entry.get("n_hillslopes")
                try:
                    n_hillslopes = int(raw_count) if raw_count is not None else 0
                except (TypeError, ValueError):
                    n_hillslopes = 0

                skipped = (
                    not contrast_name
                    or report_entry.get("status") == "skipped"
                    or n_hillslopes == 0
                )
                if skipped:
                    run_status = "skipped"
                    skip_status = {"skipped": True, "reason": "no_hillslopes"}
                else:
                    skip_reason = omni._contrast_landuse_skip_reason(
                        contrast_id,
                        contrast_name,
                        landuse_cache=landuse_cache,
                    )
                    if skip_reason:
                        run_status = "skipped"
                        skip_status = {"skipped": True, "reason": skip_reason}
                    else:
                        run_status = omni._contrast_run_status(contrast_id, contrast_name)
                        skip_status = {"skipped": False, "reason": None}

                items.append(
                    {
                        "contrast_id": contrast_id,
                        "control_scenario": control_scenario,
                        "contrast_scenario": contrast_scenario,
                        "subcatchments_group": report_entry.get("subcatchments_group"),
                        "n_hillslopes": n_hillslopes,
                        "skip_status": skip_status,
                        "run_status": run_status,
                    }
                )

            return {"selection_mode": selection_mode, "items": items}

        items = []
        for contrast_id, contrast_name in enumerate(contrast_names, start=1):
            topaz_id = None
            if contrast_name:
                try:
                    control_part, _ = contrast_name.split("__to__", maxsplit=1)
                    _, topaz_id = control_part.split(",", maxsplit=1)
                except ValueError:
                    topaz_id = None
                skip_reason = omni._contrast_landuse_skip_reason(
                    contrast_id,
                    contrast_name,
                    landuse_cache=landuse_cache,
                )
                if skip_reason:
                    run_status = "skipped"
                    skip_status = {"skipped": True, "reason": skip_reason}
                else:
                    run_status = omni._contrast_run_status(contrast_id, contrast_name)
                    skip_status = {"skipped": False, "reason": None}
            else:
                run_status = "skipped"
                skip_status = {"skipped": True, "reason": "no_hillslopes"}
            items.append(
                {
                    "contrast_id": contrast_id,
                    "topaz_id": str(topaz_id) if topaz_id is not None else None,
                    "skip_status": skip_status,
                    "run_status": run_status,
                }
            )

        return {"selection_mode": selection_mode, "items": items}
