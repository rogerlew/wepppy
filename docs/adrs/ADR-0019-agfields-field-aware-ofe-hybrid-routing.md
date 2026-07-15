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

The native slope serializer writes each OFE length to two decimal meters. The
post-write breakpoint check therefore compares reparsed cumulative fractions to
the fractions implied by those individually quantized lengths, with only a
`1e-12` floating-point comparison budget. It does not compare reparsed fractions
directly to the pre-serialization raster fractions: parent 94 proved that rule
impossible at 20 OFEs (maximum observed quantization delta `2.11e-5`). This is a
format-derived validation rule, not an additional scientific fit tolerance;
raster-cell area closure remains recorded against the unquantized plan.

The legacy PASS header writes modeled area as `.xxxxxE+xx`. Concept 1 therefore
checks PASS area against the area implied by the serialized slope with a relative
budget of `5e-5 * max(pass_area, serialized_area, 1 m2)`. The `5e-5` factor is
the maximum half-unit rounding budget of that five-decimal normalized mantissa
near 0.1; it is a file-format validation allowance, not a scientific area-fit
tolerance. The actual residual and budget are persisted per parent.

The WEPP hillslope management capacity is 32. The complete structurally
deduplicated corpus measured maxima of 24 yearly/surface scenarios, 21 operation
scenarios, 9 plant scenarios, 5 initial scenarios, and 20 OFEs. Capacity 32
retains eight yearly-scenario slots above the observed maximum. Forest `mxplan`,
`ntype`, and `ntype2` and the WEPPpy final-write guard agree at 32; the independent
Concept 1 planner limit remains 20 OFEs. A 33-scenario boundary fixture is
rejected explicitly. New `ag-fields.cfg` projects select the uniquely named
`wepp_260714` family; persisted projects must explicitly select that family before
Concept 1 or hybrid execution.

Watershed integration uses at most 16 workers. An omitted `max_workers` selects
the smaller of host CPU count and 16; an explicit value outside 1-16 is rejected
at the API, RQ worker, and integrator boundaries rather than silently clamped.
The same bound is forwarded to every hillslope interchange process pool. This is
an operational availability limit, not a scientific routing parameter. It was
set after the first full Concept 1 generation reached 60,502,848 KiB peak RSS
because the interchange layer independently expanded to host CPU count despite
the integrator's 16-worker bound.

The exact release hillslope binary completed all 1,869 Concept 1 and 1,644 hybrid
residual parent runs for 17/17 years without capacity, parse, invalid-input,
non-finite, invalid-producer, signal, or timeout failures. The p1857
zero-surface-disturbance numerical fault was fixed at the forest model boundary
with ablation evidence; no AgFields management source was coerced. This clears the
capacity/corpus gate, but the ADR remains Proposed until the scheme-aware NoDb,
hybrid, RQ/API, UI, and generated three-scheme paths satisfy the remaining
acceptance evidence.

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
- The current routing package also owns the synchronized forest hillslope
  management-capacity increase and full Concept 1/hybrid corpus validation.
- Capacity/parser defects are fixed in forest; objectively invalid source values
  are rejected or canonically normalized at authoritative AgFields ingest; and
  finite-input numerical producer failures require forest ablation evidence.

Measured Concept 1 parameter delta:

- maximum OFEs: 20;
- synchronized hillslope management capacity: 32;
- watershed integration and hillslope interchange worker ceiling: 16;
- measured maximum referenced yearly/surface scenarios: 24;
- source representation: every source, with positive field/OFE overlap;
- geometric closure: exact in raster-cell area arithmetic;
- residual length: unchanged parent length, with width set from residual area;
  and
- fit/error measures: recorded diagnostics, not hidden engineering rejection
  thresholds pending science evaluation.

Feasibility disposition: implementation continues. The geometry gates pass for
all 1,869 affected Concept 1 parents and 1,644 hybrid residual parents in the
designated project. All corresponding generated managements serialize, reparse,
and execute under the accepted capacity of 32. No numeric parameter may control
wired user behavior while the ADR status remains Proposed.

The synchronized binary capacity exceeds the unchanged 20-OFE Concept 1 planner
limit; extra binary capacity does not authorize more routed OFEs.

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

Concept 2 remains the only implemented user-facing compatibility path while the
expanded capacity/corpus milestone executes. The planner, native slope kernel,
input-synthesis spike, or a partially passing corpus are not permission to expose
partial Concept 1 or hybrid coverage.

## Evidence

- [AgFields routing scheme suite work package](../work-packages/20260714_ag_fields_routing_scheme_suite/package.md)
- [Scheme artifact compatibility plan](../work-packages/20260714_ag_fields_routing_scheme_suite/artifacts/2026-07-14_scheme_artifact_compatibility_plan.md)
- [Concept 1 and hybrid feasibility evidence](../work-packages/20260714_ag_fields_routing_scheme_suite/artifacts/2026-07-14_concept1_feasibility.md)
- [Management capacity and corpus validation plan](../work-packages/20260714_ag_fields_routing_scheme_suite/artifacts/2026-07-14_management_capacity_and_corpus_validation_plan.md)
- [Management capacity and corpus results](../work-packages/20260714_ag_fields_routing_scheme_suite/artifacts/2026-07-14_management_capacity_corpus_results.md)
- [AgFields flowpath-to-channel connectivity inventory](../work-packages/20260713_ag_fields_flowpath_channel_connectivity/package.md)
- [Completed Concept 2 implementation](../work-packages/20260713_ag_fields_concept2_watershed_integration/package.md)
- [ADR-0018 weighted PASS accounting](ADR-0018-agfields-weighted-pass-accounting.md)
- `/wc1/runs/sa/sacral-self-discipline` - designated generated-output project

Evidence still required for acceptance:

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
- Execute its integrated Milestone 2B against
  `/workdir/wepp-forest_260430_baseline`; preserve the initial detached dirty
  source/binary state and diagnose in an isolated build copy first.
- Do not silently clamp management inputs or disable floating-point traps. Apply
  canonical input validation at AgFields ingest and use the forest ablation
  protocol for finite-input model-state failures.
- Keep ADR-0018 unchanged for Concept 2 and weighted mixed-source arithmetic.
- Extend the Peridot classifier additively; do not duplicate its D8 logic in
  WEPPpy.
- Use fixed enum-to-slug mapping and scheme-specific safe clear roots.
- Update this ADR with exact measured parameters and decision provenance before
  changing its status to Accepted.
