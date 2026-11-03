# Revised Roads sensitivity protocol

Status: declared design, pending independent science review; no native calls yet.
Authority: [adjudication contract](../../../schemas/roads-parameterization-adjudication-contract.md).
This is bounded characterization of existing production controls, not default
selection or calibration. Historical failed candidates remain failed.

## Decision and scope

Determine whether road width, fill length/slope and traffic have observable,
interpretable effects through current production builders. Detect aliases and
cross-role effects before choosing the configuration layout. Reuse
`tests/roads/roads_matrix.py`, owned native readers and production segment summary.
Add tested orchestration/reporting in `tests/roads/roads_sensitivity.py`; no second
parameter formula, production persistence, application wiring or UI is introduced.

The first lane uses production legacy-template soils and committed deterministic
site climate (2000–2015). It is deliberately separate from conditioned generated
U12 `erosion_road_cap` research. Retained generated outunrut seed soil ordering
cannot be silently combined with canonical (landuse, road, fill) preparation:
its retained soil records are bare/bare/forest while canonical role composition
is forest/bare/bare. Preserve those histories and investigate their scope separately.
No generated-soil adoption follows from this lane. The six reserved materials
1718472, 53975, 1718476, 665770, 2711196 and 658566 are not used.

## Fixed panel and contrasts

All profiles use the committed median geometry and the fixture's exact shared
runtime sidecars. Four contexts are selected before new execution from the
historical committed matrix; that publication is stale and supplies sampling
context only, not current r7 outcomes or truth:

| Context | Texture | Surface | Traffic | Arrangement | Historical mean annual export kg |
| --- | --- | --- | --- | --- | ---: |
| H | silt | gravel | none | rutted | 91.10967745994182 |
| L | sand | paved | none | rutted | 0.49505905903268516 |
| P | loam | gravel | low | rutted | canonical one-factor reference |
| U | silt | paved | high | unrutted_three | 23.593472820103866 |

H/L ensure contrasting export magnitude; P is the previously passing canonical
physical-check reference, not field validation or a legacy-agreement success
claim. U exercises role reordering and geometry parity. Distinct executable soil,
management and slope signatures are counted; four labels are not four independent
material observations.

Each context runs baseline; width 2 and 8 m (baseline 4); fill length 10 and 60 m
(baseline 30); fill slope 2 and 30 percent (baseline 10); the other two traffic
states; and width 8 m plus fill length 60 m. This is exactly 40 native calls.
The width/fill interaction is the difference of the combined response and the
sum of its one-factor response differences. It is diagnostic and may reflect
changed modeled area, runoff supply or native coupling; it is not a new physical law.
No surface, texture, climate or buffer geometry change occurs within a contrast.
Inslope bare/rocked direct/buffer arrangements receive preparation-only checks
for fill no-ops and traffic aliases (12 preparations, no native invocation).

Existing canonical geometry parity/clamping is preserved and recorded. Raw
requested width does not equal emitted unrutted width. Profile area changes are
reported beside intensive and extensive responses. Bounds are existing validator
limits; tested contrast ranges are not field-calibrated or recommended ranges.

## Evidence and execution gates

Before execution bind the exact declaration, helpers, production builders,
fixtures, native reader libraries, and installed r7 binaries. Require watershed
SHA256 `4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825`
and hill SHA256 `210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936`.
Selected native source is `e0abe0581f77c6f66917e90daf8f8f429e9315c8` in the release
checkout `/workdir/wepp-forest-release-20261009`; release HEAD `547b9e7eb` is
checked separately. Use a new exclusive disposable root under
`/wc1/runs/ro/roads-parameterization-program-20261103/` and retain every failed
attempt. Never replace frozen source manifests or prior outputs.

Read requested -> effective -> emitted geometry and soil/management semantics.
Prove native geometry consumption with emitted slopes and WAT OFE areas; bind
native input/management consumer source paths for traffic semantics. Retain
full daily PASS/WAT and event ELEMENT/EBE tables, all seven raw outputs, annual
segment-summary water/sediment metrics, yearly/event response tables and per-role
boundary fluxes. Report numeric/calendar/negative-flux findings without widening
tolerances. Any numerical flag remains explicit and requires a source-supported
disposition before accepting the affected proposed control.

Reproduce actual native runtime markers; retain all sidecars. Input and source
hashes must remain unchanged during execution. Retain requested/effective values,
clipping and no-op/alias diagnostics. Expected response directions are hypotheses,
not assertions. Compare full artifacts, not only process success.

A separate disposable current-project lane uses fresh public-controller
preparation/execution and source/baseline preservation. Its protocol and receipts
are linked before execution. It does not imply browser/RQ/deployment parity.

After the first batch, review information gain and defects before any additional
calls. No full840 sweep is planned. The static configuration proposal may use
only supported characterized controls; explicit human specification/layout
approval remains required before production implementation.

## Compatible generated underprediction lane

Add seven calls using the exact retained r7 seed
`engine-seeds-v3/cases/underprediction_other_geometry/modern/r7`:
Denver, MUKEY 2711184, rutted, gravel, high traffic. This road/fill/buffer
ordering is compatible with canonical rutted preparation. The conditioned source
has bare/bare/forest OFEs. Its original mean annual export is 0.08712 kg/year,
a retained legacy-underpredicting context, not evidence of measured inaccuracy.

First rerun the frozen capsule and require all seven outputs identical. Then
write a canonical slope baseline with width 3.96 m, road length 60.96 m/grade 4%,
fill length 4.57 m/grade 50%, buffer length 39.62 m/grade 25%. The canonical
writer emits aspect 180 degrees instead of the benchmark's 100 degrees and uses
its own precision. Report this bridge response separately; do not attribute it
to width/fill sensitivity. Hold exact soil, management, climate and runtime
sidecars fixed. Against that canonical baseline, run width 2/8 m, fill length
10/60 m, and combined width 8 m/fill 60 m. These are five geometry contrasts,
not new soil parameterization. Total declared calls become 47.

The old outunrut benchmark represents transformed road/fill/buffer, confirmed by
its management scenario assignments. Its soil ordering is internally consistent;
it differs from current production upstream-landuse/road/fill topology. That
comparison limitation does not establish a production role-assignment defect.
Never splice those capsules into the current canonical topology without a
separately declared physical representation change.

## Runner receipts

The study runner invokes the pinned installed watershed binary directly with the
canonical run deck, matching retained research execution and preserving stdout,
stderr, return code and all seven outputs. There is no automatic retry. The
production controller lane separately uses its normal runner. The inherited
fixture `execution-identity.json` remains an explicitly historical fixture-input
receipt (including its 260409 identity); the new declaration and each prepared
record bind the actual 261029 binary. The frozen fixture metadata is unchanged.

The adapter reuses unchanged reviewed physical water/sediment accounting, full
calendar and strict EVENT particle auditors. Their complete role-wise water
transfers, signed sediment exchanges, bounds and flags are retained in
`audits.json`, alongside production summary and native event/daily Parquet tables.
Any postexecution reader failure gets an explicit failure receipt with complete
raw artifacts preserved. No missing row or failed case is omitted from the
planned denominator.

The release checkout is host-visible but not mounted inside the development
container. The four selected native consumer files were therefore copied from
`git show e0abe0581:src/<name>` only after byte equality with the release checkout
was verified. Their hashes and release HEAD are retained in
`revised-sensitivity-native-source-v1/source-receipt.json` beside the study root.
The declaration binds that snapshot; no alternate native binary is built or used.
The first attempted declaration failed before creating a study root because the
container could not read the checkout. No native call occurred. The subsequent
47-profile preparation succeeded. An additive declaration v2 binds final reviewer
fixes to receipt metadata, duplicate-calendar rejection and report analysis before
execution; it preserves all prepared inputs and the original declaration.
