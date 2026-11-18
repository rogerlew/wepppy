"""Unrutted crossing planning and exact-area profile reconciliation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np

from wepppy.observability.safe_traceback import safe_text
from wepppy.observability.safe_logging import current_profile
from wepppy.observability.secret_profiles import WORKER
from . import _unrutted
from ._constants import OUTSLOPE_UNRUTTED_AREA_EPSILON_M2, OUTSLOPE_UNRUTTED_LANDUSE_MIN_LENGTH_M

__all__ = [
    'plan_candidate',
    'reconcile_hillslope',
]


def _record_missing_inputs(
    roads,
    results,
    _move_outslope_candidate_to_status,
    candidate,
    inclusion_ratio,
    missing_fields,
    overlap_length_m,
    segment_hillslope_id,
    source_segment_id,
    topaz_id_hill,
    wepp_id_int,
):
    _move_outslope_candidate_to_status(candidate, "failed_missing_parameter")
    results.skipped_segments.append(
        {
            "segment_id": source_segment_id,
            "segment_hillslope_id": segment_hillslope_id,
            "reason": "failed_missing_parameter",
            "missing_fields": missing_fields,
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
            "missing_fields": missing_fields,
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
            "missing_fields": missing_fields,
        }
    )
    roads._append_roads_log(
        "run",
        "segment_skipped",
        {
            "segment_id": source_segment_id,
            "segment_hillslope_id": segment_hillslope_id,
            "reason": "failed_missing_parameter",
            "missing_fields": missing_fields,
        },
    )


def _record_profile_failure(
    roads,
    results,
    _move_outslope_candidate_to_status,
    candidate,
    exc,
    inclusion_ratio,
    overlap_length_m,
    segment_hillslope_id,
    source_segment_id,
    topaz_id_hill,
    wepp_id_int,
):
    _move_outslope_candidate_to_status(candidate, "failed_missing_parameter")
    results.skipped_segments.append(
        {
            "segment_id": source_segment_id,
            "segment_hillslope_id": segment_hillslope_id,
            "reason": "failed_missing_parameter",
            "missing_fields": ["segment_profile"],
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
            "missing_fields": ["segment_profile"],
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


def _record_missing_profiles(
    roads,
    results,
    _move_outslope_candidate_to_status,
    candidate,
    inclusion_ratio,
    overlap_length_m,
    segment_hillslope_id,
    source_segment_id,
    topaz_id_hill,
    wepp_id_int,
):
    _move_outslope_candidate_to_status(candidate, "failed_missing_parameter")
    results.skipped_segments.append(
        {
            "segment_id": source_segment_id,
            "segment_hillslope_id": segment_hillslope_id,
            "reason": "failed_missing_parameter",
            "missing_fields": ["fill_or_buffer_profile"],
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
            "missing_fields": ["fill_or_buffer_profile"],
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
            "missing_fields": ["fill_or_buffer_profile"],
        }
    )
    roads._append_roads_log(
        "run",
        "segment_skipped",
        {
            "segment_id": source_segment_id,
            "segment_hillslope_id": segment_hillslope_id,
            "reason": "failed_missing_parameter",
            "missing_fields": ["fill_or_buffer_profile"],
        },
    )


def _record_road_fill_overflow(
    roads,
    results,
    _move_outslope_candidate_to_status,
    candidate,
    discha_median_m,
    fill_profile,
    inclusion_ratio,
    overlap_length_m,
    parity_profile,
    placement,
    placement_source,
    segment_hillslope_id,
    source_segment_id,
    topaz_id_hill,
    wepp_id_int,
):
    _move_outslope_candidate_to_status(candidate, "failed_road_fill_exceeds_hillslope")
    results.skipped_segments.append(
        {
            "segment_id": source_segment_id,
            "segment_hillslope_id": segment_hillslope_id,
            "reason": "failed_road_fill_exceeds_hillslope",
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
            "reason": "failed_road_fill_exceeds_hillslope",
            "design": "outslope_unrutted",
            **placement,
            "placement_source": placement_source,
            "discha_median_m": float(discha_median_m),
            "road_width_m": float(parity_profile["sim_length_m"]),
            "fill_length_m": float(fill_profile["fill_length_m"]),
            "error": "Road plus fill exceeds hillslope length; verify supplied dimensions and representative hillslope geometry.",
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
            "reason": "failed_road_fill_exceeds_hillslope",
        }
    )
    roads._append_roads_log(
        "run",
        "segment_skipped",
        {
            "segment_id": source_segment_id,
            "segment_hillslope_id": segment_hillslope_id,
            "reason": "failed_road_fill_exceeds_hillslope",
        },
    )


def _candidate_profiles(
    roads,
    results,
    terrain,
    _move_outslope_candidate_to_status,
    candidate,
    feature,
    inclusion_ratio,
    overlap_length_m,
    params,
    properties,
    segment_hillslope_id,
    source_segment_id,
    topaz_id_hill,
    warning_limit,
    wepp_id_int,
):
    """Resolve required inputs and DEM profile before planning placement."""
    segment_inputs = roads._resolve_segment_run_inputs(
        properties=properties,
        params=params,
        segment_id=segment_hillslope_id,
        design="outslope_unrutted",
        warning_counts=results.mapping_warning_counts,
        warning_examples=results.mapping_warning_examples,
        warning_limit=warning_limit,
    )
    segment_inputs["resolution_sources"]["design"] = "segment_property"

    fill_profile, routed_buffer_profile, missing_fields = (
        roads._resolve_outslope_unrutted_required_profiles(
            properties=properties,
        )
    )
    if missing_fields:
        _record_missing_inputs(
            roads=roads,
            results=results,
            _move_outslope_candidate_to_status=_move_outslope_candidate_to_status,
            candidate=candidate,
            inclusion_ratio=inclusion_ratio,
            missing_fields=missing_fields,
            overlap_length_m=overlap_length_m,
            segment_hillslope_id=segment_hillslope_id,
            source_segment_id=source_segment_id,
            topaz_id_hill=topaz_id_hill,
            wepp_id_int=wepp_id_int,
        )
        return None

    try:
        profile = roads._build_segment_profile(
            feature=feature,
            input_crs=terrain.input_crs,
            dem_dataset=terrain.dem_dataset,
            input_to_wgs84=terrain.input_to_wgs84,
            input_to_dem=terrain.input_to_dem,
            geod=terrain.geod,
        )
    except ValueError as exc:
        _record_profile_failure(
            roads=roads,
            results=results,
            _move_outslope_candidate_to_status=_move_outslope_candidate_to_status,
            candidate=candidate,
            exc=exc,
            inclusion_ratio=inclusion_ratio,
            overlap_length_m=overlap_length_m,
            segment_hillslope_id=segment_hillslope_id,
            source_segment_id=source_segment_id,
            topaz_id_hill=topaz_id_hill,
            wepp_id_int=wepp_id_int,
        )
        return None

    profile = dict(profile)
    profile["segment_length_m"] = max(1.0, float(overlap_length_m))
    parity_profile = _unrutted.road_geometry(
        overlap_length_m, float(segment_inputs["road_width_m"]),
    )

    if fill_profile is None or routed_buffer_profile is None:
        _record_missing_profiles(
            roads=roads,
            results=results,
            _move_outslope_candidate_to_status=_move_outslope_candidate_to_status,
            candidate=candidate,
            inclusion_ratio=inclusion_ratio,
            overlap_length_m=overlap_length_m,
            segment_hillslope_id=segment_hillslope_id,
            source_segment_id=source_segment_id,
            topaz_id_hill=topaz_id_hill,
            wepp_id_int=wepp_id_int,
        )
        return None
    return segment_inputs, fill_profile, routed_buffer_profile, profile, parity_profile


def plan_candidate(
    roads,
    results,
    terrain,
    _move_outslope_candidate_to_status,
    candidate,
    discha_dataset,
    hillslope_length_m,
    params,
    topaz_id_hill,
    warning_limit,
    wepp_id_int,
    wgs84_to_discha,
):
    """Resolve one crossing and retain explicit invalid-input or fit evidence."""
    segment_hillslope_id = str(candidate["segment_hillslope_id"])
    source_segment_id = str(candidate["source_segment_id"])
    feature = candidate["feature"]
    properties = candidate["properties"]
    overlap_length_m = float(candidate["overlap_length_m"])
    inclusion_ratio = float(candidate["inclusion_ratio"])

    results.mapped_segment_count += 1

    profiles = _candidate_profiles(
        roads=roads,
        results=results,
        terrain=terrain,
        _move_outslope_candidate_to_status=_move_outslope_candidate_to_status,
        candidate=candidate,
        feature=feature,
        inclusion_ratio=inclusion_ratio,
        overlap_length_m=overlap_length_m,
        params=params,
        properties=properties,
        segment_hillslope_id=segment_hillslope_id,
        source_segment_id=source_segment_id,
        topaz_id_hill=topaz_id_hill,
        warning_limit=warning_limit,
        wepp_id_int=wepp_id_int,
    )
    if profiles is None:
        return None
    segment_inputs, fill_profile, routed_buffer_profile, profile, parity_profile = profiles

    overlap_geometry_wgs84 = candidate.get("overlap_geometry_wgs84")
    discha_median_m = None
    if overlap_geometry_wgs84 is not None:
        discha_median_m = roads._sample_discha_median_from_wgs84_geometry(
            overlap_geometry_wgs84,
            discha_dataset=discha_dataset,
            wgs84_to_discha=wgs84_to_discha,
        )
    placement_source = "distance_to_channel_median"
    if discha_median_m is None:
        discha_median_m = hillslope_length_m * 0.5
        placement_source = "mid_hillslope_fallback"

    placement = _unrutted.placement(
        hillslope_length_m, float(parity_profile["sim_length_m"]),
        float(fill_profile["fill_length_m"]), float(discha_median_m),
        OUTSLOPE_UNRUTTED_LANDUSE_MIN_LENGTH_M,
    )
    top_landuse_length_m = placement["top_landuse_length_m"]
    downslope_landuse_length_m = placement["bottom_landuse_length_m"]
    has_downslope_landuse = downslope_landuse_length_m > 0
    if not placement.pop("fits"):
        _record_road_fill_overflow(
            roads=roads,
            results=results,
            _move_outslope_candidate_to_status=_move_outslope_candidate_to_status,
            candidate=candidate,
            discha_median_m=discha_median_m,
            fill_profile=fill_profile,
            inclusion_ratio=inclusion_ratio,
            overlap_length_m=overlap_length_m,
            parity_profile=parity_profile,
            placement=placement,
            placement_source=placement_source,
            segment_hillslope_id=segment_hillslope_id,
            source_segment_id=source_segment_id,
            topaz_id_hill=topaz_id_hill,
            wepp_id_int=wepp_id_int,
        )
        return None

    return (
        {
            "candidate": candidate,
            "source_segment_id": source_segment_id,
            "segment_hillslope_id": segment_hillslope_id,
            "topaz_id_hill": int(topaz_id_hill),
            "target_hillslope_wepp_id": int(wepp_id_int),
            "segment_inputs": segment_inputs,
            "profile": profile,
            "parity_profile": parity_profile,
            "fill_profile": fill_profile,
            "routed_buffer_profile": routed_buffer_profile,
            "overlap_length_m": overlap_length_m,
            "inclusion_ratio": inclusion_ratio,
            "discha_median_m": float(discha_median_m),
            "placement_source": placement_source,
            **placement,
            "bottom_ofe_compensation_m": 0.0,
            "top_landuse_length_m": float(top_landuse_length_m),
            "bottom_landuse_length_m": float(downslope_landuse_length_m),
            "has_downslope_landuse": bool(has_downslope_landuse),
            "top_landuse_slope_pct": float(routed_buffer_profile["buffer_slope_pct"]),
            "bottom_landuse_slope_pct": float(routed_buffer_profile["buffer_slope_pct"]),
            "strip_width_m": float(parity_profile["sim_width_m"]),
            "top_ofe_compensation_m": 0.0,
        }
    )


def _record_invalid_strip_widths(
    roads,
    results,
    _move_outslope_candidate_to_status,
    strip_plans,
    topaz_id_hill,
    wepp_id_int,
):
    for plan in strip_plans:
        candidate = plan["candidate"]
        source_segment_id = str(plan["source_segment_id"])
        segment_hillslope_id = str(plan["segment_hillslope_id"])
        overlap_length_m = float(plan["overlap_length_m"])
        inclusion_ratio = float(plan["inclusion_ratio"])
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
            },
        )


def _record_invalid_compensation(
    roads,
    results,
    _move_outslope_candidate_to_status,
    strip_plans,
    topaz_id_hill,
    wepp_id_int,
):
    for plan in strip_plans:
        candidate = plan["candidate"]
        source_segment_id = str(plan["source_segment_id"])
        segment_hillslope_id = str(plan["segment_hillslope_id"])
        overlap_length_m = float(plan["overlap_length_m"])
        inclusion_ratio = float(plan["inclusion_ratio"])
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
            },
        )


def _emit_profiles(
    roads,
    area_error_after_m2,
    hillslope_area_m2,
    hillslope_length_m,
    hillslope_record,
    hillslope_width_m,
    remainder_width_m,
    represented_area_after_m2,
    strip_plans,
    topaz_id_hill,
    width_sum_before_scaling,
):
    """Serialize planned areas and verify the exact consumed slope geometry."""
    emitted_area = 0.0
    for index, plan in enumerate(strip_plans):
        lengths, slopes, plan["ofe_order"] = _unrutted.profile_parts(plan)
        plan["slope_path"] = Path(roads.roads_runs_dir) / f"unrutted-h{topaz_id_hill}-{index}.slp"
        emitted_area += _unrutted.write_slope(plan["slope_path"], plan["strip_width_m"], lengths, slopes)
        target = plan["parity_profile"]["road_target_area_m2"]
        modeled = plan["strip_width_m"] * plan["parity_profile"]["sim_length_m"]
        plan["accounting"] = {
            "geometry_policy": _unrutted.POLICY, "connectivity_limitation": _unrutted.LIMITATION,
            "source_segment_ids": plan["candidate"]["source_segment_ids"],
            "placement_source": plan["placement_source"],
            **{key: plan[key] for key in (
                "placement_policy", "placement_adjustment", "placement_adjustment_reason",
                "original_top_landuse_length_m", "hillslope_length_m",
                "upslope_runon_assumed_zero", "top_ofe_compensation_m", "bottom_ofe_compensation_m",
                "top_landuse_length_m", "bottom_landuse_length_m", "discha_median_m",
            )},
            "road_target_area_m2": target, "road_modeled_area_m2": modeled,
            "road_area_deficit_m2": max(0.0, target - modeled),
            "strip_width_factor": min(1.0, hillslope_width_m / width_sum_before_scaling),
            "area_accounting_status": "complete", "area_accounting_reason": None,
            "road_area_deficit_reason": "hillslope_width_limit" if modeled < target else None,
        }
    remainder_prepared_path = Path(roads.roads_runs_dir) / f"unrutted-h{topaz_id_hill}-remainder.slp"
    if remainder_width_m >= 0.3:
        emitted_area += _unrutted.write_slope(remainder_prepared_path, remainder_width_m,
            [hillslope_length_m], [strip_plans[0]["top_landuse_slope_pct"] / 100])
    if not np.isfinite(emitted_area) or abs(emitted_area - hillslope_area_m2) > OUTSLOPE_UNRUTTED_AREA_EPSILON_M2:
        raise ValueError(f"Unrutted emitted hillslope {topaz_id_hill} area does not close.")
    hillslope_record.update({
        "reference_area_m2": hillslope_area_m2,
        "affected_area_m2": represented_area_after_m2 - remainder_width_m * hillslope_length_m,
        "remainder_area_m2": remainder_width_m * hillslope_length_m,
        "area_residual_m2": area_error_after_m2,
        "emitted_area_residual_m2": hillslope_area_m2 - emitted_area,
        "road_target_area_m2": sum(plan["accounting"]["road_target_area_m2"] for plan in strip_plans),
        "road_modeled_area_m2": sum(plan["accounting"]["road_modeled_area_m2"] for plan in strip_plans),
        "road_area_deficit_m2": sum(plan["accounting"]["road_area_deficit_m2"] for plan in strip_plans),
        "strip_width_factor": min(1.0, hillslope_width_m / width_sum_before_scaling),
        "area_accounting_status": "complete", "area_accounting_reason": None,
    })
    return remainder_prepared_path


def reconcile_hillslope(
    roads,
    results,
    _move_outslope_candidate_to_status,
    hillslope_length_m,
    hillslope_record,
    hillslope_width_m,
    strip_plans,
    topaz_id_hill,
    wepp_id_int,
):
    """Reconcile widths and areas in the original deterministic strip order."""
    strip_plans = sorted(
        strip_plans,
        key=lambda plan: (
            -float(plan["discha_median_m"]),
            str(plan["segment_hillslope_id"]),
        ),
    )

    width_sum_before_scaling = float(sum(float(plan["strip_width_m"]) for plan in strip_plans))
    if width_sum_before_scaling <= 0.0:
        _record_invalid_strip_widths(
            roads=roads,
            results=results,
            _move_outslope_candidate_to_status=_move_outslope_candidate_to_status,
            strip_plans=strip_plans,
            topaz_id_hill=topaz_id_hill,
            wepp_id_int=wepp_id_int,
        )
        return None

    if width_sum_before_scaling > hillslope_width_m:
        width_scale = hillslope_width_m / width_sum_before_scaling
        for plan in strip_plans:
            plan["strip_width_m"] = float(plan["strip_width_m"]) * float(width_scale)

    strip_width_sum = float(sum(float(plan["strip_width_m"]) for plan in strip_plans))
    remainder_width_m = max(0.0, float(hillslope_width_m) - strip_width_sum)

    if 0.0 < remainder_width_m < 0.3 and strip_plans:
        area_to_compensate_m2 = float(remainder_width_m * hillslope_length_m)
        comp_width = float(strip_plans[0]["strip_width_m"])
        if comp_width > 0.0:
            compensation_m = area_to_compensate_m2 / comp_width
            if not _unrutted.compensate(strip_plans[0], compensation_m):
                raise ValueError("Unrutted remainder compensation produces invalid landuse length.")
            remainder_width_m = 0.0

    def _plan_total_length_m(plan_row: Mapping[str, Any]) -> float:
        return float(
            float(plan_row["top_landuse_length_m"])
            + float(plan_row["parity_profile"]["sim_length_m"])
            + float(plan_row["fill_profile"]["fill_length_m"])
            + float(plan_row["bottom_landuse_length_m"])
        )

    hillslope_area_m2 = float(hillslope_width_m * hillslope_length_m)
    if not np.isfinite(hillslope_area_m2):
        raise ValueError("Unrutted hillslope area must be finite.")
    represented_area_before_m2 = float(
        sum(
            float(plan["strip_width_m"]) * _plan_total_length_m(plan)
            for plan in strip_plans
        )
        + float(remainder_width_m * hillslope_length_m)
    )
    area_error_before_m2 = float(hillslope_area_m2 - represented_area_before_m2)

    if abs(area_error_before_m2) > OUTSLOPE_UNRUTTED_AREA_EPSILON_M2 and strip_plans:
        comp_width = float(strip_plans[0]["strip_width_m"])
        if comp_width <= 0.0:
            comp_width = 0.0
        if comp_width > 0.0:
            compensation_m = float(area_error_before_m2 / comp_width)
            if not _unrutted.compensate(strip_plans[0], compensation_m):
                _record_invalid_compensation(
                    roads=roads,
                    results=results,
                    _move_outslope_candidate_to_status=_move_outslope_candidate_to_status,
                    strip_plans=strip_plans,
                    topaz_id_hill=topaz_id_hill,
                    wepp_id_int=wepp_id_int,
                )
                strip_plans = []

    if not strip_plans:
        return None

    represented_area_after_m2 = float(
        sum(
            float(plan["strip_width_m"]) * _plan_total_length_m(plan)
            for plan in strip_plans
        )
        + float(remainder_width_m * hillslope_length_m)
    )
    area_error_after_m2 = float(hillslope_area_m2 - represented_area_after_m2)

    if hillslope_record is not None:
        hillslope_record["top_ofe_compensation_m"] = float(
            sum(float(plan["top_ofe_compensation_m"]) for plan in strip_plans)
        )
        hillslope_record["bottom_ofe_compensation_m"] = sum(
            plan["bottom_ofe_compensation_m"] for plan in strip_plans
        )
        hillslope_record["area_error_before_compensation_m2"] = float(area_error_before_m2)
        hillslope_record["area_error_after_compensation_m2"] = float(area_error_after_m2)

    remainder_prepared_path = _emit_profiles(
        roads=roads,
        area_error_after_m2=area_error_after_m2,
        hillslope_area_m2=hillslope_area_m2,
        hillslope_length_m=hillslope_length_m,
        hillslope_record=hillslope_record,
        hillslope_width_m=hillslope_width_m,
        remainder_width_m=remainder_width_m,
        represented_area_after_m2=represented_area_after_m2,
        strip_plans=strip_plans,
        topaz_id_hill=topaz_id_hill,
        width_sum_before_scaling=width_sum_before_scaling,
    )
    return strip_plans, remainder_width_m, remainder_prepared_path
