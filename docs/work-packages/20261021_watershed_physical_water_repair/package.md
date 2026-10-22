# Watershed physical water repair

**Status**: Active execution, 2026-10-21.
**Authority**: Operator explicitly requested executing this package. Source repair
and local validation are authorized; release publication remains separate.

[Active ExecPlan](prompts/active/repair_execplan.md) · [Tracker](tracker.md) ·
[Acceptance matrix](artifacts/acceptance-matrix.md)

The [validated MC checkpoint](artifacts/mc-reference-checkpoint.md), native
`e6dc19008`, repairs source/publication interfaces and retained-state propagation
while preserving MC dynamics and numerical storage authority. Full native gates
and paired replays pass. Signed soil/channel exchange and clipping remain open;
this package is not complete or release-ready.

## Purpose and evidence

Repair four native defects found while tracing Ayush’s concerns about Dp,
lateral flow, ET and Q/QOFE through the last OFE and watershed routing. The
[completed audit](../20261021_watershed_physical_water_audit/artifacts/findings.md)
is committed at WEPPpy `e85d582ed`. Its eighteen 44-year watershed configurations
and targeted probes establish reproducible failures, not hydrologic certification.

| ID | Defect | Primary native source | Decisive baseline |
| --- | --- | --- | --- |
| WPA-01 | Channel-local net water omitted from inflow rates | `src/wshchr.for` | Positive local net input with zero lateral rate; daily publication and routed hydrograph disagree |
| WPA-02 | Flat source hydrograph under-delivers volume | `src/chrqin.for` | 900 m³ over 900 s delivers 600 m³ at a 600 s step |
| WPA-03 | Hourly infiltration remainder discarded | `src/watbal_hourly.for` | Measured 0.3303–1.6632 mm/year unallocated in controlled layouts |
| WPA-04 | Initial groundwater uses terminal OFE area | `src/contin.for` | Same 100 mm initial storage yields 40/16/20 m³ first-day baseflow across equal-total-area layouts |

## Scope and complexity budget

Execution repairs these four paths on the native remote-default branch,
with portable failing regressions, reviewed scientific contracts, one change
per experimental lane, and combined hillslope/PASS/watershed accounting.
Dp/ET remain local fluxes; internal surface/lateral transfers cancel by volume;
Dp recharge and subsequent groundwater exports must not be double-counted.
Ash is excluded. Closed audit and consumer packages remain immutable evidence.

Use existing Fortran routines, native tests, observation facilities and offline
readers. No new dependency, service, datastore, queue, privilege or runtime
protocol. Preserve PASS/WAT formats, event thresholds, calendar repairs, banner,
capacities, default executable selection and established interfaces. Changes
needed outside these bounds require a concrete failing case and explicit scope
disposition; unexplained rate/volume residuals block completion rather than
justify a general routing rewrite or relaxed tolerance.

## Scientific decisions and ADR gate

Formulas, cutoffs and area conversions will change. A parameterization ADR is
required before production edits are promoted; draft it during M1 and record
exact equations, volume/timing authority, alternatives, decision owner and
implementer. ADR-0101 records the accepted narrow contracts and the operator decision to preserve MC dynamics. Flat peak/volume/duration inconsistency, positive/negative channel-local
exchange, soil availability limits and groundwater state timing need explicit
contracts. No compensation through altered ET/Dp or balancing residual exports.

## Generated-artifact acceptance

Portable native regressions must fail on 261021 source and pass on the candidate.
Read fresh paired hillslope WAT and actual PASS, loaded channel quantities,
full native rate arrays, storage states, downstream transfers and final outlet.
Independently integrate the rates: a reported zero balance is not acceptance.
Retain complete dates, all contributing OFEs, input/output hashes, compiler,
source revision and the consumed filenames. Missing stores or incomplete runs
cannot silently pass. Validate diagnostics with deliberate ledger corruptions.

Mandatory gates use committed inputs or deterministic generators from committed
resources. The audit’s private `/wc1` donor cases remain supplementary; reduce
their failures to portable fixtures before making them required. Repeat all
available original audit configurations for the full 44 years, plus explicit
Gregorian century boundaries through year 400 and native regression/watchlist
fixtures. Do not shorten a failing run and label the shortened run decisive.

Physical routing acceptance must include independent storage/flux accounting
and channel rate-versus-publication agreement under justified numerical bounds.
Remaining discrepancies after these four patches must be investigated and
resolved or explicitly block the repaired-routing claim. Passing the four unit
regressions alone does not complete the package.

## Compatibility, release and recovery

Expected numerical changes must be attributed per defect and documented for
users; unchanged paths require parity. Historical outputs remain intact. A
future release must regenerate all contributing hillslope PASS files and
watershed outputs with one paired build, then refresh affected interchange/report
artifacts through supported workflows. Never mix repaired hillslope PASS with
an old watershed executable. The original no-overwrite restriction is superseded
only by the explicit reissue authorization below.

This package targets source repair and locally validated, release-ready candidate
builds. Dated release naming/vendoring, production deployment, default changes,
push and historical project repair are separate actions, not scaffold authority.
When release is authorized, use native release tooling and `wepp_runner/AGENTS.md`
gates, matching sidecars and changelogs. Record rollback as selection of the prior
paired release, preserving the candidate and its evidence.

## Review and security

Scientific/correctness and regression QA reviews are required during execution;
resolve all medium/high findings before closeout. Reviewers must distinguish
conservation from physical calibration and audited coverage from untested modes.
Security impact: low; no auth, network, permissions or service-boundary change.
Dedicated security review is not required unless that scope changes.

Health signals: recovered missing source volume, no discarded infiltration,
layout-independent initial groundwater, and coherent routed rates/volumes/storage.
Danger signals: peak/timing regressions, negative stores/rates, hidden clamping,
retuned event thresholds or error cancellation. No temporary fallback or guard
layer is planned; observe complete configured periods rather than a deployment
monitoring window in this local-repair phase.

## Highest claim and deliverables

Current highest claim: validated bounded soil/source/state/publication and
channel-plane repairs through source d354e3c99, with an MC-preserving continuity
audit and a complete 24-year paired Cedar comparison. The separate reissue
package records release gates and publication. Signed soil/routing acceptance
and complete watershed physical closure remain open.
Planned deliverables: ADR/contracts, portable regressions, four attributable
repairs, combined generated-output ledgers, independent reviews, and an operator
handoff recording supported geometries, remaining scientific limits and release
readiness. No field-calibration or universal watershed-validity claim is implied.

## MC authority decision

Preserve Muskingum-Cunge dynamics and its numerical storage meaning. The operator
rejected a change to geometric-volume authority and authorized the consistency
audit. Geometric mismatch alone is not an MC water-creation/loss finding.
See [current findings](artifacts/mc-continuity-findings.md) for the derivation,
actual cascade-transfer discrepancy and narrow interior-state correction.

## Authorized release handoff (2026-10-21)

The owner authorized replacing the undeployed `wepp_261021` pair with reviewed
source d354e3c99. The separate [reissue package](../20261021_wepp_261021_rerelease/package.md)
retains old identities, fresh release gates and the illustrated technical report.
This authorization does not close signed soil/routing acceptance, change MC
storage authority, switch defaults or authorize production deployment.
