from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Tuple

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import Omni


class OmniContrastStatusReportService:
    """Build contrast status payloads across selection modes."""

    _SELECTION_MODE_ALIASES = {
        "stream_order_pruning": "stream_order",
        "stream-order-pruning": "stream_order",
        "user-defined-hillslope-groups": "user_defined_hillslope_groups",
        "user-defined-hillslope-group": "user_defined_hillslope_groups",
    }
    _SUPPORTED_SELECTION_MODES = {
        "cumulative",
        "user_defined_areas",
        "user_defined_hillslope_groups",
        "stream_order",
    }

    def contrast_status_report(self, omni: "Omni") -> Dict[str, Any]:
        selection_mode = self._normalize_report_selection_mode(omni._contrast_selection_mode)
        contrast_names: List[Optional[str]] = omni.contrast_names or []
        landuse_cache: Dict[str, Optional[Dict[int, Optional[str]]]] = {}

        if selection_mode == "user_defined_areas":
            items = self._build_user_defined_area_items(
                omni,
                contrast_names=contrast_names,
                landuse_cache=landuse_cache,
            )
        elif selection_mode == "user_defined_hillslope_groups":
            items = self._build_user_defined_hillslope_group_items(
                omni,
                contrast_names=contrast_names,
                landuse_cache=landuse_cache,
            )
        elif selection_mode == "stream_order":
            items = self._build_stream_order_items(
                omni,
                contrast_names=contrast_names,
                landuse_cache=landuse_cache,
            )
        else:
            items = self._build_cumulative_items(
                omni,
                contrast_names=contrast_names,
                landuse_cache=landuse_cache,
            )

        return {"selection_mode": selection_mode, "items": items}

    def _normalize_report_selection_mode(self, selection_mode: Optional[str]) -> str:
        normalized_selection_mode = (selection_mode or "cumulative").strip().lower()
        normalized_selection_mode = self._SELECTION_MODE_ALIASES.get(
            normalized_selection_mode,
            normalized_selection_mode,
        )
        if normalized_selection_mode not in self._SUPPORTED_SELECTION_MODES:
            raise ValueError(
                f'Contrast selection mode "{normalized_selection_mode}" is not implemented yet.'
            )
        return normalized_selection_mode

    def _build_user_defined_area_items(
        self,
        omni: "Omni",
        *,
        contrast_names: List[Optional[str]],
        landuse_cache: Dict[str, Optional[Dict[int, Optional[str]]]],
    ) -> List[Dict[str, Any]]:
        report_entries = self._load_report_entries_by_contrast_id(
            omni,
            selection_mode="user_defined_areas",
        )
        control_scenario = omni._normalize_scenario_key(omni._control_scenario)
        contrast_scenario = omni._normalize_scenario_key(omni._contrast_scenario)
        contrast_labels = getattr(omni, "_contrast_labels", None) or {}

        items: List[Dict[str, Any]] = []
        for contrast_id, contrast_name, report_entry in self._iter_contrast_rows(
            contrast_names,
            report_entries,
        ):
            label = report_entry.get("area_label")
            if not label:
                label = contrast_labels.get(contrast_id) or contrast_labels.get(str(contrast_id))
            if not label:
                label = str(contrast_id)

            n_hillslopes = self._coerce_n_hillslopes(
                report_entry,
                include_topaz_fallback=True,
            )
            run_status, skip_status = self._resolve_mode_item_status(
                omni,
                contrast_id=contrast_id,
                contrast_name=contrast_name,
                report_entry=report_entry,
                n_hillslopes=n_hillslopes,
                landuse_cache=landuse_cache,
            )

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

        return items

    def _build_user_defined_hillslope_group_items(
        self,
        omni: "Omni",
        *,
        contrast_names: List[Optional[str]],
        landuse_cache: Dict[str, Optional[Dict[int, Optional[str]]]],
    ) -> List[Dict[str, Any]]:
        report_entries = self._load_report_entries_by_contrast_id(
            omni,
            selection_mode="user_defined_hillslope_groups",
        )
        contrast_labels = getattr(omni, "_contrast_labels", None) or {}

        items: List[Dict[str, Any]] = []
        for contrast_id, contrast_name, report_entry in self._iter_contrast_rows(
            contrast_names,
            report_entries,
        ):
            control_scenario, contrast_scenario = self._resolve_scenarios(
                report_entry,
                contrast_name,
            )
            group_index = report_entry.get("group_index")
            if group_index in (None, ""):
                group_index = contrast_labels.get(contrast_id) or contrast_labels.get(str(contrast_id))

            n_hillslopes = self._coerce_n_hillslopes(
                report_entry,
                include_topaz_fallback=True,
            )
            run_status, skip_status = self._resolve_mode_item_status(
                omni,
                contrast_id=contrast_id,
                contrast_name=contrast_name,
                report_entry=report_entry,
                n_hillslopes=n_hillslopes,
                landuse_cache=landuse_cache,
            )

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

        return items

    def _build_stream_order_items(
        self,
        omni: "Omni",
        *,
        contrast_names: List[Optional[str]],
        landuse_cache: Dict[str, Optional[Dict[int, Optional[str]]]],
    ) -> List[Dict[str, Any]]:
        report_entries = self._load_report_entries_by_contrast_id(
            omni,
            selection_mode="stream_order",
        )

        items: List[Dict[str, Any]] = []
        for contrast_id, contrast_name, report_entry in self._iter_contrast_rows(
            contrast_names,
            report_entries,
        ):
            control_scenario, contrast_scenario = self._resolve_scenarios(
                report_entry,
                contrast_name,
            )
            n_hillslopes = self._coerce_n_hillslopes(
                report_entry,
                include_topaz_fallback=False,
            )
            run_status, skip_status = self._resolve_mode_item_status(
                omni,
                contrast_id=contrast_id,
                contrast_name=contrast_name,
                report_entry=report_entry,
                n_hillslopes=n_hillslopes,
                landuse_cache=landuse_cache,
            )

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

        return items

    def _build_cumulative_items(
        self,
        omni: "Omni",
        *,
        contrast_names: List[Optional[str]],
        landuse_cache: Dict[str, Optional[Dict[int, Optional[str]]]],
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for contrast_id, contrast_name in enumerate(contrast_names, start=1):
            run_status, skip_status = self._resolve_cumulative_item_status(
                omni,
                contrast_id=contrast_id,
                contrast_name=contrast_name,
                landuse_cache=landuse_cache,
            )
            items.append(
                {
                    "contrast_id": contrast_id,
                    "topaz_id": self._extract_topaz_id(contrast_name),
                    "skip_status": skip_status,
                    "run_status": run_status,
                }
            )

        return items

    def _load_report_entries_by_contrast_id(
        self,
        omni: "Omni",
        *,
        selection_mode: str,
    ) -> Dict[int, Dict[str, Any]]:
        report_entries: Dict[int, Dict[str, Any]] = {}
        for entry in omni._load_contrast_build_report():
            if entry.get("selection_mode") != selection_mode:
                continue

            contrast_id = entry.get("contrast_id")
            if isinstance(contrast_id, str):
                try:
                    contrast_id = int(contrast_id)
                except ValueError:
                    continue

            if isinstance(contrast_id, int):
                report_entries[contrast_id] = entry

        return report_entries

    def _iter_contrast_rows(
        self,
        contrast_names: List[Optional[str]],
        report_entries: Dict[int, Dict[str, Any]],
    ) -> Iterable[Tuple[int, Optional[str], Dict[str, Any]]]:
        max_id = max(max(report_entries.keys(), default=0), len(contrast_names))
        for contrast_id in range(1, max_id + 1):
            contrast_name = (
                contrast_names[contrast_id - 1]
                if contrast_id - 1 < len(contrast_names)
                else None
            )
            yield contrast_id, contrast_name, report_entries.get(contrast_id, {})

    def _coerce_n_hillslopes(
        self,
        report_entry: Dict[str, Any],
        *,
        include_topaz_fallback: bool,
    ) -> int:
        raw_count = report_entry.get("n_hillslopes")
        if raw_count is None and include_topaz_fallback:
            topaz_ids = report_entry.get("topaz_ids")
            if isinstance(topaz_ids, list):
                raw_count = len(topaz_ids)

        try:
            return int(raw_count) if raw_count is not None else 0
        except (TypeError, ValueError):
            return 0

    def _resolve_scenarios(
        self,
        report_entry: Dict[str, Any],
        contrast_name: Optional[str],
    ) -> Tuple[Optional[str], Optional[str]]:
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

        return control_scenario, contrast_scenario

    def _resolve_mode_item_status(
        self,
        omni: "Omni",
        *,
        contrast_id: int,
        contrast_name: Optional[str],
        report_entry: Dict[str, Any],
        n_hillslopes: int,
        landuse_cache: Dict[str, Optional[Dict[int, Optional[str]]]],
    ) -> Tuple[str, Dict[str, Any]]:
        if (
            not contrast_name
            or report_entry.get("status") == "skipped"
            or n_hillslopes == 0
        ):
            return "skipped", {"skipped": True, "reason": "no_hillslopes"}

        skip_reason = omni._contrast_landuse_skip_reason(
            contrast_id,
            contrast_name,
            landuse_cache=landuse_cache,
        )
        if skip_reason:
            return "skipped", {"skipped": True, "reason": skip_reason}
        return omni._contrast_run_status(contrast_id, contrast_name), {
            "skipped": False,
            "reason": None,
        }

    def _resolve_cumulative_item_status(
        self,
        omni: "Omni",
        *,
        contrast_id: int,
        contrast_name: Optional[str],
        landuse_cache: Dict[str, Optional[Dict[int, Optional[str]]]],
    ) -> Tuple[str, Dict[str, Any]]:
        if not contrast_name:
            return "skipped", {"skipped": True, "reason": "no_hillslopes"}

        skip_reason = omni._contrast_landuse_skip_reason(
            contrast_id,
            contrast_name,
            landuse_cache=landuse_cache,
        )
        if skip_reason:
            return "skipped", {"skipped": True, "reason": skip_reason}
        return omni._contrast_run_status(contrast_id, contrast_name), {
            "skipped": False,
            "reason": None,
        }

    def _extract_topaz_id(self, contrast_name: Optional[str]) -> Optional[str]:
        if not contrast_name:
            return None
        try:
            control_part, _ = contrast_name.split("__to__", maxsplit=1)
            _, topaz_id = control_part.split(",", maxsplit=1)
            return str(topaz_id)
        except ValueError:
            return None
