# Investigate the reported watershed one-day shift

## Purpose

Distinguish a separate routing delay from the already repaired century calendar
and schema-2 slot defects. The investigation used retained generated outputs. The user subsequently
accepted the date-label defect and requested its patch; the existing Gregorian
source repair already implements that correction.

## Progress

- [x] Read prior findings and current scheduler/read/output source.
- [x] Audit generated PASS payloads against actual watershed read traces.
- [x] Quantify legacy event-date/PASS-key offset before/after year 100.
- [x] Document conclusions and limits for Jackson's unavailable run.

- [x] User accepted the reproduced date-label defect as the repair target.
- [x] Verify the existing patch matches the validated source (16 hashes match).

Jackson-specific reproduction remains an evidence limitation, not a prerequisite
for fixing the independently reproduced defect.

## Context and plan

The reported release is ASCII `wepp_261010`; Jackson's exact run and compared
output family have been requested. Independent retained cases are under
`/workdir/wepp-gregorian-repair-20261021`. Use `ascii-baseline-hill/output` for
released legacy output and `hbp400-observe/runs/wepp_observe.log` for current
400-year actual reader/routing traces. Corrected decoded HBP payloads are in
`hbp400-final/output/interchange/H.pass.parquet`; observation on/off scientific
output parity was established in the completed repair package.

Compare nonzero runoff payloads with both same-day and neighboring-day keys;
record the exact first date divergence in the released hill output. Trace
`wshdrv` climate read, `wshred`, channel routing and outlet event write ordering.
Do not equate outlet volume to hillslope runoff: channel rainfall, subsurface
inflow, storage and losses alter it. Do not infer timing from sparse row number.

## Validation

Retain executable analysis and JSON counts/examples. Require all observed reader
records to match the serialized date's payload within diagnostic print precision.
Check calendar alignment independently of physical outlet response. No universal
attribution to Jackson is possible without his run and compared output family.

## Surprises & Discoveries

Prior raw-output date audits prove the calendar defect but do not alone prove
flux timing. The distinction requires actual loaded-array traces.

## Decision Log

2026-10-21: User requested identification of the one-day shift. Investigate using
existing source and generated artifacts while requesting Jackson's run context.
Preserve all original projects and completed work packages.

2026-10-21: User accepted the date-label shift and requested the patch. Use the
existing Gregorian repair, governed by ADR-0100 and the native
`docs/contracts/execution-calendar-contract.md`. Hillslope, watershed and PASS
dates must follow one Gregorian execution calendar. Regenerate affected outputs
with paired corrected binaries; relabeling alone leaves climate consumption
misaligned. No additional output-date offset or routing delay adjustment.

## Outcomes & Retrospective

Retained-run analysis complete: legacy PASS/EBE date-label shift reproduced;
corrected 400-year actual reader has no same-day payload mismatches. No separate
unconditional routing delay demonstrated. The accepted defect is patched in the
native and interchange working trees, with retained 200/400-year validation and
source identity reverified. No extra production edit was necessary. Binaries are
not vendored or deployed. Jackson's exact comparison remains unavailable. See
artifacts/findings.md and the completed Gregorian repair package.

Revision: recorded the user's accepted defect and patch request, replacing the
Jackson-specific attribution wait with completion of the reproduced repair.
