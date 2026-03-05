"""TerrainProcessor runtime orchestration and visualization artifact contracts."""

from __future__ import annotations

import json
import logging
import os
import shutil
import inspect
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from wepppy.topo.osm_roads.contracts import OSMRoadsService
from wepppy.topo.wbt.osm_roads_consumer import resolve_roads_source
from wepppy.topo.wbt.terrain_processor_helpers import (
    BasinSummary,
    ProvenanceEntry,
    TerrainProcessorHelperError,
    TerrainArtifactRegistry,
    build_outlet_feature_collection,
    burn_streams_at_roads_adapter,
    derive_flow_stack,
    determine_invalidated_phases,
    extract_road_stream_intersections,
    parse_unnest_basins_hierarchy_csv,
    resolve_bounded_breach_collar_pixels,
    run_bounded_breach_workflow,
    snap_outlets_to_streams,
    snap_uploaded_culvert_points_to_crossings,
)
from wepppy.topo.wbt.wbt_topaz_emulator import WhiteboxToolsTopazEmulator

_DEFAULT_OSM_HIGHWAY_FILTER: tuple[str, ...] = (
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "unclassified",
    "residential",
    "track",
)

_SLOPE_NODATA = -9999.0
_DIFF_NODATA = -9999.0
_HILLSHADE_NODATA = 0

_PHASE_1 = "phase1_dem_preparation"
_PHASE_2 = "phase2_conditioning_flow_stack"
_PHASE_3 = "phase3_culvert_enforcement"
_PHASE_4 = "phase4_outlet_resolution"
_PHASE_5 = "phase5_visualization_artifacts"
_PHASE_6 = "phase6_invalidation_reentry"

_RUNTIME_PHASE_SEQUENCE: tuple[str, ...] = (
    _PHASE_1,
    _PHASE_2,
    _PHASE_3,
    _PHASE_4,
    _PHASE_5,
    _PHASE_6,
)

_RUNTIME_INVALIDATION_RULES: dict[str, tuple[str, ...]] = {
    "smooth": _RUNTIME_PHASE_SEQUENCE,
    "smooth_algorithm": _RUNTIME_PHASE_SEQUENCE,
    "smooth_filter_size": _RUNTIME_PHASE_SEQUENCE,
    "smooth_max_diff": _RUNTIME_PHASE_SEQUENCE,
    "roads_source": _RUNTIME_PHASE_SEQUENCE,
    "roads_path": _RUNTIME_PHASE_SEQUENCE,
    "road_fill_strategy": _RUNTIME_PHASE_SEQUENCE,
    "road_fill_dy": _RUNTIME_PHASE_SEQUENCE,
    "road_fill_margin": _RUNTIME_PHASE_SEQUENCE,
    "road_buffer_width": _RUNTIME_PHASE_SEQUENCE,
    "osm_highway_filter": _RUNTIME_PHASE_SEQUENCE,
    "aoi_wgs84_geojson": _RUNTIME_PHASE_SEQUENCE,
    "conditioning": _RUNTIME_PHASE_SEQUENCE[1:],
    "blc_dist_m": _RUNTIME_PHASE_SEQUENCE[1:],
    "blc_max_cost": _RUNTIME_PHASE_SEQUENCE[1:],
    "blc_fill": _RUNTIME_PHASE_SEQUENCE[1:],
    "bounded_breach_collar_m": _RUNTIME_PHASE_SEQUENCE[1:],
    "csa": _RUNTIME_PHASE_SEQUENCE[1:],
    "mcl": _RUNTIME_PHASE_SEQUENCE[1:],
    "enforce_culverts": _RUNTIME_PHASE_SEQUENCE[2:],
    "culvert_source": _RUNTIME_PHASE_SEQUENCE[2:],
    "culvert_path": _RUNTIME_PHASE_SEQUENCE[2:],
    "culvert_method": _RUNTIME_PHASE_SEQUENCE[2:],
    "culvert_road_width": _RUNTIME_PHASE_SEQUENCE[2:],
    "breakline_burn_dy": _RUNTIME_PHASE_SEQUENCE[2:],
    "breakline_offset": _RUNTIME_PHASE_SEQUENCE[2:],
    "breakline_buffer": _RUNTIME_PHASE_SEQUENCE[2:],
    "outlet_mode": _RUNTIME_PHASE_SEQUENCE[3:],
    "outlets": _RUNTIME_PHASE_SEQUENCE[3:],
    "snap_distance": _RUNTIME_PHASE_SEQUENCE[3:],
    "visualization_max_pixels": _RUNTIME_PHASE_SEQUENCE[4:],
}


class TerrainProcessorRuntimeError(Exception):
    """Typed runtime error for contract-friendly failure propagation."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.context = dict(context or {})


@dataclass(frozen=True)
class VisualizationManifestEntry:
    """Stable backend visualization artifact contract entry."""

    artifact_id: str
    artifact_type: str
    source_phase: str
    path: str
    dependencies: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "source_phase": self.source_phase,
            "path": self.path,
            "dependencies": list(self.dependencies),
        }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


@dataclass(frozen=True)
class TerrainRunResult:
    """Materialized result from a runtime execution."""

    executed_phases: tuple[str, ...]
    invalidated_phases: tuple[str, ...]
    helper_invalidated_phases: tuple[str, ...]
    changed_config_keys: tuple[str, ...]
    current_dem_path: str
    artifacts_by_phase: dict[str, dict[str, str]]
    visualization_manifest_path: str | None
    provenance: tuple[dict[str, Any], ...]
    basin_summaries: tuple[BasinSummary, ...]


@dataclass(frozen=True)
class TerrainConfig:
    """TerrainProcessor user intent configuration."""

    smooth: bool = False
    smooth_algorithm: str = "feature_preserving"
    smooth_filter_size: int = 11
    smooth_max_diff: float = 0.5

    roads_source: str | None = None
    roads_path: str | None = None
    osm_highway_filter: tuple[str, ...] = _DEFAULT_OSM_HIGHWAY_FILTER
    aoi_wgs84_geojson: Mapping[str, Any] | None = None

    road_fill_strategy: str = "profile_relative"
    road_fill_dy: float = 5.0
    road_fill_margin: float = 2.0
    road_buffer_width: float | None = None

    conditioning: str = "breach"
    blc_dist_m: float | None = None
    blc_max_cost: float | None = None
    blc_fill: bool = True
    bounded_breach_collar_m: float | None = None

    enforce_culverts: bool = False
    culvert_source: str = "auto_intersect"
    culvert_path: str | None = None
    culvert_method: str = "burn_streams_at_roads"
    culvert_road_width: float = 10.0
    breakline_burn_dy: float = 10.0
    breakline_offset: float = 10.0
    breakline_buffer: float = 1.0

    csa: float = 5.0
    mcl: float = 60.0

    outlet_mode: str = "single"
    outlets: tuple[tuple[float, float], ...] | None = None
    snap_distance: float = 20.0
    visualization_max_pixels: int = 100_000_000

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.aoi_wgs84_geojson is not None:
            payload["aoi_wgs84_geojson"] = dict(self.aoi_wgs84_geojson)
        return payload


class TerrainProcessor:
    """Runtime TerrainProcessor with phase contracts and re-entry semantics."""

    phase_sequence: tuple[str, ...] = _RUNTIME_PHASE_SEQUENCE

    def __init__(
        self,
        *,
        wbt_wd: str,
        dem_path: str,
        config: TerrainConfig,
        emulator: Any | None = None,
        osm_service: OSMRoadsService | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.workspace = Path(wbt_wd).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.dem_path = str(Path(dem_path).resolve())
        if not os.path.exists(self.dem_path):
            raise FileNotFoundError(f"DEM file does not exist: {self.dem_path}")

        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._osm_service = osm_service
        self._emulator = (
            emulator
            if emulator is not None
            else WhiteboxToolsTopazEmulator(wbt_wd=str(self.workspace), dem_fn=self.dem_path)
        )

        self.current_dem_path = self.dem_path
        self._artifact_registry = TerrainArtifactRegistry()
        self._artifacts_by_phase: dict[str, dict[str, str]] = {}
        self._provenance: list[ProvenanceEntry] = []
        self._basin_summaries: list[BasinSummary] = []
        self._visualization_manifest: list[VisualizationManifestEntry] = []
        self._protected_input_paths: set[Path] = set()
        self._last_run_result: TerrainRunResult | None = None
        self._refresh_protected_input_paths()

        self._phase_handlers: dict[str, Callable[[Sequence[str]], None]] = {
            _PHASE_1: self._run_phase1_dem_preparation,
            _PHASE_2: self._run_phase2_conditioning_flow_stack,
            _PHASE_3: self._run_phase3_culvert_enforcement,
            _PHASE_4: self._run_phase4_outlet_resolution,
            _PHASE_5: self._run_phase5_visualization_artifacts,
            _PHASE_6: self._run_phase6_invalidation_reentry,
        }

    @property
    def artifacts_by_phase(self) -> dict[str, dict[str, str]]:
        return {phase: dict(paths) for phase, paths in self._artifacts_by_phase.items()}

    @property
    def provenance(self) -> tuple[ProvenanceEntry, ...]:
        return tuple(self._provenance)

    @property
    def basin_summaries(self) -> tuple[BasinSummary, ...]:
        return tuple(self._basin_summaries)

    @property
    def visualization_manifest(self) -> tuple[VisualizationManifestEntry, ...]:
        return tuple(self._visualization_manifest)

    @property
    def last_run_result(self) -> TerrainRunResult | None:
        return self._last_run_result

    def run(
        self,
        *,
        changed_config_keys: Sequence[str] | None = None,
    ) -> TerrainRunResult:
        """Run TerrainProcessor phases with optional invalidation/re-entry."""

        self._validate_config(self.config)

        changed_keys = tuple(dict.fromkeys(changed_config_keys or ()))
        helper_invalidated = tuple(self._determine_helper_invalidated_phases(changed_keys))
        runtime_invalidated = tuple(self._determine_runtime_invalidated_phases(changed_keys))

        start_idx = 0
        if runtime_invalidated:
            self._invalidate_runtime_phases(runtime_invalidated)
            start_idx = self.phase_sequence.index(runtime_invalidated[0])

        self.current_dem_path = self._resolve_current_dem_pointer_for_start_phase(start_idx)
        self._set_emulator_dem(self.current_dem_path)

        executed_phases: list[str] = []
        for phase in self.phase_sequence[start_idx:]:
            self._phase_handlers[phase](changed_keys)
            executed_phases.append(phase)

        manifest_path = self._artifacts_by_phase.get(_PHASE_5, {}).get("visualization_manifest_json")
        result = TerrainRunResult(
            executed_phases=tuple(executed_phases),
            invalidated_phases=runtime_invalidated,
            helper_invalidated_phases=helper_invalidated,
            changed_config_keys=changed_keys,
            current_dem_path=self.current_dem_path,
            artifacts_by_phase=self.artifacts_by_phase,
            visualization_manifest_path=manifest_path,
            provenance=tuple(entry.to_dict() for entry in self._provenance),
            basin_summaries=tuple(self._basin_summaries),
        )
        self._last_run_result = result
        return result

    def rerun_with_config(self, new_config: TerrainConfig) -> TerrainRunResult:
        """Apply config delta and rerun from the earliest invalidated phase."""

        self._validate_config(new_config)
        changed_keys = self._changed_config_keys(self.config, new_config)
        self.config = new_config
        self._refresh_protected_input_paths()
        return self.run(changed_config_keys=changed_keys)

    def _run_phase1_dem_preparation(self, _changed_keys: Sequence[str]) -> None:
        phase = _PHASE_1
        raw_dem_path = self.workspace / "dem_raw.tif"
        shutil.copy2(self.dem_path, raw_dem_path)
        self.current_dem_path = str(raw_dem_path)
        self._register_artifact(phase=phase, artifact_name="dem_raw", artifact_path=self.current_dem_path)

        if self.config.smooth:
            smoothed_path = self.workspace / "dem_smoothed.tif"
            self._smooth_dem(input_dem=self.current_dem_path, output_dem=str(smoothed_path))
            self.current_dem_path = str(smoothed_path)
            self._register_artifact(phase=phase, artifact_name="dem_smoothed", artifact_path=self.current_dem_path)
            self._add_provenance(
                step="smooth",
                artifact=self.current_dem_path,
                phase=phase,
                parameters={
                    "smooth_algorithm": self.config.smooth_algorithm,
                    "smooth_filter_size": self.config.smooth_filter_size,
                    "smooth_max_diff": self.config.smooth_max_diff,
                },
            )

        roads_path = self._resolve_roads_path()
        if roads_path is not None:
            self._register_artifact(phase=phase, artifact_name="roads_utm_geojson", artifact_path=roads_path)
            roads_dem_path = self.workspace / "dem_roads.tif"
            embankment_mask_path = self.workspace / "embankment_mask.tif"
            self._synthesize_road_embankments(
                input_dem=self.current_dem_path,
                roads_path=roads_path,
                output_dem=str(roads_dem_path),
                embankment_mask_path=str(embankment_mask_path),
            )
            self.current_dem_path = str(roads_dem_path)
            self._register_artifact(phase=phase, artifact_name="dem_roads", artifact_path=self.current_dem_path)
            if embankment_mask_path.exists():
                self._register_artifact(
                    phase=phase,
                    artifact_name="embankment_mask",
                    artifact_path=str(embankment_mask_path),
                )
            self._add_provenance(
                step="road_fill",
                artifact=self.current_dem_path,
                phase=phase,
                parameters={
                    "roads_source": self.config.roads_source,
                    "road_fill_strategy": self.config.road_fill_strategy,
                    "road_fill_dy": self.config.road_fill_dy,
                    "road_fill_margin": self.config.road_fill_margin,
                    "road_buffer_width": self.config.road_buffer_width,
                },
            )

        self._set_emulator_dem(self.current_dem_path)

    def _run_phase2_conditioning_flow_stack(self, _changed_keys: Sequence[str]) -> None:
        phase = _PHASE_2
        self._set_emulator_dem(self.current_dem_path)

        conditioning = self.config.conditioning
        if conditioning == "bounded_breach":
            try:
                fill_artifacts = derive_flow_stack(
                    self._emulator,
                    csa=self.config.csa,
                    mcl=self.config.mcl,
                fill_or_breach="fill",
                blc_dist=self._as_blc_dist(),
                blc_max_cost=self.config.blc_max_cost,
                blc_fill=self.config.blc_fill,
            )
            except (TypeError, ValueError, TerrainProcessorHelperError) as exc:
                self._raise_helper_runtime_error(
                    message="Failed to derive fill-first flow stack for bounded breach",
                    code="helper_flow_stack_error",
                    context={"phase": phase, "conditioning": conditioning},
                    exc=exc,
                )
            filled_dem_path = self.workspace / "filled_dem.tif"
            shutil.copy2(fill_artifacts.relief_path, filled_dem_path)
            self._register_artifact(
                phase=phase,
                artifact_name="filled_dem",
                artifact_path=str(filled_dem_path),
            )

            boundary_geojson_path = self._create_preliminary_boundary(fill_artifacts=fill_artifacts)
            self._register_artifact(
                phase=phase,
                artifact_name="boundary_preliminary_geojson",
                artifact_path=boundary_geojson_path,
            )

            try:
                collar_pixels = resolve_bounded_breach_collar_pixels(
                    cellsize_m=self._require_cellsize(),
                    bounded_breach_collar_m=self.config.bounded_breach_collar_m,
                )
                bounded = run_bounded_breach_workflow(
                    prepared_dem_path=self.current_dem_path,
                    boundary_mask_path=self._require_path(getattr(self._emulator, "bound", None), "bound"),
                    filled_dem_path=str(filled_dem_path),
                    output_masked_dem_path=str(self.workspace / "bounded_masked_dem.tif"),
                    output_breached_interior_path=str(self.workspace / "bounded_breached_interior.tif"),
                    output_composite_dem_path=str(self.workspace / "composite_dem.tif"),
                    collar_pixels=collar_pixels,
                    breach_runner=self._bounded_breach_runner,
                )
            except (TypeError, ValueError, FileNotFoundError, TerrainProcessorHelperError) as exc:
                self._raise_helper_runtime_error(
                    message="Bounded breach workflow failed",
                    code="helper_bounded_breach_error",
                    context={"phase": phase},
                    exc=exc,
                )
            self.current_dem_path = bounded.composite_dem_path
            self._register_artifact(phase=phase, artifact_name="bounded_masked_dem", artifact_path=bounded.masked_dem_path)
            self._register_artifact(
                phase=phase,
                artifact_name="bounded_breached_interior_dem",
                artifact_path=bounded.breached_interior_path,
            )
            self._register_artifact(phase=phase, artifact_name="composite_dem", artifact_path=bounded.composite_dem_path)
            flow_mode = "breach_least_cost"
        else:
            flow_mode = self._resolve_flow_mode_for_conditioning(conditioning)

        self._set_emulator_dem(self.current_dem_path)
        try:
            flow_artifacts = derive_flow_stack(
                self._emulator,
                csa=self.config.csa,
                mcl=self.config.mcl,
                fill_or_breach=flow_mode,
                blc_dist=self._as_blc_dist(),
                blc_max_cost=self.config.blc_max_cost,
                blc_fill=self.config.blc_fill,
            )
        except (TypeError, ValueError, TerrainProcessorHelperError) as exc:
            self._raise_helper_runtime_error(
                message="Flow stack derivation failed",
                code="helper_flow_stack_error",
                context={"phase": phase, "conditioning": conditioning},
                exc=exc,
            )
        self.current_dem_path = flow_artifacts.relief_path

        self._register_artifact(phase=phase, artifact_name="relief", artifact_path=flow_artifacts.relief_path)
        self._register_artifact(phase=phase, artifact_name="flovec", artifact_path=flow_artifacts.flow_vector_path)
        self._register_artifact(
            phase=phase,
            artifact_name="floaccum",
            artifact_path=flow_artifacts.flow_accumulation_path,
        )
        self._register_artifact(phase=phase, artifact_name="netful", artifact_path=flow_artifacts.stream_raster_path)
        self._register_artifact(
            phase=phase,
            artifact_name="netful_geojson",
            artifact_path=flow_artifacts.stream_geojson_path,
        )
        self._register_artifact(
            phase=phase,
            artifact_name="chnjnt",
            artifact_path=flow_artifacts.stream_junctions_path,
        )
        self._add_provenance(
            step="conditioning",
            artifact=flow_artifacts.relief_path,
            phase=phase,
            parameters={
                "conditioning": conditioning,
                "csa": self.config.csa,
                "mcl": self.config.mcl,
                "blc_dist_m": self.config.blc_dist_m,
                "blc_max_cost": self.config.blc_max_cost,
                "blc_fill": self.config.blc_fill,
            },
        )

    def _run_phase3_culvert_enforcement(self, _changed_keys: Sequence[str]) -> None:
        phase = _PHASE_3
        if not self.config.enforce_culverts:
            return

        roads_path = self._phase_artifact(_PHASE_1, "roads_utm_geojson")
        stream_geojson_path = self._phase_artifact(_PHASE_2, "netful_geojson")
        stream_raster_path = self._phase_artifact(_PHASE_2, "netful")
        try:
            crossings_payload = extract_road_stream_intersections(roads_path, stream_geojson_path)
        except TerrainProcessorHelperError as exc:
            self._raise_helper_runtime_error(
                message="Road/stream intersection extraction failed",
                code="helper_culvert_intersection_error",
                context={"phase": phase},
                exc=exc,
            )
        crossings_path = self.workspace / "culvert_crossings.geojson"
        self._write_json(crossings_path, crossings_payload)
        self._register_artifact(
            phase=phase,
            artifact_name="culvert_crossings_geojson",
            artifact_path=str(crossings_path),
        )

        culvert_points_payload = crossings_payload
        if self.config.culvert_source == "upload_points":
            if not self.config.culvert_path:
                raise TerrainProcessorRuntimeError(
                    "culvert_path is required when culvert_source='upload_points'",
                    code="missing_culvert_path",
                )
            try:
                culvert_points_payload = snap_uploaded_culvert_points_to_crossings(
                    uploaded_culvert_points=self.config.culvert_path,
                    crossing_points=str(crossings_path),
                    max_snap_distance_m=self.config.snap_distance,
                )
            except TerrainProcessorHelperError as exc:
                self._raise_helper_runtime_error(
                    message="Uploaded culvert snapping failed",
                    code="helper_culvert_snap_error",
                    context={"phase": phase},
                    exc=exc,
                )

        culvert_points_path = self.workspace / "culvert_points.geojson"
        self._write_json(culvert_points_path, culvert_points_payload)
        self._register_artifact(
            phase=phase,
            artifact_name="culvert_points_geojson",
            artifact_path=str(culvert_points_path),
        )

        if self.config.culvert_method != "burn_streams_at_roads":
            raise TerrainProcessorRuntimeError(
                "Only culvert_method='burn_streams_at_roads' is currently implemented",
                code="unsupported_culvert_method",
                context={"culvert_method": self.config.culvert_method},
            )

        burned_relief_path = self.workspace / "relief_burned.tif"
        try:
            burn_streams_at_roads_adapter(
                wbt=self._require_wbt_runner(),
                dem_path=self.current_dem_path,
                streams_path=stream_raster_path,
                roads_path=roads_path,
                output_path=str(burned_relief_path),
                road_width_m=self.config.culvert_road_width,
            )
        except TerrainProcessorHelperError as exc:
            self._raise_helper_runtime_error(
                message="BurnStreamsAtRoads runtime adapter failed",
                code="helper_culvert_burn_error",
                context={"phase": phase},
                exc=exc,
            )
        self.current_dem_path = str(burned_relief_path)
        self._register_artifact(
            phase=phase,
            artifact_name="relief_burned",
            artifact_path=self.current_dem_path,
        )
        self._add_provenance(
            step="burn_culverts",
            artifact=self.current_dem_path,
            phase=phase,
            parameters={
                "culvert_source": self.config.culvert_source,
                "culvert_method": self.config.culvert_method,
                "culvert_road_width": self.config.culvert_road_width,
            },
            metadata={
                "culvert_point_count": len(culvert_points_payload.get("features", [])),
            },
        )

        self._set_emulator_dem(self.current_dem_path)
        try:
            rerun_flow = derive_flow_stack(
                self._emulator,
                csa=self.config.csa,
                mcl=self.config.mcl,
                fill_or_breach=self._resolve_flow_mode_for_conditioning(self.config.conditioning),
                blc_dist=self._as_blc_dist(),
                blc_max_cost=self.config.blc_max_cost,
                blc_fill=self.config.blc_fill,
            )
        except (TypeError, ValueError, TerrainProcessorHelperError) as exc:
            self._raise_helper_runtime_error(
                message="Post-culvert flow stack rerun failed",
                code="helper_flow_stack_error",
                context={"phase": phase},
                exc=exc,
            )
        self._register_artifact(phase=phase, artifact_name="relief_v2", artifact_path=rerun_flow.relief_path)
        self._register_artifact(
            phase=phase,
            artifact_name="flovec_v2",
            artifact_path=rerun_flow.flow_vector_path,
        )
        self._register_artifact(
            phase=phase,
            artifact_name="floaccum_v2",
            artifact_path=rerun_flow.flow_accumulation_path,
        )
        self._register_artifact(
            phase=phase,
            artifact_name="netful_v2",
            artifact_path=rerun_flow.stream_raster_path,
        )
        self._register_artifact(
            phase=phase,
            artifact_name="netful_geojson_v2",
            artifact_path=rerun_flow.stream_geojson_path,
        )
        self._register_artifact(
            phase=phase,
            artifact_name="chnjnt_v2",
            artifact_path=rerun_flow.stream_junctions_path,
        )

    def _run_phase4_outlet_resolution(self, _changed_keys: Sequence[str]) -> None:
        phase = _PHASE_4

        if self.config.outlet_mode == "multiple":
            if not self.config.outlets:
                raise TerrainProcessorRuntimeError(
                    "outlets must be provided when outlet_mode='multiple'",
                    code="missing_multiple_outlets",
                )
            try:
                snapped = snap_outlets_to_streams(
                    self.config.outlets,
                    snapper=self._snap_outlet,
                )
            except ValueError as exc:
                self._raise_helper_runtime_error(
                    message="Outlet snapping failed for multiple outlet mode",
                    code="helper_outlet_snap_error",
                    context={"phase": phase},
                    exc=exc,
                )
            outlets_geojson = build_outlet_feature_collection(snapped)
            outlets_path = self.workspace / "outlets_snapped.geojson"
            self._write_json(outlets_path, outlets_geojson)
            self._register_artifact(
                phase=phase,
                artifact_name="outlets_snapped_geojson",
                artifact_path=str(outlets_path),
            )
            unnested_path, hierarchy_csv = self._run_unnest_basins(outlets_geojson_path=str(outlets_path))
            self._register_artifact(phase=phase, artifact_name="unnested_tif", artifact_path=unnested_path)
            self._register_artifact(
                phase=phase,
                artifact_name="hierarchy_csv",
                artifact_path=hierarchy_csv,
            )
            try:
                self._basin_summaries = parse_unnest_basins_hierarchy_csv(hierarchy_csv)
            except (FileNotFoundError, ValueError) as exc:
                self._raise_helper_runtime_error(
                    message="Unnest basins hierarchy parsing failed",
                    code="helper_hierarchy_parse_error",
                    context={"phase": phase, "hierarchy_csv": hierarchy_csv},
                    exc=exc,
                )
            return

        outlet_path = self.workspace / "outlet.geojson"
        if self.config.outlet_mode == "auto" or not self.config.outlets:
            self._find_outlet_auto(outlet_geojson_path=str(outlet_path))
        else:
            requested = self.config.outlets[0]
            try:
                snapped = snap_outlets_to_streams(
                    [requested],
                    snapper=self._snap_outlet,
                )
            except ValueError as exc:
                self._raise_helper_runtime_error(
                    message="Outlet snapping failed for single outlet mode",
                    code="helper_outlet_snap_error",
                    context={"phase": phase},
                    exc=exc,
                )
            fc = build_outlet_feature_collection(snapped)
            self._write_json(outlet_path, fc)
            self._set_emulator_outlet_from_geojson(str(outlet_path))

        self._register_artifact(phase=phase, artifact_name="outlet_geojson", artifact_path=str(outlet_path))
        bound_geojson = self._create_final_boundary()
        self._register_artifact(phase=phase, artifact_name="bound_geojson", artifact_path=bound_geojson)

    def _run_phase5_visualization_artifacts(self, _changed_keys: Sequence[str]) -> None:
        phase = _PHASE_5
        viz_dir = self.workspace / "visualization"
        viz_dir.mkdir(parents=True, exist_ok=True)
        self._visualization_manifest = []
        benchmark_entries: list[dict[str, Any]] = []

        raster_sources = self._collect_raster_sources_for_visualization()
        for artifact_name, source_phase, raster_path in raster_sources:
            pixel_count = self._assert_visualization_raster_within_limits(
                input_raster=raster_path,
                artifact_name=artifact_name,
            )
            self._register_manifest_source_entry(
                artifact_id=f"{artifact_name}_source",
                artifact_type="source_raster",
                source_phase=source_phase,
                path=raster_path,
            )
            hillshade_path = viz_dir / f"{artifact_name}_hillshade.tif"
            slope_path = viz_dir / f"{artifact_name}_slope.tif"
            hillshade_slope_ms = self._generate_hillshade_and_slope(
                input_raster=raster_path,
                output_hillshade=str(hillshade_path),
                output_slope=str(slope_path),
            )
            benchmark_entries.append(
                {
                    "artifact_id": f"{artifact_name}_hillshade_slope",
                    "operation": "hillshade_slope",
                    "source_phase": source_phase,
                    "source_artifact": artifact_name,
                    "elapsed_ms": hillshade_slope_ms,
                    "pixel_count": pixel_count,
                }
            )
            self._register_manifest_entry(
                VisualizationManifestEntry(
                    artifact_id=f"{artifact_name}_hillshade",
                    artifact_type="hillshade",
                    source_phase=source_phase,
                    path=str(hillshade_path),
                    dependencies=(artifact_name,),
                    metadata={
                        **self._raster_metadata(str(hillshade_path)),
                        "generation_ms": hillshade_slope_ms,
                    },
                )
            )
            self._register_manifest_entry(
                VisualizationManifestEntry(
                    artifact_id=f"{artifact_name}_slope",
                    artifact_type="slope",
                    source_phase=source_phase,
                    path=str(slope_path),
                    dependencies=(artifact_name,),
                    metadata={
                        **self._raster_metadata(str(slope_path)),
                        "generation_ms": hillshade_slope_ms,
                    },
                )
            )

        benchmark_entries.extend(self._generate_visualization_diffs(viz_dir=viz_dir))
        self._register_vector_overlays()

        manifest_path = viz_dir / "visualization_manifest.json"
        entries = [entry.to_dict() for entry in sorted(self._visualization_manifest, key=lambda item: item.artifact_id)]
        with manifest_path.open("w", encoding="utf-8") as fp:
            json.dump({"entries": entries}, fp, indent=2, sort_keys=True)
            fp.write("\n")

        self._register_artifact(
            phase=phase,
            artifact_name="visualization_manifest_json",
            artifact_path=str(manifest_path),
        )

        benchmark_path = viz_dir / "visualization_benchmarks.json"
        self._write_json(
            benchmark_path,
            {"entries": sorted(benchmark_entries, key=lambda item: item["artifact_id"])},
        )
        self._register_artifact(
            phase=phase,
            artifact_name="visualization_benchmarks_json",
            artifact_path=str(benchmark_path),
        )

        ui_payload_path = viz_dir / "visualization_ui_payload.json"
        self._write_json(
            ui_payload_path,
            self._build_visualization_ui_payload(entries=entries),
        )
        self._register_artifact(
            phase=phase,
            artifact_name="visualization_ui_payload_json",
            artifact_path=str(ui_payload_path),
        )

    def _run_phase6_invalidation_reentry(self, changed_keys: Sequence[str]) -> None:
        phase = _PHASE_6
        helper_invalidated = self._determine_helper_invalidated_phases(changed_keys)
        runtime_invalidated = self._determine_runtime_invalidated_phases(changed_keys)
        report = {
            "changed_config_keys": list(changed_keys),
            "helper_invalidated_phases": helper_invalidated,
            "runtime_invalidated_phases": runtime_invalidated,
            "phase_sequence": list(self.phase_sequence),
        }
        report_path = self.workspace / "phase6_invalidation_report.json"
        self._write_json(report_path, report)
        self._register_artifact(
            phase=phase,
            artifact_name="phase6_invalidation_report_json",
            artifact_path=str(report_path),
        )

    def _smooth_dem(self, *, input_dem: str, output_dem: str) -> None:
        method = self.config.smooth_algorithm
        wbt = self._require_wbt_runner()
        if method == "feature_preserving":
            if not hasattr(wbt, "feature_preserving_smoothing"):
                raise TerrainProcessorRuntimeError(
                    "wbt runner does not expose feature_preserving_smoothing",
                    code="missing_wbt_tool",
                )
            try:
                wbt.feature_preserving_smoothing(
                    i=input_dem,
                    output=output_dem,
                    filter=int(self.config.smooth_filter_size),
                    max_diff=float(self.config.smooth_max_diff),
                )
            except TypeError as exc:
                raise TerrainProcessorRuntimeError(
                    "feature_preserving_smoothing argument contract mismatch",
                    code="wbt_contract_error",
                ) from exc
        elif method == "gaussian":
            if not hasattr(wbt, "gaussian_filter"):
                raise TerrainProcessorRuntimeError(
                    "wbt runner does not expose gaussian_filter",
                    code="missing_wbt_tool",
                )
            try:
                wbt.gaussian_filter(
                    i=input_dem,
                    output=output_dem,
                    sigma=float(self.config.smooth_max_diff),
                )
            except TypeError as exc:
                raise TerrainProcessorRuntimeError(
                    "gaussian_filter argument contract mismatch",
                    code="wbt_contract_error",
                ) from exc
        elif method == "mean":
            if not hasattr(wbt, "mean_filter"):
                raise TerrainProcessorRuntimeError(
                    "wbt runner does not expose mean_filter",
                    code="missing_wbt_tool",
                )
            filter_size = int(self.config.smooth_filter_size)
            try:
                wbt.mean_filter(
                    i=input_dem,
                    output=output_dem,
                    filterx=filter_size,
                    filtery=filter_size,
                )
            except TypeError as exc:
                raise TerrainProcessorRuntimeError(
                    "mean_filter argument contract mismatch",
                    code="wbt_contract_error",
                ) from exc
        else:
            raise TerrainProcessorRuntimeError(
                "Unsupported smooth_algorithm",
                code="unsupported_smoothing_algorithm",
                context={"smooth_algorithm": method},
            )

        if not os.path.exists(output_dem):
            raise TerrainProcessorRuntimeError(
                "Smoothing step did not create output DEM",
                code="missing_smoothed_dem",
                context={"output_dem": output_dem},
            )

    def _synthesize_road_embankments(
        self,
        *,
        input_dem: str,
        roads_path: str,
        output_dem: str,
        embankment_mask_path: str,
    ) -> None:
        wbt = self._require_wbt_runner()
        if not hasattr(wbt, "raise_roads"):
            raise TerrainProcessorRuntimeError(
                "wbt runner does not expose raise_roads",
                code="missing_wbt_tool",
            )

        kwargs: dict[str, Any] = {
            "dem": input_dem,
            "roads": roads_path,
            "output": output_dem,
            "strategy": self.config.road_fill_strategy,
            "embankment_mask": embankment_mask_path,
        }
        if self.config.road_buffer_width is not None:
            kwargs["road_width"] = float(self.config.road_buffer_width)
        if self.config.road_fill_strategy == "constant":
            kwargs["dy"] = float(self.config.road_fill_dy)
        if self.config.road_fill_strategy == "profile_relative":
            kwargs["margin"] = float(self.config.road_fill_margin)

        try:
            wbt.raise_roads(**kwargs)
        except TypeError as exc:
            raise TerrainProcessorRuntimeError(
                "raise_roads argument contract mismatch",
                code="wbt_contract_error",
            ) from exc
        if not os.path.exists(output_dem):
            raise TerrainProcessorRuntimeError(
                "raise_roads did not create output DEM",
                code="missing_roads_dem",
                context={"output_dem": output_dem},
            )

    def _resolve_roads_path(self) -> str | None:
        if self.config.roads_source is None:
            return None

        if self.config.roads_source == "osm" and self._osm_service is None:
            raise TerrainProcessorRuntimeError(
                "OSM roads source requested but osm_service is not configured",
                code="missing_osm_service",
            )

        target_epsg = getattr(self._emulator, "epsg", None)
        return resolve_roads_source(
            roads_source=self.config.roads_source,
            roads_path=self.config.roads_path,
            osm_service=self._osm_service,  # type: ignore[arg-type]
            aoi_wgs84_geojson=self.config.aoi_wgs84_geojson,
            target_epsg=target_epsg,
            osm_highway_filter=self.config.osm_highway_filter,
        )

    def _bounded_breach_runner(self, masked_dem_path: str, output_breached_path: str) -> None:
        wbt = self._require_wbt_runner()
        if not hasattr(wbt, "breach_depressions"):
            raise TerrainProcessorRuntimeError(
                "wbt runner does not expose breach_depressions",
                code="missing_wbt_tool",
            )
        wbt.breach_depressions(dem=masked_dem_path, output=output_breached_path, fill_pits=True)

    def _create_preliminary_boundary(self, *, fill_artifacts: Any) -> str:
        if self.config.outlet_mode == "auto" or not self.config.outlets:
            self._find_outlet_auto(
                outlet_geojson_path=self._require_path(
                    getattr(self._emulator, "outlet_geojson", None),
                    "outlet_geojson",
                ),
                stream_raster_path=str(fill_artifacts.stream_raster_path),
            )
        else:
            first_outlet = self.config.outlets[0]
            self._snap_outlet(first_outlet[0], first_outlet[1])

        if not hasattr(self._emulator, "_create_bound"):
            raise TerrainProcessorRuntimeError(
                "emulator does not expose _create_bound required for bounded_breach",
                code="missing_emulator_bound_contract",
            )
        self._emulator._create_bound()
        candidate_bound_wgs = getattr(self._emulator, "bound_wgs_json", None)
        candidate_bound = getattr(self._emulator, "bound_json", None)
        boundary_source = candidate_bound_wgs if candidate_bound_wgs and os.path.exists(candidate_bound_wgs) else candidate_bound
        if not boundary_source or not os.path.exists(boundary_source):
            raise TerrainProcessorRuntimeError(
                "Bounded breach preliminary boundary GeoJSON is missing",
                code="missing_preliminary_boundary_geojson",
            )

        boundary_out = self.workspace / "boundary_preliminary.geojson"
        shutil.copy2(boundary_source, boundary_out)
        return str(boundary_out)

    def _find_outlet_auto(
        self,
        *,
        outlet_geojson_path: str,
        stream_raster_path: str | None = None,
    ) -> None:
        wbt = self._require_wbt_runner()
        if not hasattr(wbt, "find_outlet"):
            raise TerrainProcessorRuntimeError(
                "wbt runner does not expose find_outlet",
                code="missing_wbt_tool",
            )
        stream_raster = stream_raster_path or self._latest_stream_raster_path()
        try:
            wbt.find_outlet(
                d8_pntr=self._require_path(getattr(self._emulator, "flovec", None), "flovec"),
                streams=stream_raster,
                output=outlet_geojson_path,
            )
        except TypeError as exc:
            raise TerrainProcessorRuntimeError(
                "find_outlet argument contract mismatch",
                code="wbt_contract_error",
            ) from exc
        if not os.path.exists(outlet_geojson_path):
            raise TerrainProcessorRuntimeError(
                "find_outlet did not create outlet GeoJSON",
                code="missing_auto_outlet_geojson",
                context={"outlet_geojson_path": outlet_geojson_path},
            )
        self._set_emulator_outlet_from_geojson(outlet_geojson_path)

    def _set_emulator_outlet_from_geojson(self, geojson_path: str) -> None:
        if hasattr(self._emulator, "set_outlet_from_geojson"):
            self._emulator.set_outlet_from_geojson(geojson_path)

    def _create_final_boundary(self) -> str:
        if not hasattr(self._emulator, "_create_bound"):
            raise TerrainProcessorRuntimeError(
                "emulator does not expose _create_bound",
                code="missing_emulator_bound_contract",
            )
        self._emulator._create_bound()

        bound_wgs = getattr(self._emulator, "bound_wgs_json", None)
        bound_native = getattr(self._emulator, "bound_json", None)
        source = bound_wgs if bound_wgs and os.path.exists(bound_wgs) else bound_native
        if not source or not os.path.exists(source):
            raise TerrainProcessorRuntimeError(
                "Boundary GeoJSON not found after _create_bound",
                code="missing_boundary_geojson",
            )
        bound_out = self.workspace / "bound.geojson"
        shutil.copy2(source, bound_out)
        return str(bound_out)

    def _run_unnest_basins(self, *, outlets_geojson_path: str) -> tuple[str, str]:
        wbt = self._require_wbt_runner()
        if not hasattr(wbt, "unnest_basins"):
            raise TerrainProcessorRuntimeError(
                "wbt runner does not expose unnest_basins",
                code="missing_wbt_tool",
            )
        unnested_path = str(self.workspace / "unnested.tif")
        hierarchy_path = str(self.workspace / "hierarchy.csv")
        kwargs: dict[str, Any] = {
            "d8_pntr": self._require_path(getattr(self._emulator, "flovec", None), "flovec"),
            "pour_pts": outlets_geojson_path,
            "output": unnested_path,
        }
        if self._callable_supports_keyword(wbt.unnest_basins, "hierarchy"):
            kwargs["hierarchy"] = hierarchy_path
        try:
            returned = wbt.unnest_basins(**kwargs)
        except TypeError as exc:
            raise TerrainProcessorRuntimeError(
                "unnest_basins argument contract mismatch",
                code="wbt_contract_error",
            ) from exc
        if isinstance(returned, str) and returned.endswith(".csv") and os.path.exists(returned):
            hierarchy_path = returned
        elif not os.path.exists(hierarchy_path):
            detected_hierarchy = self._detect_unnest_hierarchy_sidecar(unnested_path=unnested_path)
            if detected_hierarchy is not None:
                hierarchy_path = detected_hierarchy

        if not os.path.exists(unnested_path):
            raise TerrainProcessorRuntimeError(
                "unnest_basins did not create unnested raster",
                code="missing_unnested_raster",
                context={"unnested_path": unnested_path},
            )
        if not os.path.exists(hierarchy_path):
            raise TerrainProcessorRuntimeError(
                "unnest_basins did not create hierarchy CSV",
                code="missing_unnest_hierarchy",
                context={
                    "hierarchy_path": hierarchy_path,
                    "searched_paths": self._unnest_hierarchy_search_paths(unnested_path=unnested_path),
                },
            )
        return unnested_path, hierarchy_path

    @staticmethod
    def _callable_supports_keyword(func: Callable[..., Any], keyword: str) -> bool:
        try:
            signature = inspect.signature(func)
        except (TypeError, ValueError):
            return True

        for parameter in signature.parameters.values():
            if parameter.kind is inspect.Parameter.VAR_KEYWORD:
                return True
        return keyword in signature.parameters

    def _detect_unnest_hierarchy_sidecar(self, *, unnested_path: str) -> str | None:
        for candidate in self._unnest_hierarchy_search_paths(unnested_path=unnested_path):
            if os.path.exists(candidate):
                return candidate
        return None

    def _unnest_hierarchy_search_paths(self, *, unnested_path: str) -> list[str]:
        unnested = Path(unnested_path)
        stem = unnested.stem
        return [
            str(self.workspace / "hierarchy.csv"),
            str(unnested.with_suffix(".csv")),
            str(unnested.with_name(f"{stem}_hierarchy.csv")),
            str(unnested.with_name(f"{stem}.hierarchy.csv")),
            str(self.workspace / "unnest_basins_hierarchy.csv"),
        ]

    def _snap_outlet(self, lng: float, lat: float) -> tuple[float, float]:
        if not hasattr(self._emulator, "set_outlet"):
            raise TerrainProcessorRuntimeError(
                "emulator does not expose set_outlet",
                code="missing_emulator_set_outlet",
            )
        outlet = self._emulator.set_outlet(float(lng), float(lat), pixelcoords=False)
        actual_loc = getattr(outlet, "actual_loc", None)
        if not actual_loc or len(actual_loc) != 2:
            raise TerrainProcessorRuntimeError(
                "set_outlet returned an outlet without actual_loc tuple",
                code="invalid_outlet_contract",
            )
        return float(actual_loc[0]), float(actual_loc[1])

    def _collect_raster_sources_for_visualization(self) -> list[tuple[str, str, str]]:
        candidates = (
            (_PHASE_1, "dem_raw"),
            (_PHASE_1, "dem_smoothed"),
            (_PHASE_1, "dem_roads"),
            (_PHASE_2, "filled_dem"),
            (_PHASE_2, "composite_dem"),
            (_PHASE_2, "relief"),
            (_PHASE_3, "relief_burned"),
        )
        sources: list[tuple[str, str, str]] = []
        for phase, artifact_name in candidates:
            path = self._artifacts_by_phase.get(phase, {}).get(artifact_name)
            if path is None:
                continue
            if not self._is_raster_path(path):
                continue
            if not os.path.exists(path):
                continue
            sources.append((artifact_name, phase, path))
        return sources

    def _register_vector_overlays(self) -> None:
        vector_candidates = (
            (_PHASE_1, "roads_utm_geojson"),
            (_PHASE_2, "netful_geojson"),
            (_PHASE_3, "culvert_points_geojson"),
            (_PHASE_3, "netful_geojson_v2"),
            (_PHASE_4, "outlet_geojson"),
            (_PHASE_4, "bound_geojson"),
            (_PHASE_4, "outlets_snapped_geojson"),
        )
        for phase, artifact_name in vector_candidates:
            path = self._artifacts_by_phase.get(phase, {}).get(artifact_name)
            if path is None or not os.path.exists(path):
                continue
            self._register_manifest_entry(
                VisualizationManifestEntry(
                    artifact_id=f"{artifact_name}_overlay",
                    artifact_type="vector_overlay",
                    source_phase=phase,
                    path=path,
                    dependencies=(artifact_name,),
                    metadata={"extension": Path(path).suffix.lower()},
                )
            )

    def _generate_visualization_diffs(self, *, viz_dir: Path) -> list[dict[str, Any]]:
        # Deterministic phase-by-phase DEM diffs.
        pairs: list[tuple[str, str, str]] = []
        if self._has_artifact(_PHASE_1, "dem_raw") and self._has_artifact(_PHASE_1, "dem_smoothed"):
            pairs.append(("dem_raw", "dem_smoothed", _PHASE_1))
        if self._has_artifact(_PHASE_1, "dem_smoothed") and self._has_artifact(_PHASE_1, "dem_roads"):
            pairs.append(("dem_smoothed", "dem_roads", _PHASE_1))
        elif self._has_artifact(_PHASE_1, "dem_raw") and self._has_artifact(_PHASE_1, "dem_roads"):
            pairs.append(("dem_raw", "dem_roads", _PHASE_1))
        if self._has_artifact(_PHASE_1, "dem_roads") and self._has_artifact(_PHASE_2, "relief"):
            pairs.append(("dem_roads", "relief", _PHASE_2))
        elif self._has_artifact(_PHASE_1, "dem_smoothed") and self._has_artifact(_PHASE_2, "relief"):
            pairs.append(("dem_smoothed", "relief", _PHASE_2))
        elif self._has_artifact(_PHASE_1, "dem_raw") and self._has_artifact(_PHASE_2, "relief"):
            pairs.append(("dem_raw", "relief", _PHASE_2))
        if self._has_artifact(_PHASE_2, "filled_dem") and self._has_artifact(_PHASE_2, "composite_dem"):
            pairs.append(("filled_dem", "composite_dem", _PHASE_2))
        if self._has_artifact(_PHASE_2, "relief") and self._has_artifact(_PHASE_3, "relief_burned"):
            pairs.append(("relief", "relief_burned", _PHASE_3))

        benchmark_entries: list[dict[str, Any]] = []
        for before_name, after_name, phase in pairs:
            before_path = self._find_artifact_path(before_name)
            after_path = self._find_artifact_path(after_name)
            if before_path is None or after_path is None:
                continue
            self._assert_visualization_raster_within_limits(
                input_raster=before_path,
                artifact_name=before_name,
            )
            self._assert_visualization_raster_within_limits(
                input_raster=after_path,
                artifact_name=after_name,
            )
            diff_out = viz_dir / f"{before_name}_to_{after_name}_diff.tif"
            diff_elapsed_ms = self._generate_diff_raster(
                before_raster=before_path,
                after_raster=after_path,
                output_raster=str(diff_out),
            )
            benchmark_entries.append(
                {
                    "artifact_id": f"{before_name}_to_{after_name}_diff",
                    "operation": "diff_raster",
                    "source_phase": phase,
                    "before_artifact": before_name,
                    "after_artifact": after_name,
                    "elapsed_ms": diff_elapsed_ms,
                }
            )
            self._register_manifest_entry(
                VisualizationManifestEntry(
                    artifact_id=f"{before_name}_to_{after_name}_diff",
                    artifact_type="diff_raster",
                    source_phase=phase,
                    path=str(diff_out),
                    dependencies=(before_name, after_name),
                    metadata={
                        **self._raster_metadata(str(diff_out)),
                        "generation_ms": diff_elapsed_ms,
                    },
                )
            )
        return benchmark_entries

    def _register_manifest_source_entry(
        self,
        *,
        artifact_id: str,
        artifact_type: str,
        source_phase: str,
        path: str,
    ) -> None:
        self._register_manifest_entry(
            VisualizationManifestEntry(
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                source_phase=source_phase,
                path=path,
                metadata=self._raster_metadata(path),
            )
        )

    def _register_manifest_entry(self, entry: VisualizationManifestEntry) -> None:
        self._visualization_manifest.append(entry)

    def _build_visualization_ui_payload(self, *, entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        grouped_ids: dict[str, list[str]] = {
            "source_rasters": [],
            "hillshade": [],
            "slope": [],
            "diff_rasters": [],
            "vector_overlays": [],
            "other": [],
        }
        layers: list[dict[str, Any]] = []
        for entry in entries:
            artifact_id = str(entry.get("artifact_id", ""))
            artifact_type = str(entry.get("artifact_type", ""))
            path = str(entry.get("path", ""))
            layer = dict(entry)
            layer["relative_path"] = self._relative_workspace_path(path)
            layers.append(layer)

            if artifact_type == "source_raster":
                grouped_ids["source_rasters"].append(artifact_id)
            elif artifact_type == "hillshade":
                grouped_ids["hillshade"].append(artifact_id)
            elif artifact_type == "slope":
                grouped_ids["slope"].append(artifact_id)
            elif artifact_type == "diff_raster":
                grouped_ids["diff_rasters"].append(artifact_id)
            elif artifact_type == "vector_overlay":
                grouped_ids["vector_overlays"].append(artifact_id)
            else:
                grouped_ids["other"].append(artifact_id)

        return {
            "workspace": str(self.workspace),
            "layer_count": len(layers),
            "layers": layers,
            "groups": grouped_ids,
        }

    def _generate_hillshade_and_slope(
        self,
        *,
        input_raster: str,
        output_hillshade: str,
        output_slope: str,
    ) -> float:
        import rasterio

        start = perf_counter()
        with rasterio.open(input_raster) as ds:
            arr = ds.read(1).astype(np.float64)
            transform = ds.transform
            nodata = ds.nodata
            mask = np.isfinite(arr)
            if nodata is not None and np.isfinite(nodata):
                mask &= arr != nodata
            x_res = float(abs(transform.a)) if transform.a else 1.0
            y_res = float(abs(transform.e)) if transform.e else 1.0
            gy, gx = np.gradient(np.where(mask, arr, 0.0), y_res, x_res)
            slope = np.sqrt(np.square(gx) + np.square(gy)).astype(np.float32)
            slope[~mask] = _SLOPE_NODATA

            scale = float(np.nanmax(slope[mask])) if np.any(mask) else 1.0
            if scale <= 0:
                scale = 1.0
            hillshade = np.clip(255.0 * (1.0 - (slope / scale)), 0, 255).astype(np.uint8)
            hillshade[~mask] = _HILLSHADE_NODATA

            slope_profile = ds.profile.copy()
            slope_profile.update(dtype="float32", nodata=_SLOPE_NODATA, compress="deflate")
            hillshade_profile = ds.profile.copy()
            hillshade_profile.update(dtype="uint8", nodata=_HILLSHADE_NODATA, compress="deflate")

        with rasterio.open(output_slope, "w", **slope_profile) as out_slope:
            out_slope.write(slope, 1)
        with rasterio.open(output_hillshade, "w", **hillshade_profile) as out_hillshade:
            out_hillshade.write(hillshade, 1)
        return round((perf_counter() - start) * 1000.0, 3)

    def _generate_diff_raster(
        self,
        *,
        before_raster: str,
        after_raster: str,
        output_raster: str,
    ) -> float:
        import rasterio

        start = perf_counter()
        with rasterio.open(before_raster) as before_ds, rasterio.open(after_raster) as after_ds:
            if before_ds.width != after_ds.width or before_ds.height != after_ds.height:
                raise TerrainProcessorRuntimeError(
                    "Diff raster inputs must have matching dimensions",
                    code="diff_dimension_mismatch",
                    context={"before": before_raster, "after": after_raster},
                )
            before = before_ds.read(1).astype(np.float64)
            after = after_ds.read(1).astype(np.float64)
            before_nodata = before_ds.nodata
            after_nodata = after_ds.nodata
            valid = np.isfinite(before) & np.isfinite(after)
            if before_nodata is not None and np.isfinite(before_nodata):
                valid &= before != before_nodata
            if after_nodata is not None and np.isfinite(after_nodata):
                valid &= after != after_nodata
            diff = (after - before).astype(np.float32)
            diff[~valid] = _DIFF_NODATA

            profile = before_ds.profile.copy()
            profile.update(dtype="float32", nodata=_DIFF_NODATA, compress="deflate")

        with rasterio.open(output_raster, "w", **profile) as out:
            out.write(diff, 1)
        return round((perf_counter() - start) * 1000.0, 3)

    def _assert_visualization_raster_within_limits(self, *, input_raster: str, artifact_name: str) -> int:
        import rasterio

        with rasterio.open(input_raster) as ds:
            pixel_count = int(ds.width) * int(ds.height)
        if pixel_count > self.config.visualization_max_pixels:
            raise TerrainProcessorRuntimeError(
                "Visualization source raster exceeds configured max pixel limit",
                code="visualization_raster_too_large",
                context={
                    "artifact_name": artifact_name,
                    "pixel_count": pixel_count,
                    "max_pixels": self.config.visualization_max_pixels,
                },
            )
        return pixel_count

    def _relative_workspace_path(self, path: str) -> str | None:
        try:
            relative = Path(path).resolve().relative_to(self.workspace)
        except ValueError:
            return None
        return str(relative)

    def _raster_metadata(self, path: str) -> dict[str, Any]:
        import rasterio

        with rasterio.open(path) as ds:
            return {
                "crs": str(ds.crs) if ds.crs is not None else None,
                "width": int(ds.width),
                "height": int(ds.height),
                "resolution": [float(ds.transform.a), float(abs(ds.transform.e))],
                "nodata": ds.nodata,
            }

    def _determine_helper_invalidated_phases(self, changed_keys: Sequence[str]) -> list[str]:
        if not changed_keys:
            return []
        return determine_invalidated_phases(changed_config_keys=changed_keys)

    def _determine_runtime_invalidated_phases(self, changed_keys: Sequence[str]) -> list[str]:
        if not changed_keys:
            return []
        invalidated: set[str] = set()
        for key in changed_keys:
            mapped = _RUNTIME_INVALIDATION_RULES.get(key)
            if mapped is None:
                invalidated.update(_RUNTIME_PHASE_SEQUENCE)
            else:
                invalidated.update(mapped)
        return [phase for phase in _RUNTIME_PHASE_SEQUENCE if phase in invalidated]

    def _invalidate_runtime_phases(self, invalidated_phases: Sequence[str]) -> None:
        if not invalidated_phases:
            return
        invalidated_set = set(invalidated_phases)
        for phase in self.phase_sequence:
            if phase not in invalidated_set:
                continue
            for artifact_path in self._artifacts_by_phase.get(phase, {}).values():
                self._remove_generated_artifact(artifact_path)
            self._artifacts_by_phase.pop(phase, None)

        self._provenance = [
            entry for entry in self._provenance if entry.metadata.get("phase") not in invalidated_set
        ]
        if _PHASE_4 in invalidated_set:
            self._basin_summaries = []
        if _PHASE_5 in invalidated_set:
            self._visualization_manifest = []

        self._rebuild_registry()

    def _resolve_current_dem_pointer_for_start_phase(self, start_idx: int) -> str:
        if start_idx <= self.phase_sequence.index(_PHASE_1):
            return self.dem_path
        if start_idx <= self.phase_sequence.index(_PHASE_2):
            return self._phase_artifact(_PHASE_1, "dem_roads", required=False) or self._phase_artifact(
                _PHASE_1, "dem_smoothed", required=False
            ) or self._phase_artifact(_PHASE_1, "dem_raw")
        if start_idx <= self.phase_sequence.index(_PHASE_3):
            return self._phase_artifact(_PHASE_2, "composite_dem", required=False) or self._phase_artifact(
                _PHASE_2, "relief"
            )
        return self._phase_artifact(_PHASE_3, "relief_burned", required=False) or self._phase_artifact(
            _PHASE_2, "relief"
        )

    def _changed_config_keys(self, old_config: TerrainConfig, new_config: TerrainConfig) -> tuple[str, ...]:
        old_payload = old_config.to_dict()
        new_payload = new_config.to_dict()
        keys = sorted(set(old_payload) | set(new_payload))
        changed = [key for key in keys if old_payload.get(key) != new_payload.get(key)]
        return tuple(changed)

    def _refresh_protected_input_paths(self) -> None:
        protected: set[Path] = set()
        for candidate in (self.dem_path, self.config.roads_path, self.config.culvert_path):
            if not candidate:
                continue
            protected.add(self._canonical_path(candidate))
        self._protected_input_paths = protected

    def _rebuild_registry(self) -> None:
        self._artifact_registry = TerrainArtifactRegistry()
        for phase, artifacts in self._artifacts_by_phase.items():
            for artifact_name, artifact_path in artifacts.items():
                self._artifact_registry.register(
                    phase=phase,
                    artifact_name=artifact_name,
                    artifact_path=artifact_path,
                )

    def _register_artifact(self, *, phase: str, artifact_name: str, artifact_path: str) -> None:
        self._artifact_registry.register(
            phase=phase,
            artifact_name=artifact_name,
            artifact_path=artifact_path,
        )
        phase_bucket = self._artifacts_by_phase.setdefault(phase, {})
        phase_bucket[artifact_name] = artifact_path

    def _add_provenance(
        self,
        *,
        step: str,
        artifact: str,
        phase: str,
        parameters: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        merged_metadata = dict(metadata or {})
        merged_metadata["phase"] = phase
        self._provenance.append(
            ProvenanceEntry(
                step=step,
                artifact=artifact,
                parameters=dict(parameters or {}),
                metadata=merged_metadata,
            )
        )

    def _phase_artifact(self, phase: str, artifact_name: str, *, required: bool = True) -> str:
        phase_bucket = self._artifacts_by_phase.get(phase, {})
        artifact_path = phase_bucket.get(artifact_name)
        if artifact_path is None and required:
            raise TerrainProcessorRuntimeError(
                "Required phase artifact is missing",
                code="missing_phase_artifact",
                context={"phase": phase, "artifact_name": artifact_name},
            )
        if artifact_path is None:
            return ""
        return artifact_path

    def _find_artifact_path(self, artifact_name: str) -> str | None:
        for phase in self.phase_sequence:
            path = self._artifacts_by_phase.get(phase, {}).get(artifact_name)
            if path is not None:
                return path
        return None

    def _has_artifact(self, phase: str, artifact_name: str) -> bool:
        path = self._artifacts_by_phase.get(phase, {}).get(artifact_name)
        return bool(path and os.path.exists(path))

    def _latest_stream_raster_path(self) -> str:
        stream = self._phase_artifact(_PHASE_3, "netful_v2", required=False)
        if stream:
            return stream
        return self._phase_artifact(_PHASE_2, "netful")

    def _resolve_flow_mode_for_conditioning(self, conditioning: str) -> str:
        if conditioning == "fill":
            return "fill"
        if conditioning == "breach":
            return "breach"
        if conditioning in {"breach_least_cost", "bounded_breach"}:
            return "breach_least_cost"
        raise TerrainProcessorRuntimeError(
            "Unsupported conditioning mode",
            code="unsupported_conditioning_mode",
            context={"conditioning": conditioning},
        )

    def _as_blc_dist(self) -> int | None:
        if self.config.blc_dist_m is None:
            return None
        return int(round(self.config.blc_dist_m))

    def _set_emulator_dem(self, dem_path: str) -> None:
        if hasattr(self._emulator, "_parse_dem"):
            self._emulator._parse_dem(dem_path)
            return
        if hasattr(self._emulator, "_dem"):
            self._emulator._dem = dem_path
            return
        raise TerrainProcessorRuntimeError(
            "emulator does not expose a writable DEM contract",
            code="missing_emulator_dem_contract",
        )

    def _require_cellsize(self) -> float:
        cellsize = getattr(self._emulator, "cellsize", None)
        if cellsize is None:
            raise TerrainProcessorRuntimeError(
                "emulator does not expose cellsize required for bounded_breach",
                code="missing_cellsize",
            )
        if float(cellsize) <= 0:
            raise TerrainProcessorRuntimeError(
                "emulator cellsize must be positive",
                code="invalid_cellsize",
                context={"cellsize": cellsize},
            )
        return float(cellsize)

    def _require_wbt_runner(self) -> Any:
        wbt = getattr(self._emulator, "wbt", None)
        if wbt is None:
            raise TerrainProcessorRuntimeError(
                "emulator does not expose wbt runner",
                code="missing_wbt_runner",
            )
        return wbt

    def _remove_generated_artifact(self, artifact_path: str) -> None:
        path = Path(artifact_path)
        if not path.exists():
            return

        resolved_path = self._canonical_path(str(path))
        if resolved_path in self._protected_input_paths:
            return
        try:
            resolved_path.relative_to(self.workspace)
        except ValueError:
            return

        if resolved_path.is_file():
            resolved_path.unlink()
            return
        if resolved_path.is_dir():
            shutil.rmtree(resolved_path)

    def _require_path(self, value: Any, label: str) -> str:
        if value is None:
            raise TerrainProcessorRuntimeError(
                f"{label} path is required",
                code="missing_path_contract",
                context={"label": label},
            )
        path = str(value)
        if not path:
            raise TerrainProcessorRuntimeError(
                f"{label} path is empty",
                code="missing_path_contract",
                context={"label": label},
            )
        return path

    @staticmethod
    def _is_raster_path(path: str) -> bool:
        suffix = Path(path).suffix.lower()
        return suffix in {".tif", ".tiff", ".vrt"}

    @staticmethod
    def _canonical_path(path: str) -> Path:
        return Path(path).expanduser().resolve()

    @staticmethod
    def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fp:
            json.dump(payload, fp, indent=2, sort_keys=True)
            fp.write("\n")

    def _validate_config(self, config: TerrainConfig) -> None:
        if config.smooth_filter_size <= 0:
            raise TerrainProcessorRuntimeError(
                "smooth_filter_size must be greater than zero",
                code="invalid_smooth_filter_size",
            )
        if config.csa <= 0:
            raise TerrainProcessorRuntimeError("csa must be greater than zero", code="invalid_csa")
        if config.mcl <= 0:
            raise TerrainProcessorRuntimeError("mcl must be greater than zero", code="invalid_mcl")
        if config.snap_distance <= 0:
            raise TerrainProcessorRuntimeError(
                "snap_distance must be greater than zero",
                code="invalid_snap_distance",
            )
        if config.road_buffer_width is not None and config.road_buffer_width <= 0:
            raise TerrainProcessorRuntimeError(
                "road_buffer_width must be greater than zero when provided",
                code="invalid_road_buffer_width",
            )
        if config.roads_source not in {None, "upload", "osm"}:
            raise TerrainProcessorRuntimeError(
                "roads_source must be one of: None, 'upload', 'osm'",
                code="invalid_roads_source",
                context={"roads_source": config.roads_source},
            )
        if config.roads_source == "upload" and not config.roads_path:
            raise TerrainProcessorRuntimeError(
                "roads_path is required when roads_source='upload'",
                code="missing_roads_path",
            )
        if config.roads_source == "upload" and config.roads_path and not os.path.exists(config.roads_path):
            raise TerrainProcessorRuntimeError(
                "roads_path does not exist",
                code="roads_path_missing_file",
                context={"roads_path": config.roads_path},
            )
        if config.roads_source == "osm" and config.aoi_wgs84_geojson is None:
            raise TerrainProcessorRuntimeError(
                "aoi_wgs84_geojson is required when roads_source='osm'",
                code="missing_aoi_geojson",
            )
        if config.road_fill_strategy not in {"constant", "profile_relative", "cross_section"}:
            raise TerrainProcessorRuntimeError(
                "road_fill_strategy must be one of: constant, profile_relative, cross_section",
                code="invalid_road_fill_strategy",
                context={"road_fill_strategy": config.road_fill_strategy},
            )
        if config.conditioning not in {"fill", "breach", "breach_least_cost", "bounded_breach"}:
            raise TerrainProcessorRuntimeError(
                "conditioning must be one of: fill, breach, breach_least_cost, bounded_breach",
                code="invalid_conditioning",
                context={"conditioning": config.conditioning},
            )
        if config.blc_dist_m is not None and config.blc_dist_m <= 0:
            raise TerrainProcessorRuntimeError(
                "blc_dist_m must be greater than zero when provided",
                code="invalid_blc_dist",
            )
        if config.blc_max_cost is not None and config.blc_max_cost <= 0:
            raise TerrainProcessorRuntimeError(
                "blc_max_cost must be greater than zero when provided",
                code="invalid_blc_max_cost",
            )
        if not isinstance(config.blc_fill, bool):
            raise TerrainProcessorRuntimeError(
                "blc_fill must be a boolean value",
                code="invalid_blc_fill",
            )
        if config.culvert_source not in {"auto_intersect", "upload_points"}:
            raise TerrainProcessorRuntimeError(
                "culvert_source must be one of: auto_intersect, upload_points",
                code="invalid_culvert_source",
                context={"culvert_source": config.culvert_source},
            )
        if config.culvert_road_width <= 0:
            raise TerrainProcessorRuntimeError(
                "culvert_road_width must be greater than zero",
                code="invalid_culvert_road_width",
            )
        if config.enforce_culverts and config.roads_source is None:
            raise TerrainProcessorRuntimeError(
                "enforce_culverts requires roads_source to be configured",
                code="missing_roads_for_culverts",
            )
        if config.enforce_culverts and config.culvert_source == "upload_points":
            if not config.culvert_path:
                raise TerrainProcessorRuntimeError(
                    "culvert_path is required when culvert_source='upload_points'",
                    code="missing_culvert_path",
                )
            if not os.path.exists(config.culvert_path):
                raise TerrainProcessorRuntimeError(
                    "culvert_path does not exist",
                    code="culvert_path_missing_file",
                    context={"culvert_path": config.culvert_path},
                )
        if config.outlet_mode not in {"single", "multiple", "auto"}:
            raise TerrainProcessorRuntimeError(
                "outlet_mode must be one of: single, multiple, auto",
                code="invalid_outlet_mode",
                context={"outlet_mode": config.outlet_mode},
            )
        if config.outlet_mode == "multiple":
            if not config.outlets or len(config.outlets) < 2:
                raise TerrainProcessorRuntimeError(
                    "outlet_mode='multiple' requires two or more outlet coordinates",
                    code="invalid_multiple_outlets",
                )
        if config.visualization_max_pixels <= 0:
            raise TerrainProcessorRuntimeError(
                "visualization_max_pixels must be greater than zero",
                code="invalid_visualization_max_pixels",
            )

    def _raise_helper_runtime_error(
        self,
        *,
        message: str,
        code: str,
        context: Mapping[str, Any] | None,
        exc: Exception,
    ) -> None:
        error_context = dict(context or {})
        helper_code = getattr(exc, "code", None)
        if helper_code is not None:
            error_context["helper_code"] = helper_code
        raise TerrainProcessorRuntimeError(
            message,
            code=code,
            context=error_context,
        ) from exc


__all__ = [
    "TerrainConfig",
    "TerrainProcessor",
    "TerrainProcessorRuntimeError",
    "TerrainRunResult",
    "VisualizationManifestEntry",
]
