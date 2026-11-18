"""Unrutted selection, raster lifetime and hillslope execution ordering."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

import numpy as np
import rasterio
from pyproj import CRS, Transformer

from wepppy.observability.safe_traceback import safe_text
from wepppy.observability.safe_logging import current_profile
from wepppy.observability.secret_profiles import WORKER
from . import _unrutted_planning, _unrutted_native

__all__ = [
    'execute_unrutted',
]


_LOGGER = logging.getLogger(__name__)


def _move_candidate_to_status(
    results,
    candidate,
    hillslope_records_by_topaz,
    status,
):
    segment_hillslope_id = str(candidate["segment_hillslope_id"])
    topaz_id_hill = int(candidate["topaz_id_hill"])
    candidate_row = results.outslope_unrutted_candidate_status.get(segment_hillslope_id)
    if candidate_row is not None:
        candidate_row["status"] = status
    record = hillslope_records_by_topaz.get(topaz_id_hill)
    if record is None:
        return
    included_ids = record.get("segment_ids_included") or []
    excluded_ids = record.get("segment_ids_excluded") or []
    try:
        while segment_hillslope_id in included_ids:
            included_ids.remove(segment_hillslope_id)
    except Exception as exc:  # broad-except: preserve legacy diagnostic-list continuation after recording failure
        _LOGGER.warning(
            "Roads candidate status update could not remove included membership: candidate=%s error=%s",
            safe_text(str(segment_hillslope_id), source_profile=current_profile(WORKER))[:160],
            safe_text(str(exc), source_profile=current_profile(WORKER))[:240],
        )
    if segment_hillslope_id not in excluded_ids:
        excluded_ids.append(segment_hillslope_id)


def _hillslope_dimensions(
    roads,
    results,
    _move_outslope_candidate_to_status,
    candidates,
    topaz_id_hill,
    wepp_id_int,
):
    try:
        hillslope_length_m = float(roads.watershed_instance.hillslope_length(topaz_id_hill))
        hillslope_width_m = float(roads.watershed_instance.hillslope_width(topaz_id_hill))
    except Exception as exc:  # broad-except: translate watershed geometry failures into selected-crossing diagnostics
        hillslope_length_m = 0.0
        hillslope_width_m = 0.0
        for candidate in candidates:
            segment_hillslope_id = str(candidate["segment_hillslope_id"])
            source_segment_id = str(candidate["source_segment_id"])
            overlap_length_m = float(candidate["overlap_length_m"])
            inclusion_ratio = float(candidate["inclusion_ratio"])
            _move_outslope_candidate_to_status(candidate, "failed_missing_parameter")
            results.skipped_segments.append(
                {
                    "segment_id": source_segment_id,
                    "segment_hillslope_id": segment_hillslope_id,
                    "reason": "failed_missing_parameter",
                    "missing_fields": ["hillslope_geometry"],
                }
            )
            results.segment_execution_records.append(
                {
                    "segment_id": source_segment_id,
                    "segment_hillslope_id": segment_hillslope_id,
                    "target_hillslope_wepp_id": int(wepp_id_int),
                    "target_hillslope_topaz_id": int(topaz_id_hill),
                    "status": "failed",
                    "routing_mode": "outslope_unrutted_replacement",
                    "reason": "failed_missing_parameter",
                    "missing_fields": ["hillslope_geometry"],
                    "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                    "design": "outslope_unrutted",
                    "overlap_length_m": overlap_length_m,
                    "inclusion_ratio": inclusion_ratio,
                }
            )
            results.failed_segment_records.append(
                {
                    "segment_id": source_segment_id,
                    "segment_hillslope_id": segment_hillslope_id,
                    "target_hillslope_wepp_id": int(wepp_id_int),
                    "routing_mode": "outslope_unrutted_replacement",
                    "reason": "failed_missing_parameter",
                    "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                }
            )
            roads._append_roads_log(
                "run",
                "segment_skipped",
                {
                    "segment_id": source_segment_id,
                    "segment_hillslope_id": segment_hillslope_id,
                    "reason": "failed_missing_parameter",
                    "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                },
            )
        return None

    if not np.isfinite(hillslope_length_m) or not np.isfinite(hillslope_width_m) or hillslope_length_m <= 0.0 or hillslope_width_m <= 0.0:
        for candidate in candidates:
            segment_hillslope_id = str(candidate["segment_hillslope_id"])
            source_segment_id = str(candidate["source_segment_id"])
            overlap_length_m = float(candidate["overlap_length_m"])
            inclusion_ratio = float(candidate["inclusion_ratio"])
            _move_outslope_candidate_to_status(candidate, "failed_non_positive_top_ofe")
            results.skipped_segments.append(
                {
                    "segment_id": source_segment_id,
                    "segment_hillslope_id": segment_hillslope_id,
                    "reason": "failed_non_positive_top_ofe",
                }
            )
            results.segment_execution_records.append(
                {
                    "segment_id": source_segment_id,
                    "segment_hillslope_id": segment_hillslope_id,
                    "target_hillslope_wepp_id": int(wepp_id_int),
                    "target_hillslope_topaz_id": int(topaz_id_hill),
                    "status": "failed",
                    "routing_mode": "outslope_unrutted_replacement",
                    "reason": "failed_non_positive_top_ofe",
                    "design": "outslope_unrutted",
                    "overlap_length_m": overlap_length_m,
                    "inclusion_ratio": inclusion_ratio,
                }
            )
            results.failed_segment_records.append(
                {
                    "segment_id": source_segment_id,
                    "segment_hillslope_id": segment_hillslope_id,
                    "target_hillslope_wepp_id": int(wepp_id_int),
                    "routing_mode": "outslope_unrutted_replacement",
                    "reason": "failed_non_positive_top_ofe",
                }
            )
            roads._append_roads_log(
                "run",
                "segment_skipped",
                {
                    "segment_id": source_segment_id,
                    "segment_hillslope_id": segment_hillslope_id,
                    "reason": "failed_non_positive_top_ofe",
                    "hillslope_length_m": hillslope_length_m,
                    "hillslope_width_m": hillslope_width_m,
                },
            )
        return None
    return hillslope_length_m, hillslope_width_m


def _execute_hillslope(
    roads,
    results,
    terrain,
    _move_outslope_candidate_to_status,
    discha_dataset,
    hillslope_records_by_topaz,
    params,
    routed_mofe_management_cache_by_traffic_and_order,
    selected_outslope_by_wepp,
    warning_limit,
    wepp_id_int,
    wgs84_to_discha,
):
    """Prepare all crossings before running any replacement on this hillslope."""
    candidates = sorted(
        selected_outslope_by_wepp[wepp_id_int],
        key=lambda row: str(row["segment_hillslope_id"]),
    )
    if not candidates:
        return None

    topaz_id_hill = int(candidates[0]["topaz_id_hill"])
    hillslope_record = hillslope_records_by_topaz.get(topaz_id_hill)

    dimensions = _hillslope_dimensions(
        roads=roads,
        results=results,
        _move_outslope_candidate_to_status=_move_outslope_candidate_to_status,
        candidates=candidates,
        topaz_id_hill=topaz_id_hill,
        wepp_id_int=wepp_id_int,
    )
    if dimensions is None:
        return
    hillslope_length_m, hillslope_width_m = dimensions

    strip_plans: List[Dict[str, Any]] = []
    strip_failure = False

    for candidate in candidates:
        plan = _unrutted_planning.plan_candidate(
            roads=roads,
            results=results,
            terrain=terrain,
            _move_outslope_candidate_to_status=_move_outslope_candidate_to_status,
            candidate=candidate,
            discha_dataset=discha_dataset,
            hillslope_length_m=hillslope_length_m,
            params=params,
            topaz_id_hill=topaz_id_hill,
            warning_limit=warning_limit,
            wepp_id_int=wepp_id_int,
            wgs84_to_discha=wgs84_to_discha,
        )
        if plan is None:
            strip_failure = True
            continue
        strip_plans.append(plan)

    if strip_failure or not strip_plans:
        return None

    reconciled = _unrutted_planning.reconcile_hillslope(
        roads=roads,
        results=results,
        _move_outslope_candidate_to_status=_move_outslope_candidate_to_status,
        hillslope_length_m=hillslope_length_m,
        hillslope_record=hillslope_record,
        hillslope_width_m=hillslope_width_m,
        strip_plans=strip_plans,
        topaz_id_hill=topaz_id_hill,
        wepp_id_int=wepp_id_int,
    )
    if reconciled is None:
        return
    strip_plans, remainder_width_m, remainder_prepared_path = reconciled

    for plan in strip_plans:
        _unrutted_native.execute_strip(
            roads=roads,
            results=results,
            plan=plan,
            routed_mofe_management_cache_by_traffic_and_order=routed_mofe_management_cache_by_traffic_and_order,
            topaz_id_hill=topaz_id_hill,
            wepp_id_int=wepp_id_int,
        )

    if remainder_width_m >= 0.3:
        _unrutted_native.execute_remainder(
            roads=roads,
            results=results,
            hillslope_length_m=hillslope_length_m,
            remainder_prepared_path=remainder_prepared_path,
            remainder_width_m=remainder_width_m,
            routed_mofe_management_cache_by_traffic_and_order=routed_mofe_management_cache_by_traffic_and_order,
            strip_plans=strip_plans,
            topaz_id_hill=topaz_id_hill,
            wepp_id_int=wepp_id_int,
        )


def _finalize_selection_counts(
    results,
):
    included_count = 0
    excluded_count = 0
    capped_count = 0
    for candidate_row in results.outslope_unrutted_candidate_status.values():
        status_value = str(candidate_row.get("status") or "")
        if status_value == "included":
            included_count += 1
        elif status_value == "excluded_cap_limit":
            capped_count += 1
        elif status_value.startswith("excluded_"):
            excluded_count += 1

    results.outslope_unrutted_diagnostics["outslope_unrutted_included_segment_count"] = int(included_count)
    results.outslope_unrutted_diagnostics["outslope_unrutted_excluded_segment_count"] = int(excluded_count)
    results.outslope_unrutted_diagnostics["outslope_unrutted_capped_segment_count"] = int(capped_count)
    results.outslope_unrutted_diagnostics["outslope_unrutted_targeted_hillslope_count"] = int(
        sum(
            1
            for record in results.outslope_unrutted_diagnostics.get("outslope_unrutted_hillslope_records", [])
            if isinstance(record, Mapping) and bool(record.get("segment_ids_included"))
        )
    )


def execute_unrutted(
    roads,
    results,
    terrain,
    dem_path,
    params,
    top2wepp,
    warning_limit,
):
    """Select and execute unrutted replacements after all point-source candidates."""
    selected_outslope_by_wepp, results.outslope_unrutted_diagnostics, results.outslope_unrutted_candidate_status = (
        roads._select_outslope_unrutted_hillslope_segments(
            pending_segments=results.outslope_unrutted_pending_segments,
            input_crs=terrain.input_crs,
            geod=terrain.geod,
            top2wepp=top2wepp,
        )
    )

    hillslope_records_by_topaz = {
        int(record["topaz_id_hill"]): record
        for record in results.outslope_unrutted_diagnostics.get("outslope_unrutted_hillslope_records", [])
        if isinstance(record, Mapping)
    }

    def _move_outslope_candidate_to_status(candidate, status):
        _move_candidate_to_status(
            results=results,
            candidate=candidate,
            hillslope_records_by_topaz=hillslope_records_by_topaz,
            status=status,
        )

    selected_outslope_candidate_count = int(sum(1 for rows in selected_outslope_by_wepp.values() if rows))
    discha_path = roads._normalize_existing_path(getattr(roads.watershed_instance, "discha", None))
    if discha_path is None:
        if selected_outslope_candidate_count > 0:
            raise FileNotFoundError(
                "Roads outslope_unrutted replacement requires watershed distance-to-channel raster (watershed.discha)."
            )
        discha_path = str(dem_path)

    routed_mofe_management_cache_by_traffic_and_order: Dict[Tuple[str, Tuple[int, ...]], Path] = {}

    with rasterio.open(discha_path) as discha_dataset:
        if discha_dataset.crs is None:
            raise ValueError(
                "Roads outslope_unrutted replacement requires watershed.discha to declare a CRS."
            )
        wgs84_to_discha = Transformer.from_crs(
            CRS.from_epsg(4326),
            CRS.from_user_input(discha_dataset.crs),
            always_xy=True,
        )

        for wepp_id_int in sorted(selected_outslope_by_wepp):
            _execute_hillslope(
                roads=roads,
                results=results,
                terrain=terrain,
                _move_outslope_candidate_to_status=_move_outslope_candidate_to_status,
                discha_dataset=discha_dataset,
                hillslope_records_by_topaz=hillslope_records_by_topaz,
                params=params,
                routed_mofe_management_cache_by_traffic_and_order=routed_mofe_management_cache_by_traffic_and_order,
                selected_outslope_by_wepp=selected_outslope_by_wepp,
                warning_limit=warning_limit,
                wepp_id_int=wepp_id_int,
                wgs84_to_discha=wgs84_to_discha,
            )

    _finalize_selection_counts(
        results=results,
    )
