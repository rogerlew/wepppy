# Roads WBT flow-direction repair

Status: closed 2026-10-26 (local implementation and isolated-environment validation). Owner: Roger Lew. Implementer: Codex.

## Problem and outcome

clogging-starch completed with 30 of 39 road segments. Five wrongly terminated
with invalid_flow_direction (three) or loop_detected (two) because Whitebox D8
values reached a TOPAZ-only native tracer. Temporary native-input conversion
made all five reach channels. Four other segments have NoData receiving
subcatchments and are outside this repair.

Implement the [canonical contract](../../schemas/roads-flow-direction-contract.md)
using native in-memory normalization, preserve the existing TOPAZ API, rebuild
and atomically refresh the py312 Roads extension, wire Roads to WBT, and validate
fresh generated outputs on an isolated site copy. No production deployment,
original-project mutation, new backend UI or hydrology changes.

Complexity budget: one native adapter option reusing Peridot, one caller keyword,
regressions, paired native artifact/provenance and documentation. No dependency,
service, queue, datastore, new filesystem artifact or runtime privilege.
Security impact: low; no new path handling, routes, auth, subprocess or queue
boundary. Dedicated security review is not required. Correctness review is.

## Execution and acceptance

[ExecPlan](prompts/completed/implementation_execplan.md) and [tracker](tracker.md).
Contract decision and independent reviews precede implementation in an ancestor
commit. Validation follows the generated-artifact standard: WBT raster -> native
trace -> Roads profile -> PASS -> watershed -> segment report/current receipt.
Source and baseline hashes must remain identical; do not infer success from job
status alone. Complete native tests, focused WEPPpy tests, broad suite and
independent correctness review before closing implementation.

Health: all five affected segments reach expected channels and appear in fresh
reports. Danger: encoding-dependent skips, changed original/baseline hashes,
missing report rows or native artifact mismatch. Observe through one complete
isolated run. No temporary mitigation requires retirement.

## Completed outcome

WEPPpy explicitly passes WBT to the native adapter. Native commit `71ec98a`
adds backward-compatible in-memory normalization and the paired py312 artifact.
Contract checkpoint `3a542d939` precedes implementation. Native 23 tests,
focused 108 and publication 14 pass. Broad coverage: all 11,947 collected nodes,
11,795 passes, 152 test skips plus one collection-module skip; no unresolved
failures. Independent correctness and science reviews PASS.

Fresh prepare/run of the actual site snapshot produces 35 completed segments,
including all five recovered traces, and only four NoData skips. Slope files,
PASS calendars, water/accounting tables, segment report rows, current receipt and
UI detail query data are directly verified. Source snapshot and baseline hashes
are unchanged. See [validation](artifacts/validation.md) and the retained reviews.

Historical full-project report coverage is explicitly stale; original simulation
results/provenance are preserved. A future report refresh must regenerate and
review the full design comparisons, not silently update source hashes. Production
deployment, service restart and original-project regeneration were not performed.
Deploy WEPPpy and the paired native artifact together before rerunning Roads.

## Related evidence and durable decisions

The normative encoding and compatibility decision is in
[Roads flow-direction contract](../../schemas/roads-flow-direction-contract.md),
sections Scope and decision and Compatibility and errors. Native API/provenance
are in wepppyo3 `docs/roads-flow-direction.md` and
`docs/roads-flow-direction-release-20261026.json`.

Reused existing lifecycle/current-receipt rules from
[Roads preparation lifecycle](../20261022_roads_preparation_lifecycle/package.md),
accounting checks from
[Roads accounting repair](../20261022_roads_accounting_repair/package.md),
and scientific evidence preservation from
[Roads validation suite](../20261023_roads_validation_suite/package.md).
These closed packages remain historical; their current contracts govern behavior.
This repair changes only pointer representation and caller wiring, not those
lifecycle, accounting or profile parameterization rules.
