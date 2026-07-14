"""WEPP input synthesis from an accepted AgFields Concept 1 OFE plan."""

from __future__ import annotations

import math
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from wepppy.topo.watershed_abstraction.slope_file import (
    SlopeFile,
    mofe_distance_fractions,
)
from wepppy.wepp.management.managements import read_management
from wepppy.wepp.management.utils.multi_ofe import ManagementMultipleOfeSynth
from wepppy.wepp.soils.utils.multi_ofe import SoilMultipleOfeSynth

from .concept1_planner import MAX_OFES


class Concept1InputSynthesisError(RuntimeError):
    """Raised when an accepted OFE plan cannot produce consistent WEPP inputs."""


def _coerce_subfield_id(row: Mapping[str, Any]) -> int:
    value = row.get("sub_field_id")
    if value is None or isinstance(value, float) and not math.isfinite(value):
        raise Concept1InputSynthesisError("A field OFE lacks a finite sub_field_id.")
    return int(value)


def _validated_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    parent_wepp_id: int,
) -> list[Mapping[str, Any]]:
    ordered = sorted(rows, key=lambda row: int(row["ofe_id"]))
    if not ordered or len(ordered) > MAX_OFES:
        raise Concept1InputSynthesisError(
            f"Parent {parent_wepp_id} must contain between 1 and {MAX_OFES} OFEs."
        )
    if [int(row["ofe_id"]) for row in ordered] != list(range(1, len(ordered) + 1)):
        raise Concept1InputSynthesisError(
            f"Parent {parent_wepp_id} has non-contiguous OFE identifiers."
        )
    for row in ordered:
        if int(row["parent_wepp_id"]) != parent_wepp_id:
            raise Concept1InputSynthesisError("OFE plan contains a row for another parent.")
        if row["source_kind"] not in {"background", "field"}:
            raise Concept1InputSynthesisError(
                f"Unsupported Concept 1 source kind: {row['source_kind']!r}."
            )
        if row["source_kind"] == "field":
            _coerce_subfield_id(row)

    starts = [float(row["normalized_start"]) for row in ordered]
    ends = [float(row["normalized_end"]) for row in ordered]
    if starts[0] != 0.0 or ends[-1] != 1.0:
        raise Concept1InputSynthesisError("OFE breakpoints must begin at 0 and end at 1.")
    if any(left_end != right_start for left_end, right_start in zip(ends, starts[1:])):
        raise Concept1InputSynthesisError("OFE breakpoints are not contiguous.")
    if any(not math.isfinite(start) or not math.isfinite(end) or end <= start for start, end in zip(starts, ends)):
        raise Concept1InputSynthesisError("OFE breakpoints must be finite and strictly increasing.")
    return ordered


def synthesize_concept1_parent_inputs(
    *,
    parent_wepp_id: int,
    ofe_rows: Sequence[Mapping[str, Any]],
    parent_runs_dir: Path,
    subfield_runs_dir: Path,
    target_runs_dir: Path,
    target_width_m: float,
) -> dict[str, Any]:
    """Write a consistent slope/soil/management/climate set for one parent."""
    if not math.isfinite(target_width_m) or target_width_m <= 0.0:
        raise Concept1InputSynthesisError("Concept 1 target width must be finite and positive.")
    rows = _validated_rows(ofe_rows, parent_wepp_id=parent_wepp_id)
    target_runs_dir.mkdir(parents=True, exist_ok=True)

    source_prefix = parent_runs_dir / f"p{parent_wepp_id}"
    target_prefix = target_runs_dir / f"p{parent_wepp_id}"
    breakpoints = [float(rows[0]["normalized_start"]), *(
        float(row["normalized_end"]) for row in rows
    )]
    slope = SlopeFile(str(source_prefix.with_suffix(".slp")))
    slope_count = slope.segmented_multiple_ofe_at_breakpoints(
        breakpoints,
        dst_fn=str(target_prefix.with_suffix(".slp")),
        target_width=target_width_m,
    )

    soil_sources = [str(source_prefix.with_suffix(".sol"))] * len(rows)
    SoilMultipleOfeSynth(soil_sources).write(str(target_prefix.with_suffix(".sol")))

    managements = []
    for row in rows:
        if row["source_kind"] == "background":
            source = source_prefix.with_suffix(".man")
        else:
            source = subfield_runs_dir / f"p{_coerce_subfield_id(row)}.man"
        managements.append(read_management(str(source)))
    management_synth = ManagementMultipleOfeSynth(
        managements,
        deduplicate_scenarios=True,
    )
    management_synth.write(str(target_prefix.with_suffix(".man")))

    shutil.copy2(source_prefix.with_suffix(".cli"), target_prefix.with_suffix(".cli"))
    parsed_management = read_management(str(target_prefix.with_suffix(".man")))
    scenario_count = len(
        ManagementMultipleOfeSynth._collect_referenced_yearly_loop_names(
            parsed_management
        )
    )
    fractions = mofe_distance_fractions(str(target_prefix.with_suffix(".slp")))
    if slope_count != len(rows) or parsed_management.nofe != len(rows):
        raise Concept1InputSynthesisError(
            f"Parent {parent_wepp_id} generated inconsistent OFE counts."
        )
    if not all(
        math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12)
        for actual, expected in zip(fractions, breakpoints)
    ):
        raise Concept1InputSynthesisError(
            f"Parent {parent_wepp_id} generated slope breakpoints that differ from its plan."
        )
    return {
        "parent_wepp_id": parent_wepp_id,
        "ofe_count": len(rows),
        "referenced_yearly_scenario_count": scenario_count,
        "breakpoints": breakpoints,
        "target_width_m": target_width_m,
        "target_length_m": slope.length,
        "target_area_m2": target_width_m * slope.length,
    }
