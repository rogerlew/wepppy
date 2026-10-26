# Roads WBT flow-direction repair

Status: active 2026-10-26. Owner: Roger Lew. Implementer: Codex.

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

[ExecPlan](prompts/active/implementation_execplan.md) and [tracker](tracker.md).
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
