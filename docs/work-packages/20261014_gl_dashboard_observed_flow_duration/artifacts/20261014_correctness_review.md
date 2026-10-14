# Correctness and user-experience review — observed flow duration

## Metadata and outcome

Independent reviewer: `/root/contract_correctness`, 2026-10-14 UTC.
Scope: implementation after checkpoint `4e02ee2e0`; source adapter, state/control
wiring, loader and renderer. Canonical authority: flow-duration contract,
Observed streamflow overlay section, and ADR-0093. Users can add the same measured
distribution to either simulated source without discarding observed warm-up years.

## Valid-state and input matrix

| Stored state | Required outcome | Direct evidence |
| --- | --- | --- |
| No upload / never used | Existing plots, no checkbox | route and controls tests |
| Header-only / no streamflow | Explicit unavailable; simulations usable | real CSV tests |
| Populated normalized CSV | Optional single full-record curve | real project readback/browser |
| Legacy numeric-string area | Numeric maximum before conversion | real parquet regression |
| Missing/invalid area | Observed unavailable only | real parquet tests |
| Invalid dates/flows/duplicates | Only selected observed curve invalid | loader valid-simulation regression |
| Escaping paths / oversized upload | Bounded failure, no partial records | direct filesystem/limit tests |
| Canonical Omni child | Parent observation and area, own model sources | child lineage test |
| Roads | No observed overlay | scope test |

Input dimensions: on/off; hillslope/outlet; 0/1/2/5 model warm-up; linear/log;
multiple simulated scenarios and one observed population. Tests exercise the
changed combinations and representative states; no exhaustive cross-product claim.

## Error policy and artifact evidence

Expected optional absence is a no-op. Empty/unsupported records and missing area
explain unavailability. Malformed data and ownership/resource violations are
exceptional and isolated to observations under the canonical contract. No partial
curve is substituted for an invalid upload. Reload is the recovery after repair.

Intent: browser checks Show observed streamflow, switches source/years/axis.
Persisted input: real normalized observed.csv and totalwatsed3.parquet read without
mutation; retained hashes in validation.md. New intermediate/persistence: N/A,
reader-only feature. Consumed input: bootstrap records retain normalized dates,
flow and area. Execution: actual controller, loader and renderer in Chromium.
Result: 731 measured values, matching numerical oracle on both source plots,
with legend and keyboard values. Simulated query responses in this browser harness
are fixtures; no live app deployment or full authenticated dashboard claim.

## Findings

| ID | Severity | Finding | Remediation | Status |
| --- | --- | --- | --- | --- |
| COR-01 | Medium | Area MAX before conversion breaks LIST types and numeric-string ordering | Strict conversion before MAX, explicit BOOLEAN rejection, real parquet tests | Resolved |

Reviewer confirmed final closure after inspecting fix and new tests. Added loader
regression pairs invalid observations with a valid simulated curve. No remaining
blocking findings. Canonical checkpoint ancestry and independent review ordering
verified. Valid user states, safe rendering and preserved source ownership pass.

## Verdict

PASS: local implementation correctness. Unresolved High 0, Medium 0, Low 0.
Repository-wide validation results are recorded separately in validation.md.
Production deployment is outside this package. No project files, archive paths or
upload/model-fit workflows are changed, so no new writer/archive migration gate.
