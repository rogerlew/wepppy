"""Roads segment and parameterization inspection; lifecycle guards stay on the facade."""

from __future__ import annotations

from wepppy.observability.safe_traceback import safe_text
from wepppy.observability.safe_logging import current_profile
from wepppy.observability.secret_profiles import WORKER
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple
import rasterio
from rasterio.errors import RasterioIOError
from pyproj import CRS, Geod, Transformer
from wepppy.wepp.interchange import _roads_lifecycle as roads_lifecycle
from wepppy.nodb.mods.roads import parameterization as roads_parameterization
from wepppy.nodb.mods.roads import _parameterization_comparisons
from ._constants import DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT


def _load_segment_features(self) -> List[Dict[str, Any]]:
    segment_path = Path(self.roads_monotonic_geojson_path)
    if not segment_path.exists():
        raise FileNotFoundError(
            "Prepared roads segments not found. Run prepare_segments before run_roads_wepp."
        )

    payload = json.loads(segment_path.read_text(encoding="utf-8"))
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("Prepared roads segment GeoJSON is malformed.")
    roads_lifecycle.segment_ids(features)
    self._append_roads_log(
        "run",
        "loaded_prepared_segments",
        {
            "segment_feature_count": len(features),
            "roads_monotonic_geojson_relpath": os.path.relpath(segment_path, self.wd),
        },
    )
    return features


def _load_prepared_segments_geojson(self) -> Dict[str, Any]:
    segment_path = Path(self.roads_monotonic_geojson_path)
    if not segment_path.exists():
        raise FileNotFoundError(
            "Prepared roads segments not found. Run prepare_segments first."
        )

    payload = json.loads(segment_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("Prepared roads segment GeoJSON is malformed.")
    if payload.get("type") != "FeatureCollection":
        raise ValueError("Prepared roads segment payload must be a FeatureCollection.")
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("Prepared roads segment payload is missing features.")
    return dict(payload)


def _load_segment_execution_manifest(self) -> Dict[str, Dict[str, Any]]:
    manifest_path = Path(self.roads_segment_pass_manifest_path)
    if not manifest_path.exists():
        return {}
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Roads segment pass manifest is malformed.")
    records: Dict[str, Dict[str, Any]] = {}
    for row in payload:
        if not isinstance(row, Mapping):
            continue
        segment_id = str(row.get("segment_id") or "").strip()
        if not segment_id:
            continue
        members = row.get("source_segment_ids", [segment_id])
        if not isinstance(members, list) or not members or any(not isinstance(key, str) or not key for key in members):
            raise ValueError("Roads profile source membership is malformed.")
        for member in members:
            records[member] = dict(row)

    return records


def _build_segment_profile_for_query(
    self,
    *,
    feature: Mapping[str, Any],
    params: Mapping[str, Any],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    input_crs_raw = str(params.get("input_crs") or "EPSG:4326")
    try:
        input_crs = CRS.from_user_input(input_crs_raw)
    except Exception as exc:  # broad-except: keep read-only profile diagnostics available when dependencies fail.
        return None, safe_text(f"Unable to parse Roads input CRS {input_crs_raw!r}: {exc}", source_profile=current_profile(WORKER))

    try:
        raster_paths = self._resolve_prepare_raster_paths()
    except Exception as exc:  # broad-except: keep read-only profile diagnostics available when dependencies fail.
        return None, safe_text(f"Unable to resolve Roads DEM path: {exc}", source_profile=current_profile(WORKER))

    try:
        with rasterio.open(raster_paths["dem_path"]) as dem_dataset:
            if dem_dataset.crs is None:
                return None, "Roads DEM is missing CRS metadata."
            dem_crs = CRS.from_user_input(dem_dataset.crs)
            input_to_wgs84 = Transformer.from_crs(input_crs, CRS.from_epsg(4326), always_xy=True)
            input_to_dem = Transformer.from_crs(input_crs, dem_crs, always_xy=True)
            geod = Geod(ellps="WGS84")
            profile = self._build_segment_profile(
                feature=feature,
                input_crs=input_crs,
                dem_dataset=dem_dataset,
                input_to_wgs84=input_to_wgs84,
                input_to_dem=input_to_dem,
                geod=geod,
            )
    except (RasterioIOError, ValueError) as exc:
        return None, safe_text(str(exc), source_profile=current_profile(WORKER))

    return profile, None


def _derive_routing_mode_hint(properties: Mapping[str, Any]) -> str:
    routing_eligibility = str(properties.get("_roads_routing_eligibility") or "").strip()
    chn_lowpoint = properties.get("topaz_id_chn_lowpoint")
    hill_lowpoint = properties.get("topaz_id_hill_lowpoint")
    if chn_lowpoint is not None and hill_lowpoint is not None:
        return "channel_associated"
    if routing_eligibility == "non_channel_routable":
        return "non_channel_routed"
    if routing_eligibility:
        return routing_eligibility
    return "unknown"


def query_map_segments_geojson(self) -> Dict[str, Any]:
    payload = self._load_prepared_segments_geojson()
    params = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))
    attribute_field_map = self._normalize_attribute_field_map(
        params.get("attribute_field_map"),
        known_fields=None,
    )

    features_raw = payload.get("features", [])
    features_out: List[Dict[str, Any]] = []
    for feature_index, feature in enumerate(features_raw):
        if not isinstance(feature, Mapping):
            continue
        geometry = feature.get("geometry")
        properties_raw = feature.get("properties")
        properties: Dict[str, Any] = dict(properties_raw) if isinstance(properties_raw, Mapping) else {}
        segment_id = self._segment_key(feature, fallback_index=feature_index)
        properties["segment_id"] = segment_id
        design, _ = self._resolve_design_for_feature(
            properties=properties,
            attribute_field_map=attribute_field_map,
        )
        if isinstance(design, str) and design:
            properties["design"] = design
        properties["routing_mode_hint"] = self._derive_routing_mode_hint(properties)
        properties["non_channel_routable"] = self._is_truthy_property(properties.get("_roads_non_channel_routable"))
        features_out.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": properties,
            }
        )

    response_payload: Dict[str, Any] = {
        "type": "FeatureCollection",
        "features": features_out,
    }
    if isinstance(payload.get("name"), str) and payload.get("name"):
        response_payload["name"] = payload["name"]
    self._append_roads_log(
        "query",
        "query_map_segments_geojson",
        {
            "feature_count": len(features_out),
            "roads_monotonic_geojson_relpath": os.path.relpath(self.roads_monotonic_geojson_path, self.wd),
        },
    )
    return response_payload


def query_segment_detail(self, segment_id: str) -> Dict[str, Any]:
    segment_key = str(segment_id or "").strip()
    if not segment_key:
        raise ValueError("segment_id is required.")

    payload = self._load_prepared_segments_geojson()
    feature = self._find_segment_feature(payload, segment_id=segment_key)
    if feature is None:
        raise KeyError(f"Road segment {segment_key!r} was not found in prepared roads artifacts.")

    properties_raw = feature.get("properties")
    properties: Dict[str, Any] = dict(properties_raw) if isinstance(properties_raw, Mapping) else {}
    properties["segment_id"] = segment_key

    params = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))
    attribute_field_map = self._normalize_attribute_field_map(
        params.get("attribute_field_map"),
        known_fields=None,
    )

    warning_counts: Counter[str] = Counter()
    warning_examples: List[Dict[str, Any]] = []
    design, design_source_key = self._resolve_design_for_feature(
        properties=properties,
        attribute_field_map=attribute_field_map,
        warning_counts=warning_counts,
        warning_examples=warning_examples,
        warning_limit=DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT,
        segment_id=segment_key,
    )

    resolved_inputs: Optional[Dict[str, Any]] = None
    if design is not None:
        resolved_inputs = self._resolve_segment_run_inputs(
            properties=properties,
            params=params,
            segment_id=segment_key,
            design=design,
            warning_counts=warning_counts,
            warning_examples=warning_examples,
            warning_limit=DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT,
        )
        resolved_inputs["resolution_sources"]["design"] = (
            "mapped_primary" if design_source_key == attribute_field_map.get("design") else "segment_property"
        )

    execution_records = (self._load_segment_execution_manifest()
                         if roads_lifecycle.available(self.wd) else {})
    execution_record = execution_records.get(segment_key)
    if not isinstance(execution_record, Mapping):
        execution_record = {}

    profile_values: Dict[str, Optional[float]] = {
        "segment_length_m": self._as_float_or_none(execution_record.get("segment_length_m")),
        "slope_pct_raw": self._as_float_or_none(execution_record.get("slope_pct_raw")),
        "slope_pct_clamped": self._as_float_or_none(execution_record.get("slope_pct_clamped")),
        "elevation_high_m": self._as_float_or_none(execution_record.get("elevation_high_m")),
        "elevation_low_m": self._as_float_or_none(execution_record.get("elevation_low_m")),
    }
    profile_error: Optional[str] = None
    if all(value is None for value in profile_values.values()) and design is not None:
        computed_profile, profile_error = self._build_segment_profile_for_query(
            feature=feature,
            params=params,
        )
        if computed_profile is not None:
            profile_values = {
                "segment_length_m": self._as_float_or_none(computed_profile.get("segment_length_m")),
                "slope_pct_raw": self._as_float_or_none(computed_profile.get("raw_slope_pct")),
                "slope_pct_clamped": self._as_float_or_none(computed_profile.get("slope_pct")),
                "elevation_high_m": self._as_float_or_none(computed_profile.get("elevation_high_m")),
                "elevation_low_m": self._as_float_or_none(computed_profile.get("elevation_low_m")),
            }

    topaz_id_chn_lowpoint = self._as_int_or_none(
        execution_record.get("topaz_id_chn_lowpoint", properties.get("topaz_id_chn_lowpoint"))
    )
    topaz_id_hill_lowpoint = self._as_int_or_none(
        execution_record.get("topaz_id_hill_lowpoint", properties.get("topaz_id_hill_lowpoint"))
    )
    routing_eligibility = str(
        execution_record.get("routing_eligibility")
        or properties.get("_roads_routing_eligibility")
        or ""
    )
    routing_mode = str(execution_record.get("routing_mode") or self._derive_routing_mode_hint(properties))
    non_channel_routable = self._is_truthy_property(properties.get("_roads_non_channel_routable"))
    if routing_mode == "non_channel_routed":
        non_channel_routable = True

    result: Dict[str, Any] = {
        "segment_id": segment_key,
        "design": str(execution_record.get("design") or (resolved_inputs or {}).get("design") or design or ""),
        "surface": str(execution_record.get("surface") or (resolved_inputs or {}).get("surface") or ""),
        "traffic": str(execution_record.get("traffic") or (resolved_inputs or {}).get("traffic") or ""),
        "soil_texture": str(
            execution_record.get("soil_texture") or (resolved_inputs or {}).get("soil_texture") or ""
        ),
        "rfg_pct": self._as_float_or_none(execution_record.get("rfg_pct", (resolved_inputs or {}).get("rfg_pct"))),
        "road_width_m": self._as_float_or_none(
            execution_record.get("road_width_m", (resolved_inputs or {}).get("road_width_m"))
        ),
        "segment_length_m": profile_values["segment_length_m"],
        "slope_pct_raw": profile_values["slope_pct_raw"],
        "slope_pct_clamped": profile_values["slope_pct_clamped"],
        "elevation_high_m": profile_values["elevation_high_m"],
        "elevation_low_m": profile_values["elevation_low_m"],
        "topaz_id_chn_lowpoint": topaz_id_chn_lowpoint,
        "topaz_id_hill_lowpoint": topaz_id_hill_lowpoint,
        "routing_eligibility": routing_eligibility,
        "routing_mode": routing_mode,
        "channel_associated": routing_mode == "channel_associated",
        "non_channel_routable": bool(non_channel_routable),
        "target_hillslope_wepp_id": self._as_int_or_none(execution_record.get("target_hillslope_wepp_id")),
        "segment_run_id": self._as_int_or_none(execution_record.get("segment_run_id")),
        "execution_status": str(execution_record.get("status") or ""),
        "buffer_length_m": self._as_float_or_none(
            execution_record.get("buffer_length_m", properties.get("buffer_length_m"))
        ),
        "buffer_slope_pct": self._as_float_or_none(
            execution_record.get("buffer_slope_pct", properties.get("buffer_slope_pct"))
        ),
        "fill_length_m": self._as_float_or_none(
            execution_record.get("fill_length_m", (resolved_inputs or {}).get("fill_length_m", properties.get("fill_length_m")))
        ),
        "fill_slope_pct": self._as_float_or_none(
            execution_record.get("fill_slope_pct", (resolved_inputs or {}).get("fill_slope_pct", properties.get("fill_slope_pct")))
        ),
        "trace_path_length_m": self._as_float_or_none(execution_record.get("trace_path_length_m")),
        "trace_mean_slope": self._as_float_or_none(execution_record.get("trace_mean_slope")),
        "trace_drop_m": self._as_float_or_none(execution_record.get("trace_drop_m")),
        "trace_termination_reason": str(execution_record.get("trace_termination_reason") or ""),
        "resolution_sources": dict((resolved_inputs or {}).get("resolution_sources", {})),
        "mapping_warning_counts": dict(sorted(warning_counts.items())),
        "mapping_warning_examples": warning_examples,
        "design_source_key": design_source_key,
        "roads_params_signature": self._params_signature(params),
        "profile_error": profile_error,
        "placement": {key: execution_record.get(key) for key in (
            "placement_policy", "placement_adjustment", "placement_adjustment_reason",
            "placement_source", "original_top_landuse_length_m", "hillslope_length_m",
            "top_landuse_length_m", "bottom_landuse_length_m", "discha_median_m",
            "upslope_runon_assumed_zero", "top_ofe_compensation_m", "bottom_ofe_compensation_m",
        )} if design == "outslope_unrutted" else None,
        "feature_properties": properties,
    }
    self._append_roads_log(
        "query",
        "query_segment_detail",
        {
            "segment_id": segment_key,
            "routing_mode": result["routing_mode"],
            "execution_status": result["execution_status"] or "not_run",
            "profile_error": profile_error,
        },
    )
    return result


def _parameterization_group(state, design, surface, traffic, texture, routing,
                            segment_ids, index, source_kind):
    selection_design = "outslope_rutted" if design == "outslope_unrutted" else design
    name = roads_parameterization.soil_template_name(selection_design, surface, texture)
    details = roads_parameterization.resolve_groups(state, name, traffic)
    roles = {}
    for detail in details:
        role = detail["role"]
        roles[role] = {}
        for parameter in roads_parameterization.PARAMETERS:
            source_value = detail["baseline"][parameter]
            adjusted_value = detail["adjusted"][parameter]
            roles[role][parameter] = {
                "source": source_value, "adjusted": adjusted_value,
                "resolved": detail["resolved"][parameter],
                "adjustment": ("Divide by 4 for low/no road traffic"
                               if role == "road" and parameter in ("ki_kg_s_m4", "kr_s_m") and traffic != "high"
                               else "Native input formatting" if adjusted_value != source_value else "Unchanged"),
                "source_asset": f"soils/{name}",
                "source_sha256": detail["source_sha256"],
            }
    # Inslope profiles can route through a buffer; actual membership is
    # established only by execution, never guessed from a fallback.
    applicable = ["road", "fill", "buffer"] if design.startswith("outslope") else ["road"]
    if not design.startswith("outslope") and routing != "channel_associated":
        applicable.append("buffer")
    return {
        "id": f"group-{index + 1}", "label": f"{design} / {surface} / {texture} / {traffic}",
        "design": design, "surface": surface, "traffic": traffic, "soil_texture": texture,
        "segment_ids": segment_ids, "segment_count": len(segment_ids),
        "source_asset": f"soils/{name}", "roles": roles,
        "applicable_roles": applicable, "source_kind": source_kind,
        "routing_mode": routing,
        "applicability": "preview",
        "management_asset": "managements/" + roads_parameterization.management_template_name(traffic),
        "management_note": "No traffic changes road/fill plants and initial conditions; yearly operations remain." if traffic == "none" else "High/low traffic share the ordinary management template.",
    }


def initial_parameterization_preview(cls):
    """Return a default preview for enabled first use without creating Roads."""
    state = roads_parameterization.new_state(Path(__file__).resolve().parent / "legacy_templates")
    params = cls._default_params()
    group = cls._parameterization_group(
        state, "inslope_bd", params["surface_default"], params["traffic_default"],
        params["soil_texture_default"], "unknown", [], 0, "defaults_preview",
    )
    return {"status": "unbound", "baseline_id": state["baseline"]["id"],
            "configuration_hash": None, "overrides": state["overrides"],
            "diagnostics": [], "groups": [group], "last_completed_run": None,
            "comparisons": {"available": False, "reason": "No completed Roads execution exists."}}


def _parameterization_groups(self, state, params):
    """Resolve displayed groups through the same feature/default selector as Run."""
    prepared = Path(self.roads_monotonic_geojson_path)
    staged = self.roads_staged_geojson_path
    source = prepared if prepared.exists() else (Path(staged) if staged else None)
    features = []
    source_kind = "defaults_preview"
    if source is not None and source.exists():
        payload = json.loads(source.read_text(encoding="utf-8"))
        features = payload.get("features", [])
        source_kind = "prepared_segments" if source == prepared else "uploaded_features_preview"
    mapping = self._normalize_attribute_field_map(params.get("attribute_field_map"), known_fields=None)
    groups = {}
    diagnostics = []
    for index, feature in enumerate(features):
        properties = feature.get("properties") or {}
        segment_id = self._segment_key(feature, fallback_index=index)
        warnings, examples = Counter(), []
        design, _ = self._resolve_design_for_feature(
            properties=properties, attribute_field_map=mapping,
            warning_counts=warnings, warning_examples=examples,
            warning_limit=DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT, segment_id=segment_id,
        )
        if design is None:
            continue
        try:
            resolved = self._resolve_segment_run_inputs(
                properties=properties, params=params, segment_id=segment_id, design=design,
                warning_counts=warnings, warning_examples=examples,
                warning_limit=DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT,
            )
        except ValueError as exc:
            diagnostics.append(safe_text(f"{segment_id}: {exc}", source_profile=current_profile(WORKER)))
            continue
        routing = self._derive_routing_mode_hint(properties)
        key = (design, resolved["surface"], resolved["traffic"], resolved["soil_texture"], routing)
        groups.setdefault(key, []).append(segment_id)
    if not features:
        groups[("inslope_bd", params["surface_default"], params["traffic_default"],
                params["soil_texture_default"], "unknown")] = []
    result = []
    for index, ((design, surface, traffic, texture, routing), segment_ids) in enumerate(groups.items()):
        result.append(self._parameterization_group(
            state, design, surface, traffic, texture, routing, segment_ids, index, source_kind,
        ))
    return result, diagnostics


def _last_parameterization_readback(self, diagnostics):
    last_run = getattr(self, "_last_run_summary", None)
    if isinstance(last_run, Mapping) and last_run.get("status") == "completed":
        records = [dict(row["parameterization"], segment_id=row.get("segment_id"),
                        segment_run_id=row.get("segment_run_id"))
                   for row in last_run.get("segment_execution_records", [])
                   if isinstance(row, Mapping) and row.get("status") == "completed"
                   and isinstance(row.get("parameterization"), Mapping)]
        current = roads_lifecycle.available(self.wd)
        if records and current:
            return {"configuration_hash": last_run.get("parameterization_hash"),
                    "baseline_id": records[0].get("baseline_id"), "records": records,
                    "completed_at": last_run.get("completed_at"),
                    "current": current, "historical": not current}
    project = Path(self.wd).resolve()

    def contained(root, relative):
        relative = Path(relative)
        path = root / relative
        if relative.is_absolute() or ".." in relative.parts or path.resolve() != root / relative:
            raise ValueError("Historical parameterization path must not be aliased or escape its snapshot.")
        return path

    try:
        history = contained(project, "wepp/roads/history")
        snapshots = [] if not history.is_dir() else sorted(history.iterdir(), reverse=True)
    except (OSError, ValueError) as exc:
        diagnostics.append(safe_text(f"Historical readback unavailable: {exc}", source_profile=current_profile(WORKER)))
        return None
    candidates = []
    for snapshot in snapshots:
        try:
            snapshot = contained(project, snapshot.relative_to(project))
            if not snapshot.is_dir():
                continue
            receipt_path = contained(snapshot, "wepp/roads/output/roads.current.json")
            if receipt_path.is_file():
                candidates.append((receipt_path.stat().st_mtime_ns, snapshot, receipt_path))
        except (OSError, ValueError) as exc:
            diagnostics.append(safe_text(f"Historical readback unavailable at {snapshot.name}: {exc}", source_profile=current_profile(WORKER)))
    for _, snapshot, receipt_path in sorted(candidates, reverse=True):
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            required_keys = {"policy", "is_single_storm", "required_relpaths",
                             "parameterization_hash", "parameterization_snapshot_sha256"}
            if (not isinstance(receipt, dict) or set(receipt) != required_keys
                    or receipt.get("policy") != roads_lifecycle.POLICY
                    or type(receipt.get("is_single_storm")) is not bool):
                raise ValueError("Retained completed-result receipt is invalid.")
            signature = receipt["parameterization_hash"]
            if not isinstance(signature, str) or not re.fullmatch(r"[0-9a-f]{64}", signature):
                raise ValueError("Retained parameterization identity is invalid.")
            required = receipt["required_relpaths"]
            if (not isinstance(required, list) or any(not isinstance(name, str) for name in required)
                    or len(set(required)) != len(required)
                    or not roads_lifecycle.mandatory_paths(receipt["is_single_storm"]).issubset(required)
                    or "wepp/roads/output/roads.parameterization.comparison.json" not in required):
                raise ValueError("Retained completed-result receipt has incomplete resources.")
            optional = ["wepp/roads/output/interchange/chnwb.parquet"]
            if contained(snapshot, "wepp/roads/segments/roads.accounting.json").exists():
                optional.append("wepp/roads/segments/roads.accounting.json")
                if not receipt["is_single_storm"]:
                    optional.append("wepp/roads/output/interchange/H.accounting.wat.parquet")
            if any(name not in required for name in optional
                   if name != "wepp/roads/output/interchange/chnwb.parquet"
                   or contained(snapshot, name).exists()):
                raise ValueError("Retained receipt omits produced report resources.")
            for name in required:
                if not contained(snapshot, name).is_file():
                    raise ValueError("Retained completed-result resource is missing.")
            comparison_path = contained(snapshot, "wepp/roads/output/roads.parameterization.comparison.json")
            if hashlib.sha256(comparison_path.read_bytes()).hexdigest() != receipt["parameterization_snapshot_sha256"]:
                raise ValueError("Retained parameterization snapshot hash changed.")
            comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
            if not isinstance(comparison, dict) or comparison.get("configuration_hash") != signature:
                raise ValueError("Retained parameterization snapshot identity changed.")
            manifest_name = "wepp/roads/segments/roads.segment.pass.manifest.json"
            manifest = contained(snapshot, manifest_name)
            sources = comparison.get("sources")
            if not isinstance(sources, dict):
                raise ValueError("Retained parameterization source bindings are invalid.")
            manifest_hash = sources.get(manifest_name)
            if not manifest_hash or hashlib.sha256(manifest.read_bytes()).hexdigest() != manifest_hash:
                raise ValueError("Retained native manifest hash changed.")
            rows = json.loads(manifest.read_text(encoding="utf-8"))
            if not isinstance(rows, list):
                raise ValueError("Retained execution manifest is not a list.")
            records = []
            for row in rows:
                if not isinstance(row, Mapping) or row.get("status") != "completed":
                    continue
                record = row.get("parameterization")
                if (not isinstance(record, dict) or record.get("configuration_hash") != signature
                        or record.get("baseline_id") != comparison.get("baseline_id")
                        or not isinstance(record.get("ofes"), list) or not record["ofes"]):
                    raise ValueError("Retained native readback does not match its execution.")
                files = record.get("input_files")
                if not isinstance(files, list) or len(files) != 3:
                    raise ValueError("Retained native input bindings are incomplete.")
                suffixes = set()
                for file_record in files:
                    if not isinstance(file_record, dict) or not isinstance(file_record.get("relpath"), str):
                        raise ValueError("Retained native input binding is invalid.")
                    path = contained(snapshot, file_record["relpath"])
                    suffixes.add(path.suffix)
                    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != file_record.get("sha256"):
                        raise ValueError("Retained native input hash changed.")
                if suffixes != {".sol", ".slp", ".man"}:
                    raise ValueError("Retained native input bindings are incomplete.")
                records.append(dict(record, segment_id=row.get("segment_id"),
                                    segment_run_id=row.get("segment_run_id")))
            if not records:
                raise ValueError("Retained completed native readbacks are missing.")
            return {"configuration_hash": signature, "baseline_id": records[0]["baseline_id"],
                    "records": records, "completed_at": comparison.get("completed_at"),
                    "current": False, "historical": True,
                    "history_relpath": os.path.relpath(snapshot, self.wd)}
        except (OSError, ValueError, TypeError, KeyError) as exc:
            diagnostics.append(safe_text(f"Historical readback unavailable at {snapshot.name}: {exc}", source_profile=current_profile(WORKER)))
    return None


def query_parameterization(self):
    """Inspect saved authority without enrolling or repairing legacy state."""
    raw_state = self._saved_parameterization_state()
    try:
        state = (roads_parameterization.new_state(Path(self.roads_legacy_templates_dir))
                 if raw_state is None else roads_parameterization.validate_state(raw_state))
    except (ValueError, TypeError, KeyError) as exc:
        return {"status": "invalid", "baseline_id": None, "configuration_hash": None,
                "overrides": None, "diagnostics": [safe_text(str(exc), source_profile=current_profile(WORKER))], "groups": [],
                "last_completed_run": None,
                "comparisons": {"available": False, "reason": "Repair parameterization before a new execution."}}
    params = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))
    groups, diagnostics = self._parameterization_groups(state, params)
    try:
        repository_baseline = (state["baseline"] if raw_state is None else
                               roads_parameterization.bind_baseline(Path(self.roads_legacy_templates_dir)))
        repository = {"status": "matching" if repository_baseline["id"] == state["baseline"]["id"] else "different",
                      "baseline_id": repository_baseline["id"]}
    except (OSError, ValueError, TypeError, KeyError) as exc:
        # Repository inspection is diagnostic; retained valid state remains authoritative.
        repository = {"status": "unavailable", "baseline_id": None, "reason": safe_text(str(exc), source_profile=current_profile(WORKER))}
    last_completed = self._last_parameterization_readback(diagnostics)
    if last_completed and last_completed["current"]:
        for group in groups:
            members = set(group["segment_ids"])
            actual = {ofe["role"] for row in last_completed["records"]
                      if row.get("segment_id") in members for ofe in row.get("ofes", [])}
            group["applicable_roles"] = [role for role in roads_parameterization.ROLES if role in actual]
            group["applicability"] = "last_completed_run"
    return {
        "status": "unbound" if raw_state is None else "bound",
        "baseline_id": state["baseline"]["id"],
        "repository_baseline": repository,
        "configuration_hash": None if raw_state is None else roads_parameterization.configuration_hash(state),
        "overrides": state["overrides"], "diagnostics": diagnostics, "groups": groups,
        "last_completed_run": last_completed,
        "comparisons": _parameterization_comparisons.query_comparisons(self.wd),
    }
