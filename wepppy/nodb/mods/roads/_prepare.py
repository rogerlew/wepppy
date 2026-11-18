"""Roads preparation calculations and summary presentation.

These helpers keep transient preparation data local. The Roads facade owns all
lock scopes, lifecycle guards, conversion calls, and error translation.
"""
from __future__ import annotations

import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping

from wepppy.wepp.interchange import _roads_lifecycle as roads_lifecycle
from . import parameterization as roads_parameterization, _unrutted
from ._constants import LEGACY_DESIGN_KEYS, DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT

__all__ = ["configuration", "conversion_arguments", "build_summary", "log_summary"]


def configuration(controller):
    """Resolve the parameter snapshot and design mapping before mutation."""
    params = controller._normalize_params_with_defaults(getattr(controller, "_roads_params", {}))
    attribute_field_map = controller._normalize_attribute_field_map(
        params.get("attribute_field_map"),
        known_fields=None,
    )
    design_property_keys = controller._dedupe_keys(
        (
            [attribute_field_map.get("design")] if attribute_field_map.get("design") else []
        )
        + list(LEGACY_DESIGN_KEYS)
    )
    warning_limit = DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT
    return params, attribute_field_map, design_property_keys, warning_limit


def conversion_arguments(
    controller, *, staged_path, params, raster_paths, design_property_keys, input_crs_value
):
    """Build converter arguments without executing or retrying conversion."""
    convert_kwargs = {
        "input_geojson_path": staged_path,
        "dem_path": raster_paths["dem_path"],
        "output_geojson_path": controller.roads_monotonic_geojson_path,
        "low_points_output_geojson_path": controller.roads_low_points_geojson_path,
        "input_crs": input_crs_value,
        "sample_step_m": params.get("sample_step_m"),
        "tolerance_m": float(params.get("tolerance_m", 0.5)),
        "channel_raster_path": raster_paths["channel_raster_path"],
        "topaz_id_raster_path": raster_paths["topaz_id_raster_path"],
        "design_property_keys": design_property_keys,
    }
    return convert_kwargs


def build_summary(
    controller, *, summary, params, attribute_field_map, design_property_keys,
    warning_limit, raster_paths, input_crs_value, configured_input_crs,
    source_crs, input_crs_source,
):
    """Read emitted candidates and assemble the existing preparation summary."""
    segment_payload = json.loads(Path(controller.roads_monotonic_geojson_path).read_text(encoding="utf-8"))
    features = segment_payload.get("features", [])
    roads_lifecycle.segment_ids(features)
    eligible_segments = 0
    mapped_candidates = 0
    decision_counts: Counter[str] = Counter()
    routing_eligibility_counts: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()
    warning_examples: List[Dict[str, Any]] = []
    for feature_index, feature in enumerate(features):
        properties = feature.get("properties", {}) if isinstance(feature, Mapping) else {}
        segment_id = controller._segment_key(feature, fallback_index=feature_index)
        design_value, _ = controller._resolve_design_for_feature(
            properties=properties,
            attribute_field_map=attribute_field_map,
            warning_counts=warning_counts,
            warning_examples=warning_examples,
            warning_limit=warning_limit,
            segment_id=segment_id,
        )
        if design_value is None:
            continue
        eligible_segments += 1
        decision_key = str(properties.get("_roads_lowpoint_decision") or "unknown")
        decision_counts[decision_key] += 1
        routing_key = str(properties.get("_roads_routing_eligibility") or "unknown")
        routing_eligibility_counts[routing_key] += 1
        if (
            properties.get("topaz_id_chn_lowpoint") is not None
            and properties.get("topaz_id_hill_lowpoint") is not None
        ):
            mapped_candidates += 1

    channel_associated_count = int(routing_eligibility_counts.get("channel_associated", 0))
    non_channel_routable_count = int(routing_eligibility_counts.get("non_channel_routable", 0))
    non_routable_count = int(routing_eligibility_counts.get("non_routable", 0))
    prepare_summary = {
        "unrutted_geometry_policy": _unrutted.POLICY,
        "input_feature_count": int(summary.input_feature_count),
        "output_feature_count": int(summary.output_feature_count),
        "split_feature_count": int(summary.split_feature_count),
        "low_point_feature_count": int(summary.low_point_feature_count),
        "sample_step_m": float(summary.sample_step_m),
        "tolerance_m": float(summary.tolerance_m),
        "eligible_segment_count": eligible_segments,
        "eligible_with_lowpoint_ids": mapped_candidates,
        "eligible_channel_associated_count": channel_associated_count,
        "eligible_non_channel_routable_count": non_channel_routable_count,
        "eligible_non_routable_count": non_routable_count,
        "eligible_lowpoint_decision_counts": dict(sorted(decision_counts.items())),
        "eligible_routing_eligibility_counts": dict(sorted(routing_eligibility_counts.items())),
        "mapping_warning_count": int(sum(warning_counts.values())),
        "mapping_warning_counts": dict(sorted(warning_counts.items())),
        "mapping_warning_examples": warning_examples,
        "prepare_raster_paths": {
            "dem_path": controller._path_for_summary(raster_paths["dem_path"]),
            "channel_raster_path": controller._path_for_summary(raster_paths["channel_raster_path"]),
            "topaz_id_raster_path": controller._path_for_summary(raster_paths["topaz_id_raster_path"]),
        },
        "roads_monotonic_geojson_relpath": os.path.relpath(controller.roads_monotonic_geojson_path, controller.wd),
        "roads_low_points_geojson_relpath": os.path.relpath(controller.roads_low_points_geojson_path, controller.wd),
        "summary_relpath": os.path.relpath(controller.roads_summary_path, controller.wd),
        "roads_log_relpath": os.path.relpath(controller.roads_log_path, controller.wd),
        "input_crs": input_crs_value,
        "configured_input_crs": configured_input_crs,
        "source_crs": source_crs,
        "input_crs_source": input_crs_source,
        "design_property_keys": list(design_property_keys),
        "attribute_field_map": dict(attribute_field_map),
        "roads_params_signature": controller._params_signature(params),
        "parameterization_hash": roads_parameterization.configuration_hash(controller._parameterization),
        "uploaded_geojson_sha256": getattr(controller, "_uploaded_geojson_sha256", None),
        "prepared_at": int(time.time()),
    }
    return prepare_summary


def log_summary(controller, prepare_summary):
    """Log summary counts after the artifact has been written."""
    controller._append_roads_log(
        "prepare",
        "prepare_summary_written",
        {
            "eligible_segment_count": prepare_summary["eligible_segment_count"],
            "eligible_with_lowpoint_ids": prepare_summary["eligible_with_lowpoint_ids"],
            "eligible_channel_associated_count": prepare_summary["eligible_channel_associated_count"],
            "eligible_non_channel_routable_count": prepare_summary["eligible_non_channel_routable_count"],
            "eligible_lowpoint_decision_counts": dict(sorted(prepare_summary["eligible_lowpoint_decision_counts"].items())),
            "mapping_warning_count": int(sum(prepare_summary["mapping_warning_counts"].values())),
            "summary_relpath": prepare_summary["summary_relpath"],
        },
    )
    if prepare_summary["mapping_warning_counts"]:
        controller._append_roads_log(
            "prepare",
            "mapping_warnings_detected",
            {
                "mapping_warning_count": int(sum(prepare_summary["mapping_warning_counts"].values())),
                "mapping_warning_codes": sorted(prepare_summary["mapping_warning_counts"].keys()),
            },
        )
