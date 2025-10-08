# Management Rotation Synth – Stack-and-Merge Spec

## Overview
- Extend `ManagementRotationSynth` so it supports both the existing “end-to-end” concatenation and a new “stack-and-merge” algorithm.
- `build()` will become a dispatcher that calls either `_build_end_to_end()` (current behaviour) or `_build_stack_and_merge()`.
- The stack-and-merge mode enables combining 1–2 year management rotations such that the simulated timeline remains fixed-length while first-year fall operations in 2-year segments are merged into the prior year.

## Goals
- Allow callers to request stack-and-merge without breaking existing workflows. this is still early development so there is minimal compatibility concerns
- Preserve per-section scenario integrity (plants, operations, surface sequences, yearly scenarios, management loops) in the merged result.
- Support warning emission when merged operations occur before existing events in the target year.
- Ensure first rotations of 2-year managements drop their first-year content while still exposing second-year operations.

## Out of Scope / Non-Goals
- Changes to `downgrade_to_98_4_format` or `_apply_first_year_only`.
- Any redesign of the Management object model or parser.
- Supporting rotations longer than two years in stack-and-merge mode.

## Terminology
- **Segment**: An input `Management` object participating in the stack.
- **OFEs**: Overland flow elements; all segments must share the same count.
- **Year Loop**: Entries in `management.years`.
- **Management Loop**: `Management.man.loops`, containing per-year schedules for each OFE.

## Current Behaviour Summary
- The sole `build()` method deep-copies each segment, optionally prefixes scenario names, concatenates every section, and rebuilds a single management loop covering the combined timeline.
- Description headers always claim the rotation was “concatenated.”
- Timeline validation only checks OFE counts and scenario existence.

## API Adjustments
- Accept a new mode selector when constructing `ManagementRotationSynth` (literal values `'end-to-end'` and `'stack-and-merge'`; default to `'end-to-end'`).
- Expose active mode via property/attribute for diagnostics.
- Refine `description` to document the active mode and include any warnings captured during synthesis.
- Convert `build()` into a thin router that delegates to `_build_end_to_end()` or `_build_stack_and_merge()` based on `self.mode`.

## Stack-and-Merge Algorithm

### Preconditions
- Each segment must contain exactly one management loop (`len(man.loops) == 1`).
- When in stack-and-merge mode every segment must have `nyears` of 1 or 2. Raise an error otherwise.
- All segments share the same `nofe`, already enforced in `__init__`.

### Segment Preparation
- Work on deep copies to avoid mutating caller objects.
- Reuse `_apply_prefix` for unique naming of non-initial segments.
- Capture per-segment metadata before trimming:
  - First year `YearLoop`/`SurfLoop` references (for 2-year rotations).
  - Surface operations (`SurfLoopCropland.data`) and their `mdate` values.
  - Year-level event dates (`YearLoopCropland` planting/harvest/stop, fallow options, etc.).

### Handling 1-Year Segments
- Append the year and associated surface operations directly to the timeline.
- Update management loop `_year` assignments sequentially.

### Handling 2-Year Segments
- **First segment in stack**: discard the first-year timeline entirely; only second-year content contributes to the output.
- **Subsequent segments**:
  1. Merge the first-year operations/events into the immediately preceding year of the output timeline for each OFE.
     - Append surface operations to the existing `SurfLoop` of the previous year, preserving order by insertion.
     - Track chronological ordering per OFE: compare each incoming `mdate` (converted from `Julian` where needed) to the last `mdate` already present; if incoming precedes existing, log a warning noting segment, OFE, date, and operation name.
     - Apply the same comparison to year-level events (e.g., `jdplt`, `jdharv`, `jdstop`, annual fallow dates). Warn if an incoming value is earlier than the current field.
  2. Trim the segment to exclude the first-year loops:
     - Remove first-year `YearLoop` entries from `segment.years`.
     - Remove first-year references in `segment.man.loops[0].years`.
     - Decrement `segment.sim_years` to the contribution count (1).
     - Adjust any `_year` metadata on management loop entries.
  3. Append the remaining year (second year) to the output timeline as usual.

### Warning Accumulation
- Maintain a list of structured warning messages (per OFE and year). Include them in the synthesiser description and expose via attribute for programmatic access.
- Warnings should advise users to fix management ordering when merges introduce out-of-sequence events.

### Timeline Assembly
- Continue using per-OFE timelines of management loops to rebuild the final `ManagementLoopMan`.
- Ensure `sim_years` equals the number of timeline entries after merges (first-year merges do not add a new year).
- After construction call `result.setroot()` and run `_validate_year_references`.

## Description & Diagnostics
- Header must state: total segments, active mode, and whether stack-and-merge was applied.
- Append a “Warnings” block when any chronology issues were detected.

## Data Structure Considerations
- Surface loops contain `ntill` counts that must be incremented when operations are merged.
- Year loops referencing trimmed scenarios need name changes consistent with `_apply_prefix`.
- Ensure `ScenarioReference.loop_name` updates propagate when we merge or rename loops.
- When merging operations create deep copies before mutating so original segments remain pristine.

## Error Handling
- Raise descriptive `ValueError` when prerequisites fail (e.g., >2 years in stack-and-merge mode, missing management loops, OFE mismatch after trimming).
- Detect scenarios where no prior year exists to merge into (e.g., first segment being 1-year followed by 2-year should succeed; two consecutive 2-year segments rely on the previous year produced after the first’s second year).

## Testing Strategy
- Construct lightweight fixture management files checked into the repo (e.g., in `wepppy/wepp/management/tests/data/`).
- Unit tests should cover:
  - End-to-end mode unchanged (existing test updated to call `_build_end_to_end()` implicitly).
  - Stack-and-merge with sequences of 1-year rotations only (degenerates to standard append).
  - Stack-and-merge with first segment 2-year (first year dropped).
  - Stack-and-merge merging multiple 2-year segments; validate merged operations count and `ntill` adjustments.
  - Warning emission when merged operation dates precede existing ones.
  - Error conditions (segment with 3 years, missing prior year, mismatched management loop counts).
- Assert header text reflects mode and includes warnings when expected.
- Use conda environment `wepppy310-env` for testing

## Assumptions & Notes
- Merged first-year operations originate in late fall and are expected to occur after prior-year events; warnings indicate deviations requiring manual cleanup.
- Year-level chronology checks use all available date fields even if the scenarios typically only include operations.
- `downgrade_to_98_4_format` remains untouched; the nested `_apply_first_year_only` helper may become redundant later but is not part of this effort.
- No legacy callers depend on `ManagementRotationSynth` yet (class is ~6 days old), so constructor signature changes are acceptable.

## Open Items
- Validate which year-level fields must be compared for chronology warnings (initial pass compares all Julian-valued attributes present on the year data structures). *warn for all and merge knowing we may latter need to cull these events.*
- Decide on exact warning message format (likely human-readable lines usable in CLI and log files). *provide `logger_name` hook for logging external logger. log in the management file header comments*

## Developer Log
