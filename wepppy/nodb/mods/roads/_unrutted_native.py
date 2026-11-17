"""Native execution and result records for unrutted strips and remainders."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Tuple


from wepppy.observability.safe_traceback import safe_text
from wepppy.observability.safe_logging import current_profile
from wepppy.observability.secret_profiles import WORKER
from . import _unrutted


def _materialize_strip(
    roads,
    plan,
    routed_mofe_management_cache_by_traffic_and_order,
    segment_inputs,
    segment_run_id,
):
    soil_template_path = roads._resolve_legacy_soil_template_path(
        design="outslope_rutted",
        surface=segment_inputs["surface"],
        soil_texture=segment_inputs["soil_texture"],
    )

    ofe_order = plan["ofe_order"]
    management_cache_key = (str(segment_inputs["traffic"]), tuple(ofe_order))
    management_path = routed_mofe_management_cache_by_traffic_and_order.get(management_cache_key)
    if management_path is None:
        management_template_path = roads._resolve_legacy_management_template_path(
            traffic=segment_inputs["traffic"]
        )
        management_path = (
            Path(roads.roads_runs_dir)
            / (
                f"{management_template_path.stem}.routed_mofe_"
                + "_".join(str(value) for value in ofe_order)
                + ".man"
            )
        )
        roads._build_routed_mofe_management_file(
            template_path=management_template_path,
            output_path=management_path,
            ofe_order=ofe_order,
        )
        routed_mofe_management_cache_by_traffic_and_order[management_cache_key] = management_path

    segment_soil_path = Path(roads.roads_runs_dir) / f"p{segment_run_id}.routed_mofe.sol"
    segment_slope_path = Path(roads.roads_runs_dir) / f"p{segment_run_id}.slp"

    roads._build_routed_mofe_soil_file(
        template_path=soil_template_path,
        output_path=segment_soil_path,
        traffic=segment_inputs["traffic"],
        surface=segment_inputs["surface"],
        rfg_pct=segment_inputs["rfg_pct"],
        ofe_order=ofe_order,
    )

    shutil.copyfile(plan["slope_path"], segment_slope_path)
    _unrutted.slope_area(segment_slope_path)
    return ofe_order, management_path, segment_soil_path, segment_slope_path


def _run_strip(
    roads,
    results,
    inclusion_ratio,
    management_path,
    overlap_length_m,
    plan,
    segment_hillslope_id,
    segment_run_id,
    segment_slope_path,
    segment_soil_path,
    source_segment_id,
    topaz_id_hill,
    wepp_id_int,
):
    """Retain a failed native strip while allowing other contributors to finish."""
    try:
        sim_years = int(roads.wepp_instance.climate_instance.input_years)
        roads._run_segment_hillslope(
            segment_run_id=segment_run_id,
            climate_wepp_id=int(wepp_id_int),
            sim_years=sim_years,
            wepp_bin=getattr(roads.wepp_instance, "wepp_bin", None),
            single_ofe_management_path=management_path,
            single_ofe_soil_path=segment_soil_path,
            single_ofe_slope_path=segment_slope_path,
        )
    except Exception as exc:  # broad-except: retain native strip failure evidence while other strips continue
        results.skipped_segments.append(
            {
                "segment_id": source_segment_id,
                "segment_hillslope_id": segment_hillslope_id,
                "reason": "segment_run_failed",
            }
        )
        results.segment_execution_records.append(
            {
                "segment_id": source_segment_id,
                "segment_hillslope_id": segment_hillslope_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": int(wepp_id_int),
                "target_hillslope_topaz_id": int(topaz_id_hill),
                "status": "failed",
                "routing_mode": "outslope_unrutted_replacement",
                "reason": "segment_run_failed",
                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                "design": "outslope_unrutted",
                **plan["accounting"],
                "overlap_length_m": overlap_length_m,
                "inclusion_ratio": inclusion_ratio,
            }
        )
        results.failed_segment_records.append(
            {
                "segment_id": source_segment_id,
                "segment_hillslope_id": segment_hillslope_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": int(wepp_id_int),
                "routing_mode": "outslope_unrutted_replacement",
                "reason": "segment_run_failed",
                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
            }
        )
        roads._append_roads_log(
            "run",
            "segment_run_failed",
            {
                "segment_id": source_segment_id,
                "segment_hillslope_id": segment_hillslope_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": int(wepp_id_int),
                "routing_mode": "outslope_unrutted_replacement",
                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
            },
        )
        return None
    return True


def _strip_pass(
    roads,
    results,
    inclusion_ratio,
    overlap_length_m,
    plan,
    segment_hillslope_id,
    segment_run_id,
    source_segment_id,
    topaz_id_hill,
    wepp_id_int,
):
    segment_pass_path = Path(roads.roads_output_dir) / f"H{segment_run_id}.pass.dat"
    if not segment_pass_path.exists():
        results.skipped_segments.append(
            {
                "segment_id": source_segment_id,
                "segment_hillslope_id": segment_hillslope_id,
                "reason": "segment_pass_missing",
            }
        )
        results.segment_execution_records.append(
            {
                "segment_id": source_segment_id,
                "segment_hillslope_id": segment_hillslope_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": int(wepp_id_int),
                "target_hillslope_topaz_id": int(topaz_id_hill),
                "status": "failed",
                "routing_mode": "outslope_unrutted_replacement",
                "reason": "segment_pass_missing",
                "design": "outslope_unrutted",
                **plan["accounting"],
                "overlap_length_m": overlap_length_m,
                "inclusion_ratio": inclusion_ratio,
            }
        )
        results.failed_segment_records.append(
            {
                "segment_id": source_segment_id,
                "segment_hillslope_id": segment_hillslope_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": int(wepp_id_int),
                "routing_mode": "outslope_unrutted_replacement",
                "reason": "segment_pass_missing",
            }
        )
        roads._append_roads_log(
            "run",
            "segment_run_failed",
            {
                "segment_id": source_segment_id,
                "segment_hillslope_id": segment_hillslope_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": int(wepp_id_int),
                "routing_mode": "outslope_unrutted_replacement",
                "reason": "segment_pass_missing",
            },
        )
        return None
    return segment_pass_path


def _record_strip(
    roads,
    results,
    bottom_landuse_length_m,
    discha_median_m,
    fill_profile,
    inclusion_ratio,
    ofe_order,
    overlap_length_m,
    parity_profile,
    plan,
    profile,
    routed_buffer_profile,
    segment_hillslope_id,
    segment_inputs,
    segment_pass_path,
    segment_run_id,
    source_segment_id,
    strip_width_m,
    top_landuse_length_m,
    topaz_id_hill,
    wepp_id_int,
):
    results.successful_segment_count += 1
    results.routing_mode_counts["outslope_unrutted_replacement"] += 1
    results.design_execution_counts["outslope_unrutted"] += 1
    results.replacement_pass_paths_by_wepp[int(wepp_id_int)].append(str(segment_pass_path))

    execution_record = {
        "segment_id": source_segment_id,
        "segment_hillslope_id": segment_hillslope_id,
        "segment_run_id": segment_run_id,
        "target_hillslope_wepp_id": int(wepp_id_int),
        "target_hillslope_topaz_id": int(topaz_id_hill),
        "status": "completed",
        "routing_mode": "outslope_unrutted_replacement",
        "routing_eligibility": "outslope_unrutted_replacement",
        "design": "outslope_unrutted",
        "surface": segment_inputs["surface"],
        "traffic": segment_inputs["traffic"],
        "soil_texture": segment_inputs["soil_texture"],
        "rfg_pct": segment_inputs["rfg_pct"],
        "road_width_m": segment_inputs["road_width_m"],
        "strip_width_m": strip_width_m,
        "fill_length_m": fill_profile["fill_length_m"],
        "fill_slope_pct": fill_profile["fill_slope_pct"],
        "segment_length_m": profile["segment_length_m"],
        "slope_pct_raw": profile["raw_slope_pct"],
        "slope_pct_clamped": profile["slope_pct"],
        "elevation_high_m": profile["elevation_high_m"],
        "elevation_low_m": profile["elevation_low_m"],
        "overlap_length_m": overlap_length_m,
        "inclusion_ratio": inclusion_ratio,
        "segment_pass_relpath": os.path.relpath(segment_pass_path, roads.wd),
        "contributor_ofe_count": len(ofe_order),
        "top_landuse_length_m": top_landuse_length_m,
        "bottom_landuse_length_m": bottom_landuse_length_m,
        "discha_median_m": discha_median_m,
        **plan["accounting"],
        **parity_profile,
        **fill_profile,
        **routed_buffer_profile,
    }
    results.segment_execution_records.append(execution_record)
    roads._append_roads_log("run", "segment_run_completed", execution_record)


def execute_strip(
    roads,
    results,
    plan,
    routed_mofe_management_cache_by_traffic_and_order,
    topaz_id_hill,
    wepp_id_int,
):
    """Materialize and execute one strip using the facade compatibility methods."""
    source_segment_id = str(plan["source_segment_id"])
    segment_hillslope_id = str(plan["segment_hillslope_id"])
    overlap_length_m = float(plan["overlap_length_m"])
    inclusion_ratio = float(plan["inclusion_ratio"])
    segment_inputs = plan["segment_inputs"]
    profile = plan["profile"]
    parity_profile = plan["parity_profile"]
    fill_profile = plan["fill_profile"]
    routed_buffer_profile = plan["routed_buffer_profile"]
    top_landuse_length_m = float(plan["top_landuse_length_m"])
    bottom_landuse_length_m = float(plan["bottom_landuse_length_m"])
    has_downslope_landuse = bool(plan["has_downslope_landuse"])
    discha_median_m = float(plan["discha_median_m"])
    strip_width_m = float(plan["strip_width_m"])

    results.segment_sequence += 1
    segment_run_id = 900000 + results.segment_sequence

    (ofe_order, management_path, segment_soil_path, segment_slope_path) = _materialize_strip(
        roads=roads,
        plan=plan,
        routed_mofe_management_cache_by_traffic_and_order=routed_mofe_management_cache_by_traffic_and_order,
        segment_inputs=segment_inputs,
        segment_run_id=segment_run_id,
    )

    if not _run_strip(
        roads=roads,
        results=results,
        inclusion_ratio=inclusion_ratio,
        management_path=management_path,
        overlap_length_m=overlap_length_m,
        plan=plan,
        segment_hillslope_id=segment_hillslope_id,
        segment_run_id=segment_run_id,
        segment_slope_path=segment_slope_path,
        segment_soil_path=segment_soil_path,
        source_segment_id=source_segment_id,
        topaz_id_hill=topaz_id_hill,
        wepp_id_int=wepp_id_int,
    ):
        return

    segment_pass_path = _strip_pass(
        roads=roads,
        results=results,
        inclusion_ratio=inclusion_ratio,
        overlap_length_m=overlap_length_m,
        plan=plan,
        segment_hillslope_id=segment_hillslope_id,
        segment_run_id=segment_run_id,
        source_segment_id=source_segment_id,
        topaz_id_hill=topaz_id_hill,
        wepp_id_int=wepp_id_int,
    )
    if segment_pass_path is None:
        return

    _record_strip(
        roads=roads,
        results=results,
        bottom_landuse_length_m=bottom_landuse_length_m,
        discha_median_m=discha_median_m,
        fill_profile=fill_profile,
        inclusion_ratio=inclusion_ratio,
        ofe_order=ofe_order,
        overlap_length_m=overlap_length_m,
        parity_profile=parity_profile,
        plan=plan,
        profile=profile,
        routed_buffer_profile=routed_buffer_profile,
        segment_hillslope_id=segment_hillslope_id,
        segment_inputs=segment_inputs,
        segment_pass_path=segment_pass_path,
        segment_run_id=segment_run_id,
        source_segment_id=source_segment_id,
        strip_width_m=strip_width_m,
        top_landuse_length_m=top_landuse_length_m,
        topaz_id_hill=topaz_id_hill,
        wepp_id_int=wepp_id_int,
    )


def _materialize_remainder(
    roads,
    remainder_prepared_path,
    routed_mofe_management_cache_by_traffic_and_order,
    segment_run_id,
    strip_plans,
):
    remainder_segment_inputs = strip_plans[0]["segment_inputs"]
    remainder_soil_template_path = roads._resolve_legacy_soil_template_path(
        design="outslope_rutted",
        surface=remainder_segment_inputs["surface"],
        soil_texture=remainder_segment_inputs["soil_texture"],
    )

    remainder_order: Tuple[int, ...] = (3,)
    management_cache_key = (str(remainder_segment_inputs["traffic"]), remainder_order)
    management_path = routed_mofe_management_cache_by_traffic_and_order.get(management_cache_key)
    if management_path is None:
        management_template_path = roads._resolve_legacy_management_template_path(
            traffic=remainder_segment_inputs["traffic"]
        )
        management_path = (
            Path(roads.roads_runs_dir)
            / (
                f"{management_template_path.stem}.routed_mofe_"
                + "_".join(str(value) for value in remainder_order)
                + ".man"
            )
        )
        roads._build_routed_mofe_management_file(
            template_path=management_template_path,
            output_path=management_path,
            ofe_order=remainder_order,
        )
        routed_mofe_management_cache_by_traffic_and_order[management_cache_key] = management_path

    remainder_soil_path = Path(roads.roads_runs_dir) / f"p{segment_run_id}.routed_mofe.sol"
    remainder_slope_path = Path(roads.roads_runs_dir) / f"p{segment_run_id}.slp"
    roads._build_routed_mofe_soil_file(
        template_path=remainder_soil_template_path,
        output_path=remainder_soil_path,
        traffic=remainder_segment_inputs["traffic"],
        surface=remainder_segment_inputs["surface"],
        rfg_pct=remainder_segment_inputs["rfg_pct"],
        ofe_order=remainder_order,
    )
    shutil.copyfile(remainder_prepared_path, remainder_slope_path)
    _unrutted.slope_area(remainder_slope_path)
    return management_path, remainder_soil_path, remainder_slope_path


def _record_remainder_result(
    roads,
    results,
    hillslope_length_m,
    remainder_segment_id,
    remainder_width_m,
    segment_run_id,
    topaz_id_hill,
    wepp_id_int,
):
    remainder_pass_path = Path(roads.roads_output_dir) / f"H{segment_run_id}.pass.dat"
    if not remainder_pass_path.exists():
        results.skipped_segments.append(
            {
                "segment_id": remainder_segment_id,
                "reason": "segment_pass_missing",
            }
        )
        results.segment_execution_records.append(
            {
                "segment_id": remainder_segment_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": int(wepp_id_int),
                "target_hillslope_topaz_id": int(topaz_id_hill),
                "status": "failed",
                "routing_mode": "outslope_unrutted_replacement",
                "reason": "segment_pass_missing",
                "design": "outslope_unrutted_remainder",
            }
        )
        results.failed_segment_records.append(
            {
                "segment_id": remainder_segment_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": int(wepp_id_int),
                "routing_mode": "outslope_unrutted_replacement",
                "reason": "segment_pass_missing",
            }
        )
        roads._append_roads_log(
            "run",
            "segment_run_failed",
            {
                "segment_id": remainder_segment_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": int(wepp_id_int),
                "routing_mode": "outslope_unrutted_replacement",
                "reason": "segment_pass_missing",
            },
        )
    else:
        results.successful_segment_count += 1
        results.routing_mode_counts["outslope_unrutted_replacement_remainder"] += 1
        results.replacement_pass_paths_by_wepp[int(wepp_id_int)].append(str(remainder_pass_path))
        execution_record = {
            "segment_id": remainder_segment_id,
            "segment_run_id": segment_run_id,
            "target_hillslope_wepp_id": int(wepp_id_int),
            "target_hillslope_topaz_id": int(topaz_id_hill),
            "status": "completed",
            "routing_mode": "outslope_unrutted_replacement",
            "routing_eligibility": "outslope_unrutted_replacement",
            "design": "outslope_unrutted_remainder",
            "segment_pass_relpath": os.path.relpath(remainder_pass_path, roads.wd),
            "strip_width_m": float(remainder_width_m),
            "segment_length_m": float(hillslope_length_m),
            "contributor_ofe_count": 1,
        }
        results.segment_execution_records.append(execution_record)
        roads._append_roads_log("run", "segment_run_completed", execution_record)


def execute_remainder(
    roads,
    results,
    hillslope_length_m,
    remainder_prepared_path,
    remainder_width_m,
    routed_mofe_management_cache_by_traffic_and_order,
    strip_plans,
    topaz_id_hill,
    wepp_id_int,
):
    """Execute a positive-width remainder with its original independent accounting."""
    remainder_segment_id = f"h{int(topaz_id_hill)}::remainder"
    results.segment_sequence += 1
    segment_run_id = 900000 + results.segment_sequence

    (management_path, remainder_soil_path, remainder_slope_path) = _materialize_remainder(
        roads=roads,
        remainder_prepared_path=remainder_prepared_path,
        routed_mofe_management_cache_by_traffic_and_order=routed_mofe_management_cache_by_traffic_and_order,
        segment_run_id=segment_run_id,
        strip_plans=strip_plans,
    )

    try:
        sim_years = int(roads.wepp_instance.climate_instance.input_years)
        roads._run_segment_hillslope(
            segment_run_id=segment_run_id,
            climate_wepp_id=int(wepp_id_int),
            sim_years=sim_years,
            wepp_bin=getattr(roads.wepp_instance, "wepp_bin", None),
            single_ofe_management_path=management_path,
            single_ofe_soil_path=remainder_soil_path,
            single_ofe_slope_path=remainder_slope_path,
        )
    except Exception as exc:  # broad-except: retain native remainder failure under the per-contributor result contract
        results.skipped_segments.append(
            {
                "segment_id": remainder_segment_id,
                "reason": "segment_run_failed",
            }
        )
        results.segment_execution_records.append(
            {
                "segment_id": remainder_segment_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": int(wepp_id_int),
                "target_hillslope_topaz_id": int(topaz_id_hill),
                "status": "failed",
                "routing_mode": "outslope_unrutted_replacement",
                "reason": "segment_run_failed",
                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                "design": "outslope_unrutted_remainder",
            }
        )
        results.failed_segment_records.append(
            {
                "segment_id": remainder_segment_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": int(wepp_id_int),
                "routing_mode": "outslope_unrutted_replacement",
                "reason": "segment_run_failed",
                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
            }
        )
        roads._append_roads_log(
            "run",
            "segment_run_failed",
            {
                "segment_id": remainder_segment_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": int(wepp_id_int),
                "routing_mode": "outslope_unrutted_replacement",
                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
            },
        )
    else:
        _record_remainder_result(
            roads=roads,
            results=results,
            hillslope_length_m=hillslope_length_m,
            remainder_segment_id=remainder_segment_id,
            remainder_width_m=remainder_width_m,
            segment_run_id=segment_run_id,
            topaz_id_hill=topaz_id_hill,
            wepp_id_int=wepp_id_int,
        )
