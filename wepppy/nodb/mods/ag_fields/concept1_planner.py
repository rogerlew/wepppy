"""Read-only one-dimensional OFE planning for AgFields routing schemes.

The planner converts the two-dimensional retained-subfield raster into contiguous
bands along the same discharge-rank ordering used by WEPPpy's MOFE map builder.
It performs no WEPP execution and does not decide scientific acceptance
thresholds.  Its versioned Parquet outputs are the review boundary between
geospatial fitting and later WEPP input synthesis.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from osgeo import gdal, osr


__all__ = [
    "ALGORITHM",
    "MAX_OFES",
    "PLANNER_SCHEMA_VERSION",
    "Concept1PlanningError",
    "OfeSegment",
    "ParentCandidate",
    "ParentPlan",
    "build_parent_plan",
    "run_planning_census",
]


PLANNER_SCHEMA_VERSION = "1.0"
ALGORITHM = "ag_fields_concept1_constrained_runs_v1"
MAX_OFES = 20
BACKGROUND_SOURCE_ID = 0


class Concept1PlanningError(RuntimeError):
    """Raised when planner inputs cannot satisfy the frozen geometry contract."""


@dataclass(frozen=True)
class OfeSegment:
    """One contiguous interval in discharge-rank space."""

    start_index: int
    end_index: int
    source_id: int
    agreeing_cells: int
    active_cells: int

    @property
    def cell_agreement(self) -> float:
        if self.active_cells == 0:
            return 0.0
        return self.agreeing_cells / self.active_cells


@dataclass(frozen=True)
class ParentCandidate:
    """Fit diagnostics for one parent segmentation candidate."""

    family: str
    segments: tuple[OfeSegment, ...]
    active_cells: int
    field_cells: int
    agreeing_cells: int
    agreeing_field_cells: int
    background_cells: int
    agreeing_background_cells: int
    total_absolute_source_area_error_m2: float
    max_field_area_error_fraction: float
    missing_source_count: int
    missing_field_source_count: int
    zero_overlap_field_source_count: int
    source_order_conflicts: int
    fragmented_field_count: int
    actual_downstream_background_fraction: float
    modeled_downstream_background_fraction: float

    @property
    def ofe_count(self) -> int:
        return len(self.segments)

    @property
    def overall_assignment_agreement(self) -> float:
        return self.agreeing_cells / self.active_cells

    @property
    def field_cell_agreement(self) -> float:
        if self.field_cells == 0:
            return 1.0
        return self.agreeing_field_cells / self.field_cells

    @property
    def background_cell_agreement(self) -> float:
        if self.background_cells == 0:
            return 1.0
        return self.agreeing_background_cells / self.background_cells

    @property
    def downstream_background_error_fraction(self) -> float:
        return abs(
            self.modeled_downstream_background_fraction
            - self.actual_downstream_background_fraction
        )


@dataclass(frozen=True)
class ParentPlan:
    """Selected diagnostic plan plus every candidate used to select it."""

    selected: ParentCandidate
    candidates: tuple[ParentCandidate, ...]
    ordered_source_ids: tuple[int, ...]
    active_mask: tuple[bool, ...]


@dataclass(frozen=True)
class _RasterResource:
    path: Path
    data: np.ndarray
    geotransform: tuple[float, ...]
    projection: str


class _SegmentSearch:
    def __init__(
        self,
        ordered_source_ids: np.ndarray,
        active_mask: np.ndarray,
        *,
        cell_area_m2: float,
    ) -> None:
        if ordered_source_ids.ndim != 1 or active_mask.ndim != 1:
            raise Concept1PlanningError("Ordered source ids and active mask must be one-dimensional.")
        if ordered_source_ids.size != active_mask.size:
            raise Concept1PlanningError("Ordered source ids and active mask have different lengths.")
        if not np.any(active_mask):
            raise Concept1PlanningError("A Concept 1 source requires at least one active raster cell.")
        if not math.isfinite(cell_area_m2) or cell_area_m2 <= 0.0:
            raise Concept1PlanningError(f"Invalid raster cell area: {cell_area_m2!r}.")

        self.labels = np.asarray(ordered_source_ids, dtype=np.int64)
        self.active = np.asarray(active_mask, dtype=np.bool_)
        self.cell_area_m2 = float(cell_area_m2)
        self.n_positions = int(self.labels.size)
        self.active_cells = int(np.count_nonzero(self.active))
        self.residual_area_m2 = self.active_cells * self.cell_area_m2
        self.source_ids = tuple(
            sorted(int(value) for value in np.unique(self.labels[self.active]))
        )
        self.source_index = {source_id: index for index, source_id in enumerate(self.source_ids)}
        self.prefix = np.zeros((len(self.source_ids), self.n_positions + 1), dtype=np.int64)
        for source_id, row in self.source_index.items():
            self.prefix[row, 1:] = np.cumsum(self.active & (self.labels == source_id))

        self.actual_counts = {
            source_id: self._source_count(source_id, 0, self.n_positions)
            for source_id in self.source_ids
        }
        self.field_cells = sum(
            count for source_id, count in self.actual_counts.items() if source_id > 0
        )
        self.background_cells = self.actual_counts.get(BACKGROUND_SOURCE_ID, 0)
        self.fragmented_field_count = self._fragmented_field_count()
        self.actual_downstream_background_fraction = self._actual_downstream_background_fraction()

    def _source_count(self, source_id: int, start: int, end: int) -> int:
        row = self.source_index[source_id]
        return int(self.prefix[row, end] - self.prefix[row, start])

    def _segment(self, start: int, end: int) -> OfeSegment | None:
        if start < 0 or end > self.n_positions or start >= end:
            return None
        counts = [(self._source_count(source_id, start, end), source_id) for source_id in self.source_ids]
        active_cells = sum(count for count, _source_id in counts)
        if active_cells == 0:
            return None
        max_count = max(count for count, _source_id in counts)
        tied = [source_id for count, source_id in counts if count == max_count]
        source_id = BACKGROUND_SOURCE_ID if BACKGROUND_SOURCE_ID in tied else min(tied)
        return OfeSegment(
            start_index=start,
            end_index=end,
            source_id=source_id,
            agreeing_cells=max_count,
            active_cells=active_cells,
        )

    def _fragmented_field_count(self) -> int:
        active_labels = self.labels[self.active]
        run_counts: Counter[int] = Counter()
        previous: int | None = None
        for value in active_labels:
            source_id = int(value)
            if source_id != previous:
                if source_id > 0:
                    run_counts[source_id] += 1
                previous = source_id
        return sum(run_count > 1 for run_count in run_counts.values())

    def _actual_downstream_background_fraction(self) -> float:
        field_positions = np.flatnonzero(self.active & (self.labels > 0))
        if field_positions.size == 0:
            return 1.0
        return (self.n_positions - int(field_positions[-1]) - 1) / self.n_positions

    def candidate(self, family: str, segments: Sequence[OfeSegment]) -> ParentCandidate:
        if not segments:
            raise Concept1PlanningError("A parent candidate must contain at least one OFE.")
        if segments[0].start_index != 0 or segments[-1].end_index != self.n_positions:
            raise Concept1PlanningError("Candidate OFEs do not span the complete parent profile.")
        for previous, current in zip(segments, segments[1:]):
            if previous.end_index != current.start_index:
                raise Concept1PlanningError("Candidate OFEs are not contiguous.")

        agreeing_cells = sum(segment.agreeing_cells for segment in segments)
        agreeing_field_cells = 0
        agreeing_background_cells = 0
        modeled_area_by_source: Counter[int] = Counter()
        assigned_segments_by_source: Counter[int] = Counter()
        agreeing_cells_by_source: Counter[int] = Counter()
        for segment in segments:
            if segment.source_id > 0:
                agreeing_field_cells += self._source_count(
                    segment.source_id, segment.start_index, segment.end_index
                )
            else:
                agreeing_background_cells += self._source_count(
                    BACKGROUND_SOURCE_ID, segment.start_index, segment.end_index
                )
            modeled_area_by_source[segment.source_id] += (
                self.residual_area_m2
                * (segment.end_index - segment.start_index)
                / self.n_positions
            )
            assigned_segments_by_source[segment.source_id] += 1
            agreeing_cells_by_source[segment.source_id] += segment.agreeing_cells

        source_area_errors = {
            source_id: modeled_area_by_source[source_id] - actual_count * self.cell_area_m2
            for source_id, actual_count in self.actual_counts.items()
        }
        total_absolute_source_area_error_m2 = sum(abs(value) for value in source_area_errors.values())
        field_area_error_fractions = [
            abs(source_area_errors[source_id]) / (actual_count * self.cell_area_m2)
            for source_id, actual_count in self.actual_counts.items()
            if source_id > 0
        ]
        max_field_area_error_fraction = max(field_area_error_fractions, default=0.0)
        source_order_conflicts = sum(
            max(0, count - 1)
            for source_id, count in assigned_segments_by_source.items()
            if source_id > 0
        )
        assigned_source_ids = set(assigned_segments_by_source)
        missing_source_ids = set(self.source_ids) - assigned_source_ids
        modeled_downstream_background_fraction = 0.0
        for segment in reversed(segments):
            if segment.source_id != BACKGROUND_SOURCE_ID:
                break
            modeled_downstream_background_fraction += (
                segment.end_index - segment.start_index
            ) / self.n_positions

        return ParentCandidate(
            family=family,
            segments=tuple(segments),
            active_cells=self.active_cells,
            field_cells=self.field_cells,
            agreeing_cells=agreeing_cells,
            agreeing_field_cells=agreeing_field_cells,
            background_cells=self.background_cells,
            agreeing_background_cells=agreeing_background_cells,
            total_absolute_source_area_error_m2=total_absolute_source_area_error_m2,
            max_field_area_error_fraction=max_field_area_error_fraction,
            missing_source_count=len(missing_source_ids),
            missing_field_source_count=sum(source_id > 0 for source_id in missing_source_ids),
            zero_overlap_field_source_count=sum(
                source_id > 0 and agreeing_cells_by_source[source_id] == 0
                for source_id in self.source_ids
            ),
            source_order_conflicts=source_order_conflicts,
            fragmented_field_count=self.fragmented_field_count,
            actual_downstream_background_fraction=self.actual_downstream_background_fraction,
            modeled_downstream_background_fraction=modeled_downstream_background_fraction,
        )

    def equal_band_candidates(self, max_ofes: int = 4) -> list[ParentCandidate]:
        candidates: list[ParentCandidate] = []
        for ofe_count in range(1, min(max_ofes, self.n_positions) + 1):
            quotient, remainder = divmod(self.n_positions, ofe_count)
            counts = [quotient + (1 if index < remainder else 0) for index in range(ofe_count)]
            boundaries = np.cumsum([0, *counts]).tolist()
            segments = [
                self._segment(int(start), int(end))
                for start, end in zip(boundaries, boundaries[1:])
            ]
            if all(segment is not None for segment in segments):
                candidates.append(
                    self.candidate(
                        "equal_band",
                        [segment for segment in segments if segment is not None],
                    )
                )
        return candidates

    def generalized_candidates(self, max_ofes: int) -> list[ParentCandidate]:
        active_positions = np.flatnonzero(self.active)
        active_labels = self.labels[active_positions]
        run_starts = [0]
        for index in range(1, active_labels.size):
            if active_labels[index] != active_labels[index - 1]:
                run_starts.append(index)
        run_starts.append(int(active_labels.size))

        boundaries = [0]
        for run_index in range(1, len(run_starts) - 1):
            left_active_index = run_starts[run_index] - 1
            right_active_index = run_starts[run_index]
            minimum = int(active_positions[left_active_index]) + 1
            maximum = int(active_positions[right_active_index])
            cumulative_active_fraction = right_active_index / self.active_cells
            area_balancing_boundary = int(round(cumulative_active_fraction * self.n_positions))
            boundaries.append(min(max(area_balancing_boundary, minimum), maximum))
        boundaries.append(self.n_positions)

        segments: list[OfeSegment] = []
        for start, end in zip(boundaries, boundaries[1:]):
            segment = self._segment(start, end)
            if segment is None:
                raise Concept1PlanningError(
                    "Generalized run segmentation produced an empty residual OFE."
                )
            segments.append(segment)

        candidates_by_count: dict[int, ParentCandidate] = {}
        if len(segments) <= max_ofes:
            candidates_by_count[len(segments)] = self.candidate("generalized", segments)

        while len(segments) > 1:
            assigned_counts = Counter(segment.source_id for segment in segments)
            best_merge: tuple[tuple[int, float, int], int, OfeSegment] | None = None
            for index, (left, right) in enumerate(zip(segments, segments[1:])):
                merged = self._segment(left.start_index, right.end_index)
                if merged is None:
                    continue
                proposed_counts = assigned_counts.copy()
                proposed_counts[left.source_id] -= 1
                proposed_counts[right.source_id] -= 1
                proposed_counts[merged.source_id] += 1
                if any(proposed_counts[source_id] <= 0 for source_id in self.source_ids):
                    continue
                agreement_loss = left.agreeing_cells + right.agreeing_cells - merged.agreeing_cells
                key = (agreement_loss, -merged.cell_agreement, index)
                if best_merge is None or key < best_merge[0]:
                    best_merge = (key, index, merged)
            if best_merge is None:
                break
            _key, index, merged = best_merge
            segments = [*segments[:index], merged, *segments[index + 2 :]]
            if len(segments) <= max_ofes:
                candidates_by_count[len(segments)] = self.candidate("generalized", segments)

        return [candidates_by_count[count] for count in sorted(candidates_by_count)]

    def source_order_candidate(self, max_ofes: int) -> ParentCandidate | None:
        """Represent every source once, ordered by its median discharge-rank position."""

        if len(self.source_ids) > max_ofes:
            return None
        median_positions = {
            source_id: int(
                (lambda positions: positions[(len(positions) - 1) // 2])(
                    np.flatnonzero(self.active & (self.labels == source_id))
                )
            )
            for source_id in self.source_ids
        }
        ordered_sources = sorted(
            self.source_ids,
            key=lambda source_id: (median_positions[source_id], source_id),
        )
        source_count = len(ordered_sources)
        if source_count == 1:
            boundaries = [0, self.n_positions]
        else:
            cumulative = 0
            target_boundaries: list[int] = []
            for source_id in ordered_sources[:-1]:
                cumulative += self.actual_counts[source_id]
                target_boundaries.append(
                    int(round(cumulative * self.n_positions / self.active_cells))
                )

            negative_infinity = -10**18
            previous_correct = np.full(self.n_positions + 1, negative_infinity, dtype=np.int64)
            previous_penalty = np.full(self.n_positions + 1, negative_infinity, dtype=np.int64)
            first_source = ordered_sources[0]
            first_prefix = self.prefix[self.source_index[first_source]]
            final_first_end = self.n_positions - (source_count - 1)
            for end in range(1, final_first_end + 1):
                if end <= median_positions[first_source]:
                    continue
                previous_correct[end] = first_prefix[end]
                previous_penalty[end] = -abs(end - target_boundaries[0])

            parents: list[np.ndarray] = []
            for source_position in range(1, source_count):
                source_id = ordered_sources[source_position]
                source_prefix = self.prefix[self.source_index[source_id]]
                current_correct = np.full(
                    self.n_positions + 1, negative_infinity, dtype=np.int64
                )
                current_penalty = np.full(
                    self.n_positions + 1, negative_infinity, dtype=np.int64
                )
                current_parent = np.full(self.n_positions + 1, -1, dtype=np.int64)
                remaining_sources = source_count - source_position - 1
                minimum_end = source_position + 1
                maximum_end = self.n_positions - remaining_sources
                best_base: tuple[int, int, int] | None = None
                source_median = median_positions[source_id]
                for end in range(minimum_end, maximum_end + 1):
                    candidate_start = end - 1
                    if (
                        candidate_start <= source_median
                        and previous_correct[candidate_start] > negative_infinity
                    ):
                        base = (
                            int(previous_correct[candidate_start] - source_prefix[candidate_start]),
                            int(previous_penalty[candidate_start]),
                            -candidate_start,
                        )
                        if best_base is None or base > best_base:
                            best_base = base
                    if best_base is None:
                        continue
                    if end <= source_median:
                        continue
                    start = -best_base[2]
                    current_correct[end] = best_base[0] + source_prefix[end]
                    boundary_penalty = (
                        abs(end - target_boundaries[source_position])
                        if source_position < source_count - 1
                        else 0
                    )
                    current_penalty[end] = best_base[1] - boundary_penalty
                    current_parent[end] = start
                parents.append(current_parent)
                previous_correct = current_correct
                previous_penalty = current_penalty

            if previous_correct[self.n_positions] <= negative_infinity:
                raise Concept1PlanningError("Unable to solve the source-order OFE partition.")
            reversed_boundaries = [self.n_positions]
            end = self.n_positions
            for current_parent in reversed(parents):
                end = int(current_parent[end])
                if end < 1:
                    raise Concept1PlanningError(
                        "Source-order OFE partition returned an invalid boundary."
                    )
                reversed_boundaries.append(end)
            boundaries = [0, *reversed(reversed_boundaries)]

        segments: list[OfeSegment] = []
        for source_id, start, end in zip(
            ordered_sources, boundaries, boundaries[1:]
        ):
            active_cells = int(np.count_nonzero(self.active[start:end]))
            agreeing_cells = self._source_count(source_id, start, end)
            segments.append(
                OfeSegment(
                    start_index=start,
                    end_index=end,
                    source_id=source_id,
                    agreeing_cells=agreeing_cells,
                    active_cells=active_cells,
                )
            )
        return self.candidate("source_order", segments)


def _candidate_selection_key(
    candidate: ParentCandidate,
) -> tuple[int, int, float, float, float, int]:
    return (
        -candidate.missing_source_count,
        -candidate.zero_overlap_field_source_count,
        candidate.overall_assignment_agreement,
        candidate.field_cell_agreement,
        -candidate.total_absolute_source_area_error_m2,
        -candidate.ofe_count,
    )


def build_parent_plan(
    source_ids: Sequence[int] | np.ndarray,
    discharge_ranks: Sequence[float] | np.ndarray,
    *,
    cell_area_m2: float,
    ignored_source_ids: Iterable[int] = (),
    max_ofes: int = MAX_OFES,
) -> ParentPlan:
    """Build diagnostic equal-band and variable-breakpoint candidates for one parent."""

    labels = np.asarray(source_ids, dtype=np.int64).reshape(-1)
    discha = np.asarray(discharge_ranks, dtype=np.float64).reshape(-1)
    if labels.size == 0 or labels.size != discha.size:
        raise Concept1PlanningError("Source and DISCHA arrays must be non-empty and equal length.")
    if not np.all(np.isfinite(discha)):
        raise Concept1PlanningError("DISCHA contains a non-finite value.")
    if max_ofes < 1 or max_ofes > MAX_OFES:
        raise Concept1PlanningError(f"max_ofes must be between 1 and {MAX_OFES}.")

    order = np.argsort(-discha, kind="stable")
    ordered_labels = labels[order]
    ignored = {int(value) for value in ignored_source_ids}
    active = ~np.isin(ordered_labels, list(ignored))
    search = _SegmentSearch(ordered_labels, active, cell_area_m2=cell_area_m2)
    candidates = [*search.equal_band_candidates(), *search.generalized_candidates(max_ofes)]
    source_order = search.source_order_candidate(max_ofes)
    if source_order is not None:
        candidates.append(source_order)
    selected = max(candidates, key=_candidate_selection_key)
    return ParentPlan(
        selected=selected,
        candidates=tuple(candidates),
        ordered_source_ids=tuple(int(value) for value in ordered_labels),
        active_mask=tuple(bool(value) for value in active),
    )


def _read_raster(path: Path) -> _RasterResource:
    dataset = gdal.Open(str(path), gdal.GA_ReadOnly)
    if dataset is None:
        raise FileNotFoundError(path)
    data = dataset.ReadAsArray()
    if data is None or data.ndim != 2:
        raise Concept1PlanningError(f"Raster is not a readable two-dimensional grid: {path}.")
    geotransform = dataset.GetGeoTransform(can_return_null=True)
    projection = dataset.GetProjection() or ""
    dataset = None
    if geotransform is None:
        raise Concept1PlanningError(f"Raster has no affine geotransform: {path}.")
    return _RasterResource(path, np.asarray(data), tuple(geotransform), projection)


def _projections_match(left: str, right: str) -> bool:
    if not left and not right:
        return True
    if not left or not right:
        return False
    left_srs = osr.SpatialReference()
    right_srs = osr.SpatialReference()
    if left_srs.ImportFromWkt(left) != 0 or right_srs.ImportFromWkt(right) != 0:
        return left.split() == right.split()
    return bool(left_srs.IsSame(right_srs))


def _validate_alignment(reference: _RasterResource, actual: _RasterResource) -> None:
    if reference.data.shape != actual.data.shape:
        raise Concept1PlanningError(
            f"Raster shape mismatch for {actual.path}: expected {reference.data.shape}, "
            f"received {actual.data.shape}."
        )
    if not np.allclose(reference.geotransform, actual.geotransform, rtol=1e-9, atol=1e-9):
        raise Concept1PlanningError(f"Raster geotransform mismatch for {actual.path}.")
    if not _projections_match(reference.projection, actual.projection):
        raise Concept1PlanningError(f"Raster projection mismatch for {actual.path}.")


def _cell_area_m2(geotransform: Sequence[float]) -> float:
    area = abs(geotransform[1] * geotransform[5] - geotransform[2] * geotransform[4])
    if not math.isfinite(area) or area <= 0.0:
        raise Concept1PlanningError(f"Invalid raster cell area from geotransform: {area!r}.")
    return float(area)


def _integer_grid(
    resource: _RasterResource,
    raster_name: str,
    *,
    nonfinite_value: int = np.iinfo(np.int64).min,
) -> np.ndarray:
    values = np.asarray(resource.data)
    if np.issubdtype(values.dtype, np.floating):
        finite = np.isfinite(values)
        if not np.allclose(values[finite], np.rint(values[finite]), rtol=0.0, atol=0.0):
            raise Concept1PlanningError(f"{raster_name} contains a non-integer finite value.")
        values = np.where(finite, np.rint(values), nonfinite_value)
    return values.astype(np.int64)


def _normalize_subfield_grid(resource: _RasterResource) -> np.ndarray:
    values = _integer_grid(
        resource,
        "subfield map",
        nonfinite_value=BACKGROUND_SOURCE_ID,
    )
    return np.where(values > BACKGROUND_SOURCE_ID, values, BACKGROUND_SOURCE_ID)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_parquet(path: Path, rows: list[dict[str, Any]], metadata: Mapping[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise Concept1PlanningError(f"Cannot write an empty planner artifact: {path}.")
    table = pa.Table.from_pylist(rows)
    encoded_metadata = {key.encode(): value.encode() for key, value in metadata.items()}
    table = table.replace_schema_metadata(encoded_metadata)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        pq.write_table(table, temporary, compression="snappy")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_parent_length(slope_dir: Path, topaz_id: int) -> float:
    path = slope_dir / f"hill_{topaz_id}.slp"
    if not path.is_file():
        raise FileNotFoundError(path)
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("#")]
    if len(lines) < 4 or int(lines[1]) != 1:
        raise Concept1PlanningError(f"Expected a single-OFE parent slope: {path}.")
    length = float(lines[3].split()[1])
    if not math.isfinite(length) or length <= 0.0:
        raise Concept1PlanningError(f"Invalid parent slope length in {path}: {length!r}.")
    return length


def _load_connectivity_detail(path: Path | None, expected_ids: set[int]) -> tuple[set[int], dict[str, Any] | None]:
    if path is None:
        return set(), None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("subfields"), list):
        raise Concept1PlanningError(f"Unsupported connectivity detail schema: {path}.")
    rows = payload["subfields"]
    ids = [int(row["subfield_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise Concept1PlanningError("Connectivity detail contains duplicate subfield ids.")
    received_ids = set(ids)
    if received_ids != expected_ids:
        missing = sorted(expected_ids - received_ids)[:10]
        extra = sorted(received_ids - expected_ids)[:10]
        raise Concept1PlanningError(
            f"Connectivity/detail id mismatch: missing={missing}, extra={extra}."
        )
    connected = {int(row["subfield_id"]) for row in rows if bool(row["channel_connected"])}
    return connected, payload


def _validate_subfield_ownership(
    subwta: np.ndarray,
    subfield_map: np.ndarray,
    expected_parent_by_subfield: Mapping[int, int],
) -> None:
    positive = subfield_map > 0
    raster_ids = {int(value) for value in np.unique(subfield_map[positive])}
    expected_ids = set(expected_parent_by_subfield)
    if raster_ids != expected_ids:
        raise Concept1PlanningError(
            f"Subfield raster/metadata id mismatch: missing={sorted(expected_ids - raster_ids)[:10]}, "
            f"extra={sorted(raster_ids - expected_ids)[:10]}."
        )
    pairs = np.unique(
        np.column_stack((subfield_map[positive].astype(np.int64), subwta[positive].astype(np.int64))),
        axis=0,
    )
    owners: dict[int, set[int]] = {}
    for subfield_id, topaz_id in pairs:
        owners.setdefault(int(subfield_id), set()).add(int(topaz_id))
    mismatches = [
        (subfield_id, sorted(owners.get(subfield_id, set())), expected_parent)
        for subfield_id, expected_parent in expected_parent_by_subfield.items()
        if owners.get(subfield_id) != {expected_parent}
    ]
    if mismatches:
        raise Concept1PlanningError(f"Subfield parent ownership mismatch: {mismatches[:10]}.")


def _candidate_row(topaz_id: int, wepp_id: int, branch: str, candidate: ParentCandidate) -> dict[str, Any]:
    return {
        "schema_version": PLANNER_SCHEMA_VERSION,
        "algorithm": ALGORITHM,
        "parent_topaz_id": topaz_id,
        "parent_wepp_id": wepp_id,
        "routing_branch": branch,
        "family": candidate.family,
        "ofe_count": candidate.ofe_count,
        "active_cells": candidate.active_cells,
        "field_cells": candidate.field_cells,
        "overall_assignment_agreement": candidate.overall_assignment_agreement,
        "field_cell_agreement": candidate.field_cell_agreement,
        "background_cell_agreement": candidate.background_cell_agreement,
        "total_absolute_source_area_error_m2": candidate.total_absolute_source_area_error_m2,
        "max_field_area_error_fraction": candidate.max_field_area_error_fraction,
        "missing_source_count": candidate.missing_source_count,
        "missing_field_source_count": candidate.missing_field_source_count,
        "zero_overlap_field_source_count": candidate.zero_overlap_field_source_count,
        "fragmented_field_count": candidate.fragmented_field_count,
        "source_order_conflicts": candidate.source_order_conflicts,
        "actual_downstream_background_fraction": candidate.actual_downstream_background_fraction,
        "modeled_downstream_background_fraction": candidate.modeled_downstream_background_fraction,
        "downstream_background_error_fraction": candidate.downstream_background_error_fraction,
    }


def run_planning_census(
    *,
    subwta_path: Path,
    discha_path: Path,
    subfield_map_path: Path,
    fields_parquet_path: Path,
    slope_dir: Path,
    output_dir: Path,
    connectivity_detail_path: Path | None = None,
    max_ofes: int = MAX_OFES,
) -> dict[str, Any]:
    """Plan every affected parent and write versioned read-only feasibility artifacts."""

    started = time.monotonic()
    subwta_resource = _read_raster(subwta_path)
    discha_resource = _read_raster(discha_path)
    subfield_resource = _read_raster(subfield_map_path)
    _validate_alignment(subwta_resource, discha_resource)
    _validate_alignment(subwta_resource, subfield_resource)
    cell_area_m2 = _cell_area_m2(subwta_resource.geotransform)
    subwta_grid = _integer_grid(subwta_resource, "SUBWTA")
    subfield_grid = _normalize_subfield_grid(subfield_resource)

    fields_table = pq.read_table(fields_parquet_path)
    required_columns = {"field_id", "topaz_id", "wepp_id", "sub_field_id"}
    missing_columns = required_columns - set(fields_table.column_names)
    if missing_columns:
        raise Concept1PlanningError(f"fields.parquet lacks columns: {sorted(missing_columns)}.")
    fields = fields_table.select(sorted(required_columns)).to_pylist()
    subfield_ids = [int(row["sub_field_id"]) for row in fields]
    if len(subfield_ids) != len(set(subfield_ids)):
        raise Concept1PlanningError("fields.parquet contains duplicate sub_field_id values.")
    expected_ids = set(subfield_ids)
    expected_parent_by_subfield = {
        int(row["sub_field_id"]): int(row["topaz_id"]) for row in fields
    }
    _validate_subfield_ownership(
        subwta_grid,
        subfield_grid,
        expected_parent_by_subfield,
    )
    connected_ids, connectivity_payload = _load_connectivity_detail(
        connectivity_detail_path, expected_ids
    )

    parent_rows: dict[int, list[dict[str, Any]]] = {}
    for row in fields:
        parent_rows.setdefault(int(row["topaz_id"]), []).append(row)
    topaz_to_wepp: dict[int, int] = {}
    for topaz_id, rows in parent_rows.items():
        wepp_ids = {int(row["wepp_id"]) for row in rows}
        if len(wepp_ids) != 1:
            raise Concept1PlanningError(
                f"Parent {topaz_id} maps to multiple WEPP ids: {sorted(wepp_ids)}."
            )
        topaz_to_wepp[topaz_id] = wepp_ids.pop()

    flat_subwta = subwta_grid.reshape(-1)
    flat_discha = discha_resource.data.reshape(-1).astype(np.float64)
    flat_subfields = subfield_grid.reshape(-1)
    sorted_indices = np.argsort(flat_subwta, kind="stable")
    sorted_parent_ids = flat_subwta[sorted_indices]
    unique_parents, starts, counts = np.unique(
        sorted_parent_ids, return_index=True, return_counts=True
    )
    raster_indices_by_parent = {
        int(topaz_id): sorted_indices[int(start) : int(start + count)]
        for topaz_id, start, count in zip(unique_parents, starts, counts)
        if int(topaz_id) in parent_rows
    }
    if set(raster_indices_by_parent) != set(parent_rows):
        raise Concept1PlanningError(
            f"Affected parent raster mismatch: missing={sorted(set(parent_rows) - set(raster_indices_by_parent))[:10]}."
        )

    field_metadata = {
        int(row["sub_field_id"]): (int(row["field_id"]), int(row["topaz_id"]), int(row["wepp_id"]))
        for row in fields
    }
    candidate_rows: list[dict[str, Any]] = []
    ofe_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for topaz_id in sorted(parent_rows):
        indices = raster_indices_by_parent[topaz_id]
        labels = flat_subfields[indices]
        discha = flat_discha[indices]
        parent_subfield_ids = {int(row["sub_field_id"]) for row in parent_rows[topaz_id]}
        ignored_ids = parent_subfield_ids & connected_ids
        active_cells = int(np.count_nonzero(~np.isin(labels, list(ignored_ids))))
        parent_cells = int(labels.size)
        parent_area_m2 = parent_cells * cell_area_m2
        residual_area_m2 = active_cells * cell_area_m2
        connected_area_m2 = parent_area_m2 - residual_area_m2
        if not ignored_ids:
            branch = "pure_concept_1"
        elif active_cells == 0:
            branch = "pure_concept_2"
        else:
            branch = "mixed"
        parent_length_m = _read_parent_length(slope_dir, topaz_id)
        residual_width_m = residual_area_m2 / parent_length_m if residual_area_m2 > 0.0 else 0.0

        if active_cells == 0:
            summary_rows.append(
                {
                    "schema_version": PLANNER_SCHEMA_VERSION,
                    "algorithm": ALGORITHM,
                    "parent_topaz_id": topaz_id,
                    "parent_wepp_id": topaz_to_wepp[topaz_id],
                    "routing_branch": branch,
                    "parent_cells": parent_cells,
                    "active_cells": active_cells,
                    "connected_subfield_count": len(ignored_ids),
                    "parent_area_m2": parent_area_m2,
                    "residual_area_m2": residual_area_m2,
                    "connected_area_m2": connected_area_m2,
                    "area_closure_residual_m2": parent_area_m2 - residual_area_m2 - connected_area_m2,
                    "parent_length_m": parent_length_m,
                    "residual_width_m": residual_width_m,
                    "selected_ofe_count": 0,
                    "overall_assignment_agreement": None,
                    "field_cell_agreement": None,
                    "max_field_area_error_fraction": None,
                    "missing_source_count": None,
                    "missing_field_source_count": None,
                    "zero_overlap_field_source_count": None,
                    "source_order_conflicts": None,
                    "fragmented_field_count": None,
                    "downstream_background_error_fraction": None,
                    "fit_status": "not_applicable",
                    "rejection_reason": None,
                }
            )
            continue

        plan = build_parent_plan(
            labels,
            discha,
            cell_area_m2=cell_area_m2,
            ignored_source_ids=ignored_ids,
            max_ofes=max_ofes,
        )
        selected = plan.selected
        wepp_id = topaz_to_wepp[topaz_id]
        candidate_rows.extend(
            _candidate_row(topaz_id, wepp_id, branch, candidate)
            for candidate in plan.candidates
        )
        ordered_labels = np.asarray(plan.ordered_source_ids, dtype=np.int64)
        active_mask = np.asarray(plan.active_mask, dtype=np.bool_)
        actual_area_by_source = Counter(
            int(value) for value in ordered_labels[active_mask]
        )
        for ofe_id, segment in enumerate(selected.segments, start=1):
            source_id = segment.source_id
            source_kind = "background" if source_id == BACKGROUND_SOURCE_ID else "field"
            field_id = field_metadata[source_id][0] if source_id > 0 else None
            modeled_area_m2 = residual_area_m2 * (
                segment.end_index - segment.start_index
            ) / parent_cells
            raster_area_m2 = actual_area_by_source[source_id] * cell_area_m2
            ofe_rows.append(
                {
                    "schema_version": PLANNER_SCHEMA_VERSION,
                    "algorithm": ALGORITHM,
                    "parent_topaz_id": topaz_id,
                    "parent_wepp_id": wepp_id,
                    "routing_branch": branch,
                    "plan_family": selected.family,
                    "ofe_id": ofe_id,
                    "normalized_start": segment.start_index / parent_cells,
                    "normalized_end": segment.end_index / parent_cells,
                    "source_kind": source_kind,
                    "field_id": field_id,
                    "sub_field_id": source_id if source_id > 0 else None,
                    "source_raster_area_m2": raster_area_m2,
                    "ofe_modeled_area_m2": modeled_area_m2,
                    "signed_area_error_m2": modeled_area_m2 - raster_area_m2,
                    "segment_active_cells": segment.active_cells,
                    "segment_agreeing_cells": segment.agreeing_cells,
                    "classification_agreement": segment.cell_agreement,
                    "rank_start_fraction": segment.start_index / parent_cells,
                    "rank_end_fraction": segment.end_index / parent_cells,
                    "actual_downstream_background_length_m": selected.actual_downstream_background_fraction
                    * parent_length_m,
                    "modeled_downstream_background_length_m": selected.modeled_downstream_background_fraction
                    * parent_length_m,
                    "fit_status": "candidate",
                    "rejection_reason": None,
                }
            )
        summary_rows.append(
            {
                "schema_version": PLANNER_SCHEMA_VERSION,
                "algorithm": ALGORITHM,
                "parent_topaz_id": topaz_id,
                "parent_wepp_id": wepp_id,
                "routing_branch": branch,
                "parent_cells": parent_cells,
                "active_cells": active_cells,
                "connected_subfield_count": len(ignored_ids),
                "parent_area_m2": parent_area_m2,
                "residual_area_m2": residual_area_m2,
                "connected_area_m2": connected_area_m2,
                "area_closure_residual_m2": parent_area_m2 - residual_area_m2 - connected_area_m2,
                "parent_length_m": parent_length_m,
                "residual_width_m": residual_width_m,
                "selected_ofe_count": selected.ofe_count,
                "overall_assignment_agreement": selected.overall_assignment_agreement,
                "field_cell_agreement": selected.field_cell_agreement,
                "max_field_area_error_fraction": selected.max_field_area_error_fraction,
                "missing_source_count": selected.missing_source_count,
                "missing_field_source_count": selected.missing_field_source_count,
                "zero_overlap_field_source_count": selected.zero_overlap_field_source_count,
                "source_order_conflicts": selected.source_order_conflicts,
                "fragmented_field_count": selected.fragmented_field_count,
                "downstream_background_error_fraction": selected.downstream_background_error_fraction,
                "fit_status": "candidate",
                "rejection_reason": None,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": PLANNER_SCHEMA_VERSION,
        "algorithm": ALGORITHM,
        "threshold_status": "not_applied",
    }
    _atomic_parquet(output_dir / "ofe_plan.parquet", ofe_rows, metadata)
    _atomic_parquet(output_dir / "parent_candidates.parquet", candidate_rows, metadata)
    _atomic_parquet(output_dir / "parent_summary.parquet", summary_rows, metadata)
    elapsed_seconds = time.monotonic() - started
    peak_rss_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    summary = {
        "schema_version": PLANNER_SCHEMA_VERSION,
        "algorithm": ALGORITHM,
        "threshold_status": "not_applied",
        "inputs": {
            "subwta": {"path": str(subwta_path), "sha256": _sha256(subwta_path)},
            "discha": {"path": str(discha_path), "sha256": _sha256(discha_path)},
            "subfield_map": {"path": str(subfield_map_path), "sha256": _sha256(subfield_map_path)},
            "fields_parquet": {"path": str(fields_parquet_path), "sha256": _sha256(fields_parquet_path)},
            "connectivity_detail": (
                {"path": str(connectivity_detail_path), "sha256": _sha256(connectivity_detail_path)}
                if connectivity_detail_path is not None
                else None
            ),
        },
        "classifier": (
            {
                "schema_version": connectivity_payload["schema_version"],
                "peridot_version": connectivity_payload.get("peridot_version"),
                "definition": connectivity_payload.get("definition"),
                "channel_detection": connectivity_payload.get("channel_detection"),
            }
            if connectivity_payload is not None
            else None
        ),
        "counts": {
            "retained_subfields": len(expected_ids),
            "connected_subfields": len(connected_ids),
            "affected_parents": len(parent_rows),
            "pure_concept_1_parents": sum(row["routing_branch"] == "pure_concept_1" for row in summary_rows),
            "mixed_parents": sum(row["routing_branch"] == "mixed" for row in summary_rows),
            "pure_concept_2_parents": sum(row["routing_branch"] == "pure_concept_2" for row in summary_rows),
            "ofe_plan_rows": len(ofe_rows),
            "candidate_rows": len(candidate_rows),
        },
        "cell_area_m2": cell_area_m2,
        "max_ofes": max_ofes,
        "elapsed_seconds": elapsed_seconds,
        "peak_rss_kib": peak_rss_kib,
        "artifacts": {
            "ofe_plan": "ofe_plan.parquet",
            "parent_candidates": "parent_candidates.parquet",
            "parent_summary": "parent_summary.parquet",
        },
    }
    _atomic_json(output_dir / "planning_summary.json", summary)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subwta", required=True, type=Path)
    parser.add_argument("--discha", required=True, type=Path)
    parser.add_argument("--sub-field-map", required=True, type=Path)
    parser.add_argument("--fields-parquet", required=True, type=Path)
    parser.add_argument("--slope-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--connectivity-detail", type=Path)
    parser.add_argument("--max-ofes", type=int, default=MAX_OFES)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    summary = run_planning_census(
        subwta_path=args.subwta,
        discha_path=args.discha,
        subfield_map_path=args.sub_field_map,
        fields_parquet_path=args.fields_parquet,
        slope_dir=args.slope_dir,
        output_dir=args.output_dir,
        connectivity_detail_path=args.connectivity_detail,
        max_ofes=args.max_ofes,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
