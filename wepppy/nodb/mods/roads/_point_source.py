"""Point-source routing, native input assembly and contributor execution."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import numpy as np
import rasterio

from wepppy.observability.safe_traceback import safe_text
from wepppy.observability.safe_logging import current_profile
from wepppy.observability.secret_profiles import WORKER


from dataclasses import dataclass

__all__ = [
    'TraceState',
    'execute_point_sources',
]


@dataclass
class TraceState:
    """Lazily loaded trace rasters and native entry point for one attempt."""
    context: Optional[Dict[str, Any]] = None
    function: Any = None


def _initialize_trace(
    roads,
    trace,
):
    """Load the flowpath rasters once, at the first routable seed."""
    trace_paths = roads._resolve_trace_raster_paths()
    with rasterio.open(trace_paths["topaz_id_raster_path"]) as topaz_dataset:
        topaz_arr = topaz_dataset.read(1, masked=True)
        topaz_values = np.asarray(topaz_arr.filled(np.nan), dtype=float)
        if np.ma.isMaskedArray(topaz_arr):
            topaz_values[np.ma.getmaskarray(topaz_arr)] = np.nan
        nodata = topaz_dataset.nodata
        if nodata is not None and np.isfinite(nodata):
            topaz_values[np.isclose(topaz_values, nodata, rtol=0.0, atol=1e-8)] = np.nan
    from wepppyo3.roads_flowpath import trace_downslope_flowpath

    trace.context = {"paths": trace_paths, "topaz_values": topaz_values}
    trace.function = trace_downslope_flowpath
    roads._append_roads_log(
        "run",
        "trace_context_initialized",
        {
            "trace_relief_path": roads._path_for_summary(trace_paths["dem_path"]),
            "trace_flovec_path": roads._path_for_summary(trace_paths["flovec_path"]),
            "trace_subwta_path": roads._path_for_summary(trace_paths["topaz_id_raster_path"]),
            "trace_channel_path": roads._path_for_summary(trace_paths["channel_raster_path"]),
        },
    )


def _invoke_trace(
    roads,
    results,
    trace,
    params,
    routing_mode,
    seed_col,
    seed_row,
    segment_id,
):
    """Record native tracing failure without aborting other contributors."""
    assert trace.context is not None and trace.function is not None
    trace_max_steps = int(params.get("trace_max_steps", 20000))
    results.trace_invocation_count += 1
    try:
        trace_result = trace.function(
            trace.context["paths"]["topaz_id_raster_path"],
            trace.context["paths"]["flovec_path"],
            trace.context["paths"]["dem_path"],
            seed_row,
            seed_col,
            channel_path=trace.context["paths"]["channel_raster_path"],
            max_steps=trace_max_steps,
            wbt=True,
        )
    except Exception as exc:  # broad-except: native trace failures become per-segment evidence while remaining contributors continue
        results.skipped_segments.append({"segment_id": segment_id, "reason": "trace_execution_failed"})
        results.segment_execution_records.append(
            {
                "segment_id": segment_id,
                "status": "failed",
                "routing_mode": routing_mode,
                "reason": "trace_execution_failed",
                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
            }
        )
        results.failed_segment_records.append(
            {
                "segment_id": segment_id,
                "reason": "trace_execution_failed",
                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
            }
        )
        roads._append_roads_log(
            "run",
            "segment_trace_failed",
            {
                "segment_id": segment_id,
                "routing_mode": routing_mode,
                "seed_row": seed_row,
                "seed_col": seed_col,
                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
            },
        )
        return None
    return (trace_result,)


def _admit_trace(
    roads,
    results,
    trace,
    routing_mode,
    seed_col,
    seed_row,
    segment_id,
    trace_result,
):
    """Admit only a traced channel and a resolvable receiving hillslope."""
    termination_reason = str(trace_result.get("termination_reason") or "unknown")
    results.trace_termination_reason_counts[termination_reason] += 1
    reaches_channel = bool(trace_result.get("reaches_channel"))
    if reaches_channel:
        results.trace_reaches_channel_count += 1
    trace_summary = {
        "trace_seed_row": seed_row,
        "trace_seed_col": seed_col,
        "trace_reaches_channel": reaches_channel,
        "trace_termination_reason": termination_reason,
        "trace_path_length_m": roads._as_float_or_none(trace_result.get("path_length_m")),
        "trace_mean_slope": roads._as_float_or_none(trace_result.get("mean_slope")),
        "trace_drop_m": roads._as_float_or_none(trace_result.get("drop_m")),
        "trace_profile_point_count": (
            len(trace_result.get("rows"))
            if isinstance(trace_result.get("rows"), list)
            else 0
        ),
        "trace_segment_slope_count": (
            len(trace_result.get("segment_slope"))
            if isinstance(trace_result.get("segment_slope"), list)
            else 0
        ),
    }
    if not reaches_channel:
        results.skipped_segments.append({"segment_id": segment_id, "reason": "trace_did_not_reach_channel"})
        results.segment_execution_records.append(
            {
                "segment_id": segment_id,
                "status": "skipped",
                "routing_mode": routing_mode,
                "reason": "trace_did_not_reach_channel",
                **trace_summary,
            }
        )
        roads._append_roads_log(
            "run",
            "segment_skipped",
            {
                "segment_id": segment_id,
                "routing_mode": routing_mode,
                "reason": "trace_did_not_reach_channel",
                "trace_termination_reason": termination_reason,
            },
        )
        return None

    chn_topaz_int = roads._as_int_or_none(trace_result.get("channel_topaz_id"))
    if chn_topaz_int is None:
        results.skipped_segments.append({"segment_id": segment_id, "reason": "trace_channel_topaz_missing"})
        results.segment_execution_records.append(
            {
                "segment_id": segment_id,
                "status": "skipped",
                "routing_mode": routing_mode,
                "reason": "trace_channel_topaz_missing",
                **trace_summary,
            }
        )
        roads._append_roads_log(
            "run",
            "segment_skipped",
            {
                "segment_id": segment_id,
                "routing_mode": routing_mode,
                "reason": "trace_channel_topaz_missing",
            },
        )
        return None

    hill_topaz_int = roads._resolve_trace_receiving_hillslope_topaz(
        trace_result=trace_result,
        topaz_values=trace.context["topaz_values"],
    )
    if hill_topaz_int is None:
        results.skipped_segments.append(
            {"segment_id": segment_id, "reason": "trace_receiving_hillslope_missing"}
        )
        results.segment_execution_records.append(
            {
                "segment_id": segment_id,
                "status": "skipped",
                "routing_mode": routing_mode,
                "reason": "trace_receiving_hillslope_missing",
                **trace_summary,
            }
        )
        roads._append_roads_log(
            "run",
            "segment_skipped",
            {
                "segment_id": segment_id,
                "routing_mode": routing_mode,
                "reason": "trace_receiving_hillslope_missing",
                "channel_topaz_id": chn_topaz_int,
            },
        )
        return None
    return trace_summary, hill_topaz_int, chn_topaz_int


def _trace_segment(
    roads,
    results,
    trace,
    params,
    properties,
    routing_mode,
    segment_id,
):
    seed_row = roads._as_int_or_none(properties.get("_roads_lowpoint_row"))
    seed_col = roads._as_int_or_none(properties.get("_roads_lowpoint_col"))
    if seed_row is None or seed_col is None:
        results.skipped_segments.append({"segment_id": segment_id, "reason": "trace_seed_cell_missing"})
        results.segment_execution_records.append(
            {
                "segment_id": segment_id,
                "status": "skipped",
                "routing_mode": routing_mode,
                "reason": "trace_seed_cell_missing",
            }
        )
        roads._append_roads_log(
            "run",
            "segment_skipped",
            {
                "segment_id": segment_id,
                "routing_mode": routing_mode,
                "reason": "trace_seed_cell_missing",
            },
        )
        return None

    if trace.context is None:
        _initialize_trace(
            roads=roads,
            trace=trace,
        )
    invoked = _invoke_trace(
        roads=roads,
        results=results,
        trace=trace,
        params=params,
        routing_mode=routing_mode,
        seed_col=seed_col,
        seed_row=seed_row,
        segment_id=segment_id,
    )
    if invoked is None:
        return None
    trace_result, = invoked

    admitted = _admit_trace(
        roads=roads,
        results=results,
        trace=trace,
        routing_mode=routing_mode,
        seed_col=seed_col,
        seed_row=seed_row,
        segment_id=segment_id,
        trace_result=trace_result,
    )
    if admitted is None:
        return None
    trace_summary, hill_topaz_int, chn_topaz_int = admitted
    return trace_result, trace_summary, hill_topaz_int, chn_topaz_int


def _route_segment(
    roads,
    results,
    trace,
    params,
    properties,
    segment_id,
    top2wepp,
):
    """Resolve direct or traced routing before mapping a contributor."""
    routing_eligibility = str(properties.get("_roads_routing_eligibility") or "unknown")
    channel_hill_topaz = roads._as_int_or_none(properties.get("topaz_id_hill_lowpoint"))
    channel_chn_topaz = roads._as_int_or_none(properties.get("topaz_id_chn_lowpoint"))
    non_channel_routable = roads._is_truthy_property(
        properties.get("_roads_non_channel_routable")
    ) or routing_eligibility == "non_channel_routable"

    routing_mode = "channel_associated" if (
        channel_hill_topaz is not None and channel_chn_topaz is not None
    ) else "non_channel_routed"
    if routing_mode == "non_channel_routed" and not non_channel_routable:
        results.skipped_segments.append({"segment_id": segment_id, "reason": "missing_topaz_lowpoint_ids"})
        roads._append_roads_log(
            "run",
            "segment_skipped",
            {"segment_id": segment_id, "reason": "missing_topaz_lowpoint_ids"},
        )
        return None

    trace_result: Optional[Dict[str, Any]] = None
    trace_summary: Dict[str, Any] = {}
    hill_topaz_int: Optional[int] = None
    chn_topaz_int: Optional[int] = None
    if routing_mode == "channel_associated":
        hill_topaz_int = channel_hill_topaz
        chn_topaz_int = channel_chn_topaz
        if hill_topaz_int is None or chn_topaz_int is None:
            results.skipped_segments.append(
                {"segment_id": segment_id, "reason": "invalid_topaz_lowpoint_ids"}
            )
            roads._append_roads_log(
                "run",
                "segment_skipped",
                {"segment_id": segment_id, "reason": "invalid_topaz_lowpoint_ids"},
            )
            return None
    else:
        traced = _trace_segment(
            roads=roads,
            results=results,
            trace=trace,
            params=params,
            properties=properties,
            routing_mode=routing_mode,
            segment_id=segment_id,
        )
        if traced is None:
            return None
        trace_result, trace_summary, hill_topaz_int, chn_topaz_int = traced

    wepp_id = top2wepp.get(int(hill_topaz_int))
    if wepp_id is None:
        results.skipped_segments.append(
            {"segment_id": segment_id, "reason": "translator_missing_hillslope_map"}
        )
        results.segment_execution_records.append(
            {
                "segment_id": segment_id,
                "status": "skipped",
                "routing_mode": routing_mode,
                "reason": "translator_missing_hillslope_map",
                "topaz_id_hill_lowpoint": int(hill_topaz_int),
                **trace_summary,
            }
        )
        roads._append_roads_log(
            "run",
            "segment_skipped",
            {
                "segment_id": segment_id,
                "routing_mode": routing_mode,
                "reason": "translator_missing_hillslope_map",
                "topaz_id_hill_lowpoint": int(hill_topaz_int),
            },
        )
        return None
    return routing_eligibility, routing_mode, trace_result, trace_summary, hill_topaz_int, chn_topaz_int, wepp_id


def _materialize_inputs(
    roads,
    results,
    management_cache_by_traffic,
    profile,
    properties,
    routed_management_cache_by_traffic,
    routed_three_ofe_management_cache_by_traffic,
    routing_mode,
    segment_inputs,
    segment_run_id,
    trace_result,
):
    """Write the existing single, two, or three OFE point-source inputs."""
    soil_template_path = roads._resolve_legacy_soil_template_path(
        design=segment_inputs["design"],
        surface=segment_inputs["surface"],
        soil_texture=segment_inputs["soil_texture"],
    )
    segment_soil_suffix = "single_ofe"
    management_path: Path
    segment_soil_path = Path(roads.roads_runs_dir) / f"p{segment_run_id}.single_ofe.sol"
    segment_slope_path = Path(roads.roads_runs_dir) / f"p{segment_run_id}.slp"
    routed_buffer_profile: Dict[str, Any] = {}
    fill_profile: Dict[str, float] = {}
    is_outslope_rutted = segment_inputs["design"] == "outslope_rutted"

    if is_outslope_rutted:
        if segment_inputs["resolution_sources"].get("fill_length_m") == "roads_default":
            results.fill_default_usage_counts["fill_length_m"] += 1
        if segment_inputs["resolution_sources"].get("fill_slope_pct") == "roads_default":
            results.fill_default_usage_counts["fill_slope_pct"] += 1

        fill_profile = roads._derive_fill_profile_from_inputs(
            fill_length_m=segment_inputs["fill_length_m"],
            fill_slope_pct=segment_inputs["fill_slope_pct"],
        )
        segment_soil_suffix = "routed_three_ofe"
        segment_soil_path = Path(roads.roads_runs_dir) / f"p{segment_run_id}.routed_three_ofe.sol"
        management_path = routed_three_ofe_management_cache_by_traffic.get(segment_inputs["traffic"])
        if management_path is None:
            management_path = roads._materialize_routed_three_ofe_management_template(
                traffic=segment_inputs["traffic"]
            )
            routed_three_ofe_management_cache_by_traffic[segment_inputs["traffic"]] = management_path
        roads._build_routed_three_ofe_soil_file(
            template_path=soil_template_path,
            output_path=segment_soil_path,
            traffic=segment_inputs["traffic"],
            surface=segment_inputs["surface"],
            rfg_pct=segment_inputs["rfg_pct"],
        )

        if routing_mode == "channel_associated":
            routed_buffer_profile = roads._derive_buffer_profile_from_feature_or_defaults(
                properties=properties,
                road_profile=profile,
            )
        else:
            assert trace_result is not None
            routed_buffer_profile = roads._derive_buffer_profile_from_trace(trace_result)

        roads._write_routed_three_ofe_slope_file(
            segment_slope_path,
            width_m=segment_inputs["road_width_m"],
            road_length_m=profile["segment_length_m"],
            road_slope_pct=profile["slope_pct"],
            fill_length_m=fill_profile["fill_length_m"],
            fill_slope_pct=fill_profile["fill_slope_pct"],
            buffer_length_m=routed_buffer_profile["buffer_length_m"],
            buffer_slope_pct=routed_buffer_profile["buffer_slope_pct"],
        )
    elif routing_mode == "channel_associated":
        management_path = management_cache_by_traffic.get(segment_inputs["traffic"])
        if management_path is None:
            management_path = roads._materialize_single_ofe_management_template(
                traffic=segment_inputs["traffic"]
            )
            management_cache_by_traffic[segment_inputs["traffic"]] = management_path
        roads._build_single_ofe_soil_file(
            template_path=soil_template_path,
            output_path=segment_soil_path,
            traffic=segment_inputs["traffic"],
            surface=segment_inputs["surface"],
            rfg_pct=segment_inputs["rfg_pct"],
        )
        roads._write_single_ofe_slope_file(
            segment_slope_path,
            width_m=segment_inputs["road_width_m"],
            length_m=profile["segment_length_m"],
            slope_pct=profile["slope_pct"],
        )
    else:
        assert trace_result is not None
        segment_soil_suffix = "routed_two_ofe"
        segment_soil_path = Path(roads.roads_runs_dir) / f"p{segment_run_id}.routed_two_ofe.sol"
        management_path = routed_management_cache_by_traffic.get(segment_inputs["traffic"])
        if management_path is None:
            management_path = roads._materialize_routed_two_ofe_management_template(
                traffic=segment_inputs["traffic"]
            )
            routed_management_cache_by_traffic[segment_inputs["traffic"]] = management_path
        roads._build_routed_two_ofe_soil_file(
            template_path=soil_template_path,
            output_path=segment_soil_path,
            traffic=segment_inputs["traffic"],
            surface=segment_inputs["surface"],
            rfg_pct=segment_inputs["rfg_pct"],
        )
        routed_buffer_profile = roads._derive_buffer_profile_from_trace(trace_result)
        roads._write_routed_two_ofe_slope_file(
            segment_slope_path,
            width_m=segment_inputs["road_width_m"],
            road_length_m=profile["segment_length_m"],
            road_slope_pct=profile["slope_pct"],
            buffer_length_m=routed_buffer_profile["buffer_length_m"],
            buffer_slope_pct=routed_buffer_profile["buffer_slope_pct"],
        )
    return segment_soil_suffix, management_path, segment_soil_path, segment_slope_path, routed_buffer_profile, fill_profile


def _log_inputs(
    roads,
    chn_topaz_int,
    fill_profile,
    hill_topaz_int,
    profile,
    routed_buffer_profile,
    routing_eligibility,
    routing_mode,
    segment_id,
    segment_inputs,
    segment_run_id,
    segment_soil_suffix,
    trace_summary,
    wepp_id_int,
):
    roads._append_roads_log(
        "run",
        "segment_inputs_ready",
        {
            "segment_id": segment_id,
            "segment_run_id": segment_run_id,
            "routing_mode": routing_mode,
            "routing_eligibility": routing_eligibility,
            "target_hillslope_wepp_id": wepp_id_int,
            "topaz_id_chn_lowpoint": int(chn_topaz_int),
            "topaz_id_hill_lowpoint": int(hill_topaz_int),
            "design": segment_inputs["design"],
            "surface": segment_inputs["surface"],
            "traffic": segment_inputs["traffic"],
            "soil_texture": segment_inputs["soil_texture"],
            "rfg_pct": segment_inputs["rfg_pct"],
            "soil_file_variant": segment_soil_suffix,
            "road_width_m": segment_inputs["road_width_m"],
            "fill_length_m": fill_profile.get("fill_length_m", segment_inputs.get("fill_length_m")),
            "fill_slope_pct": fill_profile.get("fill_slope_pct", segment_inputs.get("fill_slope_pct")),
            "segment_length_m": profile["segment_length_m"],
            **fill_profile,
            "slope_pct_raw": profile["raw_slope_pct"],
            "slope_pct_clamped": profile["slope_pct"],
            "high_point": profile["high_point"],
            "low_point": profile["low_point"],
            **trace_summary,
            **routed_buffer_profile,
        },
    )


def _run_native_segment(
    roads,
    results,
    management_path,
    routing_mode,
    segment_id,
    segment_run_id,
    segment_slope_path,
    segment_soil_path,
    trace_summary,
    wepp_id_int,
):
    """Run one contributor and retain native or missing-PASS failures."""
    try:
        sim_years = int(roads.wepp_instance.climate_instance.input_years)
        roads._run_segment_hillslope(
            segment_run_id=segment_run_id,
            climate_wepp_id=wepp_id_int,
            sim_years=sim_years,
            wepp_bin=getattr(roads.wepp_instance, "wepp_bin", None),
            single_ofe_management_path=management_path,
            single_ofe_soil_path=segment_soil_path,
            single_ofe_slope_path=segment_slope_path,
        )
    except Exception as exc:  # broad-except: retain native segment failures without aborting sibling contributors
        results.skipped_segments.append({"segment_id": segment_id, "reason": "segment_run_failed"})
        results.segment_execution_records.append(
            {
                "segment_id": segment_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": wepp_id_int,
                "status": "failed",
                "routing_mode": routing_mode,
                "reason": "segment_run_failed",
                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                **trace_summary,
            }
        )
        results.failed_segment_records.append(
            {
                "segment_id": segment_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": wepp_id_int,
                "routing_mode": routing_mode,
                "reason": "segment_run_failed",
                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
            }
        )
        roads._append_roads_log(
            "run",
            "segment_run_failed",
            {
                "segment_id": segment_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": wepp_id_int,
                "routing_mode": routing_mode,
                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
            },
        )
        return None

    segment_pass_path = Path(roads.roads_output_dir) / f"H{segment_run_id}.pass.dat"
    if not segment_pass_path.exists():
        results.skipped_segments.append({"segment_id": segment_id, "reason": "segment_pass_missing"})
        results.segment_execution_records.append(
            {
                "segment_id": segment_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": wepp_id_int,
                "status": "failed",
                "routing_mode": routing_mode,
                "reason": "segment_pass_missing",
                **trace_summary,
            }
        )
        results.failed_segment_records.append(
            {
                "segment_id": segment_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": wepp_id_int,
                "routing_mode": routing_mode,
                "reason": "segment_pass_missing",
            }
        )
        roads._append_roads_log(
            "run",
            "segment_run_failed",
            {
                "segment_id": segment_id,
                "segment_run_id": segment_run_id,
                "target_hillslope_wepp_id": wepp_id_int,
                "routing_mode": routing_mode,
                "reason": "segment_pass_missing",
            },
        )
        return None
    return segment_pass_path


def _record_completed_segment(
    roads,
    results,
    chn_topaz_int,
    fill_profile,
    hill_topaz_int,
    profile,
    routed_buffer_profile,
    routing_eligibility,
    routing_mode,
    segment_id,
    segment_inputs,
    segment_pass_path,
    segment_run_id,
    trace_summary,
    wepp_id_int,
):
    results.successful_segment_count += 1
    results.design_execution_counts[segment_inputs["design"]] += 1
    results.segment_pass_paths_by_wepp[wepp_id_int].append(str(segment_pass_path))
    execution_record = {
        "segment_id": segment_id,
        "segment_run_id": segment_run_id,
        "target_hillslope_wepp_id": wepp_id_int,
        "status": "completed",
        "routing_mode": routing_mode,
        "routing_eligibility": routing_eligibility,
        "topaz_id_chn_lowpoint": int(chn_topaz_int),
        "topaz_id_hill_lowpoint": int(hill_topaz_int),
        "design": segment_inputs["design"],
        "surface": segment_inputs["surface"],
        "traffic": segment_inputs["traffic"],
        "soil_texture": segment_inputs["soil_texture"],
        "rfg_pct": segment_inputs["rfg_pct"],
        "road_width_m": segment_inputs["road_width_m"],
        "fill_length_m": fill_profile.get("fill_length_m", segment_inputs.get("fill_length_m")),
        "fill_slope_pct": fill_profile.get("fill_slope_pct", segment_inputs.get("fill_slope_pct")),
        "segment_length_m": profile["segment_length_m"],
        "slope_pct_raw": profile["raw_slope_pct"],
        "slope_pct_clamped": profile["slope_pct"],
        "elevation_high_m": profile["elevation_high_m"],
        "elevation_low_m": profile["elevation_low_m"],
        "segment_pass_relpath": os.path.relpath(segment_pass_path, roads.wd),
        **fill_profile,
        **trace_summary,
        **routed_buffer_profile,
    }
    results.segment_execution_records.append(execution_record)
    roads._append_roads_log("run", "segment_run_completed", execution_record)


def _execute_point_source(
    roads,
    results,
    terrain,
    trace,
    attribute_field_map,
    design,
    design_source,
    feature,
    management_cache_by_traffic,
    params,
    properties,
    routed_management_cache_by_traffic,
    routed_three_ofe_management_cache_by_traffic,
    segment_id,
    top2wepp,
    warning_limit,
):
    """Resolve, assemble and execute one eligible point-source candidate."""
    route = _route_segment(
        roads=roads,
        results=results,
        trace=trace,
        params=params,
        properties=properties,
        segment_id=segment_id,
        top2wepp=top2wepp,
    )
    if route is None:
        return None
    routing_eligibility, routing_mode, trace_result, trace_summary, hill_topaz_int, chn_topaz_int, wepp_id = route

    results.mapped_segment_count += 1
    results.routing_mode_counts[routing_mode] += 1
    wepp_id_int = int(wepp_id)

    segment_inputs = roads._resolve_segment_run_inputs(
        properties=properties,
        params=params,
        segment_id=segment_id,
        design=design,
        warning_counts=results.mapping_warning_counts,
        warning_examples=results.mapping_warning_examples,
        warning_limit=warning_limit,
    )
    segment_inputs["resolution_sources"]["design"] = (
        "mapped_primary" if design_source == attribute_field_map.get("design") else "segment_property"
    )

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
        results.skipped_segments.append({"segment_id": segment_id, "reason": "segment_profile_unavailable"})
        results.segment_execution_records.append(
            {
                "segment_id": segment_id,
                "target_hillslope_wepp_id": wepp_id_int,
                "status": "skipped",
                "routing_mode": routing_mode,
                "reason": "segment_profile_unavailable",
                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                **trace_summary,
            }
        )
        roads._append_roads_log(
            "run",
            "segment_skipped",
            {
                "segment_id": segment_id,
                "target_hillslope_wepp_id": wepp_id_int,
                "routing_mode": routing_mode,
                "reason": "segment_profile_unavailable",
                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
            },
        )
        return None

    results.segment_sequence += 1
    segment_run_id = 900000 + results.segment_sequence
    (segment_soil_suffix, management_path, segment_soil_path, segment_slope_path, routed_buffer_profile, fill_profile) = _materialize_inputs(
        roads=roads,
        results=results,
        management_cache_by_traffic=management_cache_by_traffic,
        profile=profile,
        properties=properties,
        routed_management_cache_by_traffic=routed_management_cache_by_traffic,
        routed_three_ofe_management_cache_by_traffic=routed_three_ofe_management_cache_by_traffic,
        routing_mode=routing_mode,
        segment_inputs=segment_inputs,
        segment_run_id=segment_run_id,
        trace_result=trace_result,
    )

    _log_inputs(
        roads=roads,
        chn_topaz_int=chn_topaz_int,
        fill_profile=fill_profile,
        hill_topaz_int=hill_topaz_int,
        profile=profile,
        routed_buffer_profile=routed_buffer_profile,
        routing_eligibility=routing_eligibility,
        routing_mode=routing_mode,
        segment_id=segment_id,
        segment_inputs=segment_inputs,
        segment_run_id=segment_run_id,
        segment_soil_suffix=segment_soil_suffix,
        trace_summary=trace_summary,
        wepp_id_int=wepp_id_int,
    )

    segment_pass_path = _run_native_segment(
        roads=roads,
        results=results,
        management_path=management_path,
        routing_mode=routing_mode,
        segment_id=segment_id,
        segment_run_id=segment_run_id,
        segment_slope_path=segment_slope_path,
        segment_soil_path=segment_soil_path,
        trace_summary=trace_summary,
        wepp_id_int=wepp_id_int,
    )
    if segment_pass_path is None:
        return None

    _record_completed_segment(
        roads=roads,
        results=results,
        chn_topaz_int=chn_topaz_int,
        fill_profile=fill_profile,
        hill_topaz_int=hill_topaz_int,
        profile=profile,
        routed_buffer_profile=routed_buffer_profile,
        routing_eligibility=routing_eligibility,
        routing_mode=routing_mode,
        segment_id=segment_id,
        segment_inputs=segment_inputs,
        segment_pass_path=segment_pass_path,
        segment_run_id=segment_run_id,
        trace_summary=trace_summary,
        wepp_id_int=wepp_id_int,
    )


def execute_point_sources(
    roads,
    results,
    terrain,
    attribute_field_map,
    features,
    params,
    top2wepp,
    warning_limit,
):
    """Execute eligible point sources and defer unrutted candidates in source order."""
    management_cache_by_traffic = {}
    routed_management_cache_by_traffic = {}
    routed_three_ofe_management_cache_by_traffic = {}
    trace = TraceState()
    for feature_index, feature in enumerate(features):
        properties = feature.get("properties", {}) if isinstance(feature, Mapping) else {}
        segment_id = roads._segment_key(feature, fallback_index=feature_index)
        design, design_source = roads._resolve_design_for_feature(
            properties=properties,
            attribute_field_map=attribute_field_map,
            warning_counts=results.mapping_warning_counts,
            warning_examples=results.mapping_warning_examples,
            warning_limit=warning_limit,
            segment_id=segment_id,
        )

        if design is None:
            results.skipped_segments.append({"segment_id": segment_id, "reason": "design_not_eligible"})
            roads._append_roads_log(
                "run",
                "segment_skipped",
                {"segment_id": segment_id, "reason": "design_not_eligible"},
            )
            continue

        results.eligible_segment_count += 1
        if design == "outslope_unrutted":
            results.outslope_unrutted_pending_segments.append(
                {
                    "segment_id": segment_id,
                    "feature": feature,
                    "properties": properties,
                    "design_source": design_source,
                }
            )
            continue

        _execute_point_source(
            roads=roads,
            results=results,
            terrain=terrain,
            trace=trace,
            attribute_field_map=attribute_field_map,
            design=design,
            design_source=design_source,
            feature=feature,
            management_cache_by_traffic=management_cache_by_traffic,
            params=params,
            properties=properties,
            routed_management_cache_by_traffic=routed_management_cache_by_traffic,
            routed_three_ofe_management_cache_by_traffic=routed_three_ofe_management_cache_by_traffic,
            segment_id=segment_id,
            top2wepp=top2wepp,
            warning_limit=warning_limit,
        )
