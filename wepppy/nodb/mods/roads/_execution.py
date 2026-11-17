"""Run-local contributor execution and manifest assembly."""

from __future__ import annotations

import os
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import rasterio
from pyproj import CRS, Geod, Transformer

from . import _unrutted
from . import parameterization as roads_parameterization
import time
from . import _point_source, _unrutted_execution


from dataclasses import dataclass, field


@dataclass
class ExecutionResults:
    """Contributor outcomes and counters; never attached to persisted Roads state."""
    segment_pass_paths_by_wepp: dict = field(default_factory=lambda: defaultdict(list))
    segment_execution_records: list = field(default_factory=list)
    skipped_segments: list = field(default_factory=list)
    eligible_segment_count: int = 0
    mapped_segment_count: int = 0
    successful_segment_count: int = 0
    segment_sequence: int = 0
    failed_segment_records: list = field(default_factory=list)
    mapping_warning_counts: Counter = field(default_factory=Counter)
    mapping_warning_examples: list = field(default_factory=list)
    design_execution_counts: Counter = field(default_factory=Counter)
    fill_default_usage_counts: Counter = field(default_factory=Counter)
    replacement_pass_paths_by_wepp: dict = field(default_factory=lambda: defaultdict(list))
    outslope_unrutted_pending_segments: list = field(default_factory=list)
    outslope_unrutted_candidate_status: dict = field(default_factory=dict)
    outslope_unrutted_diagnostics: dict = field(default_factory=lambda: {
        "outslope_unrutted_targeted_hillslope_count": 0,
        "outslope_unrutted_included_segment_count": 0,
        "outslope_unrutted_excluded_segment_count": 0,
        "outslope_unrutted_capped_segment_count": 0,
        "outslope_unrutted_hillslope_records": [],
    })
    routing_mode_counts: Counter = field(default_factory=Counter)
    trace_invocation_count: int = 0
    trace_reaches_channel_count: int = 0
    trace_termination_reason_counts: Counter = field(default_factory=Counter)


@dataclass(frozen=True)
class SegmentTerrain:
    """Open DEM and transforms shared only for the duration of segment execution."""
    input_crs: CRS
    geod: Geod
    dem_dataset: Any
    input_to_wgs84: Transformer
    input_to_dem: Transformer


def write_execution_manifest(
    roads,
    results,
):
    """Attach parameterization and policy evidence before publishing the manifest."""
    for hill in results.outslope_unrutted_diagnostics.get("outslope_unrutted_hillslope_records", []):
        if hill.get("area_accounting_status") != "complete":
            hill["top_ofe_compensation_m"] = None
            hill["bottom_ofe_compensation_m"] = None
    for record in results.segment_execution_records:
        if record.get("design") != "outslope_unrutted":
            continue
        candidate = results.outslope_unrutted_candidate_status.get(record.get("segment_hillslope_id"), {})
        record.setdefault("source_segment_ids", candidate.get("source_segment_ids", [record["segment_id"]]))
        for key in ("placement_source", "placement_adjustment", "placement_adjustment_reason",
                    "original_top_landuse_length_m", "hillslope_length_m", "discha_median_m",
                    "top_landuse_length_m", "bottom_landuse_length_m", "upslope_runon_assumed_zero"):
            record.setdefault(key, None)
        record.setdefault("placement_policy", _unrutted.PLACEMENT_POLICY)
        record.setdefault("geometry_policy", _unrutted.POLICY)
        record.setdefault("connectivity_limitation", _unrutted.LIMITATION)
        if record.get("status") != "completed":
            record.update(area_accounting_status="unavailable",
                          area_accounting_reason=record.get("reason", "execution_failed"))
            for key in ("road_target_area_m2", "road_modeled_area_m2", "road_area_deficit_m2", "strip_width_factor", "top_ofe_compensation_m", "bottom_ofe_compensation_m"):
                record.setdefault(key, None)
    roads._attach_parameterization_records(results.segment_execution_records)
    Path(roads.roads_segment_pass_manifest_path).write_text(
        json.dumps(results.segment_execution_records, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    roads._append_roads_log(
        "run",
        "segment_manifest_written",
        {
            "segment_execution_count": len(results.segment_execution_records),
            "segment_pass_manifest_relpath": os.path.relpath(roads.roads_segment_pass_manifest_path, roads.wd),
        },
    )


def execute_segments(
    roads,
    attribute_field_map,
    dem_path,
    features,
    geod,
    input_crs,
    params,
    top2wepp,
    warning_limit,
):
    """Run contributors while the DEM and trace datasets retain their original lifetimes."""
    results = ExecutionResults()
    with rasterio.open(dem_path) as dem_dataset:
        if dem_dataset.crs is None:
            raise ValueError(f"Roads DEM is missing CRS metadata: {dem_path}")
        input_to_wgs84 = Transformer.from_crs(input_crs, CRS.from_epsg(4326), always_xy=True)
        input_to_dem = Transformer.from_crs(input_crs, dem_dataset.crs, always_xy=True)
        terrain = SegmentTerrain(input_crs, geod, dem_dataset, input_to_wgs84, input_to_dem)
        _point_source.execute_point_sources(
            roads=roads,
            results=results,
            terrain=terrain,
            attribute_field_map=attribute_field_map,
            features=features,
            params=params,
            top2wepp=top2wepp,
            warning_limit=warning_limit,
        )
        if results.outslope_unrutted_pending_segments:
            _unrutted_execution.execute_unrutted(
                roads=roads,
                results=results,
                terrain=terrain,
                dem_path=dem_path,
                params=params,
                top2wepp=top2wepp,
                warning_limit=warning_limit,
            )
    return results


def build_run_summary(
    roads,
    results,
    additive_targeted_ids,
    attribute_field_map,
    mapping_warning_count,
    mapping_warning_counts_dict,
    placement_marker,
    replacement_targeted_ids,
    skipped_reason_counts,
    staged_strategy,
    targeted_ids,
):
    """Assemble fields shared by failed and completed contributor attempts."""
    return {
        "eligible_segment_count": results.eligible_segment_count,
        "mapped_segment_count": results.mapped_segment_count,
        "executed_segment_count": results.successful_segment_count,
        "executed_channel_associated_segment_count": int(results.routing_mode_counts.get("channel_associated", 0)),
        "executed_non_channel_routed_segment_count": int(results.routing_mode_counts.get("non_channel_routed", 0)),
        "segment_routing_mode_counts": dict(sorted(results.routing_mode_counts.items())),
        "executed_outslope_rutted_segment_count": int(results.design_execution_counts.get("outslope_rutted", 0)),
        "executed_outslope_unrutted_segment_count": int(results.design_execution_counts.get("outslope_unrutted", 0)),
        "segment_design_counts": dict(sorted(results.design_execution_counts.items())),
        "fill_default_usage_counts": dict(sorted(results.fill_default_usage_counts.items())),
        "trace_invocation_count": int(results.trace_invocation_count),
        "trace_reached_channel_count": int(results.trace_reaches_channel_count),
        "trace_termination_reason_counts": dict(sorted(results.trace_termination_reason_counts.items())),
        "targeted_hillslope_count": len(targeted_ids),
        "targeted_hillslope_wepp_ids": targeted_ids,
        "additive_targeted_hillslope_wepp_ids": additive_targeted_ids,
        "replacement_targeted_hillslope_wepp_ids": replacement_targeted_ids,
        "skipped_segments": results.skipped_segments,
        "skipped_segment_reason_counts": dict(sorted(skipped_reason_counts.items())),
        "segment_execution_records": results.segment_execution_records,
        "parameterization_hash": roads_parameterization.configuration_hash(roads._parameterization),
        "pass_staging_strategy": staged_strategy,
        "segment_pass_count": results.successful_segment_count,
        "segment_pass_manifest_relpath": os.path.relpath(roads.roads_segment_pass_manifest_path, roads.wd),
        "roads_runs_relpath": os.path.relpath(roads.roads_runs_dir, roads.wd),
        "roads_output_relpath": os.path.relpath(roads.roads_output_dir, roads.wd),
        "roads_log_relpath": os.path.relpath(roads.roads_log_path, roads.wd),
        "mapping_warning_count": mapping_warning_count,
        "mapping_warning_counts": mapping_warning_counts_dict,
        "mapping_warning_examples": results.mapping_warning_examples,
        "attribute_field_map": dict(attribute_field_map),
        **results.outslope_unrutted_diagnostics,
        **placement_marker,
    }


def build_failed_segment_summary(
    roads,
    results,
    attribute_field_map,
    mapping_warning_count,
    mapping_warning_counts_dict,
    placement_marker,
    skipped_reason_counts,
):
    """Build the failed-attempt snapshot before the facade logs and raises."""
    additive_targeted_ids = sorted(
        int(wepp_id)
        for wepp_id, paths in results.segment_pass_paths_by_wepp.items()
        if paths
    )
    replacement_targeted_ids = sorted(
        int(wepp_id)
        for wepp_id, paths in results.replacement_pass_paths_by_wepp.items()
        if paths
    )
    targeted_ids = sorted(set(additive_targeted_ids) | set(replacement_targeted_ids))
    summary = build_run_summary(
        roads=roads,
        results=results,
        additive_targeted_ids=additive_targeted_ids,
        attribute_field_map=attribute_field_map,
        mapping_warning_count=mapping_warning_count,
        mapping_warning_counts_dict=mapping_warning_counts_dict,
        placement_marker=placement_marker,
        replacement_targeted_ids=replacement_targeted_ids,
        skipped_reason_counts=skipped_reason_counts,
        staged_strategy={},
        targeted_ids=targeted_ids,
    )
    summary.update({
        "status": "failed",
        "failed_stage": "segment_runs",
        "failed_segment_count": len(results.failed_segment_records),
        "failed_segments": results.failed_segment_records,
        "error": (
            "Roads segment execution failed for "
            f"{len(results.failed_segment_records)} segment(s); see roads.segment.pass.manifest.json and roads.log."
        ),
        "failed_at": int(time.time()),
    })
    return summary
