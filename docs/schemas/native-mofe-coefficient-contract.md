# Native MOFE coefficient ownership contract

Status: MIPA-02 implemented at native `b581352b6`; bounded ownership and PMET
conformance validated. Final local revision 6 release verification is recorded in
the release evidence. Specialized 9005/RAP native acceptance remains HOLD.

## Scope and authority

The operator requested a contract-first implementation repair, reconciliation of
producer/consumer discrepancies and revision of the undeployed `wepp_261029`
release on 2026-11-02. This contract governs plant coefficient indexing and
per-element soil-water coefficients. Existing parameter values, retention policy,
activation, fallback semantics, output formats and default executable selections
remain unchanged. Revision 6 must preserve earlier reports and evidence.

## PMET identity and capacity

`ncrop` counts plant definitions; `nowcrp` identifies a current management slot.
The current plant definition is `itype(nowcrp,iplane)`. All consumers of `kcb` and
`rawp`, including any enabled adapters, must use that mapped definition. Table
row numbers and OFE numbers are not substitutes. Both COMMON arrays must hold
all `ntype` entries accepted by the selected reader, for named and first-row
fallback assignments alike. `mxcrop` is a separate crop-slot bound.

The release source already uses `ntype` for PMET arrays (32 hill, 15000 watershed)
and direct EVAPPM mapping; the abandoned kernelized checkout's six-entry arrays
and adapter mismatch do not establish defects in this release. Verify selected
source and binary provenance and exercise capacity and crop transitions before
closing NATIVE-01/02. Do not invent a universal producer six-crop cap.

Eight-character crop tokens and existing first-row fallback remain compatible.
Generated model-ready tables must cover all staged plant definitions under the
MOFE input identity contract. Absent optional PMET state keeps native behavior;
present-empty tables have no model-ready claim. Existing reader failures remain
failures; no new validation is implied. In particular, unmatched rows are read
for their names without validating all numeric fields. This repair does not
redesign reader errors or fallback policy.

## FC and HK ownership

FC is the field-capacity water depth above the dry reference, in meters. HK is
the unsaturated conductivity exponent. Both belong to `(layer, OFE)`, just as
`st`, `ul`, `thetfc`, `thetdr` and `dg` do. Initializing or processing another OFE
must not overwrite their values. Every active producer and consumer must preserve
this identity: daily/hourly water balance, PURK, PERC, DRAIN, lateral conductivity
and tile-drain thresholds. Unequal layer counts must not expose another element's
values in overlapping layers or uninitialized values in non-overlapping layers.

Preserve the existing initialization schedule and arithmetic:
`fc = dg * (thetfc - thetdr)` and guarded `hk = -2.655 / log10(fc / ul)`.
The existing nonpositive-ratio branch remains zero; no new clipping, threshold,
retention curve, tillage refresh, density update or fallback is authorized.
Later changes to other soil state do not silently introduce a new coefficient
refresh policy. Document and test that distinction. COMMON layout changes require
clean rebuilding every translation unit and the matched executable pair.

## Acceptance and compatibility

Retain failing-before evidence and compare distinct-material and repeated-material
controls, both retention policies, daily/hourly paths, unequal layers, actual
PURK FC operands and sub-0.95 PERC HK power execution. Test drainage/lateral
consumers directly when a whole-model case does not activate them. Observation
must leave ordinary output bytes unchanged. Bind every observation to source,
inputs and executable hashes. Quantify changes in runoff, drainage, storage and
ET; coefficient differences alone are not hydrograph changes or field validation.
Guard activation, later tillage/density and missing-density cases require explicit
dispositions; unexecuted behavior must not be called validated.

Before vendoring revision 6, run native smoke/watchlist/pytest/artifact-policy gates
from the canonical default-branch release checkout, using committed fixtures or
committed deterministic generators. The older `/workdir/wepp-forest` worktree is
not the release source. Rebuild with system gfortran and the canonical dated
builder, preserving revision-5 bytes first. Validate exact final matched binaries
through WEPPpy selection, preparation, native execution and output readers,
including distinct PMET coefficients and a crop transition. Reconcile the soil/cover
support matrix explicitly: current 261029 lacks the specialized 9005/revegetation
reader, misbinds its extended header and reads the restrictive-layer record twice.
It must not be labeled 9005-compatible based on a successful generic soil read.
The release also lacks the specialized `cancov.txt`/per-OFE `.cov` readers.
SOIL-02/9005 and COVER-01 native acceptance stay HOLD until a capable consumer is bound and
validated; adding that reader/behavior requires its own contract amendment and
review before implementation. A separate compatible-engine requirement is valid
only when the selected engine and actual prepared deck are shown compatible. Preserve real input/output manifests and independent reviews.

Existing saved runs are unchanged; regenerated histories may change because they
now consume their own coefficients. Never mix old hill passes with the new
watershed build. Only matched Linux `wepp_261029` artifacts and revision-6 release
notes are included. No deployment, Windows release, default switch, bulk project
regeneration or installed Rust replacement is authorized. Unrelated scientific
limitations from revision 5 remain explicit. A bounded ownership correction does
not establish unrestricted scientific validity or erase retained failure counts.
