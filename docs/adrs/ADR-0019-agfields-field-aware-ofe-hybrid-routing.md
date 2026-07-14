# ADR-0019: AgFields Field-Aware OFE and Connectivity-Aware Hybrid Routing

Status: Proposed
Date: 2026-07-14

## Context

AgFields retains each field/hillslope intersection as an independent WEPP
sub-field run. ADR-0018 integrated those results through Concept 2: area-weighted
injection at the parent hillslope outlet followed by normal watershed/channel
routing. That implementation preserves per-sub-field source water and sediment
accounting, but it does not represent runon, deposition, or trapping between an
upslope field and the channel.

The Peridot connectivity inventory on
`/wc1/runs/sa/sacral-self-discipline` found that only 3,269 of 6,626 retained
sub-fields (49.3%) have direct channel drainage under the generated flowpath
boundary definition. The remaining 3,357 sub-fields make Concept 2's no-buffer
routing approximation less credible. The maintainer therefore reopened Concept 1
and requested a hybrid that chooses Concept 1 or Concept 2 per sub-field.

Concept 1 reduces the two-dimensional parent mosaic to ordered one-dimensional
overland flow elements (OFEs) along a representative hillslope. It can represent
water and sediment passing through downstream background/buffer OFEs, but only
when the mosaic has a defensible ordered-band approximation. Its candidate count,
fit tolerances, and residual-geometry rules change generated WEPP inputs and are
parameterization decisions governed by
`docs/standards/parameterization-adr-standard.md`.

## Decision

Expose three experimental routing schemes with independently composable outputs:

- `concept_1` / `concept-1`: field-aware hillslope routing through downstream
  OFEs.
- `concept_2` / `concept-2`: the accepted ADR-0018 area-weighted direct sub-field
  outlet injection.
- `hybrid` / `hybrid`: Concept 2 for channel-connected retained sub-fields and
  Concept 1 for all other retained sub-fields.

The UI offers those three schemes plus Run All using description-first labels.
Concept 2 remains the default for an omitted scheme so existing clients retain
their behavior. Run All expands to three independent, serially dependent jobs and
does not create an `all/` output root.

Use the existing Peridot classifier as the sole hybrid branch rule. A retained
sub-field is channel-connected when at least one generated per-cell flowpath has a
valid D8 successor outside that sub-field and the first outside cell is a channel.
When an explicit channel mask is supplied, its positive cells identify channels;
otherwise a SUBWTA identifier whose final decimal digit is `4` identifies a
channel. This classification is topology evidence, not a delivery ratio or buffer
efficiency estimate.

Plan Concept 1 at the parent level. All OFEs in one parent share one ordered set of
breakpoints. Each OFE is assigned either background or exactly one retained
sub-field source. The measured engineering planner gates are 1-20 OFEs, every
actual source represented, positive overlap between each field and its assigned
OFE, contiguous normalized breakpoints, and exact raster-cell area closure.
Assignment agreement, field/model area error, fragmentation, source-order
conflicts, and downstream-background error are persisted science diagnostics;
this ADR does not assign an undocumented acceptance threshold before Mariana's
evaluation. Ineligible parents fail explicitly; the runtime must not silently
reinterpret them or substitute Concept 2.

For a mixed hybrid parent, remove the connected sub-field cells from the Concept 1
geometry. Let `A_parent` be parent raster area, `A_connected_i` each connected
sub-field raster area, and `A_residual` the area represented by the residual
Concept 1 source:

```text
A_residual = A_parent - sum(A_connected_i)
A_residual + sum(A_connected_i) = A_parent
```

Generate and run the residual Concept 1 source at `A_residual`, then combine its
PASS with connected independent sub-field PASS sources using the ADR-0018 weighted
combiner. Adding connected sources to a full-area Concept 1 PASS is prohibited
because it double-counts area. Uniformly scaling an unchanged full-parent Concept
1 PASS to `A_residual` is also prohibited because it silently distorts the
remaining field/background geometry and nonlinear response.

The candidate search compares one-to-four equal bands, generalized contiguous
source runs, and a source-order partition, selecting first for complete source
representation/overlap and then for agreement and area fit. For a mixed hybrid,
the residual source keeps the full normalized parent profile positions and parent
length, excludes connected cells from assignment statistics, and sets width to
`A_residual / parent_length`.

The current WEPP input contract adds a second hard gate: the final structurally
deduplicated management may reference no more than 20 yearly scenarios. The
development-project census fails that gate for 141 Concept 1 and 59 hybrid
residual parents. Consequently this ADR remains Proposed and none of these
parameters may control a user-facing execution path until the decision owner
accepts either a separately validated WEPP binary-limit expansion or an explicit
revision to the all-parent fidelity contract.

The existing `sub_field_min_area_threshold_m2` remains the only small-field
retention threshold. Do not add a second hidden minimum-area filter.

## Decision Provenance

Decision Venue: Codex API conversation, 2026-07-14 08:37 PDT

Participants Present: Roger Lew, Codex

Decision Owner(s): Roger Lew, WEPPpy maintainer

Scientific Evaluator: Mariana Dobre

Implementer(s): Codex and WEPPpy/Peridot maintainers (planned)

## Change Summary

Previous behavior:

- One user-facing watershed integration scheme, Concept 2.
- A singular unscoped result at
  `wepp/ag_fields/watershed/{runs,output,manifest}`.
- Every retained sub-field delivered at its parent outlet.
- Concept 1 deferred.

Proposed behavior:

- Three independently runnable scheme roots plus a Run All UI action.
- Concept 1 reopened as a faithful field-aware OFE implementation.
- Hybrid branch selection uses the exact Peridot direct-channel classifier.
- Mixed parents conserve area through an explicit residual Concept 1 source plus
  connected Concept 2 sources.
- Concept 2 remains the omitted-value compatibility default.
- No fallback/delivery heuristic is introduced.

Measured Concept 1 parameter delta:

- maximum OFEs: 20;
- maximum native referenced yearly scenarios: 20;
- source representation: every source, with positive field/OFE overlap;
- geometric closure: exact in raster-cell area arithmetic;
- residual length: unchanged parent length, with width set from residual area;
  and
- fit/error measures: recorded diagnostics, not hidden engineering rejection
  thresholds pending science evaluation.

Feasibility disposition: blocked. The geometry gates pass for all 1,869 affected
Concept 1 parents and 1,644 hybrid residual parents in the designated project,
but management preflight passes only 1,728 Concept 1 parents (87.79% of affected
area) and 1,585 hybrid residual parents (94.53% of residual-parent area). No
numeric parameter may control wired behavior while the ADR status remains
Proposed.

## Rationale

Concept 2 has the best independent sub-field source fidelity and proven
water/sediment accounting, but bypasses downstream parent buffers. Concept 1 can
represent buffer interaction where the parent field mosaic has a defensible
one-dimensional ordering. The hybrid preserves Concept 2 where direct channel
drainage makes outlet injection most plausible and uses Concept 1 for the 50.7% of
dev-project sub-fields that do not meet that condition.

Keeping all three schemes makes the approximations explicit, preserves the
completed Concept 2 implementation, and gives Mariana comparable generated
outputs rather than forcing an engineering choice to stand in for science
evaluation.

## Alternatives Considered

1. Keep only Concept 2 - rejected because the connectivity census showed that
   3,357 retained sub-fields do not drain directly to a channel and therefore have
   the strongest unrepresented buffer-routing concern.
2. Replace Concept 2 with Concept 1 - rejected because Concept 1 is a lossy
   two-dimensional-to-one-dimensional abstraction and would discard the stronger
   independent-source fidelity where direct injection is defensible.
3. Choose one scheme per parent rather than per sub-field - rejected because mixed
   parents can contain both connected and non-connected sub-fields; parent-level
   classification would discard the requested topology distinction.
4. Inject connected sources on top of a complete Concept 1 parent - rejected
   because it double-counts represented area and mass sources.
5. Uniformly scale a complete Concept 1 parent to make room for connected sources -
   rejected because hillslope response is nonlinear and the scaling would alter
   non-connected/background geometry without modeling it.
6. Add an empirical delivery ratio or buffer-trapping correction - rejected
   because no calibrated parameter/evidence supports it and it would blur the
   physical meaning of both schemes.
7. Fall back silently to Concept 2 when a Concept 1 plan is ineligible - rejected
   because it would make the requested scheme and generated manifest scientifically
   ambiguous.

## Consequences

Users can run and compare routing approximations with labels that describe their
physical behavior. Current artifacts become scheme-composable, and legacy Concept
2 evidence remains preserved.

The implementation is substantially larger than the completed Concept 2 path. It
requires an OFE fit study, additive native segmentation, multi-OFE synthesis,
per-sub-field connectivity details, mixed-parent source composition, independent
state/RQ/UI behavior, and generated comparison evidence.

Concept 1 may reject arbitrary side-by-side or fragmented mosaics. Hybrid may also
reject a mixed parent when connected-cell removal does not leave a defensible
residual one-dimensional geometry. Explicit rejection reduces coverage but keeps
scheme semantics auditable.

The direct-channel classifier is deterministic and reusable, but does not prove
zero buffer effects or scientific suitability. All three schemes remain
experimental until Mariana records a science disposition.

The feasibility stop leaves Concept 2 as the only implemented user-facing
compatibility path. The planner, native slope kernel, and input-synthesis spike
are reusable substrate, but are not permission to expose partial Concept 1 or
hybrid coverage.

## Evidence

- [AgFields routing scheme suite work package](../work-packages/20260714_ag_fields_routing_scheme_suite/package.md)
- [Scheme artifact compatibility plan](../work-packages/20260714_ag_fields_routing_scheme_suite/artifacts/2026-07-14_scheme_artifact_compatibility_plan.md)
- [Concept 1 and hybrid feasibility evidence](../work-packages/20260714_ag_fields_routing_scheme_suite/artifacts/2026-07-14_concept1_feasibility.md)
- [AgFields flowpath-to-channel connectivity inventory](../work-packages/20260713_ag_fields_flowpath_channel_connectivity/package.md)
- [Completed Concept 2 implementation](../work-packages/20260713_ag_fields_concept2_watershed_integration/package.md)
- [ADR-0018 weighted PASS accounting](ADR-0018-agfields-weighted-pass-accounting.md)
- `/wc1/runs/sa/sacral-self-discipline` - designated generated-output project

Evidence still required for acceptance:

- a decision and implementation that resolves true `nmscen > 20` managements, or
  an owner-approved fidelity/coverage contract revision;
- remaining synthetic ordered, side-by-side, fragmented, tied-distance, buffer,
  and failure-mode fixtures;
- water/sediment closure and protected-tree inventory from all three generated
  scheme results; and
- Mariana's later science disposition (not an engineering merge gate unless she
  changes the parameter decision).

## Risk and Rollback Notes

Principal risks are poor Concept 1 coverage, geometric misclassification,
double-counted hybrid sources, management/OFE limits, memory pressure from Run All,
and users overinterpreting the classifier. The active ExecPlan requires an early
feasibility gate, serial RQ jobs, explicit manifests/reason codes, and
generated-output evidence.

Before user-facing cutover, rollback is removal/disablement of the new choices and
scheme-aware routes while retaining the completed Concept 2 route and historical
artifacts. After cutover, a safe rollback maps omitted/default behavior to Concept
2 and leaves existing scheme roots readable; it must not rewrite or delete results.

Triggers for reconsideration include unacceptable Concept 1 eligible-area
coverage, any unexplained source-area/water/sediment closure failure, residual
geometry that requires prohibited whole-parent scaling, or evidence that the
direct-channel definition does not match generated Peridot paths.

## Implementation Notes

- Execute
  `docs/work-packages/20260714_ag_fields_routing_scheme_suite/prompts/active/ag_fields_routing_scheme_suite_execplan.md`.
- Keep ADR-0018 unchanged for Concept 2 and weighted mixed-source arithmetic.
- Extend the Peridot classifier additively; do not duplicate its D8 logic in
  WEPPpy.
- Use fixed enum-to-slug mapping and scheme-specific safe clear roots.
- Update this ADR with exact measured parameters and decision provenance before
  changing its status to Accepted.
